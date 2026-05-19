"""
calcular_fidelidad_ruido.py

Análisis de fidelidad entre distribuciones teóricas y distribuciones ruidosas
del algoritmo de Shor (N=15) en FakeTorino con modelo de ruido activo.
Cuantifica la degradación estadística usando Hellinger fidelity, distancia
de Hellinger y divergencia KL. Compara contra la fidelidad ideal.

Referencia: Nielsen & Chuang §9.2.1 — Medidas de distancia entre distribuciones.
OE4 del anteproyecto: "Cuantificar degradación comparando vs ideal con Fidelidad y PST".

═══════════════════════════════════════════════════════════════════════════════
FIDELIDAD DE HELLINGER:  F_H(P, Q) = (Σ_x √(p_x · q_x))²
DISTANCIA DE HELLINGER:  D_H(P, Q) = √(1 - √F_H)
DIVERGENCIA KL:          D_KL(P||Q) = Σ_x P(x) log(P(x)/Q(x))
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import numpy as np
import matplotlib.pyplot as plt
from math import ceil, log2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from algorithm.circuit import RegisterQC
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeTorino

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────
N = 15
BASES = [4, 7]  # Reducido: a=4 (r=2) y a=7 (r=4) cubren ambos casos
SHOTS = 512  # Reducido: simulación ruidosa ~300x más lenta que ideal
SEED = 457
CONTROL_QUBITS = 9
DIM = 2 ** CONTROL_QUBITS
OPT_LEVEL = 3  # Fijo: mejor optimización

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
IMG_DIR = os.path.join(BASE_DIR, "imagenes")
REP_DIR = os.path.join(BASE_DIR, "reportes")
IDEAL_DIR = os.path.join(os.path.dirname(BASE_DIR), "simulacion_ideal", "datos")

for d in [DATOS_DIR, IMG_DIR, REP_DIR]:
    os.makedirs(d, exist_ok=True)


# ─── FUNCIONES ───────────────────────────────────────────────────────────────

def find_order(a, N):
    val = 1
    for r in range(1, N):
        val = (val * a) % N
        if val == 1:
            return r
    return None


def distribucion_teorica(a, N, m):
    """Distribución teórica del QPE: picos en y = ⌊s·2^m/r⌉, prob = 1/r."""
    r = find_order(a, N)
    dim = 2 ** m
    picos = []
    for s in range(r):
        y = round(s * dim / r)
        if y >= dim:
            y = y % dim
        picos.append(y)
    prob_vector = np.zeros(dim)
    for y in picos:
        prob_vector[y] = 1.0 / r
    return prob_vector, r, picos


def counts_a_distribucion(counts, m):
    total = sum(counts.values())
    dim = 2 ** m
    prob_vector = np.zeros(dim)
    for bs, count in counts.items():
        idx = int(bs, 2)
        prob_vector[idx] = count / total
    return prob_vector


def fidelidad_hellinger(P, Q):
    return float(np.sum(np.sqrt(P * Q)) ** 2)


def distancia_hellinger(P, Q):
    bc = np.sum(np.sqrt(P * Q))
    return float(np.sqrt(1 - bc))


def divergencia_kl(P, Q, epsilon=1e-15):
    Q_safe = np.clip(Q, epsilon, None)
    P_safe = np.clip(P, epsilon, None)
    mask = P > epsilon
    return float(np.sum(P[mask] * np.log(P_safe[mask] / Q_safe[mask])))


def cargar_fidelidad_ideal():
    """Carga los datos de fidelidad ideal para comparar."""
    json_path = os.path.join(IDEAL_DIR, "fidelidad_ideal_N15.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            return json.load(f)
    return None


# ─── EJECUCIÓN PRINCIPAL ────────────────────────────────────────────────────

def run_fidelity_analysis():
    print(f"[{time.strftime('%H:%M:%S')}] Análisis de fidelidad CON RUIDO — Shor N={N}", flush=True)
    print(f"  Opt level: {OPT_LEVEL} (fijo)", flush=True)
    print(f"  Shots: {SHOTS}\n", flush=True)

    fake_torino = FakeTorino()
    noisy_sim = AerSimulator.from_backend(fake_torino)
    # noise_model ACTIVO
    sampler = SamplerV2(mode=noisy_sim)

    datos_ideal = cargar_fidelidad_ideal()
    resultados = {}

    for a in BASES:
        print(f"\n{'='*50}", flush=True)
        print(f"  Base a={a}", flush=True)

        # Distribución teórica
        P_vec, r, picos = distribucion_teorica(a, N, CONTROL_QUBITS)
        print(f"  Orden r={r}, picos teóricos: {picos}", flush=True)

        # Simulación ruidosa
        circuito = RegisterQC()
        qc = circuito.create_circuit(N, a)
        isa = transpile(qc, backend=fake_torino, optimization_level=OPT_LEVEL,
                        layout_method='sabre', routing_method='sabre', seed_transpiler=SEED)

        job = sampler.run([(isa,)], shots=SHOTS)
        counts = job.result()[0].data.output.get_counts()
        Q_vec = counts_a_distribucion(counts, CONTROL_QUBITS)

        # Métricas vs distribución teórica
        F_H = fidelidad_hellinger(P_vec, Q_vec)
        D_H = distancia_hellinger(P_vec, Q_vec)
        D_KL = divergencia_kl(P_vec, Q_vec)

        # Concentración en picos teóricos
        prob_en_picos = sum(Q_vec[p] for p in picos)

        # Datos ideales para comparar
        ideal_F_H = None
        if datos_ideal and f"a={a}" in datos_ideal:
            ideal_F_H = datos_ideal[f"a={a}"]["fidelidad_hellinger"]

        resultados[f"a={a}"] = {
            "orden_r": r,
            "picos_teoricos": picos,
            "fidelidad_hellinger_ruido": round(F_H, 6),
            "distancia_hellinger_ruido": round(D_H, 6),
            "divergencia_kl_ruido": round(D_KL, 6),
            "prob_en_picos_teoricos_ruido": round(prob_en_picos, 6),
            "prob_fuera_picos_ruido": round(1 - prob_en_picos, 6),
            "fidelidad_hellinger_ideal": ideal_F_H,
            "degradacion_F_H": round(ideal_F_H - F_H, 6) if ideal_F_H else None,
            "shots": SHOTS,
            "optimization_level": OPT_LEVEL,
            "distribucion_ruidosa_top10": dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }

        print(f"  F_H (ruido):  {F_H:.6f}" + (f"  (ideal: {ideal_F_H:.6f}, Δ={ideal_F_H - F_H:.6f})" if ideal_F_H else ""), flush=True)
        print(f"  D_H (ruido):  {D_H:.6f}", flush=True)
        print(f"  D_KL (ruido): {D_KL:.6f}", flush=True)
        print(f"  Prob en picos: {prob_en_picos:.4f} ({prob_en_picos*100:.2f}%)", flush=True)

    # ─── GUARDAR ─────────────────────────────────────────────────────────────
    json_path = os.path.join(DATOS_DIR, "fidelidad_ruido_N15.json")
    with open(json_path, 'w') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nDatos guardados en -> {json_path}", flush=True)

    # ─── GRÁFICAS ────────────────────────────────────────────────────────────
    generar_graficas(resultados, datos_ideal)

    # ─── REPORTE ─────────────────────────────────────────────────────────────
    generar_reporte(resultados, datos_ideal)

    print(f"\n[✔] Análisis de fidelidad con ruido completado.", flush=True)


def generar_graficas(resultados, datos_ideal):
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    colores = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    # Panel 1: F_H comparativo ideal vs ruido
    ax = axes[0]
    bases_labels = [f"a={a}" for a in BASES]
    fh_ruido = [resultados[f"a={a}"]["fidelidad_hellinger_ruido"] for a in BASES]
    fh_ideal = [resultados[f"a={a}"]["fidelidad_hellinger_ideal"] or 1.0 for a in BASES]

    x = np.arange(len(BASES))
    bars1 = ax.bar(x - 0.18, fh_ideal, 0.32, color='#27ae60', alpha=0.7, label='Ideal', edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x + 0.18, fh_ruido, 0.32, color='#e74c3c', alpha=0.85, label='Ruido', edgecolor='black', linewidth=0.5)

    for bar, val in zip(bars1, fh_ideal):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, f"{val:.4f}", ha='center', fontsize=8, fontweight='bold')
    for bar, val in zip(bars2, fh_ruido):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, f"{val:.4f}", ha='center', fontsize=8, fontweight='bold')

    ax.set_title("$\\mathcal{F}_H$: Ideal vs Ruido", fontsize=12, fontweight='bold')
    ax.set_ylabel("$\\mathcal{F}_H$")
    ax.set_xticks(x)
    ax.set_xticklabels(bases_labels)
    ax.set_ylim(0, 1.15)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')

    # Panel 2: Distribución teórica vs ruidosa (ejemplo a=7, r=4)
    ax = axes[1]
    a_ejemplo = 7
    P_vec_ej, r_ej, picos_ej = distribucion_teorica(a_ejemplo, N, CONTROL_QUBITS)

    # Re-simular para obtener distribución completa
    fake_torino = FakeTorino()
    noisy_sim = AerSimulator.from_backend(fake_torino)
    sampler = SamplerV2(mode=noisy_sim)
    circuito = RegisterQC()
    qc = circuito.create_circuit(N, a_ejemplo)
    isa = transpile(qc, backend=fake_torino, optimization_level=OPT_LEVEL,
                    layout_method='sabre', routing_method='sabre', seed_transpiler=SEED)
    job = sampler.run([(isa,)], shots=SHOTS)
    counts_ej = job.result()[0].data.output.get_counts()
    Q_vec_ej = counts_a_distribucion(counts_ej, CONTROL_QUBITS)

    x_vals = np.arange(DIM) / DIM
    ax.plot(x_vals, P_vec_ej, 'g-', linewidth=2, label='Teórica $P(y)$', alpha=0.8)
    ax.plot(x_vals, Q_vec_ej, 'r-', linewidth=1, label='Ruidosa $Q(y)$', alpha=0.6)
    for p in picos_ej:
        ax.axvline(x=p/DIM, color='gray', linestyle=':', alpha=0.3)
    ax.set_title(f"Distribución: Teórica vs Ruidosa (a={a_ejemplo}, r={r_ej})", fontsize=11, fontweight='bold')
    ax.set_xlabel("Fase $y/2^m$")
    ax.set_ylabel("Probabilidad")
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3)

    # Panel 3: Probabilidad en picos vs fuera
    ax = axes[2]
    probs_picos = [resultados[f"a={a}"]["prob_en_picos_teoricos_ruido"] * 100 for a in BASES]
    probs_fuera = [resultados[f"a={a}"]["prob_fuera_picos_ruido"] * 100 for a in BASES]
    x = np.arange(len(BASES))
    ax.bar(x, probs_picos, 0.5, label='En picos teóricos', color='#27ae60', alpha=0.85)
    ax.bar(x, probs_fuera, 0.5, bottom=probs_picos, label='Fuera de picos (ruido)', color='#e74c3c', alpha=0.85)
    for i, (pp, pf) in enumerate(zip(probs_picos, probs_fuera)):
        ax.text(i, pp/2, f"{pp:.1f}%", ha='center', fontsize=10, fontweight='bold', color='white')
        ax.text(i, pp + pf/2, f"{pf:.1f}%", ha='center', fontsize=8, color='white')
    ax.set_xticks(x)
    ax.set_xticklabels(bases_labels)
    ax.set_title("Concentración de Probabilidad (con Ruido)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Probabilidad (%)")
    ax.set_ylim(0, 115)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')

    plt.suptitle("Análisis de Fidelidad con Ruido: Shor N=15 (FakeTorino)", fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    img_path = os.path.join(IMG_DIR, "fidelidad_ruido_N15.png")
    plt.savefig(img_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Gráfica guardada en -> {img_path}", flush=True)


def generar_reporte(resultados, datos_ideal):
    md_path = os.path.join(REP_DIR, "fidelidad_ruido.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Análisis de Fidelidad con Ruido: Shor N=15 (FakeTorino)\n\n")
        f.write("> **Objetivo:** Cuantificar la degradación de la fidelidad entre la distribución teórica "
                "y la distribución experimental ruidosa, comparando contra la línea base ideal (OE4).\n\n")

        f.write("## 1. Métricas Utilizadas\n\n")
        f.write("| Métrica | Fórmula | Interpretación |\n")
        f.write("|:---|:---|:---|\n")
        f.write("| Fidelidad de Hellinger | $\\mathcal{F}_H = (\\sum_x \\sqrt{P(x)Q(x)})^2$ | 1 = idénticas, 0 = disjuntas |\n")
        f.write("| Distancia de Hellinger | $D_H = \\sqrt{1 - \\sqrt{\\mathcal{F}_H}}$ | 0 = idénticas |\n")
        f.write("| Divergencia KL | $D_{KL}(P\\|Q) = \\sum_x P(x)\\log\\frac{P(x)}{Q(x)}$ | 0 = idénticas |\n\n")

        f.write("## 2. Gráficas\n\n")
        f.write("![Fidelidad con ruido](../imagenes/fidelidad_ruido_N15.png)\n\n")

        f.write("## 3. Resultados\n\n")
        f.write("| Base | $r$ | $\\mathcal{F}_H$ Ruido | $\\mathcal{F}_H$ Ideal | $\\Delta\\mathcal{F}_H$ | $D_H$ | $D_{KL}$ | Prob. picos |\n")
        f.write("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")

        for a in BASES:
            d = resultados[f"a={a}"]
            fh_i = f"{d['fidelidad_hellinger_ideal']:.4f}" if d['fidelidad_hellinger_ideal'] else "—"
            delta = f"{d['degradacion_F_H']:.4f}" if d['degradacion_F_H'] is not None else "—"
            f.write(f"| {a} | {d['orden_r']} | {d['fidelidad_hellinger_ruido']:.4f} | {fh_i} "
                    f"| {delta} | {d['distancia_hellinger_ruido']:.4f} | {d['divergencia_kl_ruido']:.4f} "
                    f"| {d['prob_en_picos_teoricos_ruido']*100:.2f}% |\n")

        f.write("\n## 4. Interpretación\n\n")
        f.write("- La **fidelidad con ruido** es significativamente menor que la fidelidad ideal (~1.0), "
                "confirmando la degradación introducida por el modelo de ruido de FakeTorino.\n")
        f.write("- La **probabilidad concentrada en picos teóricos** es menor al 100%, indicando que "
                "el ruido redistribuye probabilidad desde los picos del QPE hacia el fondo.\n")
        f.write("- Mayor profundidad 2Q → mayor exposición a decoherencia → menor fidelidad.\n")
        f.write("- Bases con $r=4$ (a=7) tienen circuitos más profundos que $r=2$ (a=4,11,14), "
                "lo que puede reflejarse en mayor degradación.\n")
        f.write("- Estos resultados serán la **referencia** para evaluar la mejora de DD y PT.\n")

    print(f"Reporte guardado en -> {md_path}", flush=True)


if __name__ == "__main__":
    run_fidelity_analysis()
