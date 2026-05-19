"""
build_precomputed_artifacts.py
==============================
Standalone notebook-friendly builder for the expensive anatomical artifacts:

  - source concept targets        c_target
  - source Jacobian priors        g_bar
  - target Jacobian priors        g_bar
  - CSV indices                   source_concepts_index.csv,
                                  source_jacobians_index.csv,
                                  target_jacobians_index.csv

Typical use:

    from build_precomputed_artifacts import build_all_precomputed_artifacts

    result = build_all_precomputed_artifacts(
        base_dir="/kaggle/input/notebooks/alejopatio/preprocess-alzheimer/model_ready_data",
        module_dir="/kaggle/working/mri_da_missing",
        atlas_path="/kaggle/working/cerebra_prepared/CerebrA_discrete_resampled_to_reference.nii.gz",
        output_dir="/kaggle/working/precomputed_artifacts_cerebra",
        recompute=False,
    )
    print(result)

Then, in a separate training notebook, call:

    train_model_with_wiring(..., precomputed_artifacts_dir=result["artifacts_dir"])
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from wire_and_train_precomputed import (
    add_module_dir_to_path,
    build_inventory_dataframes,
    choose_template_x_path,
    ensure_simpleitk_or_raise,
    find_existing_atlas_path,
)


def build_all_precomputed_artifacts(
    base_dir: str,
    module_dir: str,
    atlas_path: Optional[str] = None,
    output_dir: str = "/kaggle/working/precomputed_artifacts",
    recompute: bool = False,
    source_concepts_subdir: str = "source_concepts",
    source_jacobians_subdir: str = "source_jacobians",
    target_jacobians_subdir: str = "target_jacobians",
) -> dict:
    """
    Builds and stores all expensive precomputed artifacts in a writable directory.

    Parameters
    ----------
    base_dir:
        Read-only directory containing source_labels.csv, target_labels.csv,
        target_oasis/, etc.
    module_dir:
        Directory containing atlas_utils.py, concept_targets.py, jacobian_utils.py.
    atlas_path:
        Prepared discrete atlas path. If None, auto-discovery is attempted.
    output_dir:
        Writable directory where all precomputed artifacts and index CSVs are stored.
    recompute:
        If True, overwrite existing CSV indices and per-subject artifact files.
    """
    atlas_path = find_existing_atlas_path(atlas_path)
    add_module_dir_to_path(module_dir)

    from atlas_utils import AtlasROIManager
    from concept_targets import ConceptTargetConfig, precompute_concept_targets_from_dataframe
    from jacobian_utils import JacobianConfig, precompute_jacobians_from_dataframe

    output_dir = str(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    src_concepts_dir = os.path.join(output_dir, source_concepts_subdir)
    src_jac_dir = os.path.join(output_dir, source_jacobians_subdir)
    tgt_jac_dir = os.path.join(output_dir, target_jacobians_subdir)
    os.makedirs(src_concepts_dir, exist_ok=True)
    os.makedirs(src_jac_dir, exist_ok=True)
    os.makedirs(tgt_jac_dir, exist_ok=True)

    df_source, df_target = build_inventory_dataframes(base_dir)
    atlas_mgr = AtlasROIManager(atlas_path)
    template_x_path = choose_template_x_path(df_source)

    source_inventory_csv = os.path.join(output_dir, "source_inventory.csv")
    target_inventory_csv = os.path.join(output_dir, "target_inventory.csv")
    source_concepts_csv = os.path.join(output_dir, "source_concepts_index.csv")
    source_jac_csv = os.path.join(output_dir, "source_jacobians_index.csv")
    target_jac_csv = os.path.join(output_dir, "target_jacobians_index.csv")
    meta_json = os.path.join(output_dir, "cache_meta.json")

    df_source.to_csv(source_inventory_csv, index=False)
    df_target.to_csv(target_inventory_csv, index=False)

    if recompute or not os.path.exists(source_concepts_csv):
        print("[1/3] Building source concept targets...")
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
        print("[1/3] Reusing source concept targets index...")
        df_concepts = pd.read_csv(source_concepts_csv)

    if recompute or not os.path.exists(source_jac_csv):
        print("[2/3] Building source Jacobian priors...")
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
        print("[2/3] Reusing source Jacobian priors index...")
        df_src_jac = pd.read_csv(source_jac_csv)

    if recompute or not os.path.exists(target_jac_csv):
        print("[3/3] Building target Jacobian priors...")
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
        print("[3/3] Reusing target Jacobian priors index...")
        df_tgt_jac = pd.read_csv(target_jac_csv)

    meta = {
        "base_dir": base_dir,
        "artifacts_dir": output_dir,
        "atlas_path": atlas_path,
        "template_x_path": template_x_path,
        "K": int(atlas_mgr.K),
        "n_source": int(len(df_source)),
        "n_target": int(len(df_target)),
        "source_inventory_csv": source_inventory_csv,
        "target_inventory_csv": target_inventory_csv,
        "source_concepts_csv": source_concepts_csv,
        "source_jac_csv": source_jac_csv,
        "target_jac_csv": target_jac_csv,
    }
    Path(meta_json).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("\n[OK] Precomputed artifacts ready.")
    print(f"Artifacts dir: {output_dir}")
    print(f"K = {atlas_mgr.K}")
    print(f"Source subjects = {len(df_source)}")
    print(f"Target subjects = {len(df_target)}")

    return meta
