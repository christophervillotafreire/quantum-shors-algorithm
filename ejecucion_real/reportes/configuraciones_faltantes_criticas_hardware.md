# Configuraciones Faltantes Críticas — Shor N=15 (RegisterQC)

**Fecha**: 2026-02-16  
**Config base (óptima conocida)**: `a=4, opt=3, approx=0.7, layout=sabre, routing=sabre, PT=ON, DD=OFF`

---

## Lista A: CRÍTICAS — Máxima Prioridad

Estas configuraciones son **esenciales** para las conclusiones del trabajo de grado. Cada estudio varía UNA sola dimensión manteniendo las demás fijas.

---

### A1. Estudio de `approximation_degree`

**Pregunta de investigación**: ¿Cuál es el impacto del grado de aproximación en la señal y profundidad del circuito?

| # | a | opt | approx | layout | routing | PT | DD | Backend | Estado |
|---|---|:---:|:------:|--------|---------|:--:|:--:|---------|:------:|
| 1 | 4 | 3 | **0.5** | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 2 | 4 | 3 | **0.6** | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 3 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 4 | 4 | 3 | **0.8** | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 5 | 4 | 3 | **0.9** | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 6 | 4 | 3 | 1.0 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 7 | 4 | 3 | **0.5** | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 8 | 4 | 3 | **0.6** | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 9 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 10 | 4 | 3 | **0.8** | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 11 | 4 | 3 | **0.9** | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 12 | 4 | 3 | 1.0 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 13 | 4 | 3 | **0.5** | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |
| 14 | 4 | 3 | **0.6** | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |
| 15 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | ibm_torino | ✓ EXISTE (84.7%) |
| 16 | 4 | 3 | **0.8** | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |
| 17 | 4 | 3 | **0.9** | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |
| 18 | 4 | 3 | 1.0 | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |

**Configs faltantes: 17** | **Justificación**: Permite graficar curva signal% vs approx_degree para 3 backends.

---

### A2. Estudio de `optimization_level` (con approx=0.7 y PT)

**Pregunta**: ¿Cómo impacta el nivel de optimización cuando se usa approximation_degree=0.7 + Pauli Twirling?

> [!NOTE]
> El estudio de transpilación existente NO usó approx=0.7 ni PT. Estos resultados no son comparables.

| # | a | opt | approx | layout | routing | PT | DD | Backend | Estado |
|---|---|:---:|:------:|--------|---------|:--:|:--:|---------|:------:|
| 19 | 4 | **0** | 0.7 | trivial | basic | ON | OFF | ideal | **FALTA** |
| 20 | 4 | **1** | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 21 | 4 | **2** | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 22 | 4 | **3** | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 23 | 4 | **0** | 0.7 | trivial | basic | ON | OFF | FakeTorino | **FALTA** |
| 24 | 4 | **1** | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 25 | 4 | **2** | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 26 | 4 | **3** | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 27 | 4 | **0** | 0.7 | trivial | basic | ON | OFF | ibm_torino | **FALTA** |
| 28 | 4 | **1** | 0.7 | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |
| 29 | 4 | **2** | 0.7 | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |
| 30 | 4 | **3** | 0.7 | sabre | sabre | ON | OFF | ibm_torino | ✓ EXISTE (84.7%) |

**Configs faltantes: 11** | **Justificación**: Comparación justa de opt_levels con la misma aproximación.

---

### A3. Estudio de Bases `a` (con config óptima)

**Pregunta**: ¿Cómo varía la señal según la complejidad del circuito de exponenciación modular para cada base?

| # | a | opt | approx | layout | routing | PT | DD | Backend | Estado |
|---|---|:---:|:------:|--------|---------|:--:|:--:|---------|:------:|
| 31 | **2** | 3 | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 32 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 33 | 7 | 3 | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 34 | **8** | 3 | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 35 | **11** | 3 | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 36 | **13** | 3 | 0.7 | sabre | sabre | ON | OFF | ideal | **FALTA** |
| 37 | **2** | 3 | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 38 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 39 | 7 | 3 | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 40 | **8** | 3 | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 41 | **11** | 3 | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 42 | **13** | 3 | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 43 | **2** | 3 | 0.7 | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |
| 44 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | ibm_torino | ✓ EXISTE (84.7%) |
| 45 | 7 | 3 | 0.7 | sabre | sabre | ON | OFF | ibm_torino | ✓ EXISTE (67.5%) |
| 46 | **8** | 3 | 0.7 | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |
| 47 | **11** | 3 | 0.7 | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |
| 48 | **13** | 3 | 0.7 | sabre | sabre | ON | OFF | ibm_torino | **FALTA** |

**Configs faltantes: 16** | **Justificación**: Permite tabla completa de 6 bases × 3 backends.

---

### A4. Estudio de `layout_method`

**Pregunta**: ¿Es SABRE realmente el mejor layout? ¿Cuánto afecta dense vs trivial?

| # | a | opt | approx | layout | routing | PT | DD | Backend | Estado |
|---|---|:---:|:------:|--------|---------|:--:|:--:|---------|:------:|
| 49 | 4 | 3 | 0.7 | **trivial** | sabre | ON | OFF | FakeTorino | **FALTA** |
| 50 | 4 | 3 | 0.7 | **dense** | sabre | ON | OFF | FakeTorino | **FALTA** |
| 51 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |

**Configs faltantes: 3** | **Justificación**: Comparación directa de los 3 layouts disponibles.

---

### A5. Estudio de `routing_method`

**Pregunta**: ¿Es SABRE el mejor routing? ¿Cómo se comparan los 4 métodos disponibles?

| # | a | opt | approx | layout | routing | PT | DD | Backend | Estado |
|---|---|:---:|:------:|--------|---------|:--:|:--:|---------|:------:|
| 52 | 4 | 3 | 0.7 | sabre | **basic** | ON | OFF | FakeTorino | **FALTA** |
| 53 | 4 | 3 | 0.7 | sabre | **lookahead** | ON | OFF | FakeTorino | **FALTA** |
| 54 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | FakeTorino | **FALTA** |
| 55 | 4 | 3 | 0.7 | sabre | **stochastic** | ON | OFF | FakeTorino | **FALTA** |

**Configs faltantes: 4** | **Justificación**: Comparación directa de los 4 routing methods.

---

### A6. Estudio de Dynamical Decoupling

**Pregunta**: ¿DD mejora la señal en hardware real? ¿Qué secuencia es mejor?

| # | a | opt | approx | layout | routing | PT | DD | Backend | Estado |
|---|---|:---:|:------:|--------|---------|:--:|:--:|---------|:------:|
| 56 | 4 | 3 | 0.7 | sabre | sabre | ON | **OFF** | ibm_torino | ✓ EXISTE (84.7%) |
| 57 | 4 | 3 | 0.7 | sabre | sabre | ON | **XX** | ibm_torino | **FALTA** |
| 58 | 4 | 3 | 0.7 | sabre | sabre | ON | **XpXm** | ibm_torino | **FALTA** |
| 59 | 4 | 3 | 0.7 | sabre | sabre | ON | **XY4** | ibm_torino | **FALTA** |

**Configs faltantes: 3** | **Justificación**: Evalúa si DD mejora o empeora la señal en hardware real (evidencia previa sugiere que no ayuda).

---

### A7. Estudio de Mitigación de Errores (combinaciones PT/DD)

**Pregunta**: ¿Cuál es la mejor combinación de técnicas de mitigación?

| # | a | opt | approx | layout | routing | PT gates | PT measure | DD | Backend | Estado |
|---|---|:---:|:------:|--------|---------|:--------:|:----------:|:--:|---------|:------:|
| 60 | 4 | 3 | 0.7 | sabre | sabre | OFF | OFF | OFF | ibm_torino | **FALTA** |
| 61 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | OFF | ibm_torino | ✓ EXISTE |
| 62 | 4 | 3 | 0.7 | sabre | sabre | ON | **ON** | OFF | ibm_torino | **FALTA** |
| 63 | 4 | 3 | 0.7 | sabre | sabre | OFF | OFF | **XY4** | ibm_torino | **FALTA** |
| 64 | 4 | 3 | 0.7 | sabre | sabre | ON | OFF | **XY4** | ibm_torino | **FALTA** |
| 65 | 4 | 3 | 0.7 | sabre | sabre | ON | **ON** | **XY4** | ibm_torino | **FALTA** |

**Configs faltantes: 5** | **Justificación**: Permite determinar la contribución individual de cada técnica.

---

### Resumen Lista A

| Estudio | Configs Totales | Ya Existentes | Faltantes |
|---------|:---------------:|:-------------:|:---------:|
| A1. approximation_degree | 18 | 1 | **17** |
| A2. optimization_level | 12 | 1 | **11** |
| A3. Bases a | 18 | 2 | **16** |
| A4. layout_method | 3 | 0 | **3** |
| A5. routing_method | 4 | 0 | **4** |
| A6. DD sequences | 4 | 1 | **3** |
| A7. Mitigación combinada | 6 | 1 | **5** |
| **TOTAL Lista A** | **65** | **6** | **59** |

---

## Lista B: SECUNDARIAS — Validación Cruzada

Estas configs son útiles para validar tendencias pero **no bloquean** las conclusiones principales.

### B1. Bases adicionales con configs óptimas en FakeKyiv (no solo FakeTorino)

| # | a | Backend | Nota |
|---|---|---------|------|
| B1-1 | 2 | FakeKyiv | Validar que FakeKyiv da misma tendencia que FakeTorino |
| B1-2 | 4 | FakeKyiv | |
| B1-3 | 8 | FakeKyiv | |
| B1-4 | 11 | FakeKyiv | |
| B1-5 | 13 | FakeKyiv | |
| B1-6 | 7 | FakeKyiv | ✓ Ya existe (parcialmente) |

**Configs faltantes: ~5** con config óptima

### B2. Approximation intermedios en hardware real

| # | approx | Backend | Nota |
|---|:------:|---------|------|
| B2-1 | 0.65 | ibm_torino | Punto intermedio |
| B2-2 | 0.75 | ibm_torino | Punto intermedio |
| B2-3 | 0.85 | ibm_torino | Punto intermedio |

**Configs faltantes: 3** 

### B3. Twirling strategies en hardware real

| # | Strategy | Backend | Nota |
|---|----------|---------|------|
| B3-1 | active | ibm_torino | Estrategia usada hasta ahora |
| B3-2 | active-accum | ibm_torino | Default de Qiskit |
| B3-3 | active-circuit | ibm_torino | Más agresiva |
| B3-4 | all | ibm_torino | Máximo twirling |

**Configs faltantes: 3** (active ya cubierta)

**Total Lista B: ~11 configs faltantes**

---

## Lista C: EXPLORATORIAS — Opcional

### C1. Peor caso (referencia mínima)
- `a=7, opt=0, approx=1.0, layout=trivial, routing=basic, PT=OFF, DD=OFF, ibm_torino`
- Esperado: señal ~0-5%, circuito enorme

### C2. Layout × Routing matrix (FakeTorino)
- 3 layouts × 4 routings = 12 configs (solo FakeTorino)
- Permite heat map de profundidad 2Q

### C3. Todas las bases con approx=1.0 (sin aproximación)
- 6 bases × ideal = 6 configs para referencia

**Total Lista C: ~20 configs faltantes**

---

## Resumen Global

| Lista | Prioridad | Configs Faltantes | Impacto |
|:-----:|:---------:|:-----------------:|---------|
| **A** | 🔴 Crítica | **59** | Esencial para conclusiones |
| **B** | 🟡 Secundaria | **~11** | Validación cruzada |
| **C** | 🟢 Exploratoria | **~20** | Interés académico |
| **Total** | | **~90** | |

De estas 90, las que requieren hardware real (ibm_torino) son las más costosas en créditos IBM:
- Lista A hardware: **~22 configs** en ibm_torino
- Lista B hardware: **~6 configs** en ibm_torino
- **Total QPU: ~28 configs** × 4096 shots = ~28 jobs
