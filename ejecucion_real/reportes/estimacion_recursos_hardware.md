# Estimación de Recursos — Shor N=15 (RegisterQC)

**Fecha**: 2026-02-16  
**Cuenta IBM Quantum**: Trial (caduca en ~25 días)

---

## 1. Tiempos por Tipo de Backend

| Backend | Tiempo por Config (est.) | Nota |
|---------|:------------------------:|------|
| **Ideal (AerSimulator)** | ~5-30 s | Depende de shots (1024-4096) |
| **FakeKyiv / FakeTorino** | ~30 s – 10 min | Depende del método: statevector ~30s, MPS ~5-10 min |
| **ibm_torino (QPU)** | ~3 s quantum + ~2-60 s cola | Cola variable según demanda |

> [!NOTE]
> **Simulaciones ruidosas MPS (32 shots)** tardan ~9 min por el costo de simular 127-133 qubits con ruido realista. Se recomienda usar `method='automatic'` o statevector para circuitos poco profundos.

---

## 2. Estimación por Lista

### Lista A: Críticas (59 configs faltantes)

| Estudio | Ideal | FakeTorino | ibm_torino | Total Configs |
|---------|:-----:|:----------:|:----------:|:-------------:|
| A1. approx_degree | 6 | 6 | 5 | 17 |
| A2. opt_level | 4 | 4 | 3 | 11 |
| A3. Bases a | 6 | 6 | 4 | 16 |
| A4. layout_method | 0 | 3 | 0 | 3 |
| A5. routing_method | 0 | 4 | 0 | 4 |
| A6. DD sequences | 0 | 0 | 3 | 3 |
| A7. Mitigación | 0 | 0 | 5 | 5 |
| **Subtotales** | **16** | **23** | **20** | **59** |

#### Tiempos Estimados

| Tipo | Configs | Tiempo/Config | Tiempo Total |
|------|:-------:|:-------------:|:------------:|
| Ideal | 16 | ~10 s | **~3 min** |
| FakeTorino | 23 | ~1-5 min | **~25-115 min** |
| ibm_torino | 20 | ~5-60 s | **~2-20 min QPU** |

#### Créditos IBM (QPU)
- **20 jobs** × 4096 shots × ~3 s quantum = **~60 s de tiempo QPU real**
- Cola estimada: variable (0-300 s por job)
- **Total QPU Lista A: ~1-2 min quantum + cola**

> Los créditos IBM se miden en "segundos de uso del sistema" (system seconds). 20 jobs × ~3s = ~60 system seconds. Esto está **muy dentro** del límite de una cuenta trial (típicamente 10 minutos/mes).

---

### Lista B: Secundarias (~11 configs)

| Tipo | Configs | Tiempo Total Estimado |
|------|:-------:|:---------------------:|
| FakeKyiv | ~5 | ~5-25 min |
| ibm_torino | ~6 | ~18 s QPU + cola |

#### Créditos IBM: ~18 system seconds adicionales

---

### Lista C: Exploratorias (~20 configs)

| Tipo | Configs | Tiempo Total Estimado |
|------|:-------:|:---------------------:|
| Ideal | ~6 | ~1 min |
| FakeTorino | ~12 | ~12-60 min |
| ibm_torino | ~2 | ~6 s QPU |

#### Créditos IBM: ~6 system seconds adicionales

---

## 3. Resumen Total

| Recurso | Lista A | Lista B | Lista C | **Total** |
|---------|:-------:|:-------:|:-------:|:---------:|
| **Configs faltantes** | 59 | ~11 | ~20 | **~90** |
| **Tiempo simulación ideal** | ~3 min | — | ~1 min | **~4 min** |
| **Tiempo simulación ruidosa** | ~25-115 min | ~5-25 min | ~12-60 min | **~42-200 min** |
| **Tiempo QPU (quantum)** | ~60 s | ~18 s | ~6 s | **~84 s** |
| **Jobs QPU** | 20 | 6 | 2 | **28** |
| **Créditos IBM (system seconds)** | ~60 s | ~18 s | ~6 s | **~84 s** |

> [!IMPORTANT]
> **El cuello de botella NO son los créditos IBM** (~84 segundos de QPU total).
> El cuello de botella es el **tiempo de simulación ruidosa** (~42-200 minutos) y la **cola de QPU** (impredecible).

---

## 4. Estrategia de Ejecución Óptima

### Día 1: Simulaciones Ideales (~4 min)
- Ejecutar las 22 configs ideales (Lista A + C) en batch
- Sin costo, sin cola, resultados inmediatos
- **Output**: Profundidades de circuito y distribuciones ideales para todas las bases y approx_degrees

### Día 1-2: Simulaciones Ruidosas (~1-3 horas)
- Ejecutar 23 configs FakeTorino (Lista A) en paralelo o secuencial
- Opcional: 17 configs FakeKyiv + FakeTorino extras (Lista B + C)
- **Tip**: Usar `method='automatic'` para circuitos cortos (≤200 depth 2Q)

### Día 2-3: Hardware Real — Batch Prioritario (~20 jobs)
- Ejecutar estudios A1, A2, A3 primero (31 configs más importantes)
- Ejecutar los 20 jobs en un batch script para minimizar colas
- **Mejor horario**: Enviar jobs en horario de baja demanda (madrugada EST/COT)

### Día 3-4: Hardware Real — Mitigación (~8 jobs)
- Ejecutar estudios A6 y A7 (DD + combinaciones de mitigación)
- Requiere modificar opciones del SamplerV2

### Día 4+: Validación Cruzada (Lista B, opcionales)
- Ejecutar solo si los resultados de Lista A muestran tendencias claras

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|:------------:|:-------:|------------|
| Cola QPU larga (>10 min/job) | Media | Alto | Ejecutar en horarios de baja demanda |
| Créditos insuficientes | Baja | Alto | Solo 84s QPU total, bien dentro del límite |
| FakeTorino no disponible | Baja | Medio | Usar FakeKyiv como alternativa |
| Transpilación falla con ciertas configs | Media | Medio | Probar localmente antes de enviar a QPU |
| Cuenta trial caduca | Media | Crítico | Priorizar Lista A (28 jobs QPU) en los primeros 10 días |
