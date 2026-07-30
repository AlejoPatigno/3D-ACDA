# Phase 6 Report

Fecha: 2026-07-18. Estado: completada; Phase 7 no iniciada.

## Implementacion y Fuentes

Archivos creados: `data/records.py`, `artifact_wiring.py`, `datasets.py`,
`loaders.py`, `splits.py`; `configs/data/datasets.yaml`;
`configs/splits/default.yaml`; `docs/DATASETS_AND_SPLITS.md`; seis suites Phase
6 y un helper sintetico. Modificados: `data/__init__.py`, `exceptions.py`,
`scripts/create_splits.py`, `pyproject.toml` y `IMPLEMENTATION_AUDIT.md`.

Simbolos migrados: `LabeledMRIDatasetWired`,
`UnlabeledTargetAdaptDataset`, `SourceDomainDatasetWired`,
`TargetDomainDatasetWired`, `ClassificationOnlyMRIDataset`,
`SupervisedMRIDatasetWired`, `stratified_subject_split`,
`_make_stratified_splits`, path/index wiring y defaults DataLoader.

Las definiciones tempranas hacian discovery Kaggle y datasets separados; las
finales wired consumian indices y devolvian diccionarios. Training queda
canonico para source/target y baselines para supervised. Se excluyeron discovery
global, modelos, trainers, losses y arquitecturas baseline.

Discrepancia target: `stratified_subject_split` define 80/20 fijo, mientras
ejecuciones posteriores aplican `StratifiedKFold` target por fold. La decision
fija Phase 6 exige un target unico entre folds/metodos; produccion usa el 80/20
estratificado y documenta la eliminacion del target por fold.

## Records, Wiring y Datasets

`SubjectRecord` contiene ID/hash, cohorte, clase/indice, paths derivative,
concept/Jacobian, hashes, estados, fila original y metadata. Identidad:
`cohort:subject_hash`. Mapping fijo: `CN=0`, `MCI=1`, `AD=2`.

El wiring resuelve paths relativos contra artifact root, conserva absolutos y
solo permite remapping old/new prefix explicito y registrado. Rechaza duplicados,
cohorts/classes invalidos, mapping conflictivo, estados fallidos y archivos
requeridos ausentes. No busca reemplazos ni repara/recalcula artefactos.

Perfiles: `classification_only`; `source_with_concepts`;
`source_with_anatomy`; `source_full_artifacts`; `target_adaptation`;
`target_evaluation`. MRI: CPU float32 `(1,H,W,D)` finito. Concept/Jacobian: CPU
float32 `(K,)` finito.

Claves exactas:

- Source: `x,y,c_target,g_bar,subject_id,subject_hash,cohort,label_name`.
- Target adaptation: `x,subject_id,subject_hash,cohort`; nunca `y`.
- Target evaluation: `x,y,subject_id,subject_hash,cohort,label_name`.
- Supervised: contrato evaluation; artefactos solo por perfil explicito.

`c_target` preserva el consumidor training. `subject_hash` y `cohort` son
metadata de produccion agregada a los notebooks; no crean supervision target.
La validacion de inicializacion carga y valida tensores antes del worker.

## Splits, Hashes y Loaders

Source: `StratifiedKFold(5, shuffle=True, random_state=42)`, sujeto completo,
cada sujeto valida una vez, sin reduccion silenciosa de folds. Target: una sola
particion estratificada 80% adaptation / 20% evaluation con seed 42. Direcciones
`ADNI_to_OASIS` y `OASIS_to_ADNI` se calculan independientemente.

Manifests: `source_folds.csv`, `target_split.csv`, `class_counts.csv`,
`protocol.json`, resumen JSON/Markdown y YAML resuelto. El assignment hash usa
cohorte, hash, label, fold y particion, sin paths/timestamps. Manifests validos
se reutilizan; incompatibilidad falla salvo `overwrite`. Dry-run no escribe el
directorio final.

Loaders train source y target adaptation: `shuffle=True`, `drop_last=True`.
Validation/evaluation: `shuffle=False`, `drop_last=False`. Defaults: batch 16,
workers 2, pin memory true, persistent false, prefetch 2. Todos usan generator
y `seed_worker`; tests CPU usan workers 0.

## Verificacion

```text
python -m pip install -e .                         exit 0
python -c "import pada3dacb; print(...)"           exit 0, 0.1.0
python -m pytest -q                                exit 0
91 passed, 2 warnings in 382.75s
python -m ruff check .                             exit 0
All checks passed!
```

Las warnings son las dos existentes de `std()` en el caso degenerado Phase 4.
Paridad: mapping entero exacto; assignments reproducen sklearn con seed 42;
hashes y orden son exactos; tensores usan validacion exacta de shape/dtype y
finitud; loaders reproducen shuffle/drop_last finales.

Smoke sintetico, 15 sujetos por cohorte (5 por clase):

```text
ADNI -> OASIS                     exit 0
assignment c7b7322103aa77d1800745a53c486bfd9e52559cf42b9f89d77789f4f01c4099
OASIS -> ADNI                     exit 0
assignment bc670460e9773118c78175d5a241c59d234ca10f031ec01e7c5dd14c498fa01b
--all-directions                  exit 0, mismos hashes
--all-directions --dry-run        exit 0, ningun directorio final
```

Outputs: `artifacts/phase6_smoke/both/{ADNI_to_OASIS,OASIS_to_ADNI}` con los
siete archivos de manifest/provenance por direccion.

## Confirmaciones y Limitaciones

No se ejecuto preprocessing; no se recomputaron artefactos; no se refitieron
normalizadores ni se agrego normalizacion por fold; no se agrego target-label
firewall; no se implementaron modelos, losses, training, source-only, CORAL,
MMD ni CDAN. Phase 7 no se inicio.

Limitaciones: se requiere soporte de clase suficiente para cinco folds y split
target estratificado; no se generaron splits de cohortes reales.

Propuesta Phase 7, no creada: `models/encoder3d.py`, `models/roi_tokens.py`,
`models/concept_bottleneck.py`, `models/pada3dacb.py`, configuracion,
documentacion y tests de paridad de arquitectura/forward/state dict.
