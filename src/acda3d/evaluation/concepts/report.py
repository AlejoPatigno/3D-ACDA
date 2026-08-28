"""Report orchestration and output management for concept evaluation."""

from __future__ import annotations

import base64
import csv
import ctypes
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import time
import uuid
from collections.abc import Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from .anatomy import compute_all_anatomy
from .class_profiles import compute_binary_class_profiles, compute_binary_source_label_support
from .fidelity import compute_all_fidelity
from .figures import (
    plot_anatomy_consistency_roi_heatmap,
    plot_class_conditional_profiles,
    plot_concept_fidelity_roi_heatmap,
    plot_head_agreement_matrix,
    plot_roi_stability_heatmap,
)
from .provenance import validate_binary_concept_compatibility
from .schemas import (
    BINARY_CONCEPT_CLASS_ORDER,
    BINARY_CONCEPT_TASK_ID,
    CheckpointPolicy,
    Direction,
    MethodId,
)


@dataclass(frozen=True)
class ConceptEvaluationPlan:
    """Complete plan for concept evaluation output."""
    evaluation_identity: str
    analysis_mode: str
    methods: tuple[MethodId, ...]
    directions: tuple[Direction, ...]
    checkpoint_policies: tuple[CheckpointPolicy, ...]
    intended_relative_paths: tuple[str, ...]


@dataclass(frozen=True)
class PublicationPathBudget:
    verified_path_units: int
    verified_component_units: int

    def __post_init__(self) -> None:
        if min(self.verified_path_units, self.verified_component_units) <= 0:
            raise ValueError("verified path budgets must be positive")


_PUBLICATION_PROBE_OPERATIONS = (
    "create", "journal", "validate", "rename", "rollback", "read",
)


@dataclass(frozen=True)
class PublicationProbeResult:
    """Measured target-volume capability for one publication grammar."""

    budget: PublicationPathBudget
    operations: tuple[str, ...]
    path_units: Mapping[str, int]
    component_units: Mapping[str, int]

    def __post_init__(self) -> None:
        if self.operations != _PUBLICATION_PROBE_OPERATIONS:
            raise ValueError("publication probe operations are incomplete or reordered")
        if set(self.path_units) != set(self.operations):
            raise ValueError("publication probe path measurements are incomplete")
        if set(self.component_units) != set(self.operations):
            raise ValueError("publication probe component measurements are incomplete")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in (*self.path_units.values(), *self.component_units.values())
        ):
            raise ValueError("publication probe measurements must be positive integers")


@dataclass(frozen=True)
class PublicationNames:
    final_path: Path
    sibling_path: Path
    journal_path: Path
    backup_path: Path
    identity_token: str
    attempt_token: str
    collision_token: str | None
    canonical_identity_sha256: str


@dataclass(frozen=True)
class PreparedPublication:
    names: PublicationNames
    journal_path: Path
    capability: bytes
    canonical_relative_path: str | None = None
    owner_token: str | None = None
    expected_manifest_hash: str | None = None
    state: str = "prepared"

    @property
    def final_path(self) -> Path:
        return self.names.final_path

    @property
    def sibling_path(self) -> Path:
        return self.names.sibling_path


_PUBLICATION_SCHEMA_VERSION = "1.0"
_PUBLICATION_PROTOCOL_VERSION = "1.0"
_PUBLICATION_ROLE = "concept-output"
_CAPABILITY_BYTES = 32


@dataclass(frozen=True)
class CooperativeReaderPolicy:
    """Explicit finite retry policy for a cooperating canonical-path reader."""

    max_attempts: int
    delay_seconds: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or self.max_attempts <= 0
        ):
            raise ValueError("reader max_attempts must be a positive integer")
        if (
            isinstance(self.delay_seconds, bool)
            or not isinstance(self.delay_seconds, (int, float))
            or not np.isfinite(self.delay_seconds)
            or self.delay_seconds < 0
        ):
            raise ValueError("reader delay_seconds must be finite and non-negative")


@dataclass(frozen=True)
class CooperativeReadResult:
    """Typed result that distinguishes an available value from temporary absence."""

    status: str
    final_path: Path
    attempts: int
    value: Any = None
    reason: str | None = None


@contextmanager
def _posix_publication_lock(path: Path, *, exclusive: bool):
    try:
        import fcntl
    except ImportError as error:  # pragma: no cover - platform-specific branch
        raise RuntimeError("POSIX advisory locking is unavailable") from error

    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        raise RuntimeError(f"publication lock file cannot be opened: {error}") from error
    try:
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        try:
            fcntl.flock(descriptor, operation)
        except OSError as error:
            raise RuntimeError(f"POSIX publication locking failed: {error}") from error
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


@contextmanager
def _windows_publication_lock(path: Path, *, exclusive: bool):
    """Use Win32 byte-range locking; thread locks are not a fallback."""
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle_type = wintypes.HANDLE
    invalid_handle = handle_type(-1).value
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, handle_type,
    ]
    kernel32.CreateFileW.restype = handle_type
    kernel32.CloseHandle.argtypes = [handle_type]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.LockFileEx.argtypes = [
        handle_type, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD, ctypes.c_void_p,
    ]
    kernel32.LockFileEx.restype = wintypes.BOOL
    kernel32.UnlockFileEx.argtypes = [
        handle_type, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        ctypes.c_void_p,
    ]
    kernel32.UnlockFileEx.restype = wintypes.BOOL

    class _Overlapped(ctypes.Structure):
        _fields_ = [
            ("Internal", ctypes.c_void_p),
            ("InternalHigh", ctypes.c_void_p),
            ("Offset", wintypes.DWORD),
            ("OffsetHigh", wintypes.DWORD),
            ("hEvent", handle_type),
        ]

    desired_access = 0x80000000 | 0x40000000  # GENERIC_READ | GENERIC_WRITE
    share_mode = 0x00000001 | 0x00000002 | 0x00000004  # read/write/delete
    handle = kernel32.CreateFileW(
        str(path), desired_access, share_mode, None, 4, 0x00000080, None
    )
    if handle == invalid_handle:
        error = ctypes.get_last_error()
        raise RuntimeError(f"Win32 publication lock file cannot be opened: {error}")

    overlapped = _Overlapped()
    flags = 0x00000002 if exclusive else 0  # LOCKFILE_EXCLUSIVE_LOCK
    try:
        if not kernel32.LockFileEx(handle, flags, 0, 1, 0, ctypes.byref(overlapped)):
            error = ctypes.get_last_error()
            raise RuntimeError(f"Win32 publication locking failed: {error}")
        try:
            yield
        finally:
            if not kernel32.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(overlapped)):
                error = ctypes.get_last_error()
                raise RuntimeError(f"Win32 publication unlock failed: {error}")
    finally:
        kernel32.CloseHandle(handle)


@contextmanager
def _publication_file_lock(parent: Path, output_name: str, *, exclusive: bool):
    parent = Path(parent).absolute()
    if not output_name or Path(output_name).name != output_name:
        raise ValueError("publication lock output name must be a single path component")
    path = parent / f".{output_name}.publisher.lock"
    if path.is_symlink() or _is_reparse_point(path):
        raise RuntimeError("publication lock path is a reparse point")
    if os.name == "nt":
        with _windows_publication_lock(path, exclusive=exclusive):
            yield
    else:
        with _posix_publication_lock(path, exclusive=exclusive):
            yield


@contextmanager
def _publisher_lock(parent: Path, output_name: str):
    """Acquire a cross-process exclusive publisher lock, failing closed."""
    final = Path(parent).absolute() / output_name
    backup = final.parent / f".{output_name}.backup.unknown"
    owner = {"pid": os.getpid(), "token": uuid.uuid4().hex}
    lock = _publication_file_lock(parent, output_name, exclusive=True)
    try:
        lock.__enter__()
    except Exception as error:
        raise PublicationBlocked(
            f"publisher lock capability unavailable: {error}",
            reason="publisher_lock_unavailable",
            final_path=final,
            candidate_path=final,
            backup_path=backup,
        ) from error
    try:
        yield owner
    finally:
        lock.__exit__(None, None, None)


@contextmanager
def _reader_lock(parent: Path, output_name: str):
    """Acquire the same-parent shared lock used by cooperating readers."""
    final = Path(parent).absolute() / output_name
    backup = final.parent / f".{output_name}.backup.unknown"
    lock = _publication_file_lock(parent, output_name, exclusive=False)
    try:
        lock.__enter__()
    except Exception as error:
        raise PublicationBlocked(
            f"reader lock capability unavailable: {error}",
            reason="reader_lock_unavailable",
            final_path=final,
            candidate_path=final,
            backup_path=backup,
        ) from error
    try:
        yield
    finally:
        lock.__exit__(None, None, None)


def read_cooperative_publication(
    final_path: str | Path,
    *,
    policy: CooperativeReaderPolicy,
    reader: Any = Path.read_bytes,
    sleep: Any = time.sleep,
) -> CooperativeReadResult:
    """Read only the canonical final path under the shared publication lock.

    Absence is retried only under the caller-supplied finite policy. It is never
    converted into an empty value, and sibling/backup entries are not examined.
    """
    if not isinstance(policy, CooperativeReaderPolicy):
        raise ValueError("reader policy is required and must be explicit")
    final = Path(final_path).absolute()
    for attempt in range(1, policy.max_attempts + 1):
        absent = False
        with _reader_lock(final.parent, final.name):
            if final.is_symlink():
                return CooperativeReadResult(
                    "unavailable", final, attempt, reason="canonical_final_ambiguous"
                )
            if not final.exists():
                absent = True
            else:
                try:
                    value = reader(final)
                except FileNotFoundError:
                    absent = True
                else:
                    return CooperativeReadResult("available", final, attempt, value=value)
        if not absent:
            raise AssertionError("reader attempt ended without a result")
        if attempt < policy.max_attempts:
            sleep(policy.delay_seconds)
    return CooperativeReadResult(
        "unavailable", final, policy.max_attempts, reason="canonical_final_absent"
    )


def _is_reparse_point(path: Path) -> bool:
    """Fail closed for Windows reparse points, including junctions."""
    junction_check = getattr(path, "is_junction", None)
    if callable(junction_check):
        try:
            if junction_check():
                return True
        except FileNotFoundError:
            pass
        except OSError:
            return True
    if os.name != "nt":
        return False
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    attributes = getattr(metadata, "st_file_attributes", None)
    if isinstance(attributes, bool) or not isinstance(attributes, int):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _candidate_file_identifiers(path: Path) -> dict[str, int]:
    """Bind the validated candidate to an independent filesystem identity."""
    try:
        metadata = os.lstat(path)
    except OSError as error:
        raise ValueError("candidate file identity is unreadable") from error
    device = getattr(metadata, "st_dev", None)
    inode = getattr(metadata, "st_ino", None)
    if (
        isinstance(device, bool) or not isinstance(device, int)
        or isinstance(inode, bool) or not isinstance(inode, int)
        or device < 0 or inode < 0
    ):
        raise ValueError("candidate file identity is incomplete")
    return {"device": device, "inode": inode}


def _durable_parent_directory(parent: Path) -> None:
    """Durably persist a directory entry, surfacing every failure."""
    if os.name == "nt":
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle_type = wintypes.HANDLE
        invalid_handle = handle_type(-1).value
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, handle_type,
        ]
        kernel32.CreateFileW.restype = handle_type
        kernel32.FlushFileBuffers.argtypes = [handle_type]
        kernel32.FlushFileBuffers.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [handle_type]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateFileW(
            str(parent), 0xC0000000, 0x00000001 | 0x00000002 | 0x00000004,
            None, 3, 0x02000000, None,
        )
        if handle == invalid_handle:
            error = ctypes.get_last_error()
            raise OSError(error, f"parent-directory durability open failed: {parent}")
        try:
            if not kernel32.FlushFileBuffers(handle):
                error = ctypes.get_last_error()
                raise OSError(error, f"parent-directory durability flush failed: {parent}")
        finally:
            kernel32.CloseHandle(handle)
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(parent, flags)
    except OSError as error:
        raise OSError(f"parent-directory durability is unavailable: {error}") from error
    try:
        os.fsync(descriptor)
    except OSError as error:
        raise OSError(f"parent-directory durability failed: {error}") from error
    finally:
        os.close(descriptor)


def _durable_file(path: Path) -> None:
    """Durably persist one authenticated file or directory."""
    if path.is_symlink():
        raise OSError("cannot durably sync a symbolic link")
    if os.name == "nt" and path.is_dir():
        _durable_parent_directory(path)
        return
    flags = os.O_RDONLY if path.is_dir() else os.O_RDWR
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if path.is_dir() and hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise OSError(f"durability open failed for {path}: {error}") from error
    try:
        os.fsync(descriptor)
    except OSError as error:
        raise OSError(f"durability fsync failed for {path}: {error}") from error
    finally:
        os.close(descriptor)


def _durable_tree(root: Path) -> None:
    """Sync an authenticated tree bottom-up and then its containing directory."""
    if root.is_symlink() or not root.is_dir():
        raise OSError("durability tree root is not an owned directory")
    for path in sorted(root.rglob("*"), key=lambda item: (item.is_dir(), str(item)), reverse=False):
        if path.is_symlink() or not path.exists():
            raise OSError(f"durability tree contains an ambiguous entry: {path}")
        _durable_file(path)
    _durable_file(root)
    _durable_parent_directory(root.parent)


def _windows_query_owner_only_acl(path: Path) -> str:
    """Return the protected owner-rights DACL as SDDL using Win32 only."""
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    security_descriptor = ctypes.c_void_p()
    get_named_security_info = advapi32.GetNamedSecurityInfoW
    get_named_security_info.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    get_named_security_info.restype = wintypes.DWORD
    error = get_named_security_info(
        str(path), 1, 0x00000004, None, None, None, None,
        ctypes.byref(security_descriptor),
    )
    if error:
        raise OSError(int(error), "GetNamedSecurityInfoW failed")
    try:
        convert = advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW
        convert.argtypes = [
            ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD),
        ]
        convert.restype = wintypes.BOOL
        text = wintypes.LPWSTR()
        length = wintypes.DWORD()
        if not convert(security_descriptor, 1, 0x00000004, ctypes.byref(text), ctypes.byref(length)):
            raise OSError(ctypes.get_last_error(), "ConvertSecurityDescriptorToStringSecurityDescriptorW failed")
        try:
            return text.value or ""
        finally:
            kernel32.LocalFree(text)
    finally:
        kernel32.LocalFree(security_descriptor)


def _windows_owner_sid(path: Path) -> str:
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    owner = ctypes.c_void_p()
    descriptor = ctypes.c_void_p()
    get_named_security_info = advapi32.GetNamedSecurityInfoW
    get_named_security_info.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    get_named_security_info.restype = wintypes.DWORD
    error = get_named_security_info(
        str(path), 1, 0x00000001, ctypes.byref(owner), None, None, None,
        ctypes.byref(descriptor),
    )
    if error:
        raise OSError(int(error), "GetNamedSecurityInfoW owner query failed")
    try:
        convert = advapi32.ConvertSidToStringSidW
        convert.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        convert.restype = wintypes.BOOL
        text = wintypes.LPWSTR()
        if not convert(owner, ctypes.byref(text)):
            raise OSError(ctypes.get_last_error(), "ConvertSidToStringSidW failed")
        try:
            return text.value or ""
        finally:
            kernel32.LocalFree(text)
    finally:
        kernel32.LocalFree(descriptor)


def _windows_set_owner_only_acl(path: Path) -> None:
    """Set a protected DACL granting full control only to the current owner."""
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    owner_sid = _windows_owner_sid(path)
    if not re.fullmatch(r"S-[0-9]+(?:-[0-9]+)+", owner_sid):
        raise OSError("owner SID is invalid")
    descriptor = ctypes.c_void_p()
    convert = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.DWORD),
    ]
    convert.restype = wintypes.BOOL
    if not convert(f"D:P(A;;FA;;;{owner_sid})", 1, ctypes.byref(descriptor), None):
        raise OSError(ctypes.get_last_error(), "owner-only ACL construction failed")
    try:
        dacl = ctypes.c_void_p()
        present = wintypes.BOOL()
        defaulted = wintypes.BOOL()
        get_dacl = advapi32.GetSecurityDescriptorDacl
        get_dacl.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.BOOL),
        ]
        get_dacl.restype = wintypes.BOOL
        if not get_dacl(descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)):
            raise OSError(ctypes.get_last_error(), "GetSecurityDescriptorDacl failed")
        set_named_security_info = advapi32.SetNamedSecurityInfoW
        set_named_security_info.argtypes = [
            wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ]
        set_named_security_info.restype = wintypes.DWORD
        error = set_named_security_info(
            str(path), 1, 0x80000004, None, None, dacl, None
        )
        if error:
            raise OSError(int(error), "SetNamedSecurityInfoW failed")
    finally:
        kernel32.LocalFree(descriptor)


def _verify_owner_only_acl(path: Path) -> None:
    if os.name == "nt":
        acl = _windows_query_owner_only_acl(path)
        normalized = re.sub(r"\\s+", "", acl)
        if not re.fullmatch(r"D:P(?:AI)?\(A;;FA;;;S-[0-9]+(?:-[0-9]+)+\)", normalized):
            raise OSError("owner-only ACL verification failed")
        return
    expected_mode = 0o700 if path.is_dir() else 0o600
    if stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode) != expected_mode:
        raise OSError("owner-only mode verification failed")


def _ensure_owner_only_acl(path: Path) -> None:
    """Apply and verify the platform's owner-only protection seam."""
    if os.name == "nt":
        _windows_set_owner_only_acl(path)
    else:
        os.chmod(path, 0o700 if path.is_dir() else 0o600)
    _verify_owner_only_acl(path)


def _verify_candidate_tree_acl(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise OSError("candidate tree root is not an owned directory")
    for path in (root, *root.rglob("*")):
        if path.is_symlink() or not path.exists():
            raise OSError(f"candidate tree ACL target is ambiguous: {path}")
        _verify_owner_only_acl(path)


def _windows_create_owner_only_file(path: Path) -> int:
    """Create an empty owner-only file before any journal bytes are available."""
    from ctypes import wintypes

    class _SecurityAttributes(ctypes.Structure):
        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", wintypes.BOOL),
        ]

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # The existing parent is the owner authority for the new same-parent journal.
    owner_sid = _windows_owner_sid(path.parent)
    descriptor = ctypes.c_void_p()
    convert = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.DWORD),
    ]
    convert.restype = wintypes.BOOL
    if not convert(
        f"D:P(A;;FA;;;{owner_sid})", 1, ctypes.byref(descriptor), None
    ):
        raise OSError(
            ctypes.get_last_error(),
            "owner-only ACL construction failed before journal creation",
        )
    attributes = _SecurityAttributes(
        ctypes.sizeof(_SecurityAttributes), descriptor, 0
    )
    handle_type = wintypes.HANDLE
    invalid_handle = handle_type(-1).value
    create = kernel32.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(_SecurityAttributes), wintypes.DWORD, wintypes.DWORD,
        handle_type,
    ]
    create.restype = handle_type
    handle = create(
        str(path), 0x40000000, 0x00000001 | 0x00000002 | 0x00000004,
        ctypes.byref(attributes), 1, 0x00000080, None,
    )
    kernel32.LocalFree(descriptor)
    if handle == invalid_handle:
        raise OSError(ctypes.get_last_error(), "owner-only journal creation failed")
    try:
        # Reassert the create-time descriptor and query it before any journal bytes.
        _ensure_owner_only_acl(path)
        import msvcrt
        flags = os.O_RDWR | getattr(os, "O_BINARY", 0)
        descriptor_fd = msvcrt.open_osfhandle(handle, flags)
        handle = invalid_handle
        return descriptor_fd
    finally:
        if handle != invalid_handle:
            kernel32.CloseHandle(handle)


class PublicationBlocked(OSError):
    """Structured fail-closed result for an ambiguous publication boundary."""

    status = "BLOCKED"

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        final_path: Path,
        candidate_path: Path,
        backup_path: Path,
        rollback_succeeded: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.final_path = final_path
        self.candidate_path = candidate_path
        self.backup_path = backup_path
        self.rollback_succeeded = rollback_succeeded


def _publication_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(key): _publication_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_publication_value(item) for item in value]
    return getattr(value, "value", str(value))


def serialize_canonical_publication_identity(
    plan: ConceptEvaluationPlan, canonical_relative_path: str
) -> bytes:
    if not _safe_relative_path(canonical_relative_path):
        raise ValueError("canonical relative path is unsafe")
    payload = {
        "schema_version": _PUBLICATION_SCHEMA_VERSION,
        "protocol_version": _PUBLICATION_PROTOCOL_VERSION,
        "evaluation_identity": plan.evaluation_identity,
        "analysis_mode": plan.analysis_mode,
        "canonical_relative_path": canonical_relative_path,
        "methods": [_publication_value(item) for item in plan.methods],
        "directions": [_publication_value(item) for item in plan.directions],
        "checkpoint_policies": [
            getattr(item, "logical_checkpoint", _publication_value(item))
            for item in plan.checkpoint_policies
        ],
        "intended_relative_paths": list(plan.intended_relative_paths),
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _base36(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("base36 values must be non-negative integers")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    digits = []
    while value:
        value, remainder = divmod(value, 36)
        digits.append(alphabet[remainder])
    return "".join(reversed(digits))


def _publication_candidate_names(
    parent: Path, final_name: str, identity_token: str, attempt_token: str,
    collision: int,
) -> tuple[str, str, str]:
    collision_suffix = "" if collision == 0 else f".c{_base36(collision)}"
    sibling = f"p3dco.{_PUBLICATION_ROLE}.{identity_token}.{attempt_token}{collision_suffix}.tmp"
    journal = f".{sibling}.journal"
    backup = f".{final_name}.backup.{attempt_token}{collision_suffix}"
    return sibling, journal, backup


def _path_fits(path: Path, budget: PublicationPathBudget) -> bool:
    return (
        _utf16_units(str(path)) <= budget.verified_path_units
        and _utf16_units(path.name) <= budget.verified_component_units
    )


def _publication_paths_fit(names: PublicationNames, budget: PublicationPathBudget) -> bool:
    return all(
        _path_fits(path, budget)
        for path in (
            names.final_path,
            names.sibling_path,
            names.journal_path,
            names.backup_path,
        )
    )


def _candidate_fits(parent: Path, names: tuple[str, str, str], budget: PublicationPathBudget) -> bool:
    parent_units = _utf16_units(str(parent))
    for name in (names[0], names[1], names[2]):
        if parent_units + 1 + _utf16_units(name) > budget.verified_path_units:
            return False
        if _utf16_units(name) > budget.verified_component_units:
            return False
    return True


def _derived_identity_token(
    digest_text: str,
    parent: Path,
    final_name: str,
    attempt_token: str,
    collision: int,
    budget: PublicationPathBudget,
) -> tuple[str, int]:
    """Fit only the sibling identity representation to the measured grammar budget."""
    overhead_names = _publication_candidate_names(
        parent, final_name, "", attempt_token, collision
    )
    remaining = min(
        budget.verified_component_units - max(_utf16_units(name) for name in overhead_names),
        budget.verified_path_units - _utf16_units(str(parent)) - 1
        - max(_utf16_units(name) for name in overhead_names),
    )
    token_length = min(len(digest_text), remaining)
    if token_length <= 0:
        raise ValueError("publication path budget cannot fit canonical transaction identity representation")
    return digest_text[:token_length], token_length


def derive_publication_names(
    final_path: str | Path,
    plan: ConceptEvaluationPlan,
    canonical_relative_path: str,
    *,
    attempt: int,
    existing_names: Sequence[str] = (),
    budget: PublicationPathBudget,
) -> PublicationNames:
    final = Path(final_path)
    if not final.name or final.name in {".", ".."}:
        raise ValueError("final output path must have a name")
    parent = final.parent.absolute()
    final = parent / final.name
    if not _safe_relative_path(canonical_relative_path):
        raise ValueError("canonical relative path is unsafe")
    serialized = serialize_canonical_publication_identity(plan, canonical_relative_path)
    digest = hashlib.sha256(serialized).digest()
    digest_text = base64.b32encode(digest).decode("ascii").rstrip("=").lower()
    attempt_token = _base36(attempt)
    occupied = {str(name).casefold() for name in existing_names}
    for collision in range(len(occupied) + 2):
        identity_token, _ = _derived_identity_token(
            digest_text, parent, final.name, attempt_token, collision, budget
        )
        names = _publication_candidate_names(
            parent, final.name, identity_token, attempt_token, collision
        )
        candidate = PublicationNames(
            final, parent / names[0], parent / names[1], parent / names[2],
            identity_token, attempt_token,
            None if collision == 0 else _base36(collision),
            hashlib.sha256(serialized).hexdigest(),
        )
        if not _candidate_fits(parent, names, budget) or not _publication_paths_fit(candidate, budget):
            raise ValueError("publication path budget cannot fit transaction grammar")
        if not any(name.casefold() in occupied for name in names):
            return candidate
    raise ValueError("publication collision budget exhausted")


def _probe_publication_names(
    final: Path,
    plan: ConceptEvaluationPlan,
    canonical_relative_path: str,
    existing_names: Sequence[str],
    budget: PublicationPathBudget,
) -> PublicationNames:
    serialized = serialize_canonical_publication_identity(plan, canonical_relative_path)
    digest_text = base64.b32encode(hashlib.sha256(serialized).digest()).decode("ascii").rstrip("=").lower()
    occupied = {str(name).casefold() for name in existing_names}
    for collision in range(len(occupied) + 2):
        attempt_token = _base36(1)
        identity_token, _ = _derived_identity_token(
            digest_text,
            final.parent,
            final.name,
            attempt_token,
            collision,
            budget,
        )
        sibling, journal, backup = _publication_candidate_names(
            final.parent, final.name, identity_token, attempt_token, collision
        )
        if any(name.casefold() in occupied for name in (sibling, journal, backup)):
            continue
        return PublicationNames(
            final,
            final.parent / sibling,
            final.parent / journal,
            final.parent / backup,
            identity_token,
            attempt_token,
            None if collision == 0 else _base36(collision),
            hashlib.sha256(serialized).hexdigest(),
        )
    raise ValueError("publication probe collision budget exhausted")


def _windows_component_limit(parent: Path) -> int:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_volume_information = kernel32.GetVolumeInformationW
    get_volume_information.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD,
    ]
    get_volume_information.restype = wintypes.BOOL
    volume_name = ctypes.create_unicode_buffer(261)
    serial_number = wintypes.DWORD()
    maximum_component_length = wintypes.DWORD()
    filesystem_flags = wintypes.DWORD()
    filesystem_name = ctypes.create_unicode_buffer(261)
    volume_root = Path(parent).anchor or str(parent)
    if not get_volume_information(
        volume_root, volume_name, len(volume_name), ctypes.byref(serial_number),
        ctypes.byref(maximum_component_length), ctypes.byref(filesystem_flags),
        filesystem_name, len(filesystem_name),
    ):
        error = ctypes.get_last_error()
        raise OSError(error, "GetVolumeInformationW failed")
    if maximum_component_length.value <= 0:
        raise OSError("volume reported no component capability")
    return int(maximum_component_length.value)


def _probe_budget(parent: Path) -> PublicationPathBudget:
    final_path = parent / "canonical-output"
    try:
        if os.name == "nt":
            component_units = _windows_component_limit(parent)
            path_units = _utf16_units(str(parent)) + 1 + component_units
        else:
            path_units = int(os.pathconf(str(parent), "PC_PATH_MAX"))
            component_units = int(os.pathconf(str(parent), "PC_NAME_MAX"))
    except (AttributeError, OSError, ValueError, TypeError) as error:
        raise PublicationBlocked(
            f"publication path capability is unavailable: {error}",
            reason="path_capability_unavailable",
            final_path=final_path,
            candidate_path=final_path,
            backup_path=parent / ".canonical-output.backup.unknown",
        ) from error
    try:
        return PublicationPathBudget(path_units, component_units)
    except ValueError as error:
        raise PublicationBlocked(
            f"publication path capability is invalid: {error}",
            reason="path_capability_unavailable",
            final_path=final_path,
            candidate_path=final_path,
            backup_path=parent / ".canonical-output.backup.unknown",
        ) from error


def probe_publication_operations(
    final_path: str | Path,
    plan: ConceptEvaluationPlan,
    canonical_relative_path: str,
) -> PublicationProbeResult:
    """Probe the exact publication grammar on the target parent and volume."""
    final = Path(final_path).absolute()
    parent = final.parent
    try:
        parent_stat = parent.stat()
        budget = _probe_budget(parent)
        names = _probe_publication_names(
            final, plan, canonical_relative_path,
            tuple(entry.name for entry in parent.iterdir()), budget,
        )
        if not _publication_paths_fit(names, budget):
            raise PublicationBlocked(
                "publication grammar exceeds the measured target path capability",
                reason="path_budget_unavailable",
                final_path=names.final_path,
                candidate_path=names.sibling_path,
                backup_path=names.backup_path,
            )
    except PublicationBlocked:
        raise
    except (OSError, ValueError) as error:
        raise PublicationBlocked(
            f"publication target cannot establish probe capability: {error}",
            reason="path_capability_unavailable",
            final_path=final,
            candidate_path=final,
            backup_path=parent / f".{final.name}.backup.unknown",
        ) from error

    operation_paths = {
        "create": (names.sibling_path,),
        "journal": (names.journal_path,),
        "validate": (names.sibling_path, names.journal_path),
        "rename": (names.final_path, names.backup_path, names.sibling_path),
        "rollback": (names.final_path, names.sibling_path, names.backup_path),
        "read": (names.final_path,),
    }
    path_units = {
        operation: max(_utf16_units(str(path)) for path in paths)
        for operation, paths in operation_paths.items()
    }
    component_units = {
        operation: max(_utf16_units(path.name) for path in paths)
        for operation, paths in operation_paths.items()
    }
    probe_root = Path(tempfile.mkdtemp(prefix=".p3dco-probe-", dir=str(parent)))
    probe_final = probe_root / names.final_path.name
    probe_sibling = probe_root / names.sibling_path.name
    probe_journal = probe_root / names.journal_path.name
    probe_backup = probe_root / names.backup_path.name
    owned_entries = (probe_final, probe_sibling, probe_journal, probe_backup)
    try:
        if probe_root.stat().st_dev != parent_stat.st_dev:
            raise OSError("publication probe namespace is not same-volume")
        probe_final.mkdir()
        with probe_journal.open("xb") as stream:
            stream.write(b"publication-probe\n")
            stream.flush()
            os.fsync(stream.fileno())
        probe_sibling.mkdir()
        if (
            probe_final.is_symlink()
            or not probe_final.is_dir()
            or probe_sibling.is_symlink()
            or not probe_sibling.is_dir()
            or not probe_journal.is_file()
        ):
            raise OSError("publication probe validation failed")
        probe_journal.read_bytes()
        os.replace(probe_final, probe_backup)
        os.replace(probe_sibling, probe_final)
        probe_final.stat()
        tuple(probe_final.iterdir())
        os.replace(probe_final, probe_sibling)
        os.replace(probe_backup, probe_final)
        probe_final.stat()
        tuple(probe_final.iterdir())
    except (OSError, UnicodeError, ValueError) as error:
        raise PublicationBlocked(
            f"publication operation capability is unavailable: {error}",
            reason="publication_operation_unavailable",
            final_path=names.final_path,
            candidate_path=names.sibling_path,
            backup_path=names.backup_path,
        ) from error
    finally:
        cleanup_error = None
        for path in owned_entries:
            try:
                if path.is_symlink() or path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            except FileNotFoundError:
                continue
            except OSError as error:
                cleanup_error = error
        try:
            probe_root.rmdir()
        except FileNotFoundError:
            pass
        except OSError as error:
            cleanup_error = cleanup_error or error
        if cleanup_error is not None:
            raise PublicationBlocked(
                f"publication probe cleanup failed: {cleanup_error}",
                reason="publication_operation_unavailable",
                final_path=names.final_path,
                candidate_path=names.sibling_path,
                backup_path=names.backup_path,
            ) from cleanup_error
    if parent_stat.st_dev != parent.stat().st_dev:
        raise PublicationBlocked(
            "publication target volume changed during capability probe",
            reason="same_volume_probe_failed",
            final_path=names.final_path,
            candidate_path=names.sibling_path,
            backup_path=names.backup_path,
        )
    verified_budget = PublicationPathBudget(
        max(path_units.values()), max(component_units.values())
    )
    return PublicationProbeResult(
        verified_budget, _PUBLICATION_PROBE_OPERATIONS, path_units, component_units
    )


def request_publication_capability(provider: Any = os.urandom) -> bytes:
    try:
        capability = provider(_CAPABILITY_BYTES)
    except Exception as error:
        raise ValueError("OS CSPRNG capability is unavailable") from error
    if not isinstance(capability, (bytes, bytearray)) or len(capability) != _CAPABILITY_BYTES:
        raise ValueError("OS CSPRNG capability must return exactly 32 bytes")
    return bytes(capability)


def _write_prepared_journal(path: Path, payload: bytes) -> None:
    if os.name == "nt":
        descriptor = _windows_create_owner_only_file(path)
    else:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = os.open(path, flags, 0o600)
    try:
        if os.name != "nt" and hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if os.name == "nt":
        _verify_owner_only_acl(path)
    else:
        _ensure_owner_only_acl(path)
    _durable_file(path)
    _durable_parent_directory(path.parent)


def prepare_publication_transaction(
    final_path: str | Path,
    plan: ConceptEvaluationPlan,
    canonical_relative_path: str,
    *,
    attempt: int,
    owner_token: str,
    expected_manifest_hash: str,
    budget: PublicationPathBudget,
    capability_provider: Any = os.urandom,
) -> PreparedPublication:
    if not isinstance(owner_token, str) or not owner_token:
        raise ValueError("owner token is required")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_hash):
        raise ValueError("expected manifest hash must be a lowercase SHA-256 digest")
    final = Path(final_path)
    names = derive_publication_names(
        final, plan, canonical_relative_path, attempt=attempt,
        existing_names=tuple(entry.name for entry in final.parent.iterdir()), budget=budget,
    )
    capability = request_publication_capability(capability_provider)
    parent_stat = names.final_path.parent.stat()
    final_present = names.final_path.exists() or names.final_path.is_symlink()
    final_stat = names.final_path.stat() if final_present else parent_stat
    final_ids = _candidate_file_identifiers(names.final_path) if final_present else None
    journal = {
        "schema_version": _PUBLICATION_SCHEMA_VERSION,
        "protocol_version": _PUBLICATION_PROTOCOL_VERSION,
        "state": "prepared",
        "owner_token": owner_token,
        "attempt_token": names.attempt_token,
        "collision_token": names.collision_token,
        "role": _PUBLICATION_ROLE,
        "canonical_relative_path": canonical_relative_path,
        "canonical_identity_sha256": names.canonical_identity_sha256,
        "identity_token_length": len(names.identity_token),
        "sibling_name": names.sibling_path.name,
        "final_name": names.final_path.name,
        "backup_name": names.backup_path.name,
        "expected_manifest_hash": expected_manifest_hash,
        "capability_hex": capability.hex(),
        "same_volume_file_identifiers": {
            "parent_device": parent_stat.st_dev, "final_device": final_stat.st_dev,
        },
        "final_present": final_present,
        "final_file_identifiers": final_ids,
        "type_mode": {"expected_type": "directory", "final_mode": final_stat.st_mode},
    }
    payload = (json.dumps(journal, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    try:
        _write_prepared_journal(names.journal_path, payload)
    except PublicationBlocked:
        raise
    except Exception as error:
        raise PublicationBlocked(
            f"journal preparation blocked before publication: {error}",
            reason="journal_acl_or_durability_failed",
            final_path=names.final_path,
            candidate_path=names.sibling_path,
            backup_path=names.backup_path,
        ) from error
    return PreparedPublication(
        names,
        names.journal_path,
        capability,
        canonical_relative_path,
        owner_token,
        expected_manifest_hash,
    )


def _read_publication_journal(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("journal provenance is not an owned file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("journal provenance is unreadable") from error
    if not isinstance(payload, Mapping):
        raise ValueError("journal provenance is not an object")
    return dict(payload)


def _validate_prepared_publication(
    publication: PreparedPublication,
    plan: ConceptEvaluationPlan,
    artifacts: Mapping[str, bytes],
    *,
    required_state: str = "prepared",
) -> dict[str, Any]:
    names = publication.names
    if publication.state != required_state:
        raise ValueError(f"journal state is not {required_state}")
    if (
        publication.canonical_relative_path is None
        or publication.owner_token is None
        or publication.expected_manifest_hash is None
    ):
        raise ValueError("journal provenance is incomplete")
    if not _safe_relative_path(publication.canonical_relative_path):
        raise ValueError("journal canonical path is unsafe")
    if set(artifacts) != set(plan.intended_relative_paths):
        raise ValueError("artifacts must exactly match the evaluation plan")
    if any(not _safe_relative_path(path) for path in artifacts):
        raise ValueError("artifacts contain an unsafe path")
    manifest_payload = artifacts.get("evaluation_manifest.json")
    if not isinstance(manifest_payload, bytes):
        raise ValueError("artifacts must include evaluation_manifest.json")
    if hashlib.sha256(manifest_payload).hexdigest() != publication.expected_manifest_hash:
        raise ValueError("candidate manifest hash does not match prepared journal")

    journal = _read_publication_journal(publication.journal_path)
    expected = {
        "schema_version": _PUBLICATION_SCHEMA_VERSION,
        "protocol_version": _PUBLICATION_PROTOCOL_VERSION,
        "state": required_state,
        "owner_token": publication.owner_token,
        "attempt_token": names.attempt_token,
        "collision_token": names.collision_token,
        "role": _PUBLICATION_ROLE,
        "canonical_relative_path": publication.canonical_relative_path,
        "canonical_identity_sha256": names.canonical_identity_sha256,
        "identity_token_length": len(names.identity_token),
        "sibling_name": names.sibling_path.name,
        "final_name": names.final_path.name,
        "backup_name": names.backup_path.name,
        "expected_manifest_hash": publication.expected_manifest_hash,
    }
    if any(journal.get(key) != value for key, value in expected.items()):
        raise ValueError("journal identity or grammar binding mismatch")
    if journal.get("capability_hex") != publication.capability.hex():
        raise ValueError("journal capability binding mismatch")
    try:
        capability = bytes.fromhex(str(journal["capability_hex"]))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("journal capability is invalid") from error
    if capability != publication.capability or len(capability) != _CAPABILITY_BYTES:
        raise ValueError("journal capability binding mismatch")
    identity = hashlib.sha256(
        serialize_canonical_publication_identity(
            plan, publication.canonical_relative_path
        )
    ).hexdigest()
    if identity != names.canonical_identity_sha256:
        raise ValueError("journal canonical identity mismatch")

    parent = names.final_path.parent
    if any(path.parent != parent for path in (names.sibling_path, names.journal_path)):
        raise ValueError("journal and sibling are not in the final parent")
    if names.journal_path.name != f".{names.sibling_path.name}.journal":
        raise ValueError("journal grammar binding mismatch")
    parent_stat = parent.stat()
    final_stat = names.final_path.stat() if names.final_path.exists() else parent_stat
    volume_ids = journal.get("same_volume_file_identifiers")
    if not isinstance(volume_ids, Mapping):
        raise ValueError("journal volume binding is missing")
    if (
        volume_ids.get("parent_device") != parent_stat.st_dev
        or volume_ids.get("final_device") != final_stat.st_dev
    ):
        raise ValueError("journal volume binding mismatch")
    type_mode = journal.get("type_mode")
    if not isinstance(type_mode, Mapping) or type_mode.get("expected_type") != "directory":
        raise ValueError("journal type binding mismatch")
    final_present = journal.get("final_present")
    final_ids = journal.get("final_file_identifiers")
    if not isinstance(final_present, bool):
        raise ValueError("journal final presence binding is missing")
    final_exists = names.final_path.exists() or names.final_path.is_symlink()
    if final_present:
        if not isinstance(final_ids, Mapping):
            raise ValueError("journal final identity binding is missing")
        if final_exists:
            current_ids = _candidate_file_identifiers(names.final_path)
            if dict(final_ids) != current_ids:
                raise ValueError("journal final identity binding mismatch")
    elif final_ids is not None or final_exists:
        raise ValueError("journal final presence binding mismatch")
    if (
        final_present
        and (names.final_path.exists() or names.final_path.is_symlink())
        and type_mode.get("final_mode") != final_stat.st_mode
    ):
        raise ValueError("journal final mode binding mismatch")
    return journal


def _write_validated_journal(path: Path, journal: Mapping[str, Any]) -> None:
    payload = (json.dumps(dict(journal), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    flags = os.O_WRONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        os.ftruncate(descriptor, 0)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("journal state transition made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _ensure_owner_only_acl(path)
    _durable_file(path)
    _durable_parent_directory(path.parent)


def _durably_mark_aborted(
    publication: PreparedPublication,
    journal: Mapping[str, Any],
    reason: str,
) -> None:
    aborted = dict(journal)
    aborted["state"] = "aborted"
    aborted["abort_reason"] = str(reason)[:512]
    try:
        _write_validated_journal(publication.journal_path, aborted)
    except Exception as error:
        raise OSError(f"aborted journal state could not be persisted: {error}") from error


def create_validated_publication_sibling(
    publication: PreparedPublication,
    plan: ConceptEvaluationPlan,
    artifacts: Mapping[str, bytes],
    *,
    writer: Any = None,
) -> PreparedPublication:
    """Create, fully validate, and durably mark an owned publication sibling.

    This is deliberately limited to the pre-promotion transaction boundary. It
    never renames, replaces, removes, or adopts the canonical final path or a
    foreign collision entry.
    """
    journal = _validate_prepared_publication(publication, plan, artifacts)
    sibling = publication.sibling_path
    parent = publication.final_path.parent
    try:
        try:
            sibling.mkdir()
        except FileExistsError as error:
            raise ValueError("publication sibling collision was preserved") from error
        if sibling.is_symlink() or _is_reparse_point(sibling) or not sibling.is_dir():
            raise ValueError("publication sibling is not an owned directory")
        if sibling.parent != parent or sibling.stat().st_dev != parent.stat().st_dev:
            raise ValueError("publication sibling volume binding mismatch")
        _ensure_owner_only_acl(sibling)

        write = writer or _default_output_writer
        ordered_paths = [
            path for path in plan.intended_relative_paths
            if path != "evaluation_manifest.json"
        ]
        if "evaluation_manifest.json" in plan.intended_relative_paths:
            ordered_paths.append("evaluation_manifest.json")
        for relative_path in ordered_paths:
            write(sibling / relative_path, artifacts[relative_path])

        try:
            _validate_allowlisted_tree(sibling, set(plan.intended_relative_paths))
        except RuntimeError as error:
            raise ValueError(f"candidate output validation failed: {error}") from error
        for path in (sibling, *sibling.rglob("*")):
            if path.is_symlink() or not path.exists():
                raise ValueError(f"candidate tree contains an ambiguous entry: {path}")
            _ensure_owner_only_acl(path)
        _verify_candidate_tree_acl(sibling)
        manifest_hash = hashlib.sha256(
            (sibling / "evaluation_manifest.json").read_bytes()
        ).hexdigest()
        if manifest_hash != publication.expected_manifest_hash:
            raise ValueError("candidate manifest hash diverged")
        try:
            verify_completed_output(sibling, expected_identity=plan.evaluation_identity)
        except (OSError, ValueError) as error:
            raise ValueError(f"candidate output validation failed: {error}") from error
        _durable_tree(sibling)

        journal = _validate_prepared_publication(publication, plan, artifacts)
        journal["candidate_file_identifiers"] = _candidate_file_identifiers(sibling)
        type_mode = journal["type_mode"]
        if not isinstance(type_mode, Mapping):
            raise ValueError("candidate type binding is incomplete")
        journal["type_mode"] = {
            **type_mode,
            "candidate_mode": sibling.stat().st_mode,
        }
        journal["state"] = "validated"
        _write_validated_journal(publication.journal_path, journal)
    except Exception as error:
        try:
            _durably_mark_aborted(publication, journal, str(error))
        except Exception as abort_error:
            raise PublicationBlocked(
                f"candidate publication failed and aborted state was not durable: {abort_error}",
                reason="candidate_abort_durability_failed",
                final_path=publication.final_path,
                candidate_path=sibling,
                backup_path=publication.names.backup_path,
            ) from error
        if isinstance(error, ValueError):
            raise
        raise PublicationBlocked(
            f"candidate publication blocked at a durability boundary: {error}",
            reason="candidate_durability_failed",
            final_path=publication.final_path,
            candidate_path=sibling,
            backup_path=publication.names.backup_path,
        ) from error
    return PreparedPublication(
        publication.names,
        publication.journal_path,
        publication.capability,
        publication.canonical_relative_path,
        publication.owner_token,
        publication.expected_manifest_hash,
        "validated",
    )


def _validate_validated_publication(
    publication: PreparedPublication,
    plan: ConceptEvaluationPlan,
    *,
    recovery: bool = False,
) -> dict[str, Any]:
    sibling = publication.sibling_path
    if sibling.is_symlink() or _is_reparse_point(sibling) or not sibling.is_dir():
        raise PublicationBlocked(
            "validated publication sibling is missing or ambiguous",
            reason="candidate_not_authenticated",
            final_path=publication.final_path,
            candidate_path=sibling,
            backup_path=publication.names.backup_path,
        )
    try:
        _verify_candidate_tree_acl(sibling)
        candidate_artifacts = {
            relative_path: (sibling / relative_path).read_bytes()
            for relative_path in plan.intended_relative_paths
        }
        journal = _validate_prepared_publication(
            publication, plan, candidate_artifacts, required_state="validated"
        )
        type_mode = journal.get("type_mode")
        if not isinstance(type_mode, Mapping) or type_mode.get("expected_type") != "directory":
            raise ValueError("candidate type binding mismatch")
        if (
            isinstance(type_mode.get("candidate_mode"), bool)
            or not isinstance(type_mode.get("candidate_mode"), int)
            or type_mode["candidate_mode"] != sibling.stat().st_mode
        ):
            raise ValueError("candidate mode binding mismatch")
        candidate_ids = journal.get("candidate_file_identifiers")
        current_ids = _candidate_file_identifiers(sibling)
        if (
            not isinstance(candidate_ids, Mapping)
            or candidate_ids.get("device") != current_ids["device"]
            or candidate_ids.get("inode") != current_ids["inode"]
        ):
            raise ValueError("candidate file identity binding mismatch")
        verify_completed_output(sibling, expected_identity=plan.evaluation_identity)
    except (OSError, ValueError) as error:
        raise PublicationBlocked(
            f"validated publication sibling is not authenticated: {error}",
            reason="candidate_validation_failed",
            final_path=publication.final_path,
            candidate_path=sibling,
            backup_path=publication.names.backup_path,
        ) from error

    final = publication.final_path
    parent = final.parent
    backup = publication.names.backup_path
    if any(path.parent != parent for path in (sibling, publication.journal_path, backup)):
        raise PublicationBlocked(
            "publication entries are not same-parent",
            reason="same_parent_binding_failed",
            final_path=final,
            candidate_path=sibling,
            backup_path=backup,
        )
    if backup.exists() or backup.is_symlink():
        raise PublicationBlocked(
            "authenticated backup path is occupied by a foreign entry",
            reason="backup_collision",
            final_path=final,
            candidate_path=sibling,
            backup_path=backup,
        )
    if final.is_symlink():
        raise PublicationBlocked(
            "existing final is ambiguous and was not modified",
            reason="invalid_final",
            final_path=final,
            candidate_path=sibling,
            backup_path=backup,
        )
    if final.exists():
        try:
            if not final.is_dir() or final.stat().st_dev != parent.stat().st_dev:
                raise ValueError("existing final is not a same-volume directory")
            verify_completed_output(final)
        except (OSError, ValueError) as error:
            raise PublicationBlocked(
                f"existing final is invalid and was not modified: {error}",
                reason="invalid_final",
                final_path=final,
                candidate_path=sibling,
                backup_path=backup,
            ) from error
    return journal


_PUBLICATION_CANDIDATE_RE = re.compile(
    r"^p3dco\.concept-output\.(?P<identity>[a-z2-7]+)\.(?P<attempt>[0-9a-z]+)"
    r"(?:\.c(?P<collision>[0-9a-z]+))?\.tmp$"
)
_PUBLICATION_JOURNAL_RE = re.compile(
    r"^\.(?P<sibling>p3dco\.concept-output\.[a-z2-7]+\.[0-9a-z]+"
    r"(?:\.c[0-9a-z]+)?\.tmp)\.journal$"
)


def _parse_base36_token(token: str) -> int:
    if not token or any(character not in "0123456789abcdefghijklmnopqrstuvwxyz" for character in token):
        raise ValueError("publication token is not lowercase base36")
    value = 0
    for character in token:
        value = value * 36 + "0123456789abcdefghijklmnopqrstuvwxyz".index(character)
    if _base36(value) != token:
        raise ValueError("publication token is not canonical base36")
    return value


def _recovery_names(
    final: Path,
    plan: ConceptEvaluationPlan,
    canonical_relative_path: str,
    sibling: Path,
    budget: PublicationPathBudget,
) -> PublicationNames:
    match = _PUBLICATION_CANDIDATE_RE.fullmatch(sibling.name)
    if match is None:
        raise ValueError("publication sibling grammar is not exact")
    attempt_token = match.group("attempt")
    _parse_base36_token(attempt_token)
    collision_token = match.group("collision")
    collision = 0 if collision_token is None else _parse_base36_token(collision_token)
    if collision_token is not None and collision == 0:
        raise ValueError("publication collision token is not canonical")
    serialized = serialize_canonical_publication_identity(plan, canonical_relative_path)
    identity_digest = hashlib.sha256(serialized).hexdigest()
    digest_text = base64.b32encode(bytes.fromhex(identity_digest)).decode("ascii").rstrip("=").lower()
    expected_token, expected_token_length = _derived_identity_token(
        digest_text,
        final.parent,
        final.name,
        attempt_token,
        collision,
        budget,
    )
    identity_token = match.group("identity")
    if len(identity_token) != expected_token_length:
        raise ValueError("publication identity token length does not fit the verified budget")
    if identity_token != expected_token:
        raise ValueError("publication identity token mismatch")
    names = _publication_candidate_names(final.parent, final.name, identity_token, attempt_token, collision)
    if not _candidate_fits(final.parent, names, budget):
        raise ValueError("publication transaction grammar exceeds the verified budget")
    candidate = PublicationNames(
        final, sibling, final.parent / names[1], final.parent / names[2],
        identity_token, attempt_token, collision_token, identity_digest,
    )
    if not _publication_paths_fit(candidate, budget):
        raise ValueError("publication transaction grammar exceeds the verified budget")
    if sibling.name != names[0]:
        raise ValueError("publication sibling grammar mismatch")
    return PublicationNames(
        final, sibling, final.parent / names[1], final.parent / names[2],
        identity_token, attempt_token, collision_token, identity_digest,
    )


def _publication_candidate_like(name: str) -> bool:
    lowered = name.casefold()
    return lowered.startswith("p3dco.concept-output.") or lowered.startswith(".p3dco.concept-output.")


def _recovery_candidates(parent: Path) -> tuple[list[Path], list[Path]]:
    exact: list[Path] = []
    ambiguous: list[Path] = []
    try:
        entries = tuple(parent.iterdir())
    except OSError as error:
        raise ValueError(f"publication parent cannot be enumerated: {error}") from error
    for entry in entries:
        if _PUBLICATION_CANDIDATE_RE.fullmatch(entry.name):
            exact.append(entry)
            continue
        if _PUBLICATION_JOURNAL_RE.fullmatch(entry.name):
            sibling = parent / entry.name[1:-len(".journal")]
            if (
                not _PUBLICATION_CANDIDATE_RE.fullmatch(sibling.name)
                or not sibling.exists() and not sibling.is_symlink()
            ):
                ambiguous.append(entry)
            continue
        if _publication_candidate_like(entry.name):
            ambiguous.append(entry)
    return exact, ambiguous


def _authenticated_promoted_candidate_identity(
    publication: PreparedPublication,
    journal: Mapping[str, Any],
) -> dict[str, int]:
    """Require the current final to be the exact candidate named by the journal."""
    final = publication.final_path
    parent = final.parent
    if final.is_symlink() or not final.is_dir():
        raise ValueError("promoted candidate final is ambiguous")
    candidate_ids = journal.get("candidate_file_identifiers")
    type_mode = journal.get("type_mode")
    if not isinstance(candidate_ids, Mapping):
        raise ValueError("promoted candidate identity is missing")
    if (
        not isinstance(type_mode, Mapping)
        or type_mode.get("expected_type") != "directory"
        or isinstance(type_mode.get("candidate_mode"), bool)
        or not isinstance(type_mode.get("candidate_mode"), int)
    ):
        raise ValueError("promoted candidate type or mode binding is missing")
    current = _candidate_file_identifiers(final)
    metadata = os.lstat(final)
    if (
        dict(candidate_ids) != current
        or metadata.st_dev != parent.stat().st_dev
        or metadata.st_mode != type_mode["candidate_mode"]
    ):
        raise ValueError("promoted candidate final identity binding mismatch")
    return current


def _authenticated_backup_identity(
    publication: PreparedPublication,
    journal: Mapping[str, Any],
) -> dict[str, int]:
    """Require the exact object created by the final-to-backup rename."""
    final = publication.final_path
    backup = publication.names.backup_path
    parent = final.parent
    if backup.parent != parent or backup.is_symlink() or not backup.is_dir():
        raise ValueError("authenticated backup is unavailable")
    if (
        journal.get("capability_hex") != publication.capability.hex()
        or journal.get("backup_capability_hex") != publication.capability.hex()
    ):
        raise ValueError("authenticated backup capability binding mismatch")
    expected = journal.get("backup_file_identifiers")
    source_final = journal.get("backup_source_final_file_identifiers")
    backup_mode = journal.get("backup_type_mode")
    if not isinstance(expected, Mapping) or not isinstance(source_final, Mapping):
        raise ValueError("authenticated backup identity is missing")
    if (
        not isinstance(backup_mode, Mapping)
        or backup_mode.get("expected_type") != "directory"
        or isinstance(backup_mode.get("mode"), bool)
        or not isinstance(backup_mode.get("mode"), int)
    ):
        raise ValueError("authenticated backup type or mode binding is missing")
    current = _candidate_file_identifiers(backup)
    if dict(expected) != current:
        raise ValueError("authenticated backup object identity mismatch")
    metadata = os.lstat(backup)
    if metadata.st_mode != backup_mode["mode"] or metadata.st_dev != parent.stat().st_dev:
        raise ValueError("authenticated backup type, mode, or volume mismatch")
    if final.exists() or final.is_symlink():
        if final.is_symlink() or not final.is_dir():
            raise ValueError("rollback final is ambiguous")
        final_ids = _candidate_file_identifiers(final)
        if final_ids == current:
            raise ValueError("authenticated backup is not distinct from final")
    if source_final != expected:
        raise ValueError("final-to-backup object identity was not preserved")
    return current


def _rollback_authenticated_backup(
    publication: PreparedPublication,
    *,
    replace: Any,
    journal: Mapping[str, Any],
) -> None:
    final = publication.final_path
    sibling = publication.sibling_path
    backup = publication.names.backup_path
    _authenticated_backup_identity(publication, journal)
    if final.exists() or final.is_symlink():
        _authenticated_promoted_candidate_identity(publication, journal)
        if sibling.exists() or sibling.is_symlink():
            raise ValueError("rollback destination is ambiguous")
        replace(final, sibling)
        _durable_parent_directory(final.parent)
    if final.exists() or final.is_symlink():
        raise ValueError("final path remained occupied during rollback")
    _authenticated_backup_identity(publication, journal)
    replace(backup, final)
    _durable_tree(final)
    _durable_parent_directory(final.parent)
    verify_completed_output(final)


def _cleanup_authenticated_backup(
    publication: PreparedPublication,
    journal: Mapping[str, Any],
) -> None:
    backup = publication.names.backup_path
    _authenticated_backup_identity(publication, journal)
    verify_completed_output(backup)
    shutil.rmtree(backup)
    if backup.exists() or backup.is_symlink():
        raise OSError("authenticated backup cleanup did not remove the exact object")
    _durable_parent_directory(backup.parent)


def _durably_mark_publishing(
    publication: PreparedPublication,
    journal: Mapping[str, Any],
) -> dict[str, Any]:
    publishing = dict(journal)
    publishing["state"] = "publishing"
    _write_validated_journal(publication.journal_path, publishing)
    return publishing


def _record_authenticated_backup_after_rename(
    publication: PreparedPublication,
    journal: Mapping[str, Any],
) -> dict[str, Any]:
    backup = publication.names.backup_path
    final_ids = journal.get("final_file_identifiers")
    if not journal.get("final_present") or not isinstance(final_ids, Mapping):
        raise ValueError("final-to-backup source identity is missing")
    if backup.is_symlink() or not backup.is_dir():
        raise ValueError("renamed backup is not an owned directory")
    backup_ids = _candidate_file_identifiers(backup)
    backup_stat = os.lstat(backup)
    parent_stat = publication.final_path.parent.stat()
    if backup_stat.st_dev != parent_stat.st_dev or dict(final_ids) != backup_ids:
        raise ValueError("renamed backup identity or volume binding mismatch")
    updated = dict(journal)
    updated["backup_file_identifiers"] = backup_ids
    updated["backup_source_final_file_identifiers"] = dict(final_ids)
    updated["backup_type_mode"] = {
        "expected_type": "directory", "mode": backup_stat.st_mode,
    }
    updated["backup_capability_hex"] = publication.capability.hex()
    _durable_tree(backup)
    _durable_parent_directory(backup.parent)
    return _durably_mark_publishing(publication, updated)


def publish_validated_publication(
    publication: PreparedPublication,
    plan: ConceptEvaluationPlan,
    *,
    absent_window_timeout_seconds: float | None,
    replace: Any = os.replace,
    clock: Any = time.monotonic,
) -> Path:
    """Promote one authenticated sibling through the bounded two-rename window.

    ``absent_window_timeout_seconds`` is intentionally required: this slice does
    not invent a policy value when the caller has not supplied ``T_absent_max``.
    The final path may be absent between the two same-volume renames; this is
    not an atomic exchange or a continuous-presence guarantee.
    """
    final = publication.final_path
    parent = final.parent
    backup = publication.names.backup_path
    sibling = publication.sibling_path
    with _publisher_lock(parent, final.name):
        journal = _validate_validated_publication(publication, plan)
        if (
            final.exists()
            and (
                absent_window_timeout_seconds is None
                or isinstance(absent_window_timeout_seconds, bool)
                or not isinstance(absent_window_timeout_seconds, (int, float))
                or not np.isfinite(absent_window_timeout_seconds)
                or absent_window_timeout_seconds < 0
            )
        ):
            raise PublicationBlocked(
                "absent-window policy is required and must be finite and non-negative",
                reason="absent_window_policy_missing",
                final_path=publication.final_path,
                candidate_path=publication.sibling_path,
                backup_path=publication.names.backup_path,
            )
        backup_moved = False
        absent_started: float | None = None
        try:
            if final.exists():
                replace(final, backup)
                backup_moved = True
                absent_started = clock()
                journal = _record_authenticated_backup_after_rename(publication, journal)
                if (
                    absent_started is not None
                    and clock() - absent_started > absent_window_timeout_seconds
                ):
                    raise TimeoutError("absent window exceeded policy before promotion")
            else:
                journal = _durably_mark_publishing(publication, journal)
            replace(sibling, final)
            _durable_tree(final)
            if absent_started is not None:
                absent_duration = clock() - absent_started
                if absent_duration > absent_window_timeout_seconds:
                    raise TimeoutError(
                        f"absent window exceeded policy: {absent_duration:.9f}s"
                    )
            verify_completed_output(final)
            journal["state"] = "published"
            _write_validated_journal(publication.journal_path, journal)
            if backup_moved:
                _cleanup_authenticated_backup(publication, journal)
            return final
        except Exception as error:
            if not backup_moved and backup.exists() and not backup.is_symlink():
                try:
                    _authenticated_backup_identity(publication, journal)
                except Exception as backup_error:
                    try:
                        _durably_mark_aborted(publication, journal, str(backup_error))
                    except Exception as abort_error:
                        raise PublicationBlocked(
                            f"promotion failed; backup evidence was not authenticated and abort durability failed: {abort_error}",
                            reason="backup_authentication_and_abort_failed",
                            final_path=final,
                            candidate_path=sibling,
                            backup_path=backup,
                            rollback_succeeded=False,
                        ) from error
                    raise PublicationBlocked(
                        f"promotion failed; unauthenticated backup evidence was preserved: {backup_error}",
                        reason="backup_authentication_failed",
                        final_path=final,
                        candidate_path=sibling,
                        backup_path=backup,
                        rollback_succeeded=False,
                    ) from error
                else:
                    backup_moved = True
            if backup_moved:
                try:
                    _rollback_authenticated_backup(
                        publication, replace=replace, journal=journal
                    )
                    _durably_mark_aborted(publication, journal, str(error))
                except Exception as rollback_error:
                    try:
                        _durably_mark_aborted(publication, journal, str(rollback_error))
                    except Exception as abort_error:
                        rollback_error = OSError(
                            f"{rollback_error}; aborted state durability failed: {abort_error}"
                        )
                    raise PublicationBlocked(
                        f"promotion failed and rollback or abort durability failed: {rollback_error}",
                        reason="rollback_failed",
                        final_path=final,
                        candidate_path=sibling,
                        backup_path=backup,
                        rollback_succeeded=False,
                    ) from error
                raise PublicationBlocked(
                    f"promotion failed; rollback succeeded: {error}",
                    reason="promotion_failed",
                    final_path=final,
                    candidate_path=sibling,
                    backup_path=backup,
                    rollback_succeeded=True,
                ) from error
            try:
                _durably_mark_aborted(publication, journal, str(error))
            except Exception as abort_error:
                raise PublicationBlocked(
                    f"promotion failed and aborted state was not durable: {abort_error}",
                    reason="abort_state_durability_failed",
                    final_path=final,
                    candidate_path=sibling,
                    backup_path=backup,
                ) from error
            raise PublicationBlocked(
                f"promotion failed without an authenticated backup: {error}",
                reason="promotion_failed_without_backup",
                final_path=final,
                candidate_path=sibling,
                backup_path=backup,
            ) from error


def recover_validated_publication(
    final_path: str | Path,
    plan: ConceptEvaluationPlan,
    canonical_relative_path: str,
    *,
    budget: PublicationPathBudget,
    absent_window_timeout_seconds: float | None,
    replace: Any = os.replace,
    clock: Any = time.monotonic,
) -> Path | None:
    """Recover one exact stale transaction without broad cleanup or adoption.

    Only a complete, exact, durably ``validated`` transaction can enter the
    existing authenticated promotion path. Foreign and look-alike entries are
    surfaced and preserved. This is normal stale-process provenance, not a
    claim of authentication against a filesystem actor able to copy or alter
    entries.
    """
    final = Path(final_path).absolute()
    parent = final.parent
    unknown_backup = parent / f".{final.name}.backup.unknown"
    if final.is_symlink() or _is_reparse_point(final):
        raise PublicationBlocked(
            "existing final is ambiguous and was not modified",
            reason="invalid_final", final_path=final,
            candidate_path=final, backup_path=unknown_backup,
        )
    if final.exists():
        if not final.is_dir():
            raise PublicationBlocked(
                "existing final is invalid and was not modified",
                reason="invalid_final", final_path=final,
                candidate_path=final, backup_path=unknown_backup,
            )
        try:
            verify_completed_output(final)
        except (OSError, ValueError) as error:
            raise PublicationBlocked(
                f"existing final is invalid and was not modified: {error}",
                reason="invalid_final", final_path=final,
                candidate_path=final, backup_path=unknown_backup,
            ) from error
        return final

    try:
        candidates, ambiguous = _recovery_candidates(parent)
    except ValueError as error:
        raise PublicationBlocked(
            str(error), reason="candidate_discovery_failed", final_path=final,
            candidate_path=final, backup_path=unknown_backup,
        ) from error
    if ambiguous:
        entry = ambiguous[0]
        raise PublicationBlocked(
            f"foreign or look-alike publication entry was preserved: {entry.name}",
            reason="candidate_not_authenticated", final_path=final,
            candidate_path=entry, backup_path=unknown_backup,
        )
    if not candidates:
        return None
    if len(candidates) != 1:
        raise PublicationBlocked(
            "multiple publication candidates are ambiguous and were preserved",
            reason="candidate_ambiguous", final_path=final,
            candidate_path=candidates[0], backup_path=unknown_backup,
        )

    sibling = candidates[0]
    try:
        names = _recovery_names(final, plan, canonical_relative_path, sibling, budget)
        journal_path = names.journal_path
        if journal_path.is_symlink() or not journal_path.is_file():
            raise ValueError("publication journal is missing or not an owned file")
        parent_stat = parent.stat()
        if sibling.is_symlink() or _is_reparse_point(sibling) or not sibling.is_dir():
            raise ValueError("publication sibling is not an owned directory")
        if sibling.parent != parent or sibling.stat().st_dev != parent_stat.st_dev:
            raise ValueError("publication sibling is not same-parent and same-volume")
        journal_stat = journal_path.stat()
        if journal_path.parent != parent or journal_stat.st_dev != parent_stat.st_dev:
            raise ValueError("publication journal is not same-parent and same-volume")
        if os.name != "nt" and (journal_stat.st_mode & 0o777) != 0o600:
            raise ValueError("publication journal mode is not restrictive")
        _verify_owner_only_acl(journal_path)
        _verify_candidate_tree_acl(sibling)

        journal = _read_publication_journal(journal_path)
        required_keys = {
            "schema_version", "protocol_version", "state", "owner_token",
            "attempt_token", "collision_token", "role", "canonical_relative_path",
            "canonical_identity_sha256", "identity_token_length", "sibling_name",
            "final_name", "backup_name", "expected_manifest_hash", "capability_hex",
            "same_volume_file_identifiers",
            "final_present", "final_file_identifiers", "type_mode", "candidate_file_identifiers",
        }
        if set(journal) != required_keys:
            raise ValueError("journal provenance is incomplete")
        capability_hex = journal.get("capability_hex")
        if not isinstance(capability_hex, str) or not re.fullmatch(r"[0-9a-f]{64}", capability_hex):
            raise ValueError("journal capability is incomplete")
        capability = bytes.fromhex(capability_hex)
        owner_token = journal.get("owner_token")
        expected_manifest_hash = journal.get("expected_manifest_hash")
        if not isinstance(owner_token, str) or not owner_token:
            raise ValueError("journal owner token is incomplete")
        if not isinstance(expected_manifest_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_hash):
            raise ValueError("journal manifest hash is incomplete")
        if journal.get("state") != "validated":
            raise ValueError("journal state is not validated")
        type_mode = journal.get("type_mode")
        if (
            not isinstance(type_mode, Mapping)
            or type_mode.get("expected_type") != "directory"
            or isinstance(type_mode.get("final_mode"), bool)
            or not isinstance(type_mode.get("final_mode"), int)
            or isinstance(type_mode.get("candidate_mode"), bool)
            or not isinstance(type_mode.get("candidate_mode"), int)
        ):
            raise ValueError("journal type or mode binding is incomplete")
        volume_ids = journal.get("same_volume_file_identifiers")
        if (
            not isinstance(volume_ids, Mapping)
            or volume_ids.get("parent_device") != parent_stat.st_dev
            or volume_ids.get("final_device") != parent_stat.st_dev
        ):
            raise ValueError("journal volume binding mismatch")
        candidate_ids = journal.get("candidate_file_identifiers")
        if not isinstance(candidate_ids, Mapping):
            raise ValueError("journal candidate file identity is incomplete")
        if (
            candidate_ids.get("device") != sibling.stat().st_dev
            or candidate_ids.get("inode") != sibling.stat().st_ino
            or type_mode["candidate_mode"] != sibling.stat().st_mode
        ):
            raise ValueError("journal candidate binding mismatch")

        publication = PreparedPublication(
            names, journal_path, capability, canonical_relative_path,
            owner_token, expected_manifest_hash, "validated",
        )
        _validate_validated_publication(publication, plan, recovery=True)
    except PublicationBlocked:
        raise
    except (OSError, ValueError) as error:
        raise PublicationBlocked(
            f"validated publication sibling is not authenticated: {error}",
            reason="candidate_validation_failed", final_path=final,
            candidate_path=sibling, backup_path=unknown_backup,
        ) from error

    return publish_validated_publication(
        publication, plan,
        absent_window_timeout_seconds=absent_window_timeout_seconds,
        replace=replace, clock=clock,
    )


def evaluate_binary_concept_records(
    records: Sequence[Any],
    *,
    task_id: str,
    task_hash: str | None = None,
    expected_task_hash: str | None = None,
    artifact_hashes: Mapping[str, Any] | None = None,
    expected_artifact_hashes: Mapping[str, Any] | None = None,
    expected_k: int | None = None,
    roi_order: Sequence[Any] | None = None,
    expected_roi_order: Sequence[Any] | None = None,
    roi_order_hash: str | None = None,
    expected_roi_order_hash: str | None = None,
    atlas_hash: str | None = None,
    expected_atlas_hash: str | None = None,
    mask_hash: str | None = None,
    expected_mask_hash: str | None = None,
    refit: bool = False,
    regenerate: bool = False,
    bootstrap_replicates: int = 10000,
    bootstrap_seed: int = 12345,
) -> dict[str, Any]:
    """Evaluate retained concept predictions in the Phase 18B task scope.

    The only task-specific operation is routing historical CN/MCI/AD records
    into CN versus Impaired descriptive support. ``c_target`` and ``g_bar``
    are read directly from each record and passed to the existing fidelity and
    anatomy implementations; no target, normalizer, mask, atlas, or anatomical
    derivative is recomputed.
    """
    if task_id != BINARY_CONCEPT_TASK_ID:
        raise ValueError("binary concept evaluation requires task_id='cn_vs_impaired'")
    if not records:
        raise ValueError("binary concept evaluation requires at least one record")
    first_k = getattr(records[0], "K", None)
    if expected_k is None:
        expected_k = first_k
    if isinstance(expected_k, bool) or not isinstance(expected_k, int) or expected_k <= 0:
        raise ValueError("binary concept evaluation requires a positive K")
    for record in records:
        if getattr(record, "K", expected_k) != expected_k:
            raise ValueError("binary concept record K does not match the established artifact K")
    validate_binary_concept_compatibility(
        task_id=task_id,
        artifact_hashes=artifact_hashes,
        expected_artifact_hashes=expected_artifact_hashes,
        k=expected_k,
        expected_k=expected_k,
        roi_order=roi_order,
        expected_roi_order=expected_roi_order,
        roi_order_hash=roi_order_hash,
        expected_roi_order_hash=expected_roi_order_hash,
        atlas_hash=atlas_hash,
        expected_atlas_hash=expected_atlas_hash,
        mask_hash=mask_hash,
        expected_mask_hash=expected_mask_hash,
        task_hash=task_hash,
        expected_task_hash=expected_task_hash,
        refit=refit,
        regenerate=regenerate,
    )
    predicted = np.asarray([record.predicted_concepts for record in records], dtype=np.float64)
    c_target = np.asarray([record.concept_targets for record in records], dtype=np.float64)
    g_bar = np.asarray([record.anatomical_targets for record in records], dtype=np.float64)
    if predicted.shape != (len(records), expected_k):
        raise ValueError("predicted concept vectors do not match K")
    # These calls are the historical calculations, not binary replacements.
    fidelity = compute_all_fidelity(predicted, c_target)
    anatomy = compute_all_anatomy(predicted, g_bar)
    profiles = compute_binary_class_profiles(
        list(records), bootstrap_replicates=bootstrap_replicates, bootstrap_seed=bootstrap_seed
    )
    return {
        "task_id": BINARY_CONCEPT_TASK_ID,
        "class_order": BINARY_CONCEPT_CLASS_ORDER,
        "profiles": profiles,
        "fidelity": fidelity,
        "anatomy": anatomy,
        "provenance": {
            "task_hash": task_hash,
            "source_label_support": compute_binary_source_label_support(list(records)),
            "targets_reused": True,
            "concept_target_recomputed": False,
            "anatomical_target_recomputed": False,
            "normalizer_refit": False,
            "roi_masks_regenerated": False,
            "active_class_axes": BINARY_CONCEPT_CLASS_ORDER,
        },
    }


# Explicitly named alias for integrations that use the task as the entry point.
evaluate_binary_concepts = evaluate_binary_concept_records


def build_binary_concept_output_plan(
    evaluation_identity: str,
    analysis_mode: str,
    methods: Sequence[MethodId],
    directions: Sequence[Direction],
    checkpoint_policies: Sequence[CheckpointPolicy],
    included_methods: tuple[MethodId, ...],
    include_artifact_index: bool = True,
) -> ConceptEvaluationPlan:
    """Build a binary-only output plan without changing historical plans."""
    return build_concept_output_plan(
        evaluation_identity, analysis_mode, methods, directions,
        checkpoint_policies, included_methods, include_artifact_index,
        task_id=BINARY_CONCEPT_TASK_ID,
    )


def build_concept_output_plan(
    evaluation_identity: str,
    analysis_mode: str,
    methods: Sequence[MethodId],
    directions: Sequence[Direction],
    checkpoint_policies: Sequence[CheckpointPolicy],
    included_methods: tuple[MethodId, ...],
    include_artifact_index: bool = True,
    task_id: str | None = None,
) -> ConceptEvaluationPlan:
    """Build exact output manifest for concept evaluation."""
    paths = [
        "evaluation_config_resolved.yaml",
        "provenance_report.json",
        "method_status.csv",
        "evaluation_log.txt",
    ]
    included_methods = tuple(dict.fromkeys(included_methods))
    concept_directions = directions if included_methods else ()

    for direction in concept_directions:
        for policy in checkpoint_policies:
            base = f"concepts/{direction.value}/{policy.logical_checkpoint}"
            paths.extend([
                f"{base}/subject_outputs/subject_outputs.csv",
                f"{base}/concept_fidelity/concept_fidelity_global.csv",
                f"{base}/concept_fidelity/concept_fidelity_per_subject.csv",
                f"{base}/concept_fidelity/concept_fidelity_per_roi.csv",
                f"{base}/concept_fidelity/correlations.csv",
                f"{base}/anatomy_consistency/anatomy_consistency_global.csv",
                f"{base}/anatomy_consistency/anatomy_consistency_per_subject.csv",
                f"{base}/anatomy_consistency/anatomy_consistency_per_roi.csv",
                f"{base}/anatomy_consistency/correlations.csv",
                f"{base}/anatomy_consistency/weighted_score.csv",
                f"{base}/head_agreement/latent_predictive.csv",
                f"{base}/head_agreement/concept_predictive.csv",
                f"{base}/head_agreement/top1_agreement.csv",
                f"{base}/head_agreement/js_divergence.csv",
                f"{base}/head_agreement/consistency_direction.csv",
                f"{base}/head_agreement/per_class_disagreement.csv",
                f"{base}/roi_stability/rank_correlations.csv",
                f"{base}/roi_stability/mean_pairwise_rho.csv",
                f"{base}/roi_stability/instance_std.csv",
                f"{base}/roi_stability/jaccard_overlap.csv",
                f"{base}/roi_stability/rank_dispersion.csv",
                f"{base}/class_profiles/cn_concepts.csv",
                f"{base}/class_profiles/mci_concepts.csv",
                f"{base}/class_profiles/ad_concepts.csv",
                f"{base}/class_profiles/cn_c_targets.csv",
                f"{base}/class_profiles/mci_c_targets.csv",
                f"{base}/class_profiles/ad_c_targets.csv",
                f"{base}/class_profiles/cn_g_bar.csv",
                f"{base}/class_profiles/mci_g_bar.csv",
                f"{base}/class_profiles/ad_g_bar.csv",
                f"{base}/paired_comparisons/concept_mae_paired.csv",
                f"{base}/paired_comparisons/anatomy_mae_paired.csv",
                f"{base}/paired_comparisons/js_divergence_paired.csv",
                f"{base}/paired_comparisons/holm_adjusted.csv",
                f"{base}/figures/concept_fidelity_roi_heatmap.png",
                f"{base}/figures/anatomy_consistency_roi_heatmap.png",
                f"{base}/figures/head_agreement_matrix.png",
                f"{base}/figures/roi_stability_heatmap.png",
                f"{base}/figures/class_conditional_concept_profiles.png",
                f"{base}/tables/concept_fidelity_global.csv",
                f"{base}/tables/concept_fidelity_per_subject.csv",
                f"{base}/tables/concept_fidelity_per_roi.csv",
                f"{base}/tables/anatomy_consistency_global.csv",
                f"{base}/tables/anatomy_consistency_per_subject.csv",
                f"{base}/tables/anatomy_consistency_per_roi.csv",
                f"{base}/tables/head_agreement.csv",
                f"{base}/tables/roi_stability.csv",
                f"{base}/tables/class_conditional_profiles.csv",
                f"{base}/tables/paired_method_comparisons.csv",
                f"{base}/tables/method_status.csv",
            ])

    if task_id == BINARY_CONCEPT_TASK_ID:
        legacy_axes = ("mci", "ad")
        paths = [
            path for path in paths
            if not any(f"/class_profiles/{axis}_" in path for axis in legacy_axes)
        ]
        binary_profile_paths = []
        for path in tuple(paths):
            if "/class_profiles/cn_" in path:
                binary_profile_paths.append(path.replace("/cn_", "/impaired_"))
        paths.extend(binary_profile_paths)
    paths = sorted(paths)
    if include_artifact_index:
        paths.append("artifact_index.json")

    paths.append("evaluation_manifest.json")

    return ConceptEvaluationPlan(
        evaluation_identity=evaluation_identity,
        analysis_mode=analysis_mode,
        methods=tuple(methods),
        directions=tuple(directions),
        checkpoint_policies=tuple(checkpoint_policies),
        intended_relative_paths=tuple(paths),
    )


def build_artifact_index(artifacts: Mapping[str, bytes]) -> bytes:
    """Build optional self-excluding artifact hash inventory."""
    if "artifact_index.json" in artifacts:
        raise ValueError("artifact index input must exclude itself")

    payload = {
        "schema_version": "1.0",
        "artifacts": {
            path: hashlib.sha256(artifacts[path]).hexdigest()
            for path in sorted(artifacts)
        },
    }
    return (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def build_completion_manifest(
    plan: ConceptEvaluationPlan,
    artifacts: Mapping[str, bytes],
    identity_inputs: Mapping[str, Any],
    library_versions: Mapping[str, str],
    bootstrap_replicates: int,
    bootstrap_seed: int,
    ci_policy: str,
    gate_states: Mapping[str, bool],
    created_utc: str,
    completed_utc: str,
    disposition: str = "completed",
    task_id: str | None = None,
) -> bytes:
    """Build identity-bound completion manifest over every non-manifest artifact."""
    expected = set(plan.intended_relative_paths)
    expected.discard("evaluation_manifest.json")
    expected.discard("artifact_index.json")

    ordinary_expected = {p for p in expected if p not in {"artifact_index.json"}}
    if set(artifacts.keys()) != ordinary_expected:
        raise ValueError("completed artifacts do not exactly match the evaluation plan")

    output_sha256s = {
        path: hashlib.sha256(artifacts[path]).hexdigest()
        for path in sorted(ordinary_expected)
    }

    required_gates = ("authorized_exports", "concept_normalizer", "atlas_hash", "protocol_approval")
    gates = dict.fromkeys(required_gates, False)
    gates.update(gate_states)

    config_hash = identity_inputs.get("configuration_sha256", "0" * 64)
    auth_hash = identity_inputs.get("authorization_sha256", "0" * 64)
    ordered_inputs = identity_inputs.get("ordered_input_sha256s", [])

    payload = {
        "schema_version": "1.0",
        "protocol_version": "1.0",
        "evaluation_identity": plan.evaluation_identity,
        "analysis_mode": plan.analysis_mode,
        "created_utc": created_utc,
        "completed_utc": completed_utc,
        "methods": [m.value for m in plan.methods],
        "directions": [d.value for d in plan.directions],
        "checkpoint_policies": [p.logical_checkpoint for p in plan.checkpoint_policies],
        "class_order": (
            {"CN": 0, "Impaired": 1}
            if task_id == BINARY_CONCEPT_TASK_ID
            else {"CN": 0, "MCI": 1, "AD": 2}
        ),
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "ci_policy": ci_policy,
        },
        "configuration_sha256": config_hash,
        "authorization_sha256": auth_hash,
        "gate_states": gates,
        "ordered_input_sha256s": ordered_inputs,
        "identity_inputs": dict(identity_inputs),
        "library_versions": dict(library_versions),
        "output_sha256s": output_sha256s,
        "disposition": disposition,
    }
    return (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def _csv_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    fieldnames = list(rows[0])
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _synthetic_status_rows(
    methods: Sequence[MethodId],
    directions: Sequence[Direction],
    policies: Sequence[CheckpointPolicy],
) -> list[dict[str, Any]]:
    not_applicable_methods = (MethodId.AAGN, MethodId.FASTER_SNN)
    selected_methods = tuple(dict.fromkeys(methods))
    status_methods = tuple(dict.fromkeys((*selected_methods, *not_applicable_methods)))
    rows = []
    for direction in directions:
        for policy in policies:
            for method in status_methods:
                is_not_applicable = method in not_applicable_methods
                rows.append({
                    "method": method.value,
                    "direction": direction.value,
                    "checkpoint_policy": policy.logical_checkpoint,
                    "status": (
                        "not_applicable_no_acda3d_concept_head"
                        if is_not_applicable else "included"
                    ),
                    "reason": (
                        "no_acda3d_concept_head"
                        if is_not_applicable else "fixture_only"
                    ),
                })
    return rows


def _synthetic_csv_artifact(
    relative_path: str,
    metrics: Mapping[str, Any],
    methods: Sequence[MethodId],
) -> bytes:
    parts = relative_path.split("/")
    direction = parts[1] if len(parts) > 3 and parts[0] == "concepts" else "all"
    policy = parts[2] if len(parts) > 3 and parts[0] == "concepts" else "all"
    name = Path(relative_path).name
    method = methods[0].value
    common = {"method": method, "direction": direction, "checkpoint_policy": policy}
    if name == "subject_outputs.csv":
        return _csv_bytes([{**common, "subject_hash": "1" * 64, "true_label": 0,
            "label_name": "CN", "predicted_concepts": "[0.1,0.3,0.5]",
            "concept_targets": "[0.05,0.25,0.45]", "anatomical_targets": "[0.2,0.4,0.6]"}])
    if "concept_fidelity" in name:
        rows = [{**common, "roi_index": roi, "n_subjects": 6,
            "mae": metrics["concept_mae"], "rmse": metrics.get("concept_rmse", 0.05), "bias": 0.05}
            for roi in range(3)]
    elif "anatomy_consistency" in name or name in {"weighted_score.csv", "correlations.csv"}:
        rows = [{**common, "roi_index": roi, "n_subjects": 6,
            "mae": metrics.get("anatomy_mae", 0.1), "rmse": metrics.get("anatomy_rmse", 0.1),
            "status": "available"} for roi in range(3)]
    elif name in {"head_agreement.csv", "latent_predictive.csv", "concept_predictive.csv",
                  "top1_agreement.csv", "js_divergence.csv", "consistency_direction.csv",
                  "per_class_disagreement.csv"}:
        rows = [{**common, "n_subjects": 6,
            "top1_agreement_rate": metrics.get("top1_agreement_rate", 1.0),
            "mean_js_divergence": metrics.get("mean_js_divergence", 0.0),
            "consistency_direction": "latent_supervises_concept"}]
    elif "roi_stability" in relative_path or name in {
        "rank_correlations.csv", "mean_pairwise_rho.csv", "instance_std.csv",
        "jaccard_overlap.csv", "rank_dispersion.csv",
    }:
        rows = [{**common, "profile": profile, "roi_index": roi, "k": 2,
            "metric": "profile_specific_stability", "value": 1.0}
            for profile in ("fidelity", "anatomy", "concept", "alpha") for roi in range(3)]
    elif "class" in name or "class_profiles" in relative_path:
        rows = [{**common, "class_label": label, "class_index": index, "support": 2,
            "roi_index": roi, "mean": 0.2 + 0.1 * index + 0.05 * roi,
            "ci_low": 0.1, "ci_high": 0.8}
            for index, label in enumerate(("CN", "MCI", "AD")) for roi in range(3)]
    elif "paired" in name or "holm" in name:
        rows = [{**common, "comparator_method": comparator.value,
            "metric": "concept_mae", "mean_difference": 0.0, "ci_low": 0.0,
            "ci_high": 0.0, "raw_p_value": 1.0, "adjusted_p_value": 1.0,
            "status": "available"}
            for comparator in (MethodId.SOURCE_ONLY, MethodId.CORAL, MethodId.MMD, MethodId.CDAN)]
    elif name == "method_status.csv":
        rows = [{**common, "status": "included", "reason": "fixture_only"}]
    else:
        rows = [{**common, "fixture_only": True, "status": "available"}]
    return _csv_bytes(rows)


def _synthetic_figure_payloads(methods: Sequence[MethodId]) -> dict[str, bytes]:
    method_names = [method.value for method in methods]
    fidelity = [{"method": method, "roi_index": roi, "mae": 0.05 + 0.01 * roi}
        for method in method_names for roi in range(3)]
    anatomy = [{"method": method, "roi_index": roi, "mae": 0.1 + 0.01 * roi}
        for method in method_names for roi in range(3)]
    profiles = [{"class_label": label, "roi_index": roi, "mean": 0.2 + 0.1 * index,
        "ci_low": 0.1, "ci_high": 0.8}
        for index, label in enumerate(("CN", "MCI", "AD")) for roi in range(3)]
    stability = SimpleNamespace(
        instance_std_fidelity=(0.01, 0.02, 0.03),
        instance_std_anatomy=(0.02, 0.03, 0.04),
        instance_std_concept=(0.03, 0.04, 0.05),
        instance_std_alpha=(0.01, 0.01, 0.02),
    )
    with tempfile.TemporaryDirectory(prefix="acda3d-concept-figures-") as directory:
        root = Path(directory)
        plot_concept_fidelity_roi_heatmap(fidelity, root / "concept_fidelity_roi_heatmap.png")
        plot_anatomy_consistency_roi_heatmap(anatomy, root / "anatomy_consistency_roi_heatmap.png")
        plot_head_agreement_matrix({"source_only": {
            "comparator_method": "source_only",
            "confusion_matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
        }}, root / "head_agreement_matrix.png")
        plot_roi_stability_heatmap(stability, root / "roi_stability_heatmap.png")
        plot_class_conditional_profiles(profiles, root / "class_conditional_concept_profiles.png")
        return {path.name: path.read_bytes() for path in root.glob("*.png")}


def build_synthetic_fixture_bundle(
    *,
    evaluation_identity: str,
    methods: Sequence[MethodId],
    directions: Sequence[Direction],
    checkpoint_policies: Sequence[CheckpointPolicy],
    metrics: Mapping[str, Any],
    resolved_config: Mapping[str, Any],
    identity_inputs: Mapping[str, Any],
    library_versions: Mapping[str, str],
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> tuple[ConceptEvaluationPlan, dict[str, bytes]]:
    """Build the complete deterministic fixture-only report tree."""
    included_methods = tuple(
        method for method in methods
        if method not in {MethodId.AAGN, MethodId.FASTER_SNN}
    )
    plan = build_concept_output_plan(
        evaluation_identity,
        "synthetic_test_only",
        methods,
        directions,
        checkpoint_policies,
        included_methods,
    )
    ordinary: dict[str, bytes] = {
        "evaluation_config_resolved.yaml": (
            json.dumps(dict(resolved_config), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8"),
        "evaluation_log.txt": b"fixture_only deterministic synthetic evaluation\n",
        "method_status.csv": _csv_bytes(
            _synthetic_status_rows(methods, directions, checkpoint_policies)
        ),
        "provenance_report.json": (
            json.dumps({"candidates": [], "excluded": [], "fixture_only": True,
                "ordered_input_sha256s": [], "real_data": False},
                sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8"),
    }
    figures = _synthetic_figure_payloads(methods)
    for relative_path in plan.intended_relative_paths:
        if relative_path in ordinary or relative_path in {
            "artifact_index.json", "evaluation_manifest.json"
        }:
            continue
        ordinary[relative_path] = (
            figures[Path(relative_path).name]
            if relative_path.endswith(".png")
            else _synthetic_csv_artifact(relative_path, metrics, methods)
        )
    artifact_index = build_artifact_index(ordinary)
    manifest = build_completion_manifest(
        plan, ordinary, identity_inputs, library_versions,
        bootstrap_replicates, bootstrap_seed, "percentile_95_linear",
        {"authorized_exports": False, "concept_normalizer": False,
         "atlas_hash": False, "protocol_approval": False},
        "1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z",
    )
    return plan, {**ordinary, "artifact_index.json": artifact_index,
        "evaluation_manifest.json": manifest}


def _default_output_writer(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _relative_entries(root: Path) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    if root.is_symlink():
        raise ValueError("output root must not be a symlink")
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"output contains a symlink: {relative}")
        if path.is_file():
            files.add(relative)
        elif path.is_dir():
            directories.add(relative)
        else:
            raise ValueError(f"output contains an unsupported entry: {relative}")
    return files, directories


def _relative_files(root: Path) -> set[str]:
    return _relative_entries(root)[0]


def _safe_relative_path(relative_path: Any) -> bool:
    if not isinstance(relative_path, str) or not relative_path or "\\" in relative_path:
        return False
    path = Path(relative_path)
    return (
        not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in relative_path.split("/"))
    )


def _expected_directories(files: set[str]) -> set[str]:
    directories: set[str] = set()
    for relative_path in files:
        parts = relative_path.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            directories.add("/".join(parts[:index]))
    return directories


def _validate_allowlisted_tree(root: Path, expected_files: set[str]) -> None:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("recognized output exists and is not a directory")
    try:
        actual_files, actual_directories = _relative_entries(root)
    except ValueError as error:
        raise RuntimeError(str(error)) from error
    if actual_files != expected_files:
        unknown = sorted(actual_files - expected_files)
        missing = sorted(expected_files - actual_files)
        raise RuntimeError(
            f"unknown output paths block overwrite; unknown={unknown}, missing={missing}"
        )
    expected_directories = _expected_directories(expected_files)
    if actual_directories != expected_directories:
        unknown = sorted(actual_directories - expected_directories)
        raise RuntimeError(f"unknown output directories block overwrite: {unknown}")


def _validate_completed_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise ValueError("completed evaluation manifest is not an object")
    if manifest.get("schema_version") != "1.0" or manifest.get("protocol_version") != "1.0":
        raise ValueError("completed evaluation manifest version is unsupported")
    if not isinstance(manifest.get("evaluation_identity"), str) or not manifest["evaluation_identity"]:
        raise ValueError("completed evaluation identity is missing")
    if not isinstance(manifest.get("analysis_mode"), str) or not manifest["analysis_mode"]:
        raise ValueError("completed analysis mode is missing")
    if manifest.get("disposition") != "completed":
        raise ValueError("completed evaluation is not marked completed")
    output_hashes = manifest.get("output_sha256s")
    if not isinstance(output_hashes, Mapping):
        raise ValueError("completed output hashes are missing")
    for relative_path, expected_hash in output_hashes.items():
        if not _safe_relative_path(relative_path) or relative_path in {
            "artifact_index.json", "evaluation_manifest.json"
        }:
            raise ValueError("completed output contains an unsafe artifact path")
        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or expected_hash != expected_hash.lower()
            or any(character not in "0123456789abcdef" for character in expected_hash)
        ):
            raise ValueError(f"invalid artifact hash: {relative_path}")
    return dict(manifest)


_OWNER_METADATA_NAME = ".acda3d-owner.json"
_STALE_CONTROLLED_AGE_SECONDS = 30.0


def _process_is_alive(pid: int) -> bool:
    """Return a conservative liveness result for a controlled owner PID."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _owner_metadata_path(entry: Path, kind: str) -> Path:
    return entry / _OWNER_METADATA_NAME


def _write_owner_metadata(entry: Path, *, kind: str, pid: int, token: str) -> None:
    metadata_path = _owner_metadata_path(entry, kind)
    metadata = json.dumps(
        {"schema_version": "1", "pid": pid, "token": token},
        separators=(",", ":"),
    ).encode("utf-8")
    temporary = metadata_path.with_name(f".{metadata_path.name}.{token}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(metadata)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, metadata_path)
    finally:
        with suppress(FileNotFoundError):
            temporary.unlink()


def _read_owner_metadata(entry: Path, *, kind: str) -> dict[str, Any] | None:
    metadata_path = _owner_metadata_path(entry, kind)
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_version") != "1"
        or isinstance(payload.get("pid"), bool)
        or not isinstance(payload.get("pid"), int)
        or payload["pid"] <= 0
        or not isinstance(payload.get("token"), str)
        or not payload["token"]
    ):
        return {}
    return dict(payload)


def _controlled_entry_kind(name: str, output_name: str) -> tuple[str, str] | None:
    pattern = rf"\.{re.escape(output_name)}(?:\.v\d{{6}})?\.(stage|reserve|backup)\.([A-Za-z0-9_-]+)"
    match = re.fullmatch(pattern, name)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _controlled_destination(entry: Path, output_name: str) -> Path:
    name = entry.name
    destination_name = output_name
    version_prefix = f".{output_name}.v"
    if name.startswith(version_prefix):
        version = name[len(version_prefix):].split(".", maxsplit=1)[0]
        destination_name = f"{output_name}.v{version}"
    return entry.parent / destination_name


def _is_old_controlled_entry(entry: Path) -> bool:
    try:
        age = time.time() - entry.stat().st_mtime
    except OSError:
        return False
    return age >= _STALE_CONTROLLED_AGE_SECONDS


def _owner_is_stale(
    entry: Path,
    *,
    kind: str,
    token: str | None = None,
) -> bool:
    if entry.is_symlink() or not entry.is_dir():
        return False
    metadata = _read_owner_metadata(entry, kind=kind)
    if metadata is None and token is not None:
        encoded_pid = token.split("-", maxsplit=1)[0]
        if encoded_pid.isdigit() and int(encoded_pid) > 0:
            return not _process_is_alive(int(encoded_pid))
    if metadata is None:
        return _is_old_controlled_entry(entry)
    if not metadata:
        return False
    if token is not None and metadata["token"] != token:
        return False
    if _process_is_alive(metadata["pid"]):
        return False
    # Read twice: a writer racing an owner read is never reclaimed.
    return _read_owner_metadata(entry, kind=kind) == metadata


def _remove_controlled_entry(entry: Path, parent: Path) -> bool:
    if entry.parent != parent or entry.is_symlink() or not entry.is_dir():
        return False
    if os.name != "nt":
        shutil.rmtree(entry)
        return True
    for attempt in range(10):
        try:
            shutil.rmtree(entry)
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.02)
        else:
            return True
    return False


def _recover_stale_backup(entry: Path, output_name: str) -> None:
    destination = _controlled_destination(entry, output_name)
    if not destination.exists() and not destination.is_symlink():
        try:
            verify_completed_output(entry)
        except (OSError, ValueError):
            pass
        else:
            os.replace(entry, destination)
            return
    _remove_controlled_entry(entry, entry.parent)


def _recover_stale_controlled_entries(parent: Path, output_name: str) -> None:
    for entry in tuple(parent.iterdir()):
        controlled = _controlled_entry_kind(entry.name, output_name)
        if controlled is None:
            continue
        kind, token = controlled
        if not _owner_is_stale(entry, kind=kind, token=token):
            continue
        if kind == "backup":
            _recover_stale_backup(entry, output_name)
        else:
            _remove_controlled_entry(entry, parent)


@contextmanager
def _allocation_lock(parent: Path, output_name: str, *, timeout_seconds: float = 5.0):
    lock = parent / f".{output_name}.allocation.lock"
    owner = {"pid": os.getpid(), "token": uuid.uuid4().hex}
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            lock.mkdir()
        except FileExistsError as error:
            if _owner_is_stale(lock, kind="lock"):
                _remove_controlled_entry(lock, parent)
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError("output allocation lock is busy") from error
            time.sleep(0.01)
        else:
            try:
                _write_owner_metadata(
                    lock, kind="lock", pid=owner["pid"], token=owner["token"]
                )
            except Exception:
                _remove_controlled_entry(lock, parent)
                raise
            break
    try:
        _recover_stale_controlled_entries(parent, output_name)
        yield owner
    finally:
        metadata = _read_owner_metadata(lock, kind="lock")
        if metadata is not None and metadata.get("token") == owner["token"]:
            _remove_controlled_entry(lock, parent)


def _reservation_glob(parent: Path, destination: Path) -> str:
    return f".{destination.name}.reserve.*"


def _reserve_destination(parent: Path, destination: Path, token: str) -> Path:
    reservation = parent / f".{destination.name}.reserve.{token}"
    reservation.mkdir()
    return reservation


def _find_non_overwrite_destination(
    output: Path,
    evaluation_identity: str,
    *,
    owner: Mapping[str, Any] | None = None,
) -> tuple[Path, Path | None]:
    if output.exists() or output.is_symlink():
        if not output.is_dir():
            raise ValueError("existing output is not a completed directory")
        try:
            manifest = verify_completed_output(output)
        except ValueError as error:
            raise ValueError(
                f"existing output is invalid and was not modified: {error}"
            ) from error
        if manifest["evaluation_identity"] == evaluation_identity:
            return output, None

    token = (
        f"{owner['pid']}-{owner['token']}"
        if owner is not None else f"{os.getpid()}-{uuid.uuid4().hex}"
    )
    if (
        not output.exists()
        and not output.is_symlink()
        and not list(output.parent.glob(_reservation_glob(output.parent, output)))
    ):
        return output, _reserve_destination(
            output.parent, output, token,
        )

    version = 1
    while True:
        destination = output.with_name(f"{output.name}.v{version:06d}")
        if destination.exists() or destination.is_symlink():
            if destination.is_dir() and not destination.is_symlink():
                try:
                    manifest = verify_completed_output(destination)
                except ValueError:
                    pass
                else:
                    if manifest["evaluation_identity"] == evaluation_identity:
                        return destination, None
            version += 1
            continue
        if list(output.parent.glob(_reservation_glob(output.parent, destination))):
            version += 1
            continue
        try:
            return destination, _reserve_destination(
                output.parent, destination, token,
            )
        except FileExistsError:
            version += 1


def _replace_with_permission_retry(
    replace: Any,
    source: str | Path,
    destination: str | Path,
    *,
    attempts: int = 10,
    delay_seconds: float = 0.02,
) -> None:
    for attempt in range(attempts):
        try:
            replace(source, destination)
            return
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            time.sleep(delay_seconds)


def _publish_output(
    destination: Path,
    plan: ConceptEvaluationPlan,
    artifacts: Mapping[str, bytes],
    *,
    overwrite: bool,
    write: Any,
    replace: Any,
    reservation: Path | None,
    owner: Mapping[str, Any],
) -> Path:
    stage: Path | None = None
    backup: Path | None = None
    moved_existing = False
    committed = False
    try:
        stage = destination.parent / (
            f".{destination.name}.stage.{owner['pid']}-{owner['token']}"
        )
        stage.mkdir()
        backup = destination.parent / (
            f".{destination.name}.backup.{owner['pid']}-{owner['token']}"
        )
        ordered_paths = [
            path for path in plan.intended_relative_paths
            if path != "evaluation_manifest.json"
        ]
        if "evaluation_manifest.json" in plan.intended_relative_paths:
            ordered_paths.append("evaluation_manifest.json")
        for relative_path in ordered_paths:
            write(stage / relative_path, artifacts[relative_path])
        if overwrite and destination.exists():
            if backup.exists():
                raise RuntimeError("controlled output backup already exists")
            _replace_with_permission_retry(replace, destination, backup)
            moved_existing = True
        elif destination.exists() or destination.is_symlink():
            raise RuntimeError("reserved output destination became occupied")

        _replace_with_permission_retry(replace, stage, destination)
        committed = True
        return destination
    except Exception as error:
        restored = False
        if (
            moved_existing
            and backup is not None
            and backup.exists()
            and not destination.exists()
        ):
            try:
                _replace_with_permission_retry(replace, backup, destination)
                restored = True
            except Exception as restore_error:
                raise RuntimeError(
                    f"output commit and restoration failed; backup remains at {backup}"
                ) from restore_error
        message = "output commit failed; previous tree restored" if restored else "output commit failed"
        raise RuntimeError(f"{message}: {error}") from error
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if reservation is not None and reservation.exists():
            _remove_controlled_entry(reservation, reservation.parent)
        if committed and backup is not None and backup.exists():
            shutil.rmtree(backup, ignore_errors=True)


def _publication_budget_from_probe(result: Any) -> PublicationPathBudget:
    if isinstance(result, PublicationProbeResult):
        return result.budget
    raise PublicationBlocked(
        "publication probe returned no verified path capability",
        reason="path_capability_unavailable",
        final_path=Path("."),
        candidate_path=Path("."),
        backup_path=Path("."),
    )


def commit_output(
    output_root: str | Path,
    plan: ConceptEvaluationPlan,
    artifacts: Mapping[str, bytes],
    *,
    overwrite: bool = False,
    writer: Any = None,
    replace: Any = os.replace,
    absent_window_timeout_seconds: float | None = None,
    publication_probe: Any = None,
) -> Path:
    """Publish through the bounded journaled same-volume transaction."""
    output = Path(output_root).absolute()
    expected_files = set(plan.intended_relative_paths)
    if set(artifacts.keys()) != expected_files:
        raise ValueError("artifacts must exactly match the evaluation plan")
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.is_symlink() or output.exists():
        if output.is_symlink() or not output.is_dir():
            raise ValueError("existing output is not a completed directory")
        _validate_allowlisted_tree(output, expected_files)
        existing_manifest = verify_completed_output(output)
        if not overwrite:
            if existing_manifest["evaluation_identity"] == plan.evaluation_identity:
                return output
            raise ValueError(
                "existing output has a different evaluation identity; explicit overwrite is required"
            )

    canonical_relative_path = "reports/concepts/evaluation_manifest.json"
    probe = publication_probe or probe_publication_operations
    budget = _publication_budget_from_probe(
        probe(output, plan, canonical_relative_path)
    )
    owner_token = uuid.uuid4().hex
    manifest_hash = hashlib.sha256(artifacts["evaluation_manifest.json"]).hexdigest()
    prepared = prepare_publication_transaction(
        output,
        plan,
        canonical_relative_path,
        attempt=1,
        owner_token=owner_token,
        expected_manifest_hash=manifest_hash,
        budget=budget,
    )
    validated = create_validated_publication_sibling(
        prepared, plan, artifacts, writer=writer,
    )
    return publish_validated_publication(
        validated,
        plan,
        absent_window_timeout_seconds=absent_window_timeout_seconds,
        replace=replace,
    )


def verify_completed_output(
    output_root: str | Path,
    *,
    expected_identity: str | None = None,
) -> dict[str, Any]:
    """Verify any immutable completed output tree without writing to it."""
    root = Path(output_root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("completed output root is not a directory")
    manifest_path = root / "evaluation_manifest.json"
    try:
        manifest = _validate_completed_manifest(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("completed evaluation manifest is unreadable") from error
    if expected_identity is not None and manifest["evaluation_identity"] != expected_identity:
        raise ValueError("evaluation identity mismatch")

    output_hashes = manifest["output_sha256s"]
    expected_files = set(output_hashes) | {"artifact_index.json", "evaluation_manifest.json"}
    try:
        actual_files, actual_directories = _relative_entries(root)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if actual_files != expected_files or actual_directories != _expected_directories(expected_files):
        raise ValueError("completed output file set mismatch")

    ordinary: dict[str, bytes] = {}
    for relative_path, expected_hash in output_hashes.items():
        payload = (root / relative_path).read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected_hash:
            raise ValueError(f"artifact hash mismatch: {relative_path}")
        ordinary[str(relative_path)] = payload
    if (root / "artifact_index.json").read_bytes() != build_artifact_index(ordinary):
        raise ValueError("artifact index hash mismatch")
    return manifest


def generate_binary_concept_report(*args: Any, **kwargs: Any) -> Path:
    """Generate a binary-scoped report without touching historical paths."""
    if kwargs.get("task_id", BINARY_CONCEPT_TASK_ID) != BINARY_CONCEPT_TASK_ID:
        raise ValueError("binary concept report requires task_id='cn_vs_impaired'")
    kwargs["task_id"] = BINARY_CONCEPT_TASK_ID
    return generate_concept_report(*args, **kwargs)


def generate_concept_report(
    output_root: str | Path,
    evaluation_identity: str,
    analysis_mode: str,
    methods: Sequence[Any],
    directions: Sequence[Any],
    checkpoint_policies: Sequence[Any],
    included_methods: Sequence[Any],
    canonical_tables: Mapping[Any, Any],
    report_statistics: Mapping[Any, Any],
    root_metadata: Mapping[str, Any],
    policy_metadata: Mapping[Any, Any],
    identity_inputs: Mapping[str, Any],
    library_versions: Mapping[str, str],
    bootstrap_replicates: int,
    bootstrap_seed: int,
    ci_policy: str,
    gate_states: Mapping[str, bool],
    created_utc: str,
    completed_utc: str,
    disposition: str = "completed",
    overwrite: bool = False,
    writer: Any = None,
    replace: Any = os.replace,
    task_id: str | None = None,
    absent_window_timeout_seconds: float | None = None,
    publication_probe: Any = None,
) -> Path:
    """
    Generate complete concept evaluation report.

    This is the main entry point for report generation.
    """
    plan = build_concept_output_plan(
        evaluation_identity, analysis_mode, methods, directions,
        checkpoint_policies, included_methods, include_artifact_index=True,
        task_id=task_id,
    )

    required_metadata = {
        "resolved_config",
        "provenance_report",
        "method_status_rows",
        "evaluation_log",
    }
    missing_metadata = required_metadata - set(root_metadata)
    if missing_metadata:
        raise ValueError(f"missing root report metadata: {sorted(missing_metadata)}")
    artifacts: dict[str, bytes] = {
        "evaluation_config_resolved.yaml": (
            json.dumps(root_metadata["resolved_config"], sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
        "provenance_report.json": (
            json.dumps(root_metadata["provenance_report"], sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
        "method_status.csv": _csv_bytes(root_metadata["method_status_rows"]),
        "evaluation_log.txt": str(root_metadata["evaluation_log"]).encode("utf-8"),
    }
    figure_artifacts = report_statistics.get("figure_artifacts", {})
    for relative_path in plan.intended_relative_paths:
        if relative_path in artifacts or relative_path in {
            "artifact_index.json", "evaluation_manifest.json"
        }:
            continue
        if relative_path.endswith(".png"):
            payload = figure_artifacts.get(relative_path)
            if not isinstance(payload, bytes) or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError(f"missing valid figure artifact: {relative_path}")
            artifacts[relative_path] = payload
            continue
        rows_or_payload = canonical_tables.get(relative_path)
        if isinstance(rows_or_payload, bytes):
            artifacts[relative_path] = rows_or_payload
        elif isinstance(rows_or_payload, Sequence) and rows_or_payload:
            artifacts[relative_path] = _csv_bytes(rows_or_payload)
        else:
            raise ValueError(f"missing canonical table artifact: {relative_path}")

    ordinary_artifacts = dict(artifacts)
    artifacts["artifact_index.json"] = build_artifact_index(ordinary_artifacts)
    artifacts["evaluation_manifest.json"] = build_completion_manifest(
        plan, ordinary_artifacts, identity_inputs, library_versions,
        bootstrap_replicates, bootstrap_seed, ci_policy, gate_states,
        created_utc, completed_utc, disposition, task_id=task_id,
    )
    return commit_output(
        output_root, plan, artifacts, overwrite=overwrite,
        writer=writer, replace=replace,
        absent_window_timeout_seconds=absent_window_timeout_seconds,
        publication_probe=publication_probe,
    )