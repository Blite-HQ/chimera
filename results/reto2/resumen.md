# Reto 2 -- kernel cuantico vs baseline clasico, resuelto EN la plataforma

Regenerar: `uv run python challenges/reto2/run_all.py`

Corpus completo: **3276 filas, 5 folds**. Runtime total: 27.6s.

## 1 · Sello previo de folds

`folds_digest = e813a260c5deada66fd8ea51ed7324254ebff9ff3e8b9bc2cacd87bea4a4261d`

Comprometido por labels+seed SOLAMENTE, declarado ANTES de correr cualquiera de los dos brazos (compromiso previo, Dwork et al. 2015 -- spec `docs/specs/generalidad-retos.md` §Contrato-4).

## 2 · Brazo cuantico (kernel de fidelidad + SVM precomputado)

| fold | m_train | m_test | λ_min (pre-reparacion) | reparacion PSD | accuracy |
| ---- | ------- | ------ | ---------------------- | -------------- | -------- |
| 0    | 2620    | 656    | -4.43e-13              | clip           | 0.6616   |
| 1    | 2621    | 655    | -4.57e-13              | clip           | 0.6870   |
| 2    | 2621    | 655    | -3.82e-13              | clip           | 0.6718   |
| 3    | 2621    | 655    | -5.71e-13              | clip           | 0.6824   |
| 4    | 2621    | 655    | -2.32e-13              | clip           | 0.7008   |

Accuracy OOF agregada (brazo cuantico, 3276 filas): **0.6807**.

## 3 · Brazo clasico -- MISMO pipeline que el cuantico (CERTIFICADO)

SVM-RBF ajustado sobre las MISMAS matrices preparadas que el brazo cuantico (`prep["prepared"]`/`prep["folds"]`, modo `prepared_folds` de `blite.ml.classifier_baseline`) -- el unico grado de libertad entre los dos brazos es el KERNEL, no el preprocesamiento (`knowledge/quantum/07-catalogo-algoritmos.md` §1.3).

- accuracy: **0.6838**
- precision: 0.5854
- recall: 0.6405
- f1: 0.6117

### 3b · Informativo, fuera del certificado -- SVM-RBF sobre features CRUDAS

Mismo SVM-RBF CV-5, pero sobre las 9 features crudas (sin la seleccion top-4 por RandomForest ni el escalado a [0, π] del pipeline del brazo cuantico) -- muestra cuanto aporta el preprocesamiento frente al kernel en si mismo. **NO participa** del McNemar certificado (§4): un RBF sobre features crudas sin escalar mide la falta de preprocesamiento, no el kernel.

- accuracy: 0.5995 (informativo, no certificado)

## 4 · McNemar (mismo pipeline+folds, ambos brazos) -- CERTIFICADO

- b (clasico acierta, cuantico falla): 81
- c (cuantico acierta, clasico falla): 71
- p-valor (binomial exacto, dos colas): 0.4655

**Lectura**: el brazo cuantico es **competitivo** frente al baseline clasico (sin significancia estadistica para afirmar mas) (Δaccuracy = -0.0031, McNemar p = 0.4655) -- regla de lenguaje de `knowledge/quantum/04-estadistica-evidencia.md` §6: "competitivo" salvo significancia estadistica GENUINA y a favor del brazo cuantico; si el brazo cuantico rinde peor, se dice llanamente. Esta lectura usa el brazo clasico de MISMO pipeline (§3), nunca el de features crudas (§3b) -- comparar contra ese ultimo confundiria kernel con preprocesamiento.

## 5 · Certificado (synthetic-binary)

- Nivel titular: **AL2**
- Anclas: ['dataset', 'rule']
- Veredicto de la conclusion: **verified**
- Verificado offline: `uv run python scripts/verify-bundle.py results/reto2/certificado_synthetic-binary.json`

## 6 · Honestidad

- **Los datos son SINTETICOS** (`knowledge/tabular/corpus/synthetic-binary.json`, campo `caveats`): generados deterministicamente con `numpy.random.default_rng` (semilla fija), NO provienen de ningun CSV real ni de la fuente oficial del reto (no obtenible sin red en este entorno). Cualquier claim de un clasificador entrenado sobre este corpus es una afirmacion sobre ESTE CSV sellado (identificado por su digest), JAMAS una prediccion sobre un fenomeno del mundo real.
- El leg `ground_truth` del certificado es un PISO DE CORDURA (la accuracy recomputada por el verificador -- nunca la que el claim reporta -- contra el baseline trivial de predecir siempre la clase mayoritaria, tolerancia relativa 0.5), NO un gate de desempeño frente al baseline clasico -- esa pregunta la responde McNemar (§4), fuera del verificador.
- **Nivel titular AL2, no AL3**: `distributions/chimera/policies/reto2-statistical.yaml` declara `min_level: AL3`, pero `titular_level = mín(level_efectivo)` sobre las DOS patas (freeze §7 T2, `blite.certificate.predicate.compute_titular_level`) y `PropertyRuleVerifier` topa deliberadamente en AL2 (sin prueba formal -- docstring de `blite.verification.property_rule`): cualquier claim `statistical` verificado por estas DOS patas concretas queda en AL2, nunca AL3. `check_bundle` (punto 7) exige `required_legs`/`required_anchors` de la Policy pero NO exige `min_level` -- por eso el bundle pasa 8/8 igual. Esta tensión ya existe en la Policy tal como la entregó la spec (§Contrato-5); queda documentada aquí, no oculta.
- Si el CSV oficial CC0 del reto se vuelve disponible en este entorno, su digest SUPERSEDE a este (se reporta, no se sobreescribe); el pipeline (`tabular_prep` -> `fidelity_kernel` -> `svm_precomputed` / `classifier_baseline`) no cambia, porque el corpus es DATO, no codigo.
