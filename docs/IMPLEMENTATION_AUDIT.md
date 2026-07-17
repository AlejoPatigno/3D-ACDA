# Implementation Audit Log

Fecha de auditoria: 2026-07-17

Este documento resume todo lo nuevo implementado hasta la Fase 2 del repositorio
PADA-3DACB. Su objetivo es facilitar una auditoria tecnica del alcance, los
archivos creados y las garantias ya verificadas.

## Alcance Ejecutado

Se completaron:

- Fase 1: archivo de notebooks originales y mapa de migracion.
- Fase 2: esqueleto de paquete instalable, configuracion, paths,
  reproducibilidad, logging, scripts placeholder y tests.

No se inicio Fase 3 ni fases posteriores.

## Fase 1: Notebook Audit and Migration Map

### Notebooks Archivados

Se copiaron los cuatro notebooks canonicos a `notebooks/archive/` y se
limpiaron sus outputs sin modificar el codigo fuente de las celdas:

- `notebooks/archive/preprocess_original.ipynb`
- `notebooks/archive/precompute_original.ipynb`
- `notebooks/archive/training_original.ipynb`
- `notebooks/archive/baselines_original.ipynb`

Verificacion realizada durante la fase:

- Cada notebook archivado quedo con `outputs=0`.
- Cada celda de codigo quedo con `execution_count=None`.

### Documento de Migracion

Se creo y luego se corrigio:

- `docs/NOTEBOOK_MIGRATION_MAP.md`

Contenido principal:

- Mapa de responsabilidades por notebook.
- Identificacion de clases, funciones y bloques duplicados.
- Distincion entre pipeline completo de preprocessing y helpers NIfTI
  duplicados.
- Decision arquitectonica: la arquitectura publica final es `PADA-3DACB`.
- Exclusiones explicitas: `PADA-3DACB-Full`, `PADA-3DACB-Lite` como nombre
  publico, `ContextualROIEncoder` y activacion del encoder contextual.
- Transformacion documentada de Full a Lite/PADA-3DACB: flujo de tokens,
  dimensiones, entradas de attention/concept head, salidas y consecuencias para
  `state_dict`.
- Comparacion de definiciones de `AlzheimerDomainAdaptationModel`,
  `ConceptBottleneck` y `AnatomicalConsistencyLoss`.
- Inventario de definiciones sombreadas.
- Inventario de paths hard-coded y mapeo a futuros campos de configuracion.
- Dependencias observadas, separando modulos notebook-locales de dependencias
  externas.

## Fase 2: Package Skeleton, Configuration, Reproducibility and Logging

### Archivos de Metadata y Entorno

Se agregaron:

- `pyproject.toml`
- `requirements.txt`
- `environment.yml`
- `.gitignore`
- `README.md`
- `results/README.md`

Estrategia:

- `pyproject.toml` es la fuente canonica de metadata y dependencias.
- Dependencias runtime minimas: `numpy`, `PyYAML`, `torch`.
- Dependencias opcionales futuras: `pandas`, `nibabel`, `SimpleITK`, `monai`,
  `scikit-learn`.
- Dependencias dev: `pytest`, `ruff`.
- Los modulos notebook-locales no se declararon como dependencias externas.

### Paquete Python Creado

Se creo el paquete `src/pada3dacb/` con layout `src`.

Archivos implementados:

- `src/pada3dacb/__init__.py`
- `src/pada3dacb/config.py`
- `src/pada3dacb/exceptions.py`
- `src/pada3dacb/paths.py`
- `src/pada3dacb/training/reproducibility.py`
- `src/pada3dacb/training/experiment_logging.py`

Namespaces preparados con `__init__.py` minimo:

- `src/pada3dacb/data/`
- `src/pada3dacb/artifacts/`
- `src/pada3dacb/models/`
- `src/pada3dacb/adaptation/`
- `src/pada3dacb/losses/`
- `src/pada3dacb/training/`
- `src/pada3dacb/evaluation/`

No se implemento codigo cientifico en estos namespaces vacios.

### Excepciones Custom

Archivo:

- `src/pada3dacb/exceptions.py`

Excepciones definidas:

- `PADA3DACBError`
- `ConfigurationError`
- `InvalidPathError`
- `UnsupportedExperimentError`
- `PhaseNotImplementedError`

### Sistema de Configuracion

Archivo:

- `src/pada3dacb/config.py`

Dataclasses implementadas:

- `ProjectConfig`
- `PathsConfig`
- `DataConfig`
- `CohortConfig`
- `AtlasConfig`
- `ModelConfig`
- `TrainingConfig`
- `MonitoringConfig`
- `ExperimentConfig`

Capacidades implementadas:

- Carga YAML con `load_config(path)`.
- Validacion explicita con excepciones custom.
- Resolucion de paths relativos contra el directorio del archivo YAML.
- Serializacion a diccionario estable.
- Hash SHA-256 determinista de la configuracion.
- Hash corto con `short_hash(length=12)`.
- Guardado de configuracion resuelta con `save_resolved()`.

Reglas de validacion implementadas:

- Metodos permitidos: `source_only`, `coral`, `mmd`, `cdan`,
  `prototype_pseudo`, `baseline`.
- Cohorts permitidos: `ADNI`, `OASIS`.
- `source_domain != target_domain`.
- Para experimentos propuestos, `model.name == "PADA-3DACB"`.
- `model.contextual_encoder` debe ser `false`.
- `training.early_stopping` debe ser `false`.
- `warmup_epochs >= 0`.
- `full_epochs > 0`.
- `batch_size > 0`.
- `checkpoint_every > 0`.
- `evaluate_source_every > 0`.
- `evaluate_target_every > 0`.
- Configs con paths hard-coded prohibidos se rechazan durante validacion.
- Configs baseline pueden usar nombres de modelo baseline solo cuando
  `experiment.method == "baseline"`.

### Utilidades de Paths

Archivo:

- `src/pada3dacb/paths.py`

APIs implementadas:

- `resolve_path(value, base_dir=None, must_exist=False, required=False)`
- `ensure_directory(path)`
- `is_forbidden_hardcoded_path(value)`

Comportamiento:

- Expande variables de entorno.
- Expande `~`.
- Resuelve paths relativos contra `base_dir`.
- No crea directorios implicitamente en `resolve_path`.
- Crea directorios solo con `ensure_directory`.
- Rechaza strings vacios como path.
- Detecta familias de paths prohibidas de notebooks o usuario especifico.
- No hace busqueda recursiva ni discovery automatico de datasets.

### Reproducibilidad

Archivo:

- `src/pada3dacb/training/reproducibility.py`

APIs implementadas:

- `seed_everything(seed: int, deterministic: bool = True) -> None`
- `seed_worker(worker_id: int) -> None`
- `make_torch_generator(seed: int) -> torch.Generator`
- `collect_reproducibility_metadata() -> dict`

Comportamiento:

- Siembra `random`, NumPy, PyTorch CPU y CUDA si esta disponible.
- Activa comportamiento determinista de PyTorch cuando se solicita.
- Recoge metadata no privada: versiones de Python, NumPy, PyTorch, CUDA/cuDNN,
  disponibilidad CUDA, nombres de GPU y flags deterministas.

### Logging

Archivo:

- `src/pada3dacb/training/experiment_logging.py`

API implementada:

- `setup_experiment_logger(name, log_file=None, level=logging.INFO, context=None)`

Comportamiento:

- Logging a consola.
- Logging opcional a archivo UTF-8.
- Mensajes con timestamp.
- Contexto ordenado, por ejemplo `experiment`, `fold`, `seed`.
- Prevencion de handlers duplicados al reinicializar el mismo logger.
- No se implemento tracking de metricas.
- No se agregaron servicios externos como W&B, MLflow o TensorBoard.

### Configuraciones YAML

Se agregaron:

- `configs/data/paths.example.yaml`
- `configs/data/adni.yaml`
- `configs/data/oasis.yaml`
- `configs/model/pada3dacb.yaml`
- `configs/experiments/source_only.yaml`
- `configs/experiments/pada3dacb.yaml`
- `configs/experiments/coral.yaml`
- `configs/experiments/mmd.yaml`
- `configs/experiments/cdan.yaml`
- `configs/experiments/baselines.yaml`

Decisiones reflejadas:

- Modelo publico: `PADA-3DACB`.
- `contextual_encoder: false`.
- `early_stopping: false`.
- Rutas locales como `null` en ejemplos.
- Pesos/metodos no extraidos todavia como `null`.
- `pada3dacb.yaml` usa `method: prototype_pseudo`.
- `baselines.yaml` usa `method: baseline` y `baseline.name: null`.

### Scripts Placeholder

Se agregaron scripts import-safe con `main()` y guard
`if __name__ == "__main__":`.

Scripts:

- `scripts/verify_derivatives.py`
- `scripts/preprocess.py`
- `scripts/precompute_artifacts.py`
- `scripts/create_splits.py`
- `scripts/train.py`
- `scripts/evaluate.py`
- `scripts/evaluate_concepts.py`
- `scripts/reproduce_results.py`

Cada script falla explicitamente con `PhaseNotImplementedError` indicando la
fase futura correspondiente. No generan resultados, no descargan datos y no
implementan comportamiento cientifico.

### Tests Agregados

Se agregaron:

- `tests/test_imports.py`
- `tests/test_config.py`
- `tests/test_paths.py`
- `tests/test_reproducibility.py`
- `tests/test_logging.py`

Cobertura principal:

- Imports del paquete.
- Carga y validacion de configs validas.
- Rechazo de configuraciones invalidas.
- Reglas para `contextual_encoder`, `early_stopping`, modelo, metodos y cohorts.
- Hash de configuracion determinista.
- Resolucion de paths.
- Creacion explicita de directorios.
- Deteccion de paths prohibidos.
- Reproducibilidad de `random`, NumPy y PyTorch CPU.
- Logging a archivo UTF-8.
- No duplicacion de handlers de logging.

### Resultados de Verificacion Ejecutados

Ultimos resultados reportados al finalizar Fase 2:

```text
pip install -e .
Successfully installed pada3dacb-0.1.0
```

```text
python -c "import pada3dacb"
0.1.0
```

```text
pytest -q
29 passed in 12.64s
```

```text
ruff check .
All checks passed!
```

Tambien se verifico que `src/` no contuviera las familias de paths prohibidas
solicitadas.

## Exclusiones Deliberadas

No se implemento en Fase 2:

- MRI loading.
- NIfTI processing.
- Derivative verification.
- CerebrA atlas loading.
- Atlas resampling.
- Preprocessing.
- Artifact precomputation.
- Concept targets.
- Jacobians.
- Datasets o DataLoaders.
- Modelo PADA-3DACB.
- Losses cientificas.
- Source-only training.
- CORAL.
- MMD.
- CDAN.
- Prototype adaptation.
- Pseudo-labeling.
- Baselines.
- Metricas.
- Matrices de confusion.
- Concept validation.
- Reproduccion de resultados.

## Observaciones para Auditoria

- Los archivos `__pycache__/` pueden aparecer localmente tras ejecutar tests o
  imports; estan cubiertos por `.gitignore` y no son parte del entregable.
- La instalacion editable puede generar `*.egg-info/`; se agrego regla de
  ignore para esos artefactos.
- Ruff excluye notebooks archivados y scripts legacy de raiz que pertenecen al
  estado previo del repositorio. El lint de Fase 2 se aplica al scaffold nuevo.
- `.codex/` aparece como no trackeado en `git status`; contiene metadata local
  de Codex y no forma parte del paquete PADA-3DACB.

## Archivos Propuestos para Fase 3

Cuando se apruebe Fase 3, los archivos previstos son:

- `src/pada3dacb/data/derivative_verification.py`
- `src/pada3dacb/data/quality_control.py`
- `scripts/verify_derivatives.py`
- `docs/DERIVATIVE_VERIFICATION.md`
- `tests/test_derivative_verification.py`
- `tests/test_atlas_geometry.py`

Fase 3 no ha sido iniciada en el alcance historico de la seccion anterior.

## Actualizacion: Fases 3 a 5

La auditoria acumulada se amplio despues del scaffold inicial:

- Fase 3 agrego verificacion de derivados, geometria de atlas y control de calidad
  en `src/pada3dacb/data/derivative_verification.py` y `quality_control.py`.
- Fase 4 agrego discovery ADNI/OASIS, seleccion determinista, carga multiformato,
  normalizacion robusta, resize/crop-padding, tensores model-ready, manifiestos y
  procedencia en `src/pada3dacb/data/preprocessing.py` e `inventories.py`.
- Fase 5 agrego la precomputacion modular descrita a continuacion.

### Fase 5: Modulos Nuevos

- `src/pada3dacb/artifacts/atlas.py`: atlas discreto preparado, labels ordenados,
  mascaras ROI, hashes, validacion estricta de grid y exportacion de metadata.
- `src/pada3dacb/artifacts/regional_features.py`: pooling generico sin resampling.
- `src/pada3dacb/artifacts/concepts.py`: proxy canonical de tissue loss,
  normalizador CN por cohorte, sigmoide, serializacion y compatibilidad legacy.
- `src/pada3dacb/artifacts/jacobians.py`: Histogram Matching, Diffeomorphic Demons,
  determinante Jacobiano, `neg_log`, pooling ROI y normalizacion intra-sujeto.
- `src/pada3dacb/artifacts/cache.py`: inventario, validacion model-ready, sidecars,
  indice unificado, reanudacion independiente, fallos aislados y dry-run.
- `scripts/precompute_artifacts.py`: reemplazo del placeholder por el CLI Phase 5.
- `configs/precompute/default.yaml`: valores cientificos extraidos del notebook.
- `docs/PRECOMPUTE_ARTIFACTS.md`: contrato y ecuaciones implementadas.

Se modificaron `src/pada3dacb/artifacts/__init__.py` y
`src/pada3dacb/exceptions.py`. No se agrego resampling de atlas, no se modifican
derivados MRI, no se redisenaron conceptos ni normalizadores, y no se implemento
codigo de modelo, entrenamiento, adaptacion o baselines.
