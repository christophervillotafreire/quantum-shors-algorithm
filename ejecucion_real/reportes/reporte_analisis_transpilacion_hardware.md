# Reporte: Análisis de Transpilación + Hardware — RegisterQC N=15

**Fecha**: 2026-02-13 18:58:59
**Backend**: ibm_torino (Heron r1) | **N**: 15 | **a**: 4
**Shots**: 4096 | **Seed transpilador**: 457
**Job IDs**: d67rla9v6o8c73d5ucp0

---

## Resumen Ejecutivo

- **Objetivo**: Comparar sistemáticamente los 4 niveles de optimización del transpilador de Qiskit y cuantificar el impacto del algoritmo SABRE en la reducción de profundidad. **Ejecución en hardware real IBM Torino.**
- **Circuito**: RegisterQC para factorización de N=15 con a=4.
- **Backend**: ibm_torino — topología Heavy-Hex (Heron r1), 133 qubits.
- **Puertas nativas**: `cz, rzz, id, rx, rz, sx, x`.
- **Mejor configuración (transpilación)**: **Nivel 2** con depth 2Q = **433**.

---

## Tabla Comparativa por Nivel de Optimización (Transpilación)

| Nivel Opt. | Depth Total | Depth 2Q | 2Q Gates | SWAPs Est. | Total Gates | Layout | Routing | Tiempo (s) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 2615 | 570 | 923 | 113 | 5667 | trivial | basic | 0.255 |
| 1 | 1869 | 526 | 779 | 65 | 4042 | sabre | sabre | 0.239 |
| 2 | 1580 | 433 | 584 | 0 | 3210 | sabre | sabre | 0.429 |
| 3 | 1609 | 439 | 600 | 5 | 3328 | sabre | sabre | 1.278 |

---

## Reducción Relativa (vs Nivel 0)

| Nivel | Reducción Depth 2Q | Reducción 2Q Gates | Reducción Total Gates |
|:---:|:---:|:---:|:---:|
| 0 | 0.0% | 0.0% | 0.0% |
| 1 | 7.7% | 15.6% | 28.7% |
| 2 | 24.0% | 36.7% | 43.4% |
| 3 | 23.0% | 35.0% | 41.3% |

> **Nota**: Los porcentajes negativos indican un aumento respecto al nivel 0.

---

## Desglose de Puertas por Nivel

| Nivel | cz | measure | rz | sx | x |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 923 | 9 | 2338 | 2396 | 1 |
| 1 | 779 | 9 | 1489 | 1765 | 0 |
| 2 | 584 | 9 | 1138 | 1461 | 18 |
| 3 | 600 | 9 | 1191 | 1491 | 37 |

---

## Comparación SABRE vs Basic — Transpilación (Nivel 3)

| Algoritmo | Depth 2Q | 2Q Gates | Total Gates | Tiempo (s) |
|:---:|:---:|:---:|:---:|:---:|
| SABRE | 439 | 600 | 3338 | 0.438 |
| Basic | 662 | 1092 | 4925 | 1.812 |

---

## Análisis de SWAP Insertion

El transpilador inserta operaciones SWAP para mover qubits lógicos entre qubits físicos no adyacentes en la topología Heavy-Hex. En Heron r1, cada SWAP se descompone en **3 puertas CZ**.

| Nivel | 2Q Extras (vs mín.) | SWAPs Estimados | Overhead (%) |
|:---:|:---:|:---:|:---:|
| 0 | 339 | 113 | 36.7% |
| 1 | 195 | 65 | 25.0% |
| 2 | 0 | 0 | 0.0% |
| 3 | 16 | 5 | 2.7% |

---

## Resultados de Ejecución en Hardware Real

> **Backend**: ibm_torino | **Shots**: 4096 | **Job IDs**: d67rla9v6o8c73d5ucp0

| Nivel Opt. | Señal (%) | Ruido (%) | Bitstrings Únicos | Factores Encontrados | ¿Éxito? |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 6.1 | 93.9 | 500 | 3, 5 | ✓ |
| 1 | 15.5 | 84.5 | 487 | 3, 5 | ✓ |
| 2 | 50.8 | 49.2 | 374 | 3, 5 | ✓ |
| 3 | 3.0 | 97.0 | 421 | 3, 5 | ✓ |

### Top 5 Bitstrings por Nivel de Optimización


**Nivel 0:**

| # | Bitstring | Count | Probabilidad | Phase | Fracción | r | ¿Válido? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `000000000` | 103 | 0.0251 | 0.0000 | 0/1 | 1 |  |
| 2 | `100000000` | 87 | 0.0212 | 0.5000 | 1/2 | 2 | ✓ |
| 3 | `011000000` | 66 | 0.0161 | 0.3750 | 3/8 | 8 | ✓ |
| 4 | `001000000` | 65 | 0.0159 | 0.1250 | 1/8 | 8 | ✓ |
| 5 | `101000000` | 65 | 0.0159 | 0.6250 | 5/8 | 8 | ✓ |

**Nivel 1:**

| # | Bitstring | Count | Probabilidad | Phase | Fracción | r | ¿Válido? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `100000000` | 298 | 0.0728 | 0.5000 | 1/2 | 2 | ✓ |
| 2 | `000000000` | 276 | 0.0674 | 0.0000 | 0/1 | 1 |  |
| 3 | `111000000` | 117 | 0.0286 | 0.8750 | 7/8 | 8 | ✓ |
| 4 | `011000000` | 103 | 0.0251 | 0.3750 | 3/8 | 8 | ✓ |
| 5 | `011110000` | 66 | 0.0161 | 0.4688 | 7/15 | 15 |  |

**Nivel 2:**

| # | Bitstring | Count | Probabilidad | Phase | Fracción | r | ¿Válido? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `000000000` | 949 | 0.2317 | 0.0000 | 0/1 | 1 |  |
| 2 | `100000000` | 850 | 0.2075 | 0.5000 | 1/2 | 2 | ✓ |
| 3 | `000000010` | 175 | 0.0427 | 0.0039 | 0/1 | 1 |  |
| 4 | `100000010` | 162 | 0.0396 | 0.5039 | 1/2 | 2 | ✓ |
| 5 | `000000001` | 162 | 0.0396 | 0.0020 | 0/1 | 1 |  |

**Nivel 3:**

| # | Bitstring | Count | Probabilidad | Phase | Fracción | r | ¿Válido? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `111100000` | 209 | 0.0510 | 0.9375 | 14/15 | 15 |  |
| 2 | `011100000` | 135 | 0.0330 | 0.4375 | 4/9 | 9 |  |
| 3 | `001000000` | 117 | 0.0286 | 0.1250 | 1/8 | 8 | ✓ |
| 4 | `111100100` | 115 | 0.0281 | 0.9453 | 14/15 | 15 |  |
| 5 | `001100000` | 104 | 0.0254 | 0.1875 | 2/11 | 11 |  |

---

## SABRE vs Basic — Resultados Hardware (Nivel 3)

| Algoritmo | Señal (%) | Ruido (%) | Factores |
|:---:|:---:|:---:|:---:|
| SABRE | 5.1 | 94.9 | 3, 5 |
| Basic | 12.3 | 87.7 | 3, 5 |

---

## Conclusiones

1. **Impacto del nivel de optimización**: El nivel 3 reduce la profundidad 2Q en **23.0%** y el conteo de puertas 2Q en **35.0%** respecto al nivel 0.
2. **Algoritmo SABRE**: Los niveles 1–3 utilizan SABRE para layout y routing, lo que minimiza las operaciones SWAP insertadas al considerar la topología real del hardware.
3. **Nivel 0 (trivial)**: Utiliza layout trivial y routing basic, resultando en la mayor cantidad de SWAPs y profundidad.
4. **Configuración óptima (transpilación)**: **Nivel 2** ofrece el mejor balance entre profundidad y tiempo de transpilación.
5. **Recomendación**: Para ejecución en hardware IBM Torino, usar siempre **optimization_level=3** con SABRE routing.
6. **Mayor señal en hardware**: Nivel **2** con **50.78%** de señal para r=2.

![Plots](../imagenes/graficos_analisis_transpilacion.png)
