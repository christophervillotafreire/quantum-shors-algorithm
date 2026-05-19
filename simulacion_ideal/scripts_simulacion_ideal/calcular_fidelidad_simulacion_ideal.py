"""
calcular_fidelidad.py

Módulo de cálculo de fidelidad entre distribuciones de probabilidad teóricas
y experimentales del algoritmo de Shor. Implementa la fidelidad de Hellinger
y la divergencia KL como métricas de distancia estadística.

Referencia: Nielsen & Chuang §9.2.1 — Medidas de distancia entre distribuciones.

═══════════════════════════════════════════════════════════════════════════════
FIDELIDAD DE HELLINGER
═══════════════════════════════════════════════════════════════════════════════

Para dos distribuciones de probabilidad discretas P = {p_x} y Q = {q_x}:

    F_H(P, Q) = (Σ_x √(p_x · q_x))²

Propiedades:
    - 0 ≤ F_H ≤ 1
    - F_H = 1 si y solo si P = Q
    - F_H = 0 si P y Q tienen soportes disjuntos

Para la simulación ideal del algoritmo de Shor, la distribución teórica
concentra toda la probabilidad en r picos equiespaciados, por lo que
esperamos F_H ≈ 1.

═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import numpy as np
import matplotlib.pyplot as plt
from math import ceil, log2, gcd
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from algoritmo.circuit import RegisterQC
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
N = 15
BASES = [4, 7, 11, 14]
SHOTS = 4096
SEED = 457
CONTROL_QUBITS = 9
DIM = 2 ** CONTROL_QUBITS  # 512

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
IMG_DIR = os.path.join(BASE_DIR, "imagenes")
REP_DIR = os.path.join(BASE_DIR, "reportes")

for d in [DATOS_DIR, IMG_DIR, REP_DIR]:
    os.makedirs(d, exist_ok=True)

# ─── FUNCIONES DE FIDELIDAD ─────────────────────────────────────────────────

def find_order(a, N):
    """Orden multiplicativo de a módulo N."""
    val = 1
    for r in range(1, N):
        val = (val * a) % N
        if val == 1:
            return r
    return None

def distribucion_teorica(a, N, m):
    """
    Construye la distribución de probabilidad teórica del QPE para Shor.
    
    Para un operador U_a con orden r = ord_N(a), el QPE con m qubits de control
    produce picos en y = ⌊s·2^m/r⌉ para s = 0, 1, ..., r-1.
    En simulación ideal (sin ruido), cada pico tiene probabilidad 1/r.
    
    Args:
        a: base coprime con N
        N: número a factorizar
        m: número de qubits de control
    
    Returns:
        dict: {bitstring: probabilidad} solo para picos no nulos
        np.array: vector de probabilidades completo de dimensión 2^m
    """
    r = find_order(a, N)
    dim = 2 ** m
    
    # Posiciones teóricas de los picos
    picos = []
    for s in range(r):
        y = round(s * dim / r)
        if y >= dim:
            y = y % dim
        picos.append(y)
    
    # Distribución uniforme sobre los picos
    prob_vector = np.zeros(dim)
    for y in picos:
        prob_vector[y] = 1.0 / r
    
    # Distribución como dict de bitstrings
    prob_dict = {}
    for y in picos:
        bs = format(y, f'0{m}b')
        prob_dict[bs] = 1.0 / r
    
    return prob_dict, prob_vector, r, picos

def counts_a_distribucion(counts, m):
    """Convierte counts (dict de bitstrings) a vector de probabilidades normalizado."""
    total = sum(counts.values())
    dim = 2 ** m
    prob_vector = np.zeros(dim)
    prob_dict = {}
    for bs, count in counts.items():
        idx = int(bs, 2)
        prob = count / total
        prob_vector[idx] = prob
        prob_dict[bs] = prob
    return prob_dict, prob_vector

def fidelidad_hellinger(P, Q):
    """
    Calcula la fidelidad de Hellinger entre dos distribuciones de probabilidad.
    
    F_H(P, Q) = (Σ_x √(P(x) · Q(x)))²
    
    Args:
        P, Q: arrays numpy de probabilidades (deben sumar 1)
    
    Returns:
        float: fidelidad de Hellinger ∈ [0, 1]
    """
    return float(np.sum(np.sqrt(P * Q)) ** 2)

def distancia_hellinger(P, Q):
    """
    Distancia de Hellinger: D_H(P,Q) = √(1 - √F_H(P,Q))
    
    Nota: No confundir con la fidelidad. La distancia es 0 cuando F_H = 1.
    """
    bc = np.sum(np.sqrt(P * Q))  # Bhattacharyya coefficient
    return float(np.sqrt(1 - bc))

def divergencia_kl(P, Q, epsilon=1e-15):
    """
    Divergencia Kullback-Leibler: D_KL(P||Q) = Σ_x P(x) log(P(x)/Q(x))
    
    Se añade epsilon para evitar log(0). Solo se calcula sobre el soporte de P.
    """
    Q_safe = np.clip(Q, epsilon, None)
    P_safe = np.clip(P, epsilon, None)
    mask = P > epsilon
    return float(np.sum(P[mask] * np.log(P_safe[mask] / Q_safe[mask])))

# ─── EJECUCIÓN PRINCIPAL ────────────────────────────────────────────────────

def run_fidelity_analysis():
    print(f"[{time.strftime('%H:%M:%S')}] Iniciando análisis de fidelidad para Shor N={N}...")
    
    ideal_simulator = AerSimulator()
    sampler = SamplerV2(mode=ideal_simulator)
    
    resultados = {}
    
    for a in BASES:
        print(f"\n{'='*50}")
        print(f"  Base a={a}")
        
        # Distribución teórica
        P_dict, P_vec, r, picos = distribucion_teorica(a, N, CONTROL_QUBITS)
        picos_fases = [p / DIM for p in picos]
        
        print(f"  Orden r={r}, picos teóricos: {picos}")
        print(f"  Fases teóricas: {picos_fases}")
        
        # Simulación ideal
        circuito = RegisterQC()
        qc = circuito.create_circuit(N, a)
        isa = transpile(qc, backend=ideal_simulator, optimization_level=3, seed_transpiler=SEED)
        
        job = sampler.run([(isa,)], shots=SHOTS)
        counts = job.result()[0].data.output.get_counts()
        
        Q_dict, Q_vec = counts_a_distribucion(counts, CONTROL_QUBITS)
        
        # Métricas de fidelidad
        F_H = fidelidad_hellinger(P_vec, Q_vec)
        D_H = distancia_hellinger(P_vec, Q_vec)
        D_KL = divergencia_kl(P_vec, Q_vec)
        
        # Concentración de probabilidad en picos teóricos
        prob_en_picos = sum(Q_vec[p] for p in picos)
        
        resultados[f"a={a}"] = {
            "orden_r": r,
            "picos_teoricos": picos,
            "fases_teoricas": picos_fases,
            "fidelidad_hellinger": round(F_H, 6),
            "distancia_hellinger": round(D_H, 6),
            "divergencia_kl": round(D_KL, 6),
            "prob_en_picos_teoricos": round(prob_en_picos, 6),
            "prob_fuera_picos": round(1 - prob_en_picos, 6),
            "shots": SHOTS
        }
        
        print(f"  Fidelidad de Hellinger:  F_H = {F_H:.6f}")
        print(f"  Distancia de Hellinger:  D_H = {D_H:.6f}")
        print(f"  Divergencia KL:          D_KL = {D_KL:.6f}")
        print(f"  Prob. en picos teóricos: {prob_en_picos:.4f} ({prob_en_picos*100:.2f}%)")
    
    # ─── GUARDAR DATOS ───
    json_path = os.path.join(DATOS_DIR, "fidelidad_ideal_N15.json")
    with open(json_path, 'w') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nDatos guardados en -> {json_path}")
    
    # ─── GRÁFICAS ───
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    colores = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
    
    # Panel 1: Fidelidad de Hellinger por base
    ax = axes[0]
    bases_labels = [f"a={a}" for a in BASES]
    fidelidades = [resultados[f"a={a}"]["fidelidad_hellinger"] for a in BASES]
    bars = ax.bar(bases_labels, fidelidades, color=colores, alpha=0.85, edgecolor='black', linewidth=0.5)
    for bar, f_val in zip(bars, fidelidades):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005, 
                f"{f_val:.4f}", ha='center', fontsize=10, fontweight='bold')
    ax.set_title("Fidelidad de Hellinger $\\mathcal{F}_H(P_{teórica}, Q_{exp})$", fontsize=12, fontweight='bold')
    ax.set_ylabel("$\\mathcal{F}_H$")
    ax.set_ylim(0, 1.15)
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Ideal = 1.0')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')
    
    # Panel 2: Distribución teórica vs experimental (para a=7 como ejemplo con r=4)
    ax = axes[1]
    a_ejemplo = 7
    P_dict_ej, P_vec_ej, r_ej, picos_ej = distribucion_teorica(a_ejemplo, N, CONTROL_QUBITS)
    
    circuito_ej = RegisterQC()
    qc_ej = circuito_ej.create_circuit(N, a_ejemplo)
    isa_ej = transpile(qc_ej, backend=ideal_simulator, optimization_level=3, seed_transpiler=SEED)
    job_ej = sampler.run([(isa_ej,)], shots=SHOTS)
    counts_ej = job_ej.result()[0].data.output.get_counts()
    _, Q_vec_ej = counts_a_distribucion(counts_ej, CONTROL_QUBITS)
    
    x_vals = np.arange(DIM) / DIM
    ax.plot(x_vals, P_vec_ej, 'r-', linewidth=2, label='Teórica $P(y)$', alpha=0.8)
    ax.plot(x_vals, Q_vec_ej, 'b-', linewidth=1, label='Experimental $Q(y)$', alpha=0.6)
    for p in picos_ej:
        ax.axvline(x=p/DIM, color='gray', linestyle=':', alpha=0.3)
    ax.set_title(f"Distribución: Teórica vs Experimental (a={a_ejemplo}, r={r_ej})", fontsize=11, fontweight='bold')
    ax.set_xlabel("Fase $y/2^m$")
    ax.set_ylabel("Probabilidad")
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Panel 3: Probabilidad concentrada en picos
    ax = axes[2]
    probs_picos = [resultados[f"a={a}"]["prob_en_picos_teoricos"] * 100 for a in BASES]
    probs_fuera = [resultados[f"a={a}"]["prob_fuera_picos"] * 100 for a in BASES]
    x = np.arange(len(BASES))
    ax.bar(x, probs_picos, 0.5, label='En picos teóricos', color='#27ae60', alpha=0.85)
    ax.bar(x, probs_fuera, 0.5, bottom=probs_picos, label='Fuera de picos (ruido)', color='#e74c3c', alpha=0.85)
    for i, (pp, pf) in enumerate(zip(probs_picos, probs_fuera)):
        ax.text(i, pp/2, f"{pp:.1f}%", ha='center', fontsize=10, fontweight='bold', color='white')
    ax.set_xticks(x)
    ax.set_xticklabels(bases_labels)
    ax.set_title("Concentración de Probabilidad en Picos Teóricos", fontsize=11, fontweight='bold')
    ax.set_ylabel("Probabilidad (%)")
    ax.set_ylim(0, 115)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')
    
    plt.suptitle("Análisis de Fidelidad: Simulación Ideal de Shor (N=15)", fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    img_path = os.path.join(IMG_DIR, "fidelidad_ideal_N15.png")
    plt.savefig(img_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Gráfica guardada en -> {img_path}")
    
    # ─── REPORTE ───
    md_path = os.path.join(REP_DIR, "fidelidad_ideal.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Análisis de Fidelidad: Simulación Ideal del Algoritmo de Shor (N=15)\n\n")
        f.write("> **Objetivo:** Cuantificar la similitud entre la distribución de probabilidad teórica "
                "del QPE y la distribución experimental obtenida mediante simulación ideal.\n\n")
        
        f.write("## 1. Métricas Utilizadas\n\n")
        f.write("### Fidelidad de Hellinger\n")
        f.write("$$\\mathcal{F}_H(P, Q) = \\left( \\sum_{x} \\sqrt{P(x) \\cdot Q(x)} \\right)^2$$\n\n")
        f.write("### Distancia de Hellinger\n")
        f.write("$$D_H(P, Q) = \\sqrt{1 - \\sqrt{\\mathcal{F}_H(P, Q)}}$$\n\n")
        f.write("### Divergencia de Kullback-Leibler\n")
        f.write("$$D_{KL}(P \\| Q) = \\sum_{x} P(x) \\log \\frac{P(x)}{Q(x)}$$\n\n")
        
        f.write("## 2. Distribución Teórica\n\n")
        f.write("Para el QPE con $m$ qubits de control y operador $U_a$ con orden $r$, "
                "los picos teóricos están en:\n")
        f.write("$$y_s = \\left\\lfloor \\frac{s \\cdot 2^m}{r} \\right\\rceil, \\quad s = 0, 1, \\ldots, r-1$$\n\n")
        f.write("con probabilidad $P(y_s) = 1/r$ cada uno.\n\n")
        
        f.write("## 3. Resultados\n\n")
        f.write("| Base | Orden $r$ | Picos | $\\mathcal{F}_H$ | $D_H$ | $D_{KL}$ | Prob. en picos |\n")
        f.write("|:---:|:---:|:---|:---:|:---:|:---:|:---:|\n")
        for a in BASES:
            d = resultados[f"a={a}"]
            picos_str = ", ".join(map(str, d["picos_teoricos"]))
            f.write(f"| {a} | {d['orden_r']} | {{{picos_str}}} | {d['fidelidad_hellinger']:.4f} "
                    f"| {d['distancia_hellinger']:.4f} | {d['divergencia_kl']:.4f} | {d['prob_en_picos_teoricos']*100:.2f}% |\n")
        
        f.write("\n## 4. Gráficas\n\n")
        f.write("![Fidelidad ideal](../imagenes/fidelidad_ideal_N15.png)\n\n")
        
        f.write("## 5. Interpretación\n\n")
        f.write("- Una **fidelidad de Hellinger ≈ 1** confirma que la simulación ideal reproduce "
                "fielmente la distribución teórica del QPE.\n")
        f.write("- La **concentración de probabilidad ≈ 100%** en los picos teóricos valida que "
                "el circuito RegisterQC implementa correctamente la estimación de fase.\n")
        f.write("- Estas métricas servirán como línea base para cuantificar la degradación "
                "introducida por el ruido en las Fases III y IV del anteproyecto.\n")
    
    print(f"Reporte guardado en -> {md_path}")
    print(f"\n[✔] Análisis de fidelidad completado exitosamente.")

if __name__ == "__main__":
    run_fidelity_analysis()
