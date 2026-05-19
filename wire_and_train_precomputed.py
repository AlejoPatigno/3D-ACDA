"""
wire_and_train_precomputed.py
=============================
Patched wiring script for two-stage usage:

1) Artifact notebook:
   - generate source concept targets
   - generate source Jacobian priors
   - generate target Jacobian priors
   - save CSV indices in a writable directory

2) Training notebook:
   - reuse an existing precomputed_artifacts_dir
   - skip all expensive artifact generation
   - only read MRI tensors + precomputed vectors

Relative to the original wiring file, the key new capability is:
    precomputed_artifacts_dir=...   -> load cached artifacts directly

This file remains compatible with the original on-the-fly mode through:
    recompute_artifacts=False/True
    cache_dir=...
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset


LABEL_MAP = {"CN": 0, "MCI": 1, "AD": 2}
INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}


def add_module_dir_to_path(module_dir: str | os.PathLike) -> None:
    module_dir = str(module_dir)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)


def load_tensor_like(obj_path: str) -> torch.Tensor:
    obj = torch.load(obj_path, map_location="cpu", weights_only=False)
    if isinstance(obj, dict):
        for key in ["x", "image", "mri", "tensor", "volume"]:
            if key in obj and torch.is_tensor(obj[key]):
                x = obj[key]
                break
        else:
            raise KeyError(f"Could not find tensor-like key in dict loaded from {obj_path}")
    elif torch.is_tensor(obj):
        x = obj
    else:
        raise TypeError(f"Unsupported object type loaded from {obj_path}: {type(obj)}")

    if x.ndim == 3:
        x = x.unsqueeze(0)
    if x.ndim != 4:
        raise ValueError(f"Expected MRI tensor with shape (1,H,W,D), got {tuple(x.shape)} from {obj_path}")
    return x.to(torch.float32)


def build_source_path_map() -> Dict[str, str]:
    path_map = {}
    for f in glob.glob("/kaggle/input/**/*.pt", recursive=True):
        fl = f.lower()
        if any(tok in fl for tok in ["c_target", "g_bar", "g_jacobian", "target_oasis", "oasis"]):
            continue
        basename = os.path.basename(f).replace(".pt", "")
        path_map[basename] = f
    return path_map


def resolve_source_x_path(row: pd.Series, source_path_map: Dict[str, str]) -> str:
    sub_id = str(row["Subject_ID"])
    if sub_id in source_path_map:
        return source_path_map[sub_id]
    for col in ["File_Path", "Raw_File_Path", "Processed_File_Path", "x_path"]:
        if col in row and pd.notna(row[col]) and os.path.exists(str(row[col])):
            return str(row[col])
    raise FileNotFoundError(f"Could not resolve source MRI path for Subject_ID={sub_id}")


def resolve_target_x_path(row: pd.Series, base_dir: str) -> str:
    sub_id = str(row["Subject_ID"])
    label = str(row["Label"])

    candidate = os.path.join(base_dir, "target_oasis", label, f"{sub_id}_MRI.pt")
    if os.path.exists(candidate):
        return candidate

    for col in ["Processed_File_Path", "File_Path", "Raw_File_Path", "x_path"]:
        if col in row and pd.notna(row[col]) and os.path.exists(str(row[col])):
            return str(row[col])
    raise FileNotFoundError(f"Could not resolve target MRI path for Subject_ID={sub_id}")


def build_inventory_dataframes(base_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    source_csv = os.path.join(base_dir, "source_labels.csv")
    target_csv = os.path.join(base_dir, "target_labels.csv")

    if not os.path.exists(source_csv):
        raise FileNotFoundError(f"Missing source CSV: {source_csv}")
    if not os.path.exists(target_csv):
        raise FileNotFoundError(f"Missing target CSV: {target_csv}")

    df_source = pd.read_csv(source_csv)
    df_target = pd.read_csv(target_csv)

    df_source = df_source[df_source["Label"].isin(LABEL_MAP)].reset_index(drop=True)
    df_target = df_target[df_target["Label"].isin(LABEL_MAP)].reset_index(drop=True)

    source_path_map = build_source_path_map()

    df_source = df_source.copy()
    df_source["subject_id"] = df_source["Subject_ID"].astype(str)
    df_source["label"] = df_source["Label"].astype(str)
    df_source["x_path"] = df_source.apply(lambda r: resolve_source_x_path(r, source_path_map), axis=1)

    df_target = df_target.copy()
    df_target["subject_id"] = df_target["Subject_ID"].astype(str)
    df_target["label"] = df_target["Label"].astype(str)
    df_target["x_path"] = df_target.apply(lambda r: resolve_target_x_path(r, base_dir), axis=1)

    return df_source[["subject_id", "label", "x_path"]], df_target[["subject_id", "label", "x_path"]]


def find_existing_atlas_path(explicit_atlas_path: Optional[str] = None) -> str:
    if explicit_atlas_path is not None and os.path.exists(explicit_atlas_path):
        return explicit_atlas_path

    patterns = [
        "/kaggle/input/**/*atlas*.nii*",
        "/kaggle/input/**/*aal*.nii*",
        "/kaggle/input/**/*harvard*oxford*.nii*",
        "/kaggle/input/**/*label*.nii*",
        "/kaggle/working/**/*atlas*.nii*",
    ]
    hits = []
    for pat in patterns:
        hits.extend(glob.glob(pat, recursive=True))
    hits = sorted(set(hits))
    if not hits:
        raise FileNotFoundError("Atlas file not found automatically. Please pass atlas_path explicitly.")
    return hits[0]


def ensure_simpleitk_or_raise() -> None:
    try:
        import SimpleITK  # noqa: F401
    except Exception as e:
        raise ImportError(
            "SimpleITK is required to compute g_bar Jacobian priors. "
            "Install it in Kaggle before running artifact generation."
        ) from e


def choose_template_x_path(df_source: pd.DataFrame) -> str:
    cn = df_source[df_source["label"] == "CN"].reset_index(drop=True)
    if len(cn) == 0:
        return str(df_source.iloc[0]["x_path"])
    return str(cn.iloc[0]["x_path"])


def _safe_name_from_path(path: str) -> str:
    base = os.path.basename(os.path.normpath(path)) or "dataset"
    digest = hashlib.md5(path.encode("utf-8")).hexdigest()[:8]
    return f"{base}_{digest}"


def _default_cache_dir(base_dir: str) -> str:
    return os.path.join("/kaggle/working", "derived_artifacts", _safe_name_from_path(base_dir))


def _validate_index_columns(df: pd.DataFrame, required: list[str], name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def _validate_subject_coverage(df_inventory: pd.DataFrame, df_index: pd.DataFrame, name: str) -> None:
    inv = set(df_inventory["subject_id"].astype(str).tolist())
    idx = set(df_index["subject_id"].astype(str).tolist())
    missing = sorted(inv - idx)
    if missing:
        head = missing[:10]
        raise ValueError(
            f"{name} does not cover all inventory subjects. Missing={len(missing)}. "
            f"First missing: {head}"
        )


def ensure_artifact_cache(
    base_dir: str,
    module_dir: str,
    atlas_path: str,
    recompute: bool = False,
    cache_dir: Optional[str] = None,
) -> dict:
    add_module_dir_to_path(module_dir)

    from atlas_utils import AtlasROIManager
    from concept_targets import ConceptTargetConfig, precompute_concept_targets_from_dataframe
    from jacobian_utils import JacobianConfig, precompute_jacobians_from_dataframe

    df_source, df_target = build_inventory_dataframes(base_dir)

    if cache_dir is None:
        cache_dir = _default_cache_dir(base_dir)

    artifacts_dir = cache_dir
    src_concepts_dir = os.path.join(artifacts_dir, "source_concepts")
    src_jac_dir = os.path.join(artifacts_dir, "source_jacobians")
    tgt_jac_dir = os.path.join(artifacts_dir, "target_jacobians")
    os.makedirs(src_concepts_dir, exist_ok=True)
    os.makedirs(src_jac_dir, exist_ok=True)
    os.makedirs(tgt_jac_dir, exist_ok=True)

    atlas_mgr = AtlasROIManager(atlas_path)
    template_x_path = choose_template_x_path(df_source)

    source_inventory_csv = os.path.join(artifacts_dir, "source_inventory.csv")
    target_inventory_csv = os.path.join(artifacts_dir, "target_inventory.csv")
    source_concepts_csv = os.path.join(artifacts_dir, "source_concepts_index.csv")
    source_jac_csv = os.path.join(artifacts_dir, "source_jacobians_index.csv")
    target_jac_csv = os.path.join(artifacts_dir, "target_jacobians_index.csv")
    cache_meta_json = os.path.join(artifacts_dir, "cache_meta.json")

    df_source.to_csv(source_inventory_csv, index=False)
    df_target.to_csv(target_inventory_csv, index=False)

    if recompute or not os.path.exists(source_concepts_csv):
        _, df_concepts = precompute_concept_targets_from_dataframe(
            df=df_source,
            atlas_mgr=atlas_mgr,
            x_column="x_path",
            label_column="label",
            subject_id_column="subject_id",
            output_dir=src_concepts_dir,
            cfg=ConceptTargetConfig(normal_class_name="CN"),
        )
        df_concepts.to_csv(source_concepts_csv, index=False)
    else:
        df_concepts = pd.read_csv(source_concepts_csv)

    if recompute or not os.path.exists(source_jac_csv):
        ensure_simpleitk_or_raise()
        df_src_jac = precompute_jacobians_from_dataframe(
            df=df_source,
            atlas_mgr=atlas_mgr,
            template_x_path=template_x_path,
            x_column="x_path",
            subject_id_column="subject_id",
            output_dir=src_jac_dir,
            cfg=JacobianConfig(),
        )
        df_src_jac.to_csv(source_jac_csv, index=False)
    else:
        df_src_jac = pd.read_csv(source_jac_csv)

    if recompute or not os.path.exists(target_jac_csv):
        ensure_simpleitk_or_raise()
        df_tgt_jac = precompute_jacobians_from_dataframe(
            df=df_target,
            atlas_mgr=atlas_mgr,
            template_x_path=template_x_path,
            x_column="x_path",
            subject_id_column="subject_id",
            output_dir=tgt_jac_dir,
            cfg=JacobianConfig(),
        )
        df_tgt_jac.to_csv(target_jac_csv, index=False)
    else:
        df_tgt_jac = pd.read_csv(target_jac_csv)

    meta = {
        "base_dir": base_dir,
        "cache_dir": artifacts_dir,
        "atlas_path": atlas_path,
        "template_x_path": template_x_path,
        "K": int(atlas_mgr.K),
        "n_source": int(len(df_source)),
        "n_target": int(len(df_target)),
    }
    with open(cache_meta_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return {
        "atlas_path": atlas_path,
        "template_x_path": template_x_path,
        "K": atlas_mgr.K,
        "df_source": df_source,
        "df_target": df_target,
        "df_concepts": df_concepts,
        "df_src_jac": df_src_jac,
        "df_tgt_jac": df_tgt_jac,
        "source_inventory_csv": source_inventory_csv,
        "target_inventory_csv": target_inventory_csv,
        "source_concepts_csv": source_concepts_csv,
        "source_jac_csv": source_jac_csv,
        "target_jac_csv": target_jac_csv,
        "cache_dir": artifacts_dir,
        "cache_meta_json": cache_meta_json,
    }


def load_precomputed_artifacts(
    base_dir: str,
    module_dir: str,
    atlas_path: str,
    precomputed_artifacts_dir: str,
) -> dict:
    add_module_dir_to_path(module_dir)
    from atlas_utils import AtlasROIManager

    artifacts_dir = str(precomputed_artifacts_dir)
    if not os.path.isdir(artifacts_dir):
        raise FileNotFoundError(f"precomputed_artifacts_dir does not exist: {artifacts_dir}")

    source_concepts_csv = os.path.join(artifacts_dir, "source_concepts_index.csv")
    source_jac_csv = os.path.join(artifacts_dir, "source_jacobians_index.csv")
    target_jac_csv = os.path.join(artifacts_dir, "target_jacobians_index.csv")
    source_inventory_csv = os.path.join(artifacts_dir, "source_inventory.csv")
    target_inventory_csv = os.path.join(artifacts_dir, "target_inventory.csv")
    cache_meta_json = os.path.join(artifacts_dir, "cache_meta.json")

    for path in [source_concepts_csv, source_jac_csv, target_jac_csv]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required precomputed index file: {path}")

    if os.path.exists(source_inventory_csv) and os.path.exists(target_inventory_csv):
        df_source = pd.read_csv(source_inventory_csv)
        df_target = pd.read_csv(target_inventory_csv)
    else:
        df_source, df_target = build_inventory_dataframes(base_dir)

    df_concepts = pd.read_csv(source_concepts_csv)
    df_src_jac = pd.read_csv(source_jac_csv)
    df_tgt_jac = pd.read_csv(target_jac_csv)

    _validate_index_columns(df_source, ["subject_id", "label", "x_path"], "source_inventory")
    _validate_index_columns(df_target, ["subject_id", "label", "x_path"], "target_inventory")
    _validate_index_columns(df_concepts, ["subject_id", "concept_target_path"], "source_concepts_index")
    _validate_index_columns(df_src_jac, ["subject_id", "g_bar_path"], "source_jacobians_index")
    _validate_index_columns(df_tgt_jac, ["subject_id", "g_bar_path"], "target_jacobians_index")

    _validate_subject_coverage(df_source, df_concepts, "source_concepts_index")
    _validate_subject_coverage(df_source, df_src_jac, "source_jacobians_index")
    _validate_subject_coverage(df_target, df_tgt_jac, "target_jacobians_index")

    atlas_mgr = AtlasROIManager(atlas_path)
    template_x_path = choose_template_x_path(df_source)

    payload = {
        "atlas_path": atlas_path,
        "template_x_path": template_x_path,
        "K": atlas_mgr.K,
        "df_source": df_source,
        "df_target": df_target,
        "df_concepts": df_concepts,
        "df_src_jac": df_src_jac,
        "df_tgt_jac": df_tgt_jac,
        "source_inventory_csv": source_inventory_csv if os.path.exists(source_inventory_csv) else None,
        "target_inventory_csv": target_inventory_csv if os.path.exists(target_inventory_csv) else None,
        "source_concepts_csv": source_concepts_csv,
        "source_jac_csv": source_jac_csv,
        "target_jac_csv": target_jac_csv,
        "cache_dir": artifacts_dir,
        "cache_meta_json": cache_meta_json if os.path.exists(cache_meta_json) else None,
    }

    if os.path.exists(cache_meta_json):
        try:
            payload["cache_meta"] = json.loads(Path(cache_meta_json).read_text())
        except Exception:
            payload["cache_meta"] = None

    return payload


def _index_by_subject(df: pd.DataFrame, path_col: str) -> Dict[str, str]:
    out = {}
    for _, row in df.iterrows():
        out[str(row["subject_id"])] = str(row[path_col])
    return out


def _load_vector(path: str, expected_last_dim: int) -> torch.Tensor:
    v = torch.load(path, map_location="cpu", weights_only=False)
    if not torch.is_tensor(v):
        raise TypeError(f"Expected tensor at {path}, got {type(v)}")
    v = v.to(torch.float32).view(-1)
    if v.numel() != expected_last_dim:
        raise ValueError(f"Expected vector with K={expected_last_dim} at {path}, got shape {tuple(v.shape)}")
    return v


class SourceDomainDatasetWired(Dataset):
    def __init__(self, df_source, df_concepts, df_src_jac, K: int):
        super().__init__()
        self.data = df_source.reset_index(drop=True)
        self.K = int(K)
        self.c_map = _index_by_subject(df_concepts, "concept_target_path")
        self.g_map = _index_by_subject(df_src_jac, "g_bar_path")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        sub_id = str(row["subject_id"])
        label_str = str(row["label"])

        x = load_tensor_like(str(row["x_path"]))
        y = torch.tensor(LABEL_MAP[label_str], dtype=torch.long)
        c_target = _load_vector(self.c_map[sub_id], expected_last_dim=self.K)
        g_bar = _load_vector(self.g_map[sub_id], expected_last_dim=self.K)

        return {
            "x": x,
            "y": y,
            "c_target": c_target,
            "g_bar": g_bar,
            "subject_id": sub_id,
            "label_name": label_str,
        }


class TargetDomainDatasetWired(Dataset):
    def __init__(self, df_target, df_tgt_jac, K: int):
        super().__init__()
        self.data = df_target.reset_index(drop=True)
        self.K = int(K)
        self.g_map = _index_by_subject(df_tgt_jac, "g_bar_path")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        sub_id = str(row["subject_id"])
        label_str = str(row["label"])

        x = load_tensor_like(str(row["x_path"]))
        y = torch.tensor(LABEL_MAP[label_str], dtype=torch.long)
        g_bar = _load_vector(self.g_map[sub_id], expected_last_dim=self.K)

        return {
            "x": x,
            "y": y,
            "g_bar": g_bar,
            "subject_id": sub_id,
            "label_name": label_str,
        }


def get_domain_adaptation_dataloaders_wired(
    base_dir: str,
    module_dir: str,
    atlas_path: str,
    batch_size: int = 2,
    num_workers: int = 2,
    recompute_artifacts: bool = False,
    cache_dir: Optional[str] = None,
    precomputed_artifacts_dir: Optional[str] = None,
):
    if precomputed_artifacts_dir is not None:
        cache = load_precomputed_artifacts(
            base_dir=base_dir,
            module_dir=module_dir,
            atlas_path=atlas_path,
            precomputed_artifacts_dir=precomputed_artifacts_dir,
        )
    else:
        cache = ensure_artifact_cache(
            base_dir=base_dir,
            module_dir=module_dir,
            atlas_path=atlas_path,
            recompute=recompute_artifacts,
            cache_dir=cache_dir,
        )

    K = int(cache["K"])
    source_dataset = SourceDomainDatasetWired(
        df_source=cache["df_source"],
        df_concepts=cache["df_concepts"],
        df_src_jac=cache["df_src_jac"],
        K=K,
    )
    target_dataset = TargetDomainDatasetWired(
        df_target=cache["df_target"],
        df_tgt_jac=cache["df_tgt_jac"],
        K=K,
    )

    use_pin_memory = torch.cuda.is_available()
    source_loader = DataLoader(
        source_dataset,
        batch_size=batch_size,
        shuffle=True,
        drop_last=True,
        num_workers=num_workers,
        pin_memory=use_pin_memory,
    )
    target_loader = DataLoader(
        target_dataset,
        batch_size=batch_size,
        shuffle=True,
        drop_last=True,
        num_workers=num_workers,
        pin_memory=use_pin_memory,
    )
    return source_loader, target_loader, cache


def build_patched_model(
    project_root: str,
    K: int,
    n_classes: int = 3,
    C_f: int = 256,
    C_t: int = 128,
    n_heads: int = 4,
    n_layers: int = 2,
    base_ch: int = 32,
):
    add_module_dir_to_path(project_root)
    from model import AlzheimerDomainAdaptationModel
    from model_patch_concept import ConceptBottleneck as PatchedConceptBottleneck

    model = AlzheimerDomainAdaptationModel(
        K=K,
        C_f=C_f,
        C_t=C_t,
        n_classes=n_classes,
        n_heads=n_heads,
        n_layers=n_layers,
        base_ch=base_ch,
    )
    model.cbm = PatchedConceptBottleneck(K=K, C_t=C_t, n_classes=n_classes)
    model.K = K
    return model


def train_model_with_wiring(
    base_dir: str,
    project_root: str,
    module_dir: str,
    atlas_path: Optional[str] = None,
    batch_size: int = 2,
    num_workers: int = 2,
    n_epochs_stage1: int = 5,
    n_epochs_stage2: int = 10,
    lr: float = 1e-4,
    weight_decay: float = 1e-4,
    recompute_artifacts: bool = False,
    save_dir: Optional[str] = None,
    cache_dir: Optional[str] = None,
    precomputed_artifacts_dir: Optional[str] = None,
):
    atlas_path = find_existing_atlas_path(atlas_path)
    add_module_dir_to_path(module_dir)
    add_module_dir_to_path(project_root)

    source_loader, target_loader, cache = get_domain_adaptation_dataloaders_wired(
        base_dir=base_dir,
        module_dir=module_dir,
        atlas_path=atlas_path,
        batch_size=batch_size,
        num_workers=num_workers,
        recompute_artifacts=recompute_artifacts,
        cache_dir=cache_dir,
        precomputed_artifacts_dir=precomputed_artifacts_dir,
    )

    K = int(cache["K"])
    from atlas_utils import AtlasROIManager
    from trainer import DomainAdaptationTrainer, TrainConfig
    from losses import TotalLoss

    atlas_mgr = AtlasROIManager(atlas_path)
    roi_weights = atlas_mgr.roi_weights_from_volume(power=0.0)

    model = build_patched_model(
        project_root=project_root,
        K=K,
        n_classes=len(LABEL_MAP),
    )

    loss_fn = TotalLoss(
        n_classes=len(LABEL_MAP),
        K=K,
        roi_weights=roi_weights,
        tau_p=0.90,
        margin=1.0,
        lambda_cls=1.0,
        lambda_proto=0.5,
        lambda_pl=0.3,
        lambda_cbm=0.5,
        lambda_anat=0.2,
        lambda_sep=0.1,
        label_smoothing=0.1,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    cfg = TrainConfig(
        n_epochs_stage1=n_epochs_stage1,
        n_epochs_stage2=n_epochs_stage2,
        lr=lr,
        weight_decay=weight_decay,
        num_workers=num_workers,
        device=device,
        log_every=10,
        use_amp=torch.cuda.is_available(),
    )

    trainer = DomainAdaptationTrainer(
        model=model,
        loss_fn=loss_fn,
        atlas_mgr=atlas_mgr,
        input_shape=(128, 128, 128),
        cfg=cfg,
    )

    history = trainer.fit(
        source_loader=source_loader,
        target_loader=target_loader,
        val_loader=None,
    )

    payload = {
        "K": K,
        "atlas_path": atlas_path,
        "template_x_path": cache["template_x_path"],
        "cache_dir": cache.get("cache_dir"),
        "precomputed_artifacts_dir": precomputed_artifacts_dir,
        "history": history,
        "train_cfg": asdict(cfg),
    }

    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        ckpt_path = os.path.join(save_dir, "alzheimer_da_cbm.pt")
        hist_path = os.path.join(save_dir, "history.json")
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "K": K,
                "atlas_path": atlas_path,
                "train_cfg": asdict(cfg),
                "history": history,
            },
            ckpt_path,
        )
        with open(hist_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        payload["checkpoint_path"] = ckpt_path
        payload["history_path"] = hist_path

    return payload
