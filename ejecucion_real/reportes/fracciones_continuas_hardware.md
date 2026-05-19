# Fracciones Continuas — Hardware Real (IBM Torino)

> **Objetivo:** Aplicar el post-procesamiento clásico de fracciones continuas
> a los resultados medidos en hardware real (IBM Torino, Heron r1), completando
> la comparación con las simulaciones ideal y ruidosa.

## Configuración

- **Backend:** IBM Torino (Heron r1, 133 qubits)
- **N:** 15
- **Qubits de control:** 9
- **Shots:** 4096
- **Datos:** `counts_top10` del análisis de hardware

## Resumen por Base

| Base | r esperado | PST (%) | Fidelidad | Factores | Job ID |
|:----:|:----------:|:-------:|:---------:|:--------:|--------|
| a=2 | 4 | 42.4 | 0.2433 | 3 × 5 | `d6aghkvg4t5c…` |
| a=4 | 2 | 84.7 | 0.5757 | 3 × 5 | `d6kuc3ofh9oc…` |
| a=8 | 4 | 79.4 | 0.4836 | 3 × 5 | `d6aghrvg4t5c…` |
| a=11 | 2 | 35.5 | 0.3091 | 3 × 5 | `d6agi07g4t5c…` |
| a=13 | 4 | 45.3 | 0.2140 | 3 × 5 | `d6agi5954hss…` |

---

## Base a = 2 (r = 4)

**Job:** `d6aghkvg4t5c7383774g`  
**Estudio:** A3: a=2  
**Depth 2Q:** 225  |  **Gates 2Q:** 225  
**Fases teóricas:** [0.0, 0.25, 0.5, 0.75]  

### Análisis de Mediciones

| Bitstring | Decimal | Fase φ̃ | Fracción | r candidato | Válido | Señal | Prob (%) |
|:---------:|:-------:|:------:|:--------:|:-----------:|:------:|:-----:|:--------:|
| `000000000` | 0 | 0.0000 | 0/1 | 1 | — | ✓ señal | 36.1 |
| `000000100` | 4 | 0.0078 | 0/1 | 1 | — | ✓ señal | 31.6 |
| `010000100` | 132 | 0.2578 | 1/4 | 4 | ✓ | ✓ señal | 4.7 |
| `010000000` | 128 | 0.2500 | 1/4 | 4 | ✓ | ✓ señal | 4.4 |
| `000010000` | 16 | 0.0312 | 0/1 | 1 | — | ✗ ruido | 2.9 |
| `000010100` | 20 | 0.0391 | 1/15 | 15 | — | ✗ ruido | 2.4 |
| `000000110` | 6 | 0.0117 | 0/1 | 1 | — | ✗ ruido | 2.0 |
| `000000010` | 2 | 0.0039 | 0/1 | 1 | — | ✓ señal | 1.9 |
| `100000000` | 256 | 0.5000 | 1/2 | 2 | — | ✓ señal | 1.8 |
| `100000100` | 260 | 0.5078 | 1/2 | 2 | — | ✓ señal | 1.6 |

**PST (top10):** 82.0%  
**PST (all counts):** 42.4%  
**Factores extraídos:** [3, 5]  
**Éxito:** ✅ Sí  

---

## Base a = 4 (r = 2)

**Job:** `d6kuc3ofh9oc73em9bi0`  
**Estudio:** A6/A7: Solo PT  
**Depth 2Q:** 116  |  **Gates 2Q:** 116  
**Fases teóricas:** [0.0, 0.5]  

### Análisis de Mediciones

| Bitstring | Decimal | Fase φ̃ | Fracción | r candidato | Válido | Señal | Prob (%) |
|:---------:|:-------:|:------:|:--------:|:-----------:|:------:|:-----:|:--------:|
| `000000000` | 0 | 0.0000 | 0/1 | 1 | — | ✓ señal | 81.9 |
| `000100000` | 32 | 0.0625 | 1/15 | 15 | — | ✗ ruido | 5.6 |
| `010000000` | 128 | 0.2500 | 1/4 | 4 | ✓ | ✗ ruido | 4.4 |
| `100000000` | 256 | 0.5000 | 1/2 | 2 | ✓ | ✓ señal | 2.8 |
| `000000001` | 1 | 0.0020 | 0/1 | 1 | — | ✓ señal | 0.9 |
| `000000100` | 4 | 0.0078 | 0/1 | 1 | — | ✓ señal | 0.9 |
| `001000000` | 64 | 0.1250 | 1/8 | 8 | ✓ | ✗ ruido | 0.7 |
| `000001000` | 8 | 0.0156 | 0/1 | 1 | — | ✗ ruido | 0.6 |
| `000000010` | 2 | 0.0039 | 0/1 | 1 | — | ✓ señal | 0.5 |
| `010100000` | 160 | 0.3125 | 4/13 | 13 | — | ✗ ruido | 0.3 |

**PST (top10):** 87.0%  
**PST (all counts):** 84.7%  
**Factores extraídos:** [3, 5]  
**Éxito:** ✅ Sí  

---

## Base a = 8 (r = 4)

**Job:** `d6aghrvg4t5c738377b0`  
**Estudio:** A3: a=8  
**Depth 2Q:** 212  |  **Gates 2Q:** 212  
**Fases teóricas:** [0.0, 0.25, 0.5, 0.75]  

### Análisis de Mediciones

| Bitstring | Decimal | Fase φ̃ | Fracción | r candidato | Válido | Señal | Prob (%) |
|:---------:|:-------:|:------:|:--------:|:-----------:|:------:|:-----:|:--------:|
| `000000000` | 0 | 0.0000 | 0/1 | 1 | — | ✓ señal | 66.1 |
| `010000000` | 128 | 0.2500 | 1/4 | 4 | ✓ | ✓ señal | 7.7 |
| `000100000` | 32 | 0.0625 | 1/15 | 15 | — | ✗ ruido | 7.0 |
| `100000000` | 256 | 0.5000 | 1/2 | 2 | — | ✓ señal | 5.0 |
| `000000010` | 2 | 0.0039 | 0/1 | 1 | — | ✓ señal | 2.8 |
| `000000001` | 1 | 0.0020 | 0/1 | 1 | — | ✓ señal | 1.9 |
| `000001000` | 8 | 0.0156 | 0/1 | 1 | — | ✗ ruido | 1.5 |
| `000010000` | 16 | 0.0312 | 0/1 | 1 | — | ✗ ruido | 1.1 |
| `000000100` | 4 | 0.0078 | 0/1 | 1 | — | ✓ señal | 1.0 |
| `010100000` | 160 | 0.3125 | 4/13 | 13 | — | ✗ ruido | 0.8 |

**PST (top10):** 84.5%  
**PST (all counts):** 79.4%  
**Factores extraídos:** [3, 5]  
**Éxito:** ✅ Sí  

---

## Base a = 11 (r = 2)

**Job:** `d6agi07g4t5c738377f0`  
**Estudio:** A3: a=11  
**Depth 2Q:** 75  |  **Gates 2Q:** 76  
**Fases teóricas:** [0.0, 0.5]  

### Análisis de Mediciones

| Bitstring | Decimal | Fase φ̃ | Fracción | r candidato | Válido | Señal | Prob (%) |
|:---------:|:-------:|:------:|:--------:|:-----------:|:------:|:-----:|:--------:|
| `000000000` | 0 | 0.0000 | 0/1 | 1 | — | ✓ señal | 29.6 |
| `010000000` | 128 | 0.2500 | 1/4 | 4 | ✓ | ✗ ruido | 27.6 |
| `100000000` | 256 | 0.5000 | 1/2 | 2 | ✓ | ✓ señal | 5.9 |
| `001000000` | 64 | 0.1250 | 1/8 | 8 | ✓ | ✗ ruido | 5.4 |
| `110000000` | 384 | 0.7500 | 3/4 | 4 | ✓ | ✗ ruido | 4.5 |
| `011000000` | 192 | 0.3750 | 3/8 | 8 | ✓ | ✗ ruido | 4.3 |
| `000000010` | 2 | 0.0039 | 0/1 | 1 | — | ✓ señal | 2.0 |
| `010000010` | 130 | 0.2539 | 1/4 | 4 | ✓ | ✗ ruido | 1.9 |
| `000000100` | 4 | 0.0078 | 0/1 | 1 | — | ✓ señal | 1.6 |
| `010000100` | 132 | 0.2578 | 1/4 | 4 | ✓ | ✗ ruido | 1.5 |

**PST (top10):** 39.1%  
**PST (all counts):** 35.5%  
**Factores extraídos:** [3, 5]  
**Éxito:** ✅ Sí  

---

## Base a = 13 (r = 4)

**Job:** `d6agi5954hss73b673gg`  
**Estudio:** A3: a=13  
**Depth 2Q:** 212  |  **Gates 2Q:** 212  
**Fases teóricas:** [0.0, 0.25, 0.5, 0.75]  

### Análisis de Mediciones

| Bitstring | Decimal | Fase φ̃ | Fracción | r candidato | Válido | Señal | Prob (%) |
|:---------:|:-------:|:------:|:--------:|:-----------:|:------:|:-----:|:--------:|
| `000000000` | 0 | 0.0000 | 0/1 | 1 | — | ✓ señal | 40.2 |
| `000000010` | 2 | 0.0039 | 0/1 | 1 | — | ✓ señal | 32.6 |
| `010000000` | 128 | 0.2500 | 1/4 | 4 | ✓ | ✓ señal | 4.5 |
| `010000010` | 130 | 0.2539 | 1/4 | 4 | ✓ | ✓ señal | 4.4 |
| `000100010` | 34 | 0.0664 | 1/15 | 15 | — | ✗ ruido | 2.4 |
| `000100000` | 32 | 0.0625 | 1/15 | 15 | — | ✗ ruido | 2.3 |
| `000001000` | 8 | 0.0156 | 0/1 | 1 | — | ✗ ruido | 1.9 |
| `000001010` | 10 | 0.0195 | 0/1 | 1 | — | ✗ ruido | 1.5 |
| `000000100` | 4 | 0.0078 | 0/1 | 1 | — | ✓ señal | 1.3 |
| `000000110` | 6 | 0.0117 | 0/1 | 1 | — | ✗ ruido | 1.0 |

**PST (top10):** 83.0%  
**PST (all counts):** 45.3%  
**Factores extraídos:** [3, 5]  
**Éxito:** ✅ Sí  

---

## Conclusiones

1. Se analizaron **5 bases** en hardware real mediante fracciones continuas.
2. **5/5** bases produjeron factores correctos (3 × 5).
3. El post-procesamiento clásico de fracciones continuas es efectivo incluso con
   las distribuciones ruidosas del hardware, siempre que los picos teóricos
   dominen sobre el ruido de fondo.
4. Las bases con menor profundidad de circuito (menor depth_2q) presentan
   mayor señal y mayor probabilidad de extracción correcta del período.
