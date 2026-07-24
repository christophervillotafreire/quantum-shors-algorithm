# Evaluación y Optimización del Algoritmo de Shor en Procesadores NISQ
**Un estudio comparativo de fidelidad y transpilación en IBM Quantum**

Este repositorio contiene el código y los datos del proyecto de investigación enfocado en diseñar, optimizar y ejecutar el algoritmo de Shor para la factorización de $N=15$, evaluando su rendimiento en hardware cuántico comercial en la era NISQ.

## 🚀 Metodología Experimental
El flujo de trabajo unifica el procesamiento clásico y cuántico en tres fases:
1. **Simulación Ideal:** Línea base lógica sin ruido (conectividad *all-to-all*).
2. **Modelos de Ruido (Fake Backends):** Inyección de ruido estocástico usando `FakeTorino`.
3. **Ejecución en Hardware Real:** Pruebas en el procesador `ibm_torino` (Arquitectura Heron r1, 133 qubits, topología *Heavy-Hex*).

## ⚙️ Técnicas Implementadas
Para adaptar el circuito teórico a los estrictos tiempos de coherencia ($T_1, T_2$) del hardware físico, se utilizaron:
- **Enrutamiento Heurístico:** Mapeo mediante el algoritmo SABRE.
- **Compresión de Circuitos:** Reducción de profundidad mediante `approx_degree=0.7`.
- **Supresión de Errores:** Aplicación de Pauli Twirling (PT) y Desacoplamiento Dinámico (DD) con secuencias XY4.

## 📊 Hallazgos Principales
- **Factorización Exitosa:** Se extrajeron los factores $\{3, 5\}$ en 6 de las 7 bases coprimas válidas en el hardware real.
- **Métricas:** Con el nivel de optimización máximo (`opt=3`), se alcanzó una Probabilidad de Éxito de la Señal (PST) del **82.8%** y una Fidelidad de Hellinger de **0.547**.
- **Impacto de la Transpilación:** La optimización estructural del circuito resultó ser más crítica que las técnicas de supresión de errores pasivas, mejorando el éxito hasta en dos órdenes de magnitud.
- **Límites del DD:** El Desacoplamiento Dinámico introdujo *crosstalk* y ruido de calibración extra, resultando contraproducente en estos circuitos de profundidad moderada.

## 📂 Estructura del Repositorio
```text
├── circuits/          # Diagramas de los circuitos lógicos y transpilados
├── configs/           # Archivos de configuración para compilación en Qiskit
├── notebooks/         # Jupyter Notebooks por fases
│   ├── fase1_simulacion_ideal.ipynb
│   ├── fase2_modelos_ruido.ipynb
│   └── fase3_ejecucion_hardware.ipynb
├── src/               # Scripts de procesamiento clásico (Fracciones continuas, paridad)
└── data/              # Datos de calibración de las QPUs e histogramas

```

## 🛠️ Requisitos e Instalación

Se requiere Python 3.10+ y las librerías oficiales de IBM Quantum:

```bash
pip install qiskit qiskit-ibm-runtime matplotlib numpy scipy

```

Configura tu token para acceder a los procesadores cuánticos:

```python
from qiskit_ibm_runtime import QiskitRuntimeService
QiskitRuntimeService.save_account(channel="ibm_quantum", token="TU_API_TOKEN", overwrite=True)

```

## 🎓 Autor

**Christopher Andrey Villota Freire**

*Director:* Jorge Hernán López Melo, PhD.

Departamento de Física, Facultad de Ciencias Exactas y Naturales

Universidad de Nariño (Pasto, Colombia) - 2026

```
