# Phase 5 Report

Fecha: 2026-07-17. Estado: completada; Phase 6 no iniciada.

## Implementacion

Archivos creados: `artifacts/atlas.py`, `concepts.py`, `jacobians.py`,
`regional_features.py`, `cache.py`; `configs/precompute/default.yaml`;
`docs/PRECOMPUTE_ARTIFACTS.md`; seis archivos de test Phase 5. Archivos
modificados: `artifacts/__init__.py`, `exceptions.py`,
`scripts/precompute_artifacts.py` y `docs/IMPLEMENTATION_AUDIT.md`.

Simbolos migrados desde `precompute_original.ipynb`: `AtlasConfig`,
`AtlasROIManager`, `load_label_atlas`, `infer_label_values`,
`ConceptTargetConfig`, `ConceptNormalizer`, `extract_tissue_loss_proxy`,
`fit_concept_normalizer`, `build_subject_concept_target`,
`precompute_concept_targets_from_dataframe`, `JacobianConfig`,
`estimate_displacement_field`, `jacobian_determinant_from_displacement`,
`apply_psi`, `pool_roi_deformation`, `compute_g_bar_from_template_and_subject`,
`precompute_jacobians_from_dataframe`, conversion/guardado de tensor plano y
`build_all_precomputed_artifacts` (alias de la orquestacion de cache).

Excluidos deliberadamente: preparacion/resampling CerebrA, discovery automatico,
datasets/DataLoaders, splits, modelos, losses, trainer, loops, baselines,
metricas y reproduccion de resultados.

## Contratos Cientificos

Atlas: NIfTI 3D preparado, labels finitos e integer-like, background `0`
excluido, orden numerico ascendente, `K=102` por defecto y mascaras float32
`(K,H,W,D)` no vacias. El grid debe coincidir exactamente con el tensor MRI;
no existe ruta de resampling.

Concepto: foreground `x>0`; `q_n=percentile(foreground,20)`;
`s[n,k]=mean(x[v]<=q_n, v in ROI_k)`. Por cada cohorte/inventario suministrado,
el normalizador usa todos los sujetos `CN`, calcula `mu=mean(s)` y
`sigma=std(s,ddof=0)` por ROI, y produce
`sigmoid((s-mu)/(sigma+1e-6))`. No hay clipping adicional ni normalizador por
fold. Su JSON incluye estadisticas, labels ROI, poblacion de ajuste, composicion,
hashes de configuracion/inventario y version.

Jacobiano: template=fixed, sujeto=moving; spacing voxel `(1,1,1)`; histogram
matching (128 niveles, 10 puntos); Diffeomorphic Demons (50 iteraciones,
standard deviation 1.0); suavizado recursive Gaussian 1.0; determinante de
SimpleITK; `psi(J)=-log(clip(J,1e-6,infinity))`; media ROI; y
`g_bar=sigmoid((g-mean(g))/(std(g)+1e-6))`. No se guardan campos ni volumenes
intermedios por defecto.

Outputs concepto y Jacobiano: tensor CPU float32 finito `(K,)`, con orden ROI
del atlas. Tolerancias de paridad: operaciones enteras exactas; float32
`allclose` con defaults NumPy/PyTorch; determinante sintetico interior
`atol=1e-5`.

## Cache y Ejecucion

Estructura: `atlas/`, `concepts/normalizers/`, `concepts/subjects/`,
`jacobians/subjects/`, `sidecars/`, `artifact_index.csv`, `failures.csv`,
`skipped.csv`, resumen JSON/Markdown, config resuelta y metadata. El indice
incluye identidad, cohorte/clase, paths, estados independientes, hashes,
shapes, fila original, runtime, warnings y errores.

Resume solo salta un branch si tensor y sidecar cargan y coinciden en forma,
dtype, finitud, hash de atlas, hash precompute y derivado. Un artefacto corrupto
o incompatible se reporta y solo se reemplaza con `overwrite`. Escritura de
tensores/JSON es atomica. Dry-run valida y escribe exclusivamente plan/reportes;
no crea atlas cache, normalizadores ni vectores.

Discrepancia resuelta: la ultima celda precompute guarda algunos vectores en
diccionarios, mientras el loader posterior de training exige `torch.Tensor`
plano. Se preservo el consumidor efectivo: tensor plano y metadata en sidecar.
La normalizacion se mantiene por cohorte porque el builder canonico invoca el
ajuste por separado para source y target.

Limitaciones: SimpleITK es opcional pero obligatorio al activar Jacobianos;
ejecucion default de un worker y un sujeto a la vez; no se inventaron tiempos
de cohort completo. No se ejecuto computation sobre cohortes reales.

## Verificacion

Comandos de aceptacion:

```text
<python> -m pip install -e .                     exit 0
<python> -c "import pada3dacb; print(...)"       exit 0, 0.1.0
<python> -m pytest -q                            exit 0
72 passed, 2 warnings in 284.10s
<python> -m ruff check .                         exit 0
All checks passed!
```

Las dos warnings pertenecen al caso degenerado de `std()` ya existente en la
normalizacion Phase 4 y su referencia de test.

Smoke tests sinteticos (shape 4, dos ROIs, Demons de una iteracion solo para el
fixture) ejecutaron `scripts/precompute_artifacts.py` con:

```text
--compute-concepts --no-jacobians --overwrite    exit 0
--no-concepts --compute-jacobians --overwrite    exit 0
--compute-concepts --compute-jacobians --overwrite exit 0
```

Outputs persistentes: `artifacts/phase5_smoke/concept_only`,
`jacobian_only` y `combined`. Los tres contienen `artifact_index.csv`; el
combinado contiene `concepts/subjects/smoke01.pt` y
`jacobians/subjects/smoke01.pt`, ambos con estado `COMPUTED`.

## Confirmaciones y Phase 6

No se agrego atlas resampling; no se modifico ningun derivado de preprocessing;
no se redisenaron conceptos ni normalizacion; no se agrego normalizador por
fold; no se implementaron modelos, training, source-only, CORAL, MMD, CDAN,
prototipos, pseudo-labeling ni baselines.

Archivos propuestos, no creados, para Phase 6:
`src/pada3dacb/data/datasets.py`, `src/pada3dacb/data/splits.py`,
`scripts/create_splits.py`, configuracion/documentacion y tests de contratos de
batches, resolucion de paths de cache y splits estratificados deterministas.
