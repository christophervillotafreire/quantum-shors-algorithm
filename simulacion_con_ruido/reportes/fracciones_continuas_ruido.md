# Fracciones Continuas con Ruido: Post-Procesamiento de Shor (N=15)

> **Objetivo:** Analizar cómo el ruido afecta la extracción de factores vía fracciones continuas. Se ejecuta con DD+PT (mejor mitigación) para mostrar el post-procesamiento en condiciones realistas.

## 1. Configuración

- **Backend:** FakeTorino (ruido activo)
- **Mitigación:** DD (XpXm) + PT (active)
- **Opt level:** 3
- **Shots:** 512

## 2. Método de Fracciones Continuas

Para cada medición $y$ del QPE:
1. Calcular la fase: $\varphi = y / 2^m$
2. Aproximar por fracción continua: $\varphi \approx s/r$ con $r < N$
3. Verificar: $a^r \equiv 1 \pmod{N}$?
4. Si $r$ par: $\gcd(a^{r/2} \pm 1, N) \to$ factores

**Con ruido**, aparecen mediciones espúreas ($y$ que no corresponden a ninguna fase teórica $s/r$), generando candidatos $r$ falsos.

## 3.1 Base $a = 4$ ($r = 2$)

**Fases esperadas:** [0.0, 0.5]

**PST:** 4.49% | **Factores:** [3, 5] | **Éxito:** ✅

| # | Bitstring | $y$ | $\varphi$ | Aprox. | $r$ cand. | Válido | Tipo | Prob. |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `011111011` | 251 | 0.4902 | 1/2 | 2 | ✓ | señal | 1.17% |
| 2 | `111011101` | 477 | 0.9316 | 14/15 | 15 | ✗ | **ruido** | 0.98% |
| 3 | `001100110` | 102 | 0.1992 | 1/5 | 5 | ✗ | **ruido** | 0.78% |
| 4 | `000111100` | 60 | 0.1172 | 1/9 | 9 | ✗ | **ruido** | 0.78% |
| 5 | `111111000` | 504 | 0.9844 | 1/1 | 1 | ✗ | **ruido** | 0.78% |
| 6 | `011011010` | 218 | 0.4258 | 3/7 | 7 | ✗ | **ruido** | 0.78% |
| 7 | `101010100` | 340 | 0.6641 | 2/3 | 3 | ✗ | **ruido** | 0.78% |
| 8 | `010100100` | 164 | 0.3203 | 4/13 | 13 | ✗ | **ruido** | 0.78% |
| 9 | `111100101` | 485 | 0.9473 | 14/15 | 15 | ✗ | **ruido** | 0.78% |
| 10 | `101111101` | 381 | 0.7441 | 3/4 | 4 | ✓ | **ruido** | 0.78% |
| 11 | `011100001` | 225 | 0.4395 | 4/9 | 9 | ✗ | **ruido** | 0.78% |
| 12 | `100100111` | 295 | 0.5762 | 4/7 | 7 | ✗ | **ruido** | 0.78% |
| 13 | `100111011` | 315 | 0.6152 | 8/13 | 13 | ✗ | **ruido** | 0.78% |
| 14 | `110100111` | 423 | 0.8262 | 5/6 | 6 | ✓ | **ruido** | 0.78% |
| 15 | `111011100` | 476 | 0.9297 | 13/14 | 14 | ✓ | **ruido** | 0.78% |

## 3.2 Base $a = 7$ ($r = 4$)

**Fases esperadas:** [0.0, 0.25, 0.5, 0.75]

**PST:** 46.68% | **Factores:** [3, 5] | **Éxito:** ✅

| # | Bitstring | $y$ | $\varphi$ | Aprox. | $r$ cand. | Válido | Tipo | Prob. |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `000000000` | 0 | 0.0000 | 0/1 | 1 | ✗ | señal | 8.98% |
| 2 | `100000000` | 256 | 0.5000 | 1/2 | 2 | ✗ | señal | 7.23% |
| 3 | `010000000` | 128 | 0.2500 | 1/4 | 4 | ✓ | señal | 7.03% |
| 4 | `110000000` | 384 | 0.7500 | 3/4 | 4 | ✓ | señal | 6.84% |
| 5 | `100000001` | 257 | 0.5020 | 1/2 | 2 | ✗ | señal | 2.15% |
| 6 | `110000001` | 385 | 0.7520 | 3/4 | 4 | ✓ | señal | 1.76% |
| 7 | `100100000` | 288 | 0.5625 | 5/9 | 9 | ✗ | **ruido** | 1.76% |
| 8 | `011000000` | 192 | 0.3750 | 3/8 | 8 | ✓ | **ruido** | 1.76% |
| 9 | `101000000` | 320 | 0.6250 | 5/8 | 8 | ✓ | **ruido** | 1.76% |
| 10 | `000001000` | 8 | 0.0156 | 0/1 | 1 | ✗ | **ruido** | 1.76% |
| 11 | `000000010` | 2 | 0.0039 | 0/1 | 1 | ✗ | señal | 1.56% |
| 12 | `110100000` | 416 | 0.8125 | 9/11 | 11 | ✗ | **ruido** | 1.56% |
| 13 | `000000001` | 1 | 0.0020 | 0/1 | 1 | ✗ | señal | 1.56% |
| 14 | `010010000` | 144 | 0.2812 | 2/7 | 7 | ✗ | **ruido** | 1.56% |
| 15 | `010100000` | 160 | 0.3125 | 4/13 | 13 | ✗ | **ruido** | 1.37% |

## 4. Impacto del Ruido en la Extracción de Factores

- **Fases espúreas:** El ruido genera mediciones en posiciones $y$ que no corresponden a ningún múltiplo de $2^m/r$, produciendo fracciones continuas con denominadores incorrectos.
- **Candidatos $r$ falsos:** Estas fases espúreas generan candidatos $r$ que no satisfacen $a^r \equiv 1 \pmod{N}$ (filtrados por la verificación clásica).
- **Robustez:** A pesar del ruido, si la señal (PST) es suficiente, los picos teóricos dominan y la extracción de factores sigue siendo exitosa.
- **DD+PT ayuda:** La mitigación de errores concentra más probabilidad en los picos teóricos, mejorando la tasa de éxito de la extracción.
