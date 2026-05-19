# Análisis de Configuraciones Existentes — Shor N=15

**Fecha de análisis**: 2026-02-16  
**Circuito foco**: RegisterQC  
**Fuente**: Todos los archivos `REPORTE_*.md` y `resultados_*.md` del repositorio

---

## 1. Inventario Completo de Ejecuciones

### 1.1 Ejecuciones en Hardware Real — IBM Torino (Heron r1)

| # | a | Circuito | Opt Level | Approx Degree | Layout | Routing | PT | DD | Backend | Depth 2Q | Señal (%) | Factores | Job ID |
|---|---|----------|:---------:|:-------------:|--------|---------|:--:|:--:|---------|:--------:|:---------:|----------|--------|
| 1 | 14 | RegisterQC | 3 | 0.7 | sabre | sabre | ✓ | ✗ | ibm_torino | 117 | 82.8 | 1, 15 (trivial) | `d672j2pv6o8c73d4ufqg` |
| 2 | 7 | RegisterQC | 3 | 0.7 | sabre | sabre | ✓ | ✗ | ibm_torino | 244 | 67.5 | **3, 5** ✓ | `d672p6gqbmes739ertc0` |
| 3 | 4 | RegisterQC | 3 | 0.7 | sabre | sabre | ✓ | ✗ | ibm_torino | 116 | 84.7 | **3, 5** ✓ | `d673l15bujdc73cvejag` |

### 1.2 Análisis de Transpilación con Hardware Real — IBM Torino (a=4)

| # | a | Opt Level | Layout | Routing | PT | DD | Backend | Depth 2Q | 2Q Gates | Señal (%) | Factores | Job ID |
|---|---|:---------:|--------|---------|:--:|:--:|---------|:--------:|:--------:|:---------:|----------|--------|
| 4 | 4 | 0 | trivial | basic | ✗ | ✗ | ibm_torino | 570 | 923 | 6.1 | 3, 5 | `d67rla9v6o8c73d5ucp0` |
| 5 | 4 | 1 | sabre | sabre | ✗ | ✗ | ibm_torino | 526 | 779 | 15.5 | 3, 5 | `d67rla9v6o8c73d5ucp0` |
| 6 | 4 | 2 | sabre | sabre | ✗ | ✗ | ibm_torino | 433 | 584 | 50.8 | 3, 5 | `d67rla9v6o8c73d5ucp0` |
| 7 | 4 | 3 | sabre | sabre | ✗ | ✗ | ibm_torino | 439 | 600 | 3.0 | 3, 5 | `d67rla9v6o8c73d5ucp0` |
| 8 | 4 | 3 | sabre | basic | ✗ | ✗ | ibm_torino | 662 | 1092 | 12.3 | 3, 5 | `d67rla9v6o8c73d5ucp0` |
| 9 | 4 | 3 | sabre | sabre | ✗ | ✗ | ibm_torino | 439 | 600 | 5.1 | 3, 5 | `d67rla9v6o8c73d5ucp0` |

> [!NOTE]
> Las configs 4-9 son del reporte de transpilación y **NO tenían Pauli Twirling ni approximation_degree=0.7**.
> La config preferida (#3) con PT + approx=0.7 logró 84.7% de señal con solo 116 CZ, muy superior a las configs sin aproximación (433-662 CZ).

### 1.3 Simulaciones en FakeKyiv (Eagle r3)

| # | a | Circuito | Opt Level | Approx Degree | Layout | Routing | Tipo Sim | Backend | Depth 2Q | Señal (%) | Factores |
|---|---|----------|:---------:|:-------------:|--------|---------|----------|---------|:--------:|:---------:|----------|
| 10 | 7 | RegisterQC | 2 | 1.0 | sabre | sabre | Ideal | FakeKyiv | 947 | 100.0 | **3, 5** ✓ |
| 11 | 7 | RegisterQC | 2 | 1.0 | sabre | sabre | Ruidoso (MPS, 32 shots) | FakeKyiv | 947 | 6.25 | No encontrados |
| 12 | 14 | RegisterQC | 3 | 0.7 | sabre | sabre | Ruidoso (1024 shots) | FakeKyiv | 55 | 79.1 | No encontrados |

### 1.4 RegisterQC Optimizado — FakeKyiv (3 variantes)

| # | a | Variante | Opt Level | Approx Degree | Layout | Routing | PT | DD | Backend | Depth 2Q | ECR | Señal (%) |
|---|---|----------|:---------:|:-------------:|--------|---------|:--:|:--:|---------|:--------:|:---:|:---------:|
| 13 | 14 | V1: PT+SO | 3 | 0.7 | sabre | sabre | ✓ | ✗ | FakeKyiv | 55 | 55 | — |
| 14 | 14 | V2: PT+SO+DD | 3 | 0.7 | sabre | sabre | ✓ | ✓ (XY4) | FakeKyiv | 55 | 55 | — |
| 15 | 14 | V3: Solo SO | 3 | 0.7 | sabre | sabre | ✗ | ✗ | FakeKyiv | 55 | 55 | 79.1 |

---

## 2. Resumen de Cobertura Actual

### 2.1 Por Base `a` (RegisterQC, circuito foco)

| a | gcd(a,15) | ord(a,15) | Hardware Real | FakeKyiv Sim | Ideal Sim | Factores posibles |
|:-:|:---------:|:---------:|:-------------:|:------------:|:---------:|:-----------------:|
| 2 | 1 ✓ | 4 | ✗ | ✗ | ✗ | **3, 5** |
| 4 | 1 ✓ | 2 | ✓ (84.7%) | ✗ | ✗ | **3, 5** |
| 7 | 1 ✓ | 4 | ✓ (67.5%) | ✓ | ✓ | **3, 5** |
| 8 | 1 ✓ | 4 | ✗ | ✗ | ✗ | **3, 5** |
| 11 | 1 ✓ | 2 | ✗ | ✗ | ✗ | **3, 5** |
| 13 | 1 ✓ | 4 | ✗ | ✗ | ✗ | **3, 5** |
| 14 | 1 ✓ | 2 | ✓ (82.8%) | ✓ | ✗ | 1, 15 (trivial) |

### 2.2 Por Dimensión de Configuración (solo RegisterQC)

| Dimensión | Valores Cubiertos | Valores Posibles | Cobertura |
|-----------|:-----------------:|:----------------:|:---------:|
| **a** | {4, 7, 14} | {2, 4, 7, 8, 11, 13} | 3/6 (50%) |
| **optimization_level** | {0, 1, 2, 3} | {0, 1, 2, 3} | 4/4 (100%) |
| **approximation_degree** | {0.7, 1.0} | {0.0–1.0} | 2/∞ |
| **layout_method** | {trivial, sabre} | {trivial, dense, sabre} | 2/3 (67%) |
| **routing_method** | {basic, sabre} | {basic, lookahead, sabre, stochastic} | 2/4 (50%) |
| **Pauli Twirling** | {ON, OFF} | {ON, OFF} | 2/2 (100%) |
| **Dynamical Decoupling** | {OFF, XY4} | {OFF, XX, XpXm, XY4} | 2/4 (50%) |
| **Backend (simulación)** | {FakeKyiv} | {FakeKyiv, FakeTorino} | 1/2 (50%) |
| **Backend (real)** | {ibm_torino} | {ibm_torino} | 1/1 (100%) |

### 2.3 Configuración Más Repetida

La configuración más utilizada es la **"V1 óptima"**:
```
RegisterQC, opt=3, approx=0.7, layout=sabre, routing=sabre, PT=ON, DD=OFF, ibm_torino
```
Ejecutada con a=4, 7 y 14.

---

## 3. Observaciones Importantes

1. **No hay ejecuciones con a=2, 8, 11, 13** en ningún backend — gap crítico para estudio exhaustivo de bases.

2. **Falta approximation_degree en rango intermedio** — Solo se tienen 0.7 y 1.0 (sin aproximación). No se probaron 0.5, 0.6, 0.8, 0.9.

3. **Nunca se probó layout=dense** — Se desconoce su impacto vs. sabre.

4. **routing = lookahead y stochastic** nunca fueron probados.

5. **DD sequences XX y XpXm** no fueron evaluadas — solo XY4 (y solo en simulación FakeKyiv, no en hardware real).

6. **FakeTorino nunca fue utilizado** como backend de simulación — solo FakeKyiv.

7. **SamplerV2 no tiene resilience_level** — La mitigación para Sampler se hace exclusivamente via:
   - Twirling (Pauli Twirling = `enable_gates=True`)
   - Measurement Twirling (`enable_measure=True`)
   - Dynamical Decoupling

8. **El análisis de transpilación (configs 4-9) no usó approximation_degree=0.7**, lo cual infla artificialmente la profundidad. Los resultados de señal (3-50.8%) no son comparables directamente con las configs V1 (84.7%).

---

*Total de configuraciones únicas ejecutadas: **15***
