# Simulador con Ruido: Explicación Rigurosa del Funcionamiento

> **Contexto:** Este documento describe con rigor técnico cómo funciona el simulador con ruido utilizado en la carpeta `simulacion_con_ruido/` del proyecto de trabajo de grado. Se explica la cadena completa: desde la construcción del backend simulado (`FakeTorino`) hasta la forma en que el ruido se aplica a cada operación del circuito de Shor.

---

## 1. ¿Qué es el Simulador con Ruido?

El simulador con ruido es una **simulación clásica** de un procesador cuántico que incorpora un **modelo de ruido aproximado** basado en los datos de calibración reales de un chip de IBM. En este proyecto, se utiliza la siguiente cadena de software:

```python
from qiskit_ibm_runtime.fake_provider import FakeTorino
from qiskit_aer import AerSimulator

fake_torino = FakeTorino()                          # (1) Carga el snapshot del chip real
noisy_sim = AerSimulator.from_backend(fake_torino)   # (2) Construye un simulador con ruido
```

Esto produce un simulador clásico que **emula** el comportamiento ruidoso del procesador cuántico real `ibm_torino`, sin necesidad de acceder al hardware.

> **Clave:** No se simula cuánticamente. Se resuelven numéricamente las ecuaciones que describen la evolución del estado cuántico (incluyendo errores) en una computadora clásica.

---

## 2. FakeTorino: El Snapshot del Hardware Real

### 2.1 ¿Qué es `FakeTorino`?

`FakeTorino` es una clase de la familia `FakeBackendV2` del paquete `qiskit_ibm_runtime.fake_provider`. Es un **objeto Python** que almacena un *system snapshot* (instantánea del sistema) del procesador real `ibm_torino` de IBM.

Este snapshot fue tomado en un momento específico durante una calibración del dispositivo y contiene **toda la información** necesaria para construir un modelo de ruido realista:

### 2.2 Especificaciones del procesador `ibm_torino` (Heron r1)

| Propiedad | Valor |
|:---|:---|
| **Procesador** | IBM Heron r1 |
| **Nombre del sistema** | `ibm_torino` |
| **Número de qubits** | **133 qubits** superconductores de tipo transmon |
| **Topología** | **Heavy-Hex** (acoplamiento de vecinos cercanos) |
| **Basis gates (compuertas nativas)** | `CZ`, `ID`, `RZ`, `SX`, `X` |
| **Compuerta 2Q nativa** | `CZ` (Controlled-Z) |
| **Error mediano de CZ** | $\sim 4.8 \times 10^{-3}$ (0.48%) |
| **Tiempo mediano de gate CZ** | $\sim 84$ ns |
| **Errores de 1Q** | $\sim 10^{-4}$ (0.01%) |
| **$T_1$ típico** | $\sim 200\text{–}300\;\mu\text{s}$ (varía por qubit) |
| **$T_2$ típico** | $\sim 100\text{–}200\;\mu\text{s}$ (varía por qubit) |

### 2.3 ¿Qué datos almacena el snapshot?

El snapshot de `FakeTorino` contiene cuatro categorías de información:

1. **Coupling Map (mapa de acoplamiento):** Una lista de pares $(q_i, q_j)$ que indica qué qubits físicos están conectados y pueden ejecutar una compuerta `CZ` directa. La topología Heavy-Hex implica que cada qubit está conectado a **máximo 3 vecinos** (a diferencia de un grafo completo).

2. **Propiedades de qubit (por qubit):**
   - $T_1^{(i)}$: tiempo de relajación longitudinal del qubit $i$
   - $T_2^{(i)}$: tiempo de decoherencia transversal del qubit $i$
   - Frecuencia de resonancia $f_i$
   - Error de lectura (*readout error*): probabilidades $P(0|1)$ y $P(1|0)$

3. **Propiedades de compuerta (por gate):**
   - Tasa de error de cada compuerta: $\epsilon_{gate}^{(i)}$ o $\epsilon_{gate}^{(i,j)}$
   - Duración de la compuerta: $t_{gate}$ (en nanosegundos)
   - Compuertas soportadas en cada qubit/par de qubits

4. **Configuración del backend:** basis gates, número de qubits, versión del firmware.

---

## 3. Construcción del Modelo de Ruido: `AerSimulator.from_backend()`

Cuando se ejecuta `AerSimulator.from_backend(fake_torino)`, Qiskit Aer **extrae** los datos del snapshot y construye automáticamente un objeto `NoiseModel` que define tres tipos de errores cuánticos.

### 3.1 Errores de Compuerta de 1 Qubit

Para cada compuerta de un qubit (como `SX`, `X`, `RZ`) aplicada al qubit $i$, se modelan **dos canales de error en serie**:

$$\mathcal{E}_{1Q}^{(i)} = \mathcal{E}_{\text{thermal}}^{(i)} \circ \mathcal{E}_{\text{depol}}^{(i)}$$

#### a) Error Depolarizante de 1 Qubit

El canal depolarizante de un qubit actúa sobre la matriz de densidad $\rho$ como:

$$\mathcal{E}_{\text{depol}}(\rho) = (1 - \lambda)\,\rho + \lambda\,\frac{I}{2}$$

donde:
- $\lambda$ es la **probabilidad de despolarización**, calibrada para que el error combinado (depolarización + relajación térmica) reproduzca el `gate_error` reportado en las propiedades del backend.
- $I/2$ es el **estado máximamente mezclado** de 1 qubit.

Físicamente, con probabilidad $(1 - \lambda)$ el qubit permanece inalterado, y con probabilidad $\lambda$ se reemplaza por un estado completamente aleatorio. La representación equivalente en operadores de Kraus es:

$$\mathcal{E}_{\text{depol}}(\rho) = (1 - p)\,\rho + \frac{p}{3}\left(X\rho X + Y\rho Y + Z\rho Z\right)$$

donde $p = \frac{3\lambda}{4}$, es decir, se aplica un operador de Pauli aleatorio ($X$, $Y$ o $Z$) con probabilidad $p/3$ cada uno.

#### b) Error de Relajación Térmica de 1 Qubit

Este canal modela la interacción del qubit con el baño térmico del criostato. Depende de tres parámetros del qubit $i$:

- $T_1^{(i)}$: tiempo de relajación de energía (decaimiento $|1\rangle \to |0\rangle$)
- $T_2^{(i)}$: tiempo de decoherencia de fase
- $t_{gate}$: duración de la compuerta

Se definen dos probabilidades:

$$p_{\text{relax}} = 1 - e^{-t_{gate}/T_1}$$

$$p_{\text{phase}} = 1 - e^{-t_{gate}/T_\varphi}$$

donde $T_\varphi$ es el **tiempo de desfase puro**, definido por:

$$\frac{1}{T_\varphi} = \frac{1}{T_2} - \frac{1}{2T_1}$$

La restricción física fundamental es $T_2 \leq 2T_1$ (el desfase no puede ser más lento que el doble de la relajación).

**Interpretación física:**
- **$T_1$ (relajación):** El qubit pierde energía y decae desde $|1\rangle$ hacia $|0\rangle$, análogo a un átomo excitado que emite un fotón. Esto destruye la componente de población del estado.
- **$T_2$ (decoherencia):** El qubit pierde coherencia de fase, es decir, la fase relativa entre $|0\rangle$ y $|1\rangle$ se aleatoriza. Esto destruye la capacidad de interferencia.

El canal se implementa con **operadores de Kraus** cuya forma depende de la relación $T_2 \leq T_1$ o $T_1 < T_2 \leq 2T_1$:

- Si $T_2 \leq T_1$: se usa un canal de *mixed reset + unitary error*.
- Si $T_1 < T_2 \leq 2T_1$: se requieren operadores de Kraus **no unitarios** generales.

### 3.2 Errores de Compuerta de 2 Qubits

Para cada compuerta de dos qubits (`CZ` en Heron) aplicada al par $(q_i, q_j)$:

$$\mathcal{E}_{2Q}^{(i,j)} = \left[\mathcal{E}_{\text{thermal}}^{(i)} \otimes \mathcal{E}_{\text{thermal}}^{(j)}\right] \circ \mathcal{E}_{\text{depol}}^{(i,j)}$$

#### a) Error Depolarizante de 2 Qubits

El canal depolarizante de 2 qubits generaliza la fórmula:

$$\mathcal{E}_{\text{depol}}(\rho) = (1 - \lambda)\,\rho + \lambda\,\frac{I_4}{4}$$

donde $I_4/4 = I/2 \otimes I/2$ es el estado máximamente mezclado de 2 qubits. Equivalentemente, se aplica un operador de Pauli aleatorio de 2 qubits $P_a \otimes P_b$ (con $P \in \{I, X, Y, Z\}$, excluyendo $I \otimes I$) con probabilidad uniforme $\lambda/15$.

La probabilidad $\lambda$ se **calibra** para que el error total del canal (depolarización + relajación térmica) coincida con el `gate_error` del par $(q_i, q_j)$ reportado en el snapshot.

#### b) Relajación Térmica de 2 Qubits

Se aplica la relajación térmica **independientemente** a cada qubit del par, usando los $T_1^{(i)}$, $T_2^{(i)}$ del qubit $i$ y el tiempo de ejecución de la compuerta `CZ` ($t_{CZ} \approx 84$ ns):

$$\mathcal{E}_{\text{thermal}}^{(i)} \otimes \mathcal{E}_{\text{thermal}}^{(j)}$$

### 3.3 Errores de Lectura (*Readout Errors*)

Los errores de medición se modelan mediante una **matriz de asignación** $A_i$ para cada qubit $i$:

$$A_i = \begin{pmatrix} P(0|0)_i & P(0|1)_i \\ P(1|0)_i & P(1|1)_i \end{pmatrix}$$

donde:
- $P(0|0)_i$: probabilidad de medir "0" cuando el estado real es $|0\rangle$
- $P(1|0)_i$: probabilidad de medir "1" cuando el estado real es $|0\rangle$ (error tipo "bit-flip de lectura")
- Análogamente para $P(0|1)_i$ y $P(1|1)_i$

Estos errores se aplican **después** de la operación de medición proyectiva ideal, transformando la distribución de probabilidad real en la distribución observada.

Para $n$ qubits con errores de lectura independientes, la matriz de asignación total es:

$$A = A_1 \otimes A_2 \otimes \cdots \otimes A_n$$

---

## 4. Método de Simulación: ¿Cómo se Ejecuta Numéricamente?

### 4.1 Selección Automática del Método

`AerSimulator` en modo `automatic` (el predeterminado) elige el método de simulación más adecuado según el circuito, el modelo de ruido y la memoria disponible:

| Método | Representación del Estado | Memoria requerida | Qubits máximos (CPU típica) |
|:---|:---|:---|:---|
| `statevector` | Vector $|\psi\rangle \in \mathbb{C}^{2^n}$ | $2^n \times 16$ bytes | ~30–32 qubits |
| `density_matrix` | Matriz $\rho \in \mathbb{C}^{2^n \times 2^n}$ | $2^{2n} \times 16$ bytes | ~15–16 qubits |
| `matrix_product_state` | Tensores MPS comprimidos | Proporcional al entrelazamiento | Hasta ~50+ según circuito |

### 4.2 ¿Qué método se usa en este proyecto?

Para simulación **con ruido**, Aer típicamente utiliza el método **`density_matrix`** cuando el número de qubits es pequeño, o el método **`statevector`** con muestreo estocástico (*Monte Carlo sampling*):

- **Con `statevector` (muestreo estocástico):** Para cada *shot*, se genera una **instancia aleatoria del circuito ruidoso**, donde cada canal de error se *samplea* (es decir, se elige uno de los operadores de Kraus con la probabilidad correspondiente). Se simula el vector de estados puro resultante y se realiza una medición proyectiva. Se repite por cada shot.

- **Con `density_matrix`:** Se evoluciona directamente la matriz de densidad $\rho$ (estado mixto) aplicando los canales de error como superoperadores: $\rho \mapsto \sum_k E_k \rho E_k^\dagger$. La distribución de probabilidad se extrae directamente de $\text{diag}(\rho)$ al final, sin necesidad de repetir shots individuales.

### 4.3 ¿Cuántos qubits se simulan en este proyecto?

El circuito de Shor para $N = 15$ utiliza la clase `RegisterQC`:

```python
control_qubits = 2 * ceil(log2(15)) + 1 = 2 * 4 + 1 = 9   # registro QPE
target_qubits  = ceil(log2(15))          = 4                 # registro moduloaritmético
# ──────────────────────────────────────────────────
# Total = 13 qubits lógicos
```

**Sin embargo**, tras la transpilación a la topología de **133 qubits** de FakeTorino, el circuito se mapea a qubits **físicos** del chip. El transpilador:

1. Asigna los 13 qubits lógicos a 13 de los 133 qubits físicos disponibles (usando SABRE layout).
2. Inserta **compuertas SWAP** adicionales para conectar qubits no vecinos, pero esto no aumenta el número total de qubits ocupados más allá de los 13 originales (los SWAPs usan los mismos qubits, solo mueven el estado).

**Resultado:** Se simulan efectivamente **13 qubits** con el modelo de ruido que corresponde a los qubits físicos específicos del chip donde fueron asignados (cada uno con sus propios $T_1$, $T_2$ y tasas de error individuales).

> **Nota importante:** Aunque FakeTorino tiene 133 qubits, el simulador solo necesita simular los qubits afectados por el circuito. Aer optimiza esto automáticamente, simulando solo los 13 qubits activos, pero aplicando las propiedades de ruido de los qubits físicos concretos del chip donde se mapearon.

---

## 5. Flujo Completo de la Simulación Ruidosa

A continuación se describe el flujo paso a paso que ocurre en el proyecto:

```
┌──────────────────────────────────────────────────────────────┐
│ 1. CONSTRUCCIÓN DEL CIRCUITO LÓGICO                          │
│    RegisterQC.create_circuit(N=15, a=7)                      │
│    → Circuito de 13 qubits (9 control + 4 target)            │
│    → Compuertas: H, CU (exponenciación modular), QFT⁻¹      │
│    → Compuertas abstractas de alto nivel                      │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. TRANSPILACIÓN                                             │
│    transpile(qc, backend=fake_torino, opt_level=3,           │
│              layout_method='sabre', routing_method='sabre')   │
│                                                              │
│    a) Unrolling: CU → CZ, RZ, SX, X (basis gates de Heron)  │
│    b) Layout: 13 qubits lógicos → 13 qubits físicos del chip│
│    c) Routing: inserción de SWAPs para respetar coupling map │
│    d) Optimización: cancelación de gates redundantes          │
│                                                              │
│    Resultado: circuito ISA (Instruction Set Architecture)     │
│    → a=4, opt=3: depth_2Q = 439, gates_2Q = 600             │
│    → a=7, opt=3: depth_2Q = 869, gates_2Q = 1071            │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. SIMULACIÓN CON RUIDO (AerSimulator)                       │
│                                                              │
│    Para cada gate del circuito ISA:                           │
│                                                              │
│    ┌─ Gate 1Q (ej. SX en qubit q3) ─────────────────────┐   │
│    │  (i)  Aplicar gate ideal: ρ → SX · ρ · SX†         │   │
│    │  (ii) Aplicar error depolarizante (λ calibrado)     │   │
│    │  (iii)Aplicar relajación térmica (T₁³, T₂³, t_SX)  │   │
│    └─────────────────────────────────────────────────────┘   │
│                                                              │
│    ┌─ Gate 2Q (ej. CZ en q3, q7) ───────────────────────┐   │
│    │  (i)   Aplicar gate ideal: ρ → CZ · ρ · CZ†        │   │
│    │  (ii)  Aplicar depolarización 2Q (λ₂ calibrado)     │   │
│    │  (iii) Relajación térmica en q3 (T₁³, T₂³, t_CZ)   │   │
│    │  (iv)  Relajación térmica en q7 (T₁⁷, T₂⁷, t_CZ)   │   │
│    └─────────────────────────────────────────────────────┘   │
│                                                              │
│    ┌─ Medición en qubit qᵢ ─────────────────────────────┐   │
│    │  (i)   Medición proyectiva ideal → bitstring        │   │
│    │  (ii)  Error de readout: aplicar Aᵢ al resultado    │   │
│    └─────────────────────────────────────────────────────┘   │
│                                                              │
│    Se repite 512 veces (SHOTS = 512)                         │
│    Resultado: diccionario de counts {bitstring: frecuencia}  │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. POST-PROCESAMIENTO CLÁSICO                                │
│                                                              │
│    counts → distribución de probabilidad experimental Q(y)   │
│    Comparación con distribución teórica P(y)                 │
│    → Fidelidad de Hellinger: F_H = (Σ √(P·Q))²             │
│    → PST (señal): % de counts en picos teóricos             │
│    → Fracciones continuas: y/2ᵐ → s/r → factores           │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. ¿Por qué la Simulación con Ruido es ~300× más Lenta que la Ideal?

La simulación ideal (sin ruido) con `statevector` aplica cada compuerta como una multiplicación de matrices unitarias. Es determinista: un solo cálculo produce la distribución de probabilidad exacta.

La simulación con ruido es **drásticamente** más costosa por tres razones:

1. **Muestreo estocástico:** Cada *shot* requiere una ejecución independiente del circuito, ya que los errores son probabilísticos y varían entre ejecuciones.

2. **Canales de ruido adicionales:** Cada compuerta ejecuta no solo la operación ideal, sino también el canal depolarizante y el canal de relajación térmica. Esto triplica (aproximadamente) el número de operaciones matriciales por compuerta.

3. **Mayor profundidad efectiva:** Las compuertas SWAP insertadas durante la transpilación (para respetar la topología del chip) **no existían** en el circuito ideal, pero ahora cada una contribuye con errores 2Q adicionales.

**Tiempos observados en este proyecto (a=7, opt=3, 512 shots):**

| Simulación | Tiempo |
|:---|:---|
| Ideal | ~2 s |
| Ruido (baseline) | ~6,020 s (~100 min) |
| Ruido (DD + PT) | ~11,500 s (~3.2 h) |

---

## 7. ¿Qué NO Captura el Modelo de Ruido?

Es fundamental entender las **limitaciones** de la simulación con `FakeTorino`:

| Fenómeno real | ¿Modelado? | Comentario |
|:---|:---:|:---|
| Errores depolarizantes de gate | ✅ | Aproximado como canal de Pauli |
| Decoherencia $T_1$/$T_2$ | ✅ | Modelo de relajación térmica |
| Errores de lectura | ✅ | Matriz de asignación clásica |
| Topología (coupling map) | ✅ | Heavy-Hex de 133 qubits |
| **Crosstalk** (interferencia entre qubits) | ❌ | No modelado — en hardware real, operar sobre $q_i$ puede afectar a $q_j$ vecino |
| **Errores coherentes de gate** | ❌ | El modelo usa errores *estocásticos*; los errores reales tienen componentes coherentes (rotaciones sistemáticas) |
| **Drift** (variaciones temporales) | ❌ | El snapshot es una foto fija; el hardware real varía minuto a minuto |
| **Errores correlacionados** | ❌ | Los errores de lectura se modelan como independientes entre qubits |
| **Leakage** (fugas a estados no computacionales) | ❌ | Los qubits transmon tienen niveles energéticos superiores a $|0\rangle$, $|1\rangle$ que no se modelan |

> Esta es la razón fundamental por la que DD y PT **no mejoran** la señal en la simulación con `FakeTorino`, pero sí pueden mejorarla en el hardware real: las técnicas de mitigación actúan sobre fenómenos (errores coherentes, acoplamiento ambiental continuo) que el simulador no reproduce fielmente.

---

## 8. Resumen: La Cadena Completa

```mermaid
graph LR
    A["ibm_torino<br/>(hardware real)"] -->|calibración| B["Snapshot<br/>(JSON con T₁, T₂,<br/>errores, coupling map)"]
    B -->|almacenado en| C["FakeTorino<br/>(qiskit_ibm_runtime)"]
    C -->|from_backend()| D["NoiseModel<br/>(errores 1Q, 2Q, readout)"]
    D -->|configura| E["AerSimulator<br/>(simulador clásico)"]
    E -->|ejecuta| F["Circuito ISA<br/>(13 qubits transpilados)"]
    F -->|512 shots| G["Counts<br/>{bitstring: frecuencia}"]
    G -->|post-procesamiento| H["Métricas<br/>(PST, F_H, factores)"]

    style A fill:#e74c3c,color:white
    style C fill:#3498db,color:white
    style D fill:#f39c12,color:white
    style E fill:#27ae60,color:white
    style G fill:#9b59b6,color:white
```

En resumen:
1. **FakeTorino** proporciona un snapshot del chip real `ibm_torino` (Heron r1, 133 qubits).
2. **`AerSimulator.from_backend()`** extrae las propiedades y construye un `NoiseModel` con tres tipos de error: depolarizante, relajación térmica y readout.
3. El circuito de Shor (13 qubits lógicos) se **transpila** a las basis gates y la topología del chip.
4. La simulación aplica el gate ideal + canales de error por cada operación, repitiendo 512 veces.
5. Los counts resultantes reflejan una distribución contaminada por ruido, que luego se analiza con las métricas del trabajo de grado ($\mathcal{F}_H$, PST, fracciones continuas).

---

## Referencias

- **Qiskit Aer Documentation:** [Building Noise Models](https://qiskit.github.io/qiskit-aer/apidocs/aer_noise.html)
- **Qiskit IBM Runtime:** [Fake Provider API](https://docs.quantum.ibm.com/api/qiskit-ibm-runtime/fake_provider)
- **IBM Quantum:** [ibm_torino System Page](https://quantum.ibm.com/services/resources?system=ibm_torino)
- **Nielsen & Chuang:** *Quantum Computation and Quantum Information*, §8 — Quantum Noise and Quantum Operations.
- **Preskill, J. (2018):** "Quantum Computing in the NISQ era and beyond." *Quantum* 2, 79.
