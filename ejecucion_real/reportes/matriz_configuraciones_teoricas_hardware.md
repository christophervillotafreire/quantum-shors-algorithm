# Matriz de Configuraciones Teóricas — Shor N=15 (RegisterQC)

**Fecha**: 2026-02-16  
**Fuente**: Documentación oficial de Qiskit 2.3.0 + Qiskit Runtime v0.45.0

---

## 1. Dimensiones del Espacio de Configuración

### 1.1 Valores de `a` (Coprimos con 15, excluidos triviales)

Los valores de `a` válidos para Shor con N=15 satisfacen `1 < a < N` y `gcd(a, N) = 1`.

| a | gcd(a,15) | Coprimo | ord(a,15) | a^(r/2) mod 15 | gcd(…-1,15) | gcd(…+1,15) | Resultado |
|:-:|:---------:|:-------:|:---------:|:--------------:|:-----------:|:-----------:|:---------:|
| 1 | 1 | ✓ | 1 | — | — | — | **Excluir** (trivial, a=1) |
| 2 | 1 | ✓ | **4** | 4 | **3** | **5** | ★ Factores |
| 3 | 3 | ✗ | — | — | — | — | **Excluir** (no coprimo) |
| 4 | 1 | ✓ | **2** | 4 | **3** | **5** | ★ Factores |
| 5 | 5 | ✗ | — | — | — | — | **Excluir** (no coprimo) |
| 6 | 3 | ✗ | — | — | — | — | **Excluir** (no coprimo) |
| 7 | 1 | ✓ | **4** | 4 | **3** | **5** | ★ Factores |
| 8 | 1 | ✓ | **4** | 4 | **3** | **5** | ★ Factores |
| 9 | 3 | ✗ | — | — | — | — | **Excluir** (no coprimo) |
| 10 | 5 | ✗ | — | — | — | — | **Excluir** (no coprimo) |
| 11 | 1 | ✓ | **2** | 11 | **5** | **3** | ★ Factores |
| 12 | 3 | ✗ | — | — | — | — | **Excluir** (no coprimo) |
| 13 | 1 | ✓ | **4** | 4 | **3** | **5** | ★ Factores |
| 14 | 1 | ✓ | **2** | 14 | 1 (trivial) | 15 (trivial) | ✗ Trivial |

**Bases válidas para factores no triviales**: `a ∈ {2, 4, 7, 8, 11, 13}` (6 valores)

> [!IMPORTANT]
> a=14 siempre da factores triviales (14 ≡ -1 mod 15). Útil como referencia pero no como demostración de factorización.

---

### 1.2 Niveles de Optimización

| optimization_level | Layout Default | Routing Default | Descripción |
|:------------------:|:--------------:|:---------------:|-------------|
| 0 | trivial | basic | Sin optimización, mapeo directo |
| 1 | sabre | sabre | Optimización básica con SABRE |
| 2 | sabre | sabre | Optimización media con síntesis de puertas |
| 3 | sabre | sabre | Máxima optimización (más lento, mejores resultados) |

---

### 1.3 Grado de Aproximación

| approximation_degree | Efecto | Nota |
|:--------------------:|--------|------|
| 1.0 | Sin aproximación (circuito exacto) | Default |
| 0.9 | Aproximación mínima | |
| 0.8 | Aproximación ligera | |
| 0.7 | **Usado en configs V1** — buen balance | Probado |
| 0.6 | Aproximación moderada | |
| 0.5 | Aproximación agresiva | |
| 0.0 | Máxima aproximación (mínimas puertas) | Extremo |
| None | Usa la tasa de error reportada del backend | |

**Rango válido**: 0.0 – 1.0 (float) o None.

---

### 1.4 Métodos de Layout (verificado con docs oficiales)

| layout_method | Descripción | Disponible |
|:-------------:|-------------|:----------:|
| `trivial` | Mapeo directo qubit lógico → físico (sin optimización) | ✓ |
| `dense` | Busca un subgrafo denso del coupling map | ✓ |
| `sabre` | SABRE: layout iterativo optimizado por routing | ✓ |

---

### 1.5 Métodos de Routing (verificado con docs oficiales)

| routing_method | Descripción | Disponible |
|:--------------:|-------------|:----------:|
| `basic` | Routing básico con SWAPs en ruta más corta | ✓ |
| `lookahead` | Routing con búsqueda anticipada | ✓ |
| `sabre` | SABRE: routing heurístico optimizado | ✓ (default) |
| `stochastic` | Routing estocástico (aleatorio con optimización) | ✓ |
| `none` | Sin routing (requiere layout compatible) | ✓ |

---

### 1.6 Mitigación de Errores — SamplerV2

> [!WARNING]
> **SamplerV2 NO tiene `resilience_level`**. La mitigación se configura manualmente.

#### Twirling (Pauli Twirling)
| Opción | Valores | Default (SamplerV2) |
|--------|---------|:-------------------:|
| `enable_gates` | True/False | False |
| `enable_measure` | True/False | False |
| `strategy` | active, active-accum, active-circuit, all | active-accum |
| `num_randomizations` | int | auto |

#### Dynamical Decoupling
| Opción | Valores | Nota |
|--------|---------|------|
| `enable` | True/False | |
| `sequence_type` | XX, XpXm, XY4 | 3 secuencias disponibles |

#### Combinaciones de Mitigación
| Combinación | PT (gates) | PT (measure) | DD | Nota |
|:-----------:|:----------:|:------------:|:--:|------|
| Sin mitigación | ✗ | ✗ | ✗ | Línea base |
| Solo PT gates | ✓ | ✗ | ✗ | **Config V1 usada** |
| PT gates + measure | ✓ | ✓ | ✗ | Añade twirling medición |
| Solo DD | ✗ | ✗ | ✓ | Solo decoupling |
| PT + DD | ✓ | ✗ | ✓ | Config V2 |
| PT + PT_meas + DD | ✓ | ✓ | ✓ | Máxima mitigación |

---

### 1.7 Backends Disponibles

| Tipo | Nombre | Qubits | Gate 2Q | T₂ (μs) | Nota |
|------|--------|:------:|:-------:|:--------:|------|
| ideal | AerSimulator | N/A | N/A | ∞ | Sin ruido |
| fake_provider | FakeKyiv | 127 | ECR | 156 | Eagle r3 |
| fake_provider | FakeTorino | 133 | CZ | ~250 | Heron r1 |
| ibmqpu | ibm_torino | 133 | CZ | ~250 | **Hardware real** |

---

## 2. Espacio Total de Configuraciones

### Para estudio controlado (una variable a la vez):

| Dimensión | Valores | Cantidad |
|-----------|---------|:--------:|
| Circuito | RegisterQC | 1 |
| a | 2, 4, 7, 8, 11, 13 | 6 |
| optimization_level | 0, 1, 2, 3 | 4 |
| approximation_degree | 0.5, 0.6, 0.7, 0.8, 0.9, 1.0 | 6 |
| layout_method | trivial, dense, sabre | 3 |
| routing_method | basic, lookahead, sabre, stochastic | 4 |
| PT (gates) | ON, OFF | 2 |
| DD | OFF, XX, XpXm, XY4 | 4 |
| Backend | ideal, FakeKyiv, FakeTorino, ibm_torino | 4 |

### Producto cartesiano total: 1 × 6 × 4 × 6 × 3 × 4 × 2 × 4 × 4 = **27,648 configuraciones**

> [!CAUTION]
> Es inviable ejecutar todas. Un estudio sistemático **varía una dimensión a la vez** manteniendo las demás fijas en valores óptimos.

### Para estudio one-at-a-time (OFAT) con config base:

**Config base recomendada**: `a=4, opt=3, approx=0.7, layout=sabre, routing=sabre, PT=ON, DD=OFF`

| Estudio | Configs | × Backends | Total |
|---------|:-------:|:----------:|:-----:|
| Barrido de `a` | 6 | 4 | 24 |
| Barrido de `opt_level` | 4 | 4 | 16 |
| Barrido de `approx_degree` | 6 | 4 | 24 |
| Barrido de `layout_method` | 3 | 2 (fake+real) | 6 |
| Barrido de `routing_method` | 4 | 2 | 8 |
| Barrido de PT/DD | 6 combinaciones | 2 | 12 |
| **Total OFAT** | | | **90 configs** |

---

## 3. Nota sobre `resilience_level`

En los reportes previos se menciona `resilience_level` como parámetro. Sin embargo:

- **SamplerV2** (usado en este proyecto) **no tiene `resilience_level`**.
- Los `resilience_level` (0, 1, 2, 3) son exclusivos de **EstimatorV2**.
- Para SamplerV2, la mitigación se configura manualmente via `TwirlingOptions` y `DynamicalDecouplingOptions`.
- **Recomendación**: En los documentos del estudio, reemplazar `resilience_level` por las opciones específicas de twirling y DD que sí aplican al Sampler.
