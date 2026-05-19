"""
wire_and_train.py
=================
Wires together:
  - existing model.py / losses.py
  - the missing modules already created:
        atlas_utils.py
        concept_targets.py
        jacobian_utils.py
        trainer.py
        model_patch_concept.py
  - the user's Kaggle-style data layout

This script is based on the user's working dataloader pattern, but upgrades it so
that batches satisfy the mathematical contract required by Stage I and Stage II:

    Source batch: {x, y, c_target, g_bar, subject_id, label_name}
    Target batch: {x, y, g_bar, subject_id, label_name}

Key fixes relative to the base example:
  1) target batches now include g_bar, which Stage II needs.
  2) both c_target and g_bar are cached if missing.
  3) K is taken from the atlas, not from hard-coded defaults.
  4) the concept head is patched so it matches c_{n,k}=sigmoid(w_k^T u_{n,k}+b_k).
  5) the model is trained through the CBM logits, matching the more interpretable
     option stated in the Materials and Methods.

Expected environment:
  - Kaggle-style mounted data.
  - model.py and losses.py available in the working directory or a project folder.
  - SimpleITK installed if Jacobian priors must be computed from scratch.
"""

from __future__ import annotations

import os
import sys
import glob
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader


# ---------------------------------------------------------------------
# 0) LABEL MAP
# ---------------------------------------------------------------------
LABEL_MAP = {
    "CN": 0,
    "MCI": 1,
    "AD": 2,
}
INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}


# ---------------------------------------------------------------------
# 1) PATH BOOTSTRAP
# ---------------------------------------------------------------------
def add_module_dir_to_path(module_dir: str | os.PathLike) -> None:
    module_dir = str(module_dir)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)


def resolve_single_path(candidates) -> str:
    candidates = [str(p) for p in candidates if p and os.path.exists(str(p))]
    if not candidates:
        raise FileNotFoundError("No valid path found among candidates.")
    return candidates[0]


def discover_project_file(filename: str, search_roots: list[str]) -> str:
    hits = []
    for root in search_roots:
        if not root or not os.path.exists(root):
            continue
        hits.extend(glob.glob(os.path.join(root, "**", filename), recursive=True))
    hits = sorted(set(hits))
    if not hits:
        raise FileNotFoundError(f"Could not find {filename!r} in the provided roots.")
    return hits[0]


# ---------------------------------------------------------------------
# 2) ROBUST .pt LOADING
# ---------------------------------------------------------------------
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
        x = x.unsqueeze(0)  # (1,H,W,D)
    if x.ndim != 4:
        raise ValueError(f"Expected MRI tensor with shape (1,H,W,D), got {tuple(x.shape)} from {obj_path}")
    return x.to(torch.float32)


# ---------------------------------------------------------------------
# 3) METADATA RESOLUTION FROM THE USER'S BASE LAYOUT
# ---------------------------------------------------------------------
def build_source_path_map() -> Dict[str, str]:
    """
    Mirrors the user's base example: dynamically searches /kaggle/input for ADNI .pt
    tensors while excluding cached concept/Jacobian artifacts and OASIS files.
    """
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

    # fallback to whichever path-like columns may exist in the CSV
    for col in ["File_Path", "Raw_File_Path", "Processed_File_Path", "x_path"]:
        if col in row and pd.notna(row[col]) and os.path.exists(str(row[col])):
            return str(row[col])

    raise FileNotFoundError(f"Could not resolve source MRI path for Subject_ID={sub_id}")


def resolve_target_x_path(row: pd.Series, base_dir: str) -> str:
    sub_id = str(row["Subject_ID"])
    label = str(row["Label"])

    # First try the normalized storage layout produced in preprocessing.
    candidate = os.path.join(base_dir, "target_oasis", label, f"{sub_id}_MRI.pt")
    if os.path.exists(candidate):
        return candidate

    # Then trust any explicit path in the CSV if present.
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
    df_target = df_target.copy()

    df_source["subject_id"] = df_source["Subject_ID"].astype(str)
    df_source["label"] = df_source["Label"].astype(str)
    df_source["x_path"] = df_source.apply(lambda r: resolve_source_x_path(r, source_path_map), axis=1)

    df_target["subject_id"] = df_target["Subject_ID"].astype(str)
    df_target["label"] = df_target["Label"].astype(str)
    df_target["x_path"] = df_target.apply(lambda r: resolve_target_x_path(r, base_dir), axis=1)

    return df_source[["subject_id", "label", "x_path"]], df_target[["subject_id", "label", "x_path"]]


# ---------------------------------------------------------------------
# 4) ARTIFACT CACHE CREATION (K and L)
# ---------------------------------------------------------------------
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
        raise FileNotFoundError(
            "Atlas file not found automatically. Please pass atlas_path explicitly."
        )
    return hits[0]


def ensure_simpleitk_or_raise():
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
        # fallback: first source sample
        return str(df_source.iloc[0]["x_path"])
    return str(cn.iloc[0]["x_path"])


def ensure_artifact_cache(
    base_dir: str,
    module_dir: str,
    atlas_path: str,
    recompute: bool = False,
) -> dict:
    add_module_dir_to_path(module_dir)

    from atlas_utils import AtlasROIManager
    from concept_targets import (
        ConceptTargetConfig,
        precompute_concept_targets_from_dataframe,
    )
    from jacobian_utils import (
        JacobianConfig,
        precompute_jacobians_from_dataframe,
    )

    df_source, df_target = build_inventory_dataframes(base_dir)

    artifacts_dir = os.path.join(base_dir, "derived_artifacts")
    src_concepts_dir = os.path.join(artifacts_dir, "source_concepts")
    src_jac_dir = os.path.join(artifacts_dir, "source_jacobians")
    tgt_jac_dir = os.path.join(artifacts_dir, "target_jacobians")
    os.makedirs(artifacts_dir, exist_ok=True)

    atlas_mgr = AtlasROIManager(atlas_path)
    template_x_path = choose_template_x_path(df_source)

    source_concepts_csv = os.path.join(artifacts_dir, "source_concepts_index.csv")
    source_jac_csv = os.path.join(artifacts_dir, "source_jacobians_index.csv")
    target_jac_csv = os.path.join(artifacts_dir, "target_jacobians_index.csv")

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

    return {
        "atlas_path": atlas_path,
        "template_x_path": template_x_path,
        "K": atlas_mgr.K,
        "df_source": df_source,
        "df_target": df_target,
        "df_concepts": df_concepts,
        "df_src_jac": df_src_jac,
        "df_tgt_jac": df_tgt_jac,
        "source_concepts_csv": source_concepts_csv,
        "source_jac_csv": source_jac_csv,
        "target_jac_csv": target_jac_csv,
    }


# ---------------------------------------------------------------------
# 5) DATASETS AND DATALOADERS (adapted from the user's base example)
# ---------------------------------------------------------------------
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
):
    cache = ensure_artifact_cache(
        base_dir=base_dir,
        module_dir=module_dir,
        atlas_path=atlas_path,
        recompute=recompute_artifacts,
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


# ---------------------------------------------------------------------
# 6) MODEL FACTORY WITH CONCEPT-HEAD PATCH
# ---------------------------------------------------------------------
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

    # Replace only the CBM module so the math matches Section J exactly.
    model.cbm = PatchedConceptBottleneck(K=K, C_t=C_t, n_classes=n_classes)
    model.K = K
    return model


# ---------------------------------------------------------------------
# 7) TRAINING ENTRY POINT
# ---------------------------------------------------------------------
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

    cfg = TrainConfig(
        n_epochs_stage1=n_epochs_stage1,
        n_epochs_stage2=n_epochs_stage2,
        lr=lr,
        weight_decay=weight_decay,
        num_workers=num_workers,
        device="cuda",
        log_every=10,
        use_amp=True,
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


# ---------------------------------------------------------------------
# 8) EXAMPLE CALL
# ---------------------------------------------------------------------
# Example usage inside Kaggle / notebook:
#
# MODULE_DIR  = "/kaggle/working/mri_da_missing"
# PROJECT_ROOT = "/kaggle/working/your_project"   # folder that contains model.py and losses.py
# BASE_DIR    = "/kaggle/input/notebooks/alejopatio/preprocess-alzheimer/model_ready_data"
# ATLAS_PATH  = "/kaggle/input/your_atlas/atlas_labels.nii.gz"
#
# result = train_model_with_wiring(
#     base_dir=BASE_DIR,
#     project_root=PROJECT_ROOT,
#     module_dir=MODULE_DIR,
#     atlas_path=ATLAS_PATH,
#     batch_size=2,
#     num_workers=2,
#     n_epochs_stage1=5,
#     n_epochs_stage2=10,
#     lr=1e-4,
#     weight_decay=1e-4,
#     recompute_artifacts=False,
#     save_dir="/kaggle/working/exp_da_cbm",
# )
# print(result)
