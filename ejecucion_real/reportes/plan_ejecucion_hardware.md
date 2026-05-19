# Plan de Ejecución — Estudio Exhaustivo Shor N=15 (RegisterQC)

**Fecha**: 2026-02-16  
**Cuenta IBM Quantum**: Trial (~25 días restantes)  
**Config base**: `RegisterQC, a=4, opt=3, approx=0.7, layout=sabre, routing=sabre, PT=ON, DD=OFF`

---

## Resumen

| Métrica | Valor |
|---------|:-----:|
| Configs ejecutadas | **15** |
| Configs faltantes críticas (Lista A) | **59** |
| Configs faltantes secundarias (Lista B) | **~11** |
| Configs faltantes exploratorias (Lista C) | **~20** |
| **Total configs para estudio completo** | **~105** |
| Tiempo QPU estimado total | **~84 s** |
| Jobs QPU total | **~28** |

---

## Fase 1: Simulaciones Ideales (22 configs — ~4 min)

**Día 1** — Sin costo, sin cola, respuesta inmediata.

**Propósito**: Establecer la línea base perfecta (señal 100%) para cada configuración y medir profundidades de circuito post-transpilación.

### Configs a ejecutar

#### A1 - Barrido approx_degree (6 configs)
```bash
# a=4, opt=3, layout=sabre, routing=sabre, PT=ON, DD=OFF, backend=ideal
for APPROX in 0.5 0.6 0.7 0.8 0.9 1.0; do
    python main.py --config config_ideal_study.ini \
        --override "random_a=4" \
        --override "approximation_degree=$APPROX" \
        --override "backend_type=ideal"
done
```

#### A2 - Barrido opt_level (4 configs)
```bash
# a=4, approx=0.7, layout/routing=auto, PT=ON, DD=OFF, backend=ideal
for OPT in 0 1 2 3; do
    python main.py --config config_ideal_study.ini \
        --override "random_a=4" \
        --override "optimization_level=$OPT"
done
```

#### A3 - Barrido bases a (6 configs)
```bash
# opt=3, approx=0.7, layout=sabre, routing=sabre, PT=ON, DD=OFF, backend=ideal
for A in 2 4 7 8 11 13; do
    python main.py --config config_ideal_study.ini \
        --override "random_a=$A"
done
```

#### C3 - Bases con approx=1.0 (6 configs, referencia)
```bash
for A in 2 4 7 8 11 13; do
    python main.py --config config_ideal_study.ini \
        --override "random_a=$A" \
        --override "approximation_degree=1.0"
done
```

> [!TIP]
> **Output esperado**: JSON con `depth_2q`, `total_gates`, `2q_gates`, `signal_percentage=100%` para cada config. Esto te da las profundidades reales para cada combinación antes de añadir ruido.

---

## Fase 2: Simulaciones con Ruido — FakeTorino (23 configs — ~1-2 horas)

**Días 1-2** — Sin costo QPU, pero cada config tarda ~1-5 min.

**Propósito**: Evaluar el impacto del ruido con el modelo calibrado de Heron r1 antes de usar créditos QPU.

### Configs a ejecutar

#### A1 - Barrido approx_degree (6 configs)
```bash
for APPROX in 0.5 0.6 0.7 0.8 0.9 1.0; do
    python main.py --config config_faketorino_study.ini \
        --override "random_a=4" \
        --override "approximation_degree=$APPROX"
done
```

#### A2 - Barrido opt_level (4 configs)
```bash
for OPT in 0 1 2 3; do
    python main.py --config config_faketorino_study.ini \
        --override "random_a=4" \
        --override "optimization_level=$OPT"
done
```

#### A3 - Barrido bases a (6 configs)
```bash
for A in 2 4 7 8 11 13; do
    python main.py --config config_faketorino_study.ini \
        --override "random_a=$A"
done
```

#### A4 - Barrido layout_method (3 configs)
```bash
for LAYOUT in trivial dense sabre; do
    python main.py --config config_faketorino_study.ini \
        --override "random_a=4" \
        --override "layout_method=$LAYOUT"
done
```

#### A5 - Barrido routing_method (4 configs)
```bash
for ROUTING in basic lookahead sabre stochastic; do
    python main.py --config config_faketorino_study.ini \
        --override "random_a=4" \
        --override "routing_method=$ROUTING"
done
```

### Criterio de filtrado para Fase 3
Solo las configuraciones con **señal simulada > 30%** pasan a hardware real. Esto evita desperdiciar créditos QPU en configs que ya se sabe que fallarán.

---

## Fase 3: Hardware Real — Batch Prioritario (20 jobs — ~60 s QPU)

**Días 2-3** — Requiere créditos IBM. Enviar en horario de baja demanda.

### Batch 1: Estudios principales (12 jobs)

#### A1 - approx_degree en hardware (5 jobs nuevos)
```bash
for APPROX in 0.5 0.6 0.8 0.9 1.0; do
    python main.py --config config_torino_study.ini \
        --override "random_a=4" \
        --override "approximation_degree=$APPROX"
done
# Nota: approx=0.7 YA EXISTE (Job d673l15bujdc73cvejag, 84.7%)
```

#### A2 - opt_level en hardware (3 jobs nuevos)
```bash
for OPT in 0 1 2; do
    python main.py --config config_torino_study.ini \
        --override "random_a=4" \
        --override "optimization_level=$OPT"
done
# Nota: opt=3 YA EXISTE (Job d673l15bujdc73cvejag, 84.7%)
```

#### A3 - Bases faltantes en hardware (4 jobs nuevos)
```bash
for A in 2 8 11 13; do
    python main.py --config config_torino_study.ini \
        --override "random_a=$A"
done
# Nota: a=4 y a=7 YA EXISTEN
```

### Batch 2: Mitigación de errores (8 jobs)

#### A6 - DD sequences en hardware (3 jobs)
```bash
for DD_SEQ in XX XpXm XY4; do
    python main.py --config config_torino_study.ini \
        --override "random_a=4" \
        --override "dd_enable=True" \
        --override "dd_sequence=$DD_SEQ"
done
```

#### A7 - Combinaciones de mitigación (5 jobs)
```bash
# Sin mitigación
python main.py --config config_torino_study.ini --override "random_a=4" \
    --override "pt_enable=False" --override "dd_enable=False"

# Solo PT measure
python main.py --config config_torino_study.ini --override "random_a=4" \
    --override "pt_enable=True" --override "pt_measure=True"

# Solo DD (sin PT)
python main.py --config config_torino_study.ini --override "random_a=4" \
    --override "pt_enable=False" --override "dd_enable=True" --override "dd_sequence=XY4"

# PT + DD XY4
python main.py --config config_torino_study.ini --override "random_a=4" \
    --override "pt_enable=True" --override "dd_enable=True" --override "dd_sequence=XY4"

# PT + PT_measure + DD XY4 (máximo)
python main.py --config config_torino_study.ini --override "random_a=4" \
    --override "pt_enable=True" --override "pt_measure=True" \
    --override "dd_enable=True" --override "dd_sequence=XY4"
```

---

## Fase 4: Validación Cruzada — Lista B (11 configs)

**Días 3-4** — Solo si Fases 1-3 muestran tendencias claras.

### B1 - FakeKyiv cross-validation (5 configs)
```bash
for A in 2 4 8 11 13; do
    python main.py --config config_fakekyiv_study.ini \
        --override "random_a=$A"
done
```

### B2 - Approx intermedios en hardware (3 configs)
```bash
for APPROX in 0.65 0.75 0.85; do
    python main.py --config config_torino_study.ini \
        --override "random_a=4" \
        --override "approximation_degree=$APPROX"
done
```

### B3 - Twirling strategies (3 configs)
```bash
for STRATEGY in active-accum active-circuit all; do
    python main.py --config config_torino_study.ini \
        --override "random_a=4" \
        --override "pt_strategy=$STRATEGY"
done
```

---

## Fase 5: Exploratoria — Lista C (solo si hay tiempo)

**Días 4+** — Opcional.

- Peor caso extremo (1 config hardware)
- Layout × Routing matrix (12 configs FakeTorino)
- Bases con approx=1.0 en ideal (6 configs, ya en Fase 1)

---

## Archivos de Configuración Necesarios

> [!IMPORTANT]
> Antes de ejecutar, crear estos archivos `.ini` basados en `config_torino_v1_a4.ini`:

| Archivo | Backend | Descripción |
|---------|---------|-------------|
| `config_ideal_study.ini` | ideal (AerSimulator) | Shots: 4096, sin ruido |
| `config_faketorino_study.ini` | fakeprov (FakeTorino) | Shots: 1024-4096, ruido Heron r1 |
| `config_fakekyiv_study.ini` | fakeprov (FakeKyiv) | Shots: 1024, ruido Eagle r3 |
| `config_torino_study.ini` | ibmqpu (ibm_torino) | Shots: 4096, hardware real |

> [!WARNING]
> Los comandos `--override` son **pseudo-código**. El script `main.py` actual puede no soportar overrides por CLI. Será necesario:
> 1. Crear un archivo `.ini` por config, **O**
> 2. Modificar `main.py` para aceptar overrides, **O**
> 3. Crear un script Python de batch (`run_study_batch.py`) que itere sobre las configs programáticamente.
>
> **Recomendación**: Opción 3 — crear un script de batch que use directamente las APIs del framework.

---

## Cronograma Sugerido

| Día | Actividad | Configs | Costo |
|:---:|-----------|:-------:|:-----:|
| 1 | Crear configs .ini + ejecutar Fase 1 (ideal) | 22 | Gratis |
| 1-2 | Ejecutar Fase 2 (FakeTorino) | 23 | Gratis |
| 2 | Analizar resultados simulados, filtrar configs para QPU | — | — |
| 2-3 | Ejecutar Fase 3 Batch 1 (hardware) | 12 | ~36 s QPU |
| 3 | Ejecutar Fase 3 Batch 2 (mitigación) | 8 | ~24 s QPU |
| 3-4 | Ejecutar Fase 4 (validación) | 11 | ~18 s QPU |
| 4+ | Ejecutar Fase 5 (exploratoria, opcional) | ~20 | ~6 s QPU |
| 5 | **Análisis final + generación de gráficos comparativos** | — | — |

---

## Gráficos Esperados del Estudio Completo

1. **Señal (%) vs approximation_degree** — 3 curvas (ideal, fake, real)
2. **Señal (%) vs optimization_level** — 3 curvas
3. **Depth 2Q vs base `a`** — Barras para 6 bases
4. **Señal (%) vs base `a`** — 3 curvas por backend
5. **Señal (%) por combinación de mitigación** — Barras agrupadas (PT, DD, PT+DD, ninguna)
6. **Depth 2Q vs layout_method** — Barras comparativas
7. **Depth 2Q vs routing_method** — Barras comparativas
8. **Heat map: Señal vs (approx_degree, opt_level)** — Solo si hay suficientes datos
