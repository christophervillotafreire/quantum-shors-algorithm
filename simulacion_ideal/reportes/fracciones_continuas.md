# Análisis de Fracciones Continuas: Algoritmo de Shor (N=15)

> **Objetivo:** Documentar con rigor completo cómo el post-procesamiento clásico del algoritmo de Shor recupera los factores de $N$ a partir de los resultados cuánticos de medición. Se muestra paso a paso la cadena completa: **medición $\to$ fase $\to$ fracciones continuas $\to$ período $\to$ factores**.

## 1. ¿Cómo se conecta la parte cuántica con la extracción de factores?

El algoritmo de Shor consta de **dos partes** que cooperan:

### Parte cuántica: Estimación de Fase (QPE)

El circuito cuántico implementa la **Estimación de Fase Cuántica** (QPE) sobre el operador unitario $U_a |y\rangle = |ay \bmod N\rangle$. Los eigenvalores de $U_a$ son:

$$U_a |u_s\rangle = e^{2\pi i s/r} |u_s\rangle, \quad s = 0, 1, \ldots, r-1$$

donde $r = \text{ord}_N(a)$ es el **orden multiplicativo** de $a$ módulo $N$ (el menor entero positivo tal que $a^r \equiv 1 \pmod{N}$).

Al medir el registro de control (de $m$ qubits), obtenemos un valor $y$ cuya fase es:

$$\tilde{\varphi} = \frac{y}{2^m} \approx \frac{s}{r}$$

Es decir, la medición cuántica nos da una **aproximación binaria** a la fracción $s/r$, donde $s$ es aleatorio pero $r$ es el período que necesitamos.

### Parte clásica: De la fase al período y de ahí a los factores

El problema es que conocemos $\tilde{\varphi} = y/2^m$ como número decimal, pero necesitamos recuperar el denominador $r$ de la fracción $s/r$. Esto se logra con el **algoritmo de fracciones continuas**.

Una vez que tenemos $r$, los factores de $N$ se extraen con **aritmética clásica**:

$$p = \gcd\left(a^{r/2} - 1,\; N\right), \quad q = \gcd\left(a^{r/2} + 1,\; N\right)$$

Si $r$ es par y $a^{r/2} \not\equiv -1 \pmod{N}$, entonces $p$ y $q$ son factores **no triviales** de $N$.

## 2. Algoritmo de Fracciones Continuas (detalle formal)

### 2.1 ¿Por qué funciona? (N&C Teorema 5.1, pág. 229)

> **Teorema 5.1 (Nielsen & Chuang, pág. 229).** Supóngase que $s/r$ es un número racional tal que
> $$\left|\frac{s}{r} - \varphi\right| \le \frac{1}{2r^2}$$
> Entonces $s/r$ es un **convergente** de la expansión en fracción continua de $\varphi$.

Este teorema garantiza que si la fase medida $\tilde{\varphi} = y/2^t$ es suficientemente cercana a $s/r$, entonces $s/r$ aparecerá como convergente. Como tenemos $t = 2L+1$ qubits de control (con $L = \lceil \log_2 N \rceil$), se cumple que $2^t > 2N^2$, lo que asegura $|\tilde{\varphi} - s/r| \le 1/2^{t+1} \le 1/(2r^2)$ para $r < N$.

### 2.2 Paso 1: Descomposición en coeficientes

Dada la fase $\tilde{\varphi} = y/2^t$, aplicamos el algoritmo de Euclides para obtener los coeficientes $[a_0; a_1, a_2, \ldots]$ tales que:

$$\frac{y}{2^t} = a_0 + \cfrac{1}{a_1 + \cfrac{1}{a_2 + \cfrac{1}{\ddots}}}$$

donde cada $a_k = \lfloor \text{numerador}_k / \text{denominador}_k \rfloor$, y la iteración es:

$$\text{num}_{k+1} = \text{den}_k, \quad \text{den}_{k+1} = \text{num}_k - a_k \cdot \text{den}_k$$

### 2.3 Paso 2: Cálculo de convergentes

Los convergentes $p_k/q_k$ se calculan con la **recursión de Euler**:

$$p_k = a_k \cdot p_{k-1} + p_{k-2}, \quad q_k = a_k \cdot q_{k-1} + q_{k-2}$$

con condiciones iniciales $p_{-2} = 0,\; p_{-1} = 1,\; q_{-2} = 1,\; q_{-1} = 0$ (N&C Box 5.3, pág. 230).

Cada convergente $p_k/q_k$ es la **mejor aproximación racional** a $y/2^t$ con denominador $\le q_k$.

### 2.4 Paso 3: Identificación del período

Para cada convergente, evaluamos si el denominador $q_k$ es el período $r$:

1. ¿$1 < q_k < N$? → Es **candidato**
2. ¿$a^{q_k} \equiv 1 \pmod{N}$? → Es **período válido**

### 2.5 Paso 4: Extracción de factores

Si $r$ es par, calculamos:

$$a^{r/2} \bmod N \quad \text{(exponenciación modular clásica)}$$

Luego:

$$p = \gcd(a^{r/2} - 1, N), \quad q = \gcd(a^{r/2} + 1, N)$$

**¿Por qué funciona esto?** Porque $a^r \equiv 1 \pmod{N}$ implica:

$$a^r - 1 \equiv 0 \pmod{N} \implies (a^{r/2} - 1)(a^{r/2} + 1) \equiv 0 \pmod{N}$$

Es decir, $N$ divide al producto $(a^{r/2} - 1)(a^{r/2} + 1)$. Si $N$ no divide a ninguno de los dos factores individualmente (es decir, $a^{r/2} \not\equiv \pm 1 \pmod{N}$), entonces $\gcd(a^{r/2} \pm 1, N)$ nos da factores **no triviales** de $N$.

## 3. Resultados por Base — Ejemplos Trabajados Paso a Paso

### Base $a=4$, $\text{ord}_{15}(4) = 2$

| $y$ (decimal) | Bitstring | Prob. | Fase $\tilde{\varphi}$ | FC | Período $r$ | Factores |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 256 | `100000000` | 0.5139 | 0.500000 | [0; 2] | 2 | 3, 5 |
| 0 | `000000000` | 0.4861 | 0.000000 | [0] | — | — |

#### Ejemplo completo: resultado de medición $y = 256$

**Paso 1 — Fase estimada:**

$$\tilde{\varphi} = \frac{y}{2^m} = \frac{256}{512} = 0.5$$

**Paso 2 — Descomposición en fracción continua:**

Aplicamos el algoritmo de Euclides a $256/512$:

| Iteración | Numerador | Denominador | $a_k = \lfloor \text{num}/\text{den} \rfloor$ | Nuevo num | Nuevo den |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 256 | 512 | **0** | 512 | 256 |
| 1 | 512 | 256 | **2** | 256 | 0 |

Resultado: $\tilde{\varphi} = [0; 2]$

**Paso 3 — Cálculo de convergentes (recursión de Euler):**

Aplicamos la recursión con semillas $p_{{-2}}=0, p_{{-1}}=1, q_{{-2}}=1, q_{{-1}}=0$:

| $k$ | $a_k$ | $p_k = a_k \cdot p_{k-1} + p_{k-2}$ | $q_k = a_k \cdot q_{k-1} + q_{k-2}$ | Convergente $p_k/q_k$ | Valor |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 0 | $0 \cdot 1 + 0 = 0$ | $0 \cdot 0 + 1 = 1$ | $0/1$ = 0.0 | |
| 1 | 2 | $2 \cdot 0 + 1 = 1$ | $2 \cdot 1 + 0 = 2$ | $1/2$ = 0.5 | |

**Paso 4 — Evaluación de candidatos a período $r$:**

| $k$ | $q_k$ | ¿$1 < q_k < N$? | ¿$a^{q_k} \equiv 1 \pmod{N}$? | Período válido |
|:---:|:---:|:---:|:---:|:---:|
| 0 | 1 | ❌ No ($q_k=1$) | — | — |
| 1 | 2 | ✅ Sí | ✅ Sí ($4^{2} \equiv 1 \pmod{15}$) | **$r = 2$** |

**Paso 5 — Extracción de factores de $N=15$:**

El período encontrado es $r = 2$, que es **par** ✅

Calculamos la exponenciación modular clásica:

$$a^{r/2} \bmod N = 4^{1} \bmod 15 = 4$$

Ahora usamos la identidad $(a^{r/2} - 1)(a^{r/2} + 1) \equiv 0 \pmod{N}$:

$$(4 - 1)(4 + 1) = 3 \cdot 5 = 15$$

Verificación: $15 = 1 \times 15 + 0$ → $15 \equiv 0 \pmod{15}$ ✅

Factores:

$$p = \gcd(3,\; 15) = \gcd(4^{1} - 1,\; 15) = \boxed{3}$$

$$q = \gcd(5,\; 15) = \gcd(4^{1} + 1,\; 15) = \boxed{5}$$

**Resultado:** $N = 3 \times 5 = 15$ → ✅ **¡Factorización exitosa!**

El circuito cuántico midió $y=256$, de ahí extraímos $r=2$, y con aritmética clásica obtuvimos $\boxed{15 = 3 \times 5}$.

#### Caso $y = 0$

La medición $y=0$ corresponde a la fase $\tilde{\varphi} = 0/2^m = 0$, que equivale a $s = 0$ en $s/r$. Este resultado **no aporta información** sobre el período y se descarta. En simulación ideal, ocurre con probabilidad $1/r = 1/2 = 0.5$.

---

### Base $a=7$, $\text{ord}_{15}(7) = 4$

| $y$ (decimal) | Bitstring | Prob. | Fase $\tilde{\varphi}$ | FC | Período $r$ | Factores |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 384 | `110000000` | 0.2620 | 0.750000 | [0; 1, 3] | 4 | 3, 5 |
| 0 | `000000000` | 0.2507 | 0.000000 | [0] | — | — |
| 128 | `010000000` | 0.2459 | 0.250000 | [0; 4] | 4 | 3, 5 |
| 256 | `100000000` | 0.2415 | 0.500000 | [0; 2] | — | — |

#### Ejemplo completo: resultado de medición $y = 384$

**Paso 1 — Fase estimada:**

$$\tilde{\varphi} = \frac{y}{2^m} = \frac{384}{512} = 0.75$$

**Paso 2 — Descomposición en fracción continua:**

Aplicamos el algoritmo de Euclides a $384/512$:

| Iteración | Numerador | Denominador | $a_k = \lfloor \text{num}/\text{den} \rfloor$ | Nuevo num | Nuevo den |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 384 | 512 | **0** | 512 | 384 |
| 1 | 512 | 384 | **1** | 384 | 128 |
| 2 | 384 | 128 | **3** | 128 | 0 |

Resultado: $\tilde{\varphi} = [0; 1, 3]$

**Paso 3 — Cálculo de convergentes (recursión de Euler):**

Aplicamos la recursión con semillas $p_{{-2}}=0, p_{{-1}}=1, q_{{-2}}=1, q_{{-1}}=0$:

| $k$ | $a_k$ | $p_k = a_k \cdot p_{k-1} + p_{k-2}$ | $q_k = a_k \cdot q_{k-1} + q_{k-2}$ | Convergente $p_k/q_k$ | Valor |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 0 | $0 \cdot 1 + 0 = 0$ | $0 \cdot 0 + 1 = 1$ | $0/1$ = 0.0 | |
| 1 | 1 | $1 \cdot 0 + 1 = 1$ | $1 \cdot 1 + 0 = 1$ | $1/1$ = 1.0 | |
| 2 | 3 | $3 \cdot 1 + 0 = 3$ | $3 \cdot 1 + 1 = 4$ | $3/4$ = 0.75 | |

**Paso 4 — Evaluación de candidatos a período $r$:**

| $k$ | $q_k$ | ¿$1 < q_k < N$? | ¿$a^{q_k} \equiv 1 \pmod{N}$? | Período válido |
|:---:|:---:|:---:|:---:|:---:|
| 0 | 1 | ❌ No ($q_k=1$) | — | — |
| 1 | 1 | ❌ No ($q_k=1$) | — | — |
| 2 | 4 | ✅ Sí | ✅ Sí ($7^{4} \equiv 1 \pmod{15}$) | **$r = 4$** |

**Paso 5 — Extracción de factores de $N=15$:**

El período encontrado es $r = 4$, que es **par** ✅

Calculamos la exponenciación modular clásica:

$$a^{r/2} \bmod N = 7^{2} \bmod 15 = 4$$

Ahora usamos la identidad $(a^{r/2} - 1)(a^{r/2} + 1) \equiv 0 \pmod{N}$:

$$(4 - 1)(4 + 1) = 3 \cdot 5 = 15$$

Verificación: $15 = 1 \times 15 + 0$ → $15 \equiv 0 \pmod{15}$ ✅

Factores:

$$p = \gcd(3,\; 15) = \gcd(7^{2} - 1,\; 15) = \boxed{3}$$

$$q = \gcd(5,\; 15) = \gcd(7^{2} + 1,\; 15) = \boxed{5}$$

**Resultado:** $N = 3 \times 5 = 15$ → ✅ **¡Factorización exitosa!**

El circuito cuántico midió $y=384$, de ahí extraímos $r=4$, y con aritmética clásica obtuvimos $\boxed{15 = 3 \times 5}$.

#### Caso $y = 0$

La medición $y=0$ corresponde a la fase $\tilde{\varphi} = 0/2^m = 0$, que equivale a $s = 0$ en $s/r$. Este resultado **no aporta información** sobre el período y se descarta. En simulación ideal, ocurre con probabilidad $1/r = 1/4 = 0.25$.

---

### Base $a=11$, $\text{ord}_{15}(11) = 2$

| $y$ (decimal) | Bitstring | Prob. | Fase $\tilde{\varphi}$ | FC | Período $r$ | Factores |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | `000000000` | 0.5024 | 0.000000 | [0] | — | — |
| 256 | `100000000` | 0.4976 | 0.500000 | [0; 2] | 2 | 3, 5 |

#### Ejemplo completo: resultado de medición $y = 256$

**Paso 1 — Fase estimada:**

$$\tilde{\varphi} = \frac{y}{2^m} = \frac{256}{512} = 0.5$$

**Paso 2 — Descomposición en fracción continua:**

Aplicamos el algoritmo de Euclides a $256/512$:

| Iteración | Numerador | Denominador | $a_k = \lfloor \text{num}/\text{den} \rfloor$ | Nuevo num | Nuevo den |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 256 | 512 | **0** | 512 | 256 |
| 1 | 512 | 256 | **2** | 256 | 0 |

Resultado: $\tilde{\varphi} = [0; 2]$

**Paso 3 — Cálculo de convergentes (recursión de Euler):**

Aplicamos la recursión con semillas $p_{{-2}}=0, p_{{-1}}=1, q_{{-2}}=1, q_{{-1}}=0$:

| $k$ | $a_k$ | $p_k = a_k \cdot p_{k-1} + p_{k-2}$ | $q_k = a_k \cdot q_{k-1} + q_{k-2}$ | Convergente $p_k/q_k$ | Valor |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 0 | $0 \cdot 1 + 0 = 0$ | $0 \cdot 0 + 1 = 1$ | $0/1$ = 0.0 | |
| 1 | 2 | $2 \cdot 0 + 1 = 1$ | $2 \cdot 1 + 0 = 2$ | $1/2$ = 0.5 | |

**Paso 4 — Evaluación de candidatos a período $r$:**

| $k$ | $q_k$ | ¿$1 < q_k < N$? | ¿$a^{q_k} \equiv 1 \pmod{N}$? | Período válido |
|:---:|:---:|:---:|:---:|:---:|
| 0 | 1 | ❌ No ($q_k=1$) | — | — |
| 1 | 2 | ✅ Sí | ✅ Sí ($11^{2} \equiv 1 \pmod{15}$) | **$r = 2$** |

**Paso 5 — Extracción de factores de $N=15$:**

El período encontrado es $r = 2$, que es **par** ✅

Calculamos la exponenciación modular clásica:

$$a^{r/2} \bmod N = 11^{1} \bmod 15 = 11$$

Ahora usamos la identidad $(a^{r/2} - 1)(a^{r/2} + 1) \equiv 0 \pmod{N}$:

$$(11 - 1)(11 + 1) = 10 \cdot 12 = 120$$

Verificación: $120 = 8 \times 15 + 0$ → $120 \equiv 0 \pmod{15}$ ✅

Factores:

$$p = \gcd(10,\; 15) = \gcd(11^{1} - 1,\; 15) = \boxed{5}$$

$$q = \gcd(12,\; 15) = \gcd(11^{1} + 1,\; 15) = \boxed{3}$$

**Resultado:** $N = 5 \times 3 = 15$ → ✅ **¡Factorización exitosa!**

El circuito cuántico midió $y=256$, de ahí extraímos $r=2$, y con aritmética clásica obtuvimos $\boxed{15 = 5 \times 3}$.

#### Caso $y = 0$

La medición $y=0$ corresponde a la fase $\tilde{\varphi} = 0/2^m = 0$, que equivale a $s = 0$ en $s/r$. Este resultado **no aporta información** sobre el período y se descarta. En simulación ideal, ocurre con probabilidad $1/r = 1/2 = 0.5$.

---

### Base $a=14$, $\text{ord}_{15}(14) = 2$

| $y$ (decimal) | Bitstring | Prob. | Fase $\tilde{\varphi}$ | FC | Período $r$ | Factores |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | `000000000` | 0.5015 | 0.000000 | [0] | — | — |
| 256 | `100000000` | 0.4985 | 0.500000 | [0; 2] | 2 | triviales |

#### Ejemplo completo: resultado de medición $y = 256$

**Paso 1 — Fase estimada:**

$$\tilde{\varphi} = \frac{y}{2^m} = \frac{256}{512} = 0.5$$

**Paso 2 — Descomposición en fracción continua:**

Aplicamos el algoritmo de Euclides a $256/512$:

| Iteración | Numerador | Denominador | $a_k = \lfloor \text{num}/\text{den} \rfloor$ | Nuevo num | Nuevo den |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 256 | 512 | **0** | 512 | 256 |
| 1 | 512 | 256 | **2** | 256 | 0 |

Resultado: $\tilde{\varphi} = [0; 2]$

**Paso 3 — Cálculo de convergentes (recursión de Euler):**

Aplicamos la recursión con semillas $p_{{-2}}=0, p_{{-1}}=1, q_{{-2}}=1, q_{{-1}}=0$:

| $k$ | $a_k$ | $p_k = a_k \cdot p_{k-1} + p_{k-2}$ | $q_k = a_k \cdot q_{k-1} + q_{k-2}$ | Convergente $p_k/q_k$ | Valor |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 0 | $0 \cdot 1 + 0 = 0$ | $0 \cdot 0 + 1 = 1$ | $0/1$ = 0.0 | |
| 1 | 2 | $2 \cdot 0 + 1 = 1$ | $2 \cdot 1 + 0 = 2$ | $1/2$ = 0.5 | |

**Paso 4 — Evaluación de candidatos a período $r$:**

| $k$ | $q_k$ | ¿$1 < q_k < N$? | ¿$a^{q_k} \equiv 1 \pmod{N}$? | Período válido |
|:---:|:---:|:---:|:---:|:---:|
| 0 | 1 | ❌ No ($q_k=1$) | — | — |
| 1 | 2 | ✅ Sí | ✅ Sí ($14^{2} \equiv 1 \pmod{15}$) | **$r = 2$** |

**Paso 5 — Extracción de factores de $N=15$:**

El período encontrado es $r = 2$, que es **par** ✅

Calculamos la exponenciación modular clásica:

$$a^{r/2} \bmod N = 14^{1} \bmod 15 = 14$$

Ahora usamos la identidad $(a^{r/2} - 1)(a^{r/2} + 1) \equiv 0 \pmod{N}$:

$$(14 - 1)(14 + 1) = 13 \cdot 15 = 195$$

Verificación: $195 = 13 \times 15 + 0$ → $195 \equiv 0 \pmod{15}$ ✅

Factores:

$$p = \gcd(13,\; 15) = \gcd(14^{1} - 1,\; 15) = \boxed{1}$$

$$q = \gcd(15,\; 15) = \gcd(14^{1} + 1,\; 15) = \boxed{15}$$

**Resultado:** Los factores $1$ y $15$ son **triviales** ($\{1, N\}$).

Esto ocurre porque $a = 14 \equiv -1 \pmod{15}$, por lo que:

$$a^{r/2} = 14^1 = 14 \equiv -1 \pmod{15}$$

y entonces $\gcd(a^{r/2} + 1, N) = \gcd(15, 15) = 15$ (trivial). Este es un caso conocido donde el algoritmo de Shor falla y debe reintentar con otro $a$.

#### Caso $y = 0$

La medición $y=0$ corresponde a la fase $\tilde{\varphi} = 0/2^m = 0$, que equivale a $s = 0$ en $s/r$. Este resultado **no aporta información** sobre el período y se descarta. En simulación ideal, ocurre con probabilidad $1/r = 1/2 = 0.5$.

---

## 4. Resumen: La Cadena Completa de Factorización

```
┌─────────────────────────────────────────────────────────────────┐
│  PARTE CUÁNTICA                                                │
│                                                                │
│  1. Preparar |1⟩ en registro target                            │
│  2. Hadamard en todos los qubits de control                    │
│  3. Aplicar C-U_{a^{2^k}} para k = 0, ..., m-1                │
│  4. Aplicar QFT⁻¹ al registro de control                      │
│  5. Medir → obtener y (entero de m bits)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │  y = resultado de medición
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PARTE CLÁSICA                                                 │
│                                                                │
│  6. Calcular fase: φ̃ = y / 2^m                                │
│  7. Fracciones continuas: φ̃ → [a₀; a₁, ...] → convergentes   │
│  8. Identificar r: buscar q_k tal que a^{q_k} ≡ 1 (mod N)     │
│  9. Si r par: calcular gcd(a^{r/2} ± 1, N)                    │
│  10. Verificar p × q = N → ¡Factores encontrados!              │
└─────────────────────────────────────────────────────────────────┘
```

## 5. Conclusiones

1. El algoritmo de fracciones continuas **recupera exitosamente** el período $r$ a partir de las fases medidas por el QPE para $a \in \{4, 7, 11\}$.

2. La cadena completa funciona: el QPE mide $y$, la fracción continua extrae $s/r$ del valor $y/2^m$, el denominador $r$ es el período, y $\gcd(a^{r/2} \pm 1, N)$ da los factores $3$ y $5$ de $N = 15$.

3. Para $a=14$ ($a \equiv -1 \pmod{15}$), el período $r=2$ se encuentra correctamente, pero los factores son **triviales** ($\{1, 15\}$). Esto es una limitación algebraica intrínseca, no un error del circuito (ver Nielsen & Chuang §5.3.2).

4. La medición $y=0$ (fase $\varphi = 0$) no aporta información sobre el período y debe descartarse. En simulación ideal ocurre con probabilidad exactamente $1/r$.

5. La trazabilidad completa de cada paso (Euclides → convergentes → candidatos → GCD) permite verificar rigurosamente el post-procesamiento clásico del algoritmo.
