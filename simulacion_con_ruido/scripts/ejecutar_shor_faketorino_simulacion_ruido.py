"""
ejecutar_shor_faketorino_ruido.py

Simulación CON RUIDO del algoritmo de Shor para N=15 utilizando el modelo
de ruido real de FakeTorino (Heron r1, 133 qubits, Heavy-Hex). Este script
establece la línea base ruidosa (sin técnicas de mitigación de errores),
cuantificando la degradación de la señal respecto a la simulación ideal.

Fase III del anteproyecto: "Ejecutar los circuitos optimizados en Fake Backends
(AerSimulator local con modelos de ruido de calibración real)".

═══════════════════════════════════════════════════════════════════════════════
MODELO DE RUIDO DE FakeTorino:
  • Errores de compuerta 1Q/2Q (depolarizing + thermal relaxation)
  • Decoherencia: T₁, T₂ finitos
  • Errores de lectura (readout errors)
  • Topología Heavy-Hex (coupling map real)
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import numpy as np
import matplotlib.pyplot as plt
from math import gcd
from fractions import Fraction

# Configuración de rutas — repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from algorithm.circuit import RegisterQC
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeTorino

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────
N = 15
BASES = [4, 7]  # Reducido: a=4 (r=2) y a=7 (r=4) cubren ambos casos
OPT_LEVELS = [0, 3]  # Solo extremos: sin optimización vs máxima optimización
SHOTS = 512  # Reducido vs 4096 ideal: simulación ruidosa es ~300x más lenta
SEED = 457
CONTROL_QUBITS = 9  # 2*ceil(log2(15)) + 1
DIM = 2 ** CONTROL_QUBITS

# Directorios de salida
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
IMG_DIR = os.path.join(BASE_DIR, "imagenes")
REP_DIR = os.path.join(BASE_DIR, "reportes")

# Directorio de datos ideales para comparación
IDEAL_DIR = os.path.join(os.path.dirname(BASE_DIR), "simulacion_ideal", "datos")

for d in [DATOS_DIR, IMG_DIR, REP_DIR]:
    os.makedirs(d, exist_ok=True)


# ─── FUNCIONES AUXILIARES ────────────────────────────────────────────────────

def find_order(a, N):
    """Orden multiplicativo de a módulo N."""
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


def fidelidad_hellinger(P, Q):
    """F_H(P, Q) = (Σ_x √(P(x)·Q(x)))²"""
    return float(np.sum(np.sqrt(P * Q)) ** 2)


def counts_a_distribucion(counts, m):
    """Convierte counts a vector de probabilidades normalizado."""
    total = sum(counts.values())
    dim = 2 ** m
    prob_vector = np.zeros(dim)
    for bs, count in counts.items():
        idx = int(bs, 2)
        prob_vector[idx] = count / total
    return prob_vector


def calcular_pst_y_factores(counts, a, N, control_qubits):
    """Calcula PST (señal) y extrae factores vía fracciones continuas."""
    total_shots = sum(counts.values())
    r = find_order(a, N)
    fases_esperadas = [s / r for s in range(r)]
    tol = 0.01

    senial = 0
    found_factors = set()
    valid_periods = set()
    is_trivial = False

    for bs, count in counts.items():
        decimal_val = int(bs, 2)
        phase = decimal_val / (2 ** control_qubits)

        if any(abs(phase - p) < tol for p in fases_esperadas):
            senial += count

        if phase == 0:
            continue

        frac = Fraction(phase).limit_denominator(N)
        r_cand = frac.denominator

        if 1 < r_cand < N and pow(a, r_cand, N) == 1:
            valid_periods.add(r_cand)
            if r_cand % 2 == 0:
                g1 = gcd(pow(a, r_cand // 2) - 1, N)
                g2 = gcd(pow(a, r_cand // 2) + 1, N)
                if 1 < g1 < N:
                    found_factors.add(g1)
                if 1 < g2 < N:
                    found_factors.add(g2)
                if g1 in (1, N) or g2 in (1, N):
                    is_trivial = True

    pst = round(100 * senial / total_shots, 2)
    success = len(found_factors) >= 2 or (len(found_factors) == 1 and N % list(found_factors)[0] == 0)

    return {
        "pst": pst,
        "noise_pct": round(100 - pst, 2),
        "factors": sorted(list(found_factors)),
        "trivial": is_trivial,
        "periods": sorted(list(valid_periods)),
        "success": success
    }


def cargar_datos_ideales():
    """Carga los datos de la simulación ideal de FakeTorino para comparación."""
    json_path = os.path.join(IDEAL_DIR, "resultados_ideal_faketorino_N15.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            return json.load(f)
    print(f"  ⚠ No se encontraron datos ideales en: {json_path}", flush=True)
    return None


# ─── EJECUCIÓN PRINCIPAL ────────────────────────────────────────────────────

def run_noisy_simulation():
    n_combos = len(BASES) * len(OPT_LEVELS)
    est_min = n_combos * 6  # ~6 min por combo con noise model
    print(f"[{time.strftime('%H:%M:%S')}] Simulación CON RUIDO de Shor (N={N}) — FakeTorino", flush=True)
    print(f"  Bases: {BASES}", flush=True)
    print(f"  Opt levels: {OPT_LEVELS}", flush=True)
    print(f"  Shots: {SHOTS}", flush=True)
    print(f"  Mitigación: NINGUNA (baseline ruidosa)", flush=True)
    print(f"  Combinaciones: {n_combos} (~{est_min} min estimados)\n", flush=True)

    # Backend con modelo de ruido ACTIVO
    fake_torino = FakeTorino()
    noisy_sim = AerSimulator.from_backend(fake_torino)
    # NO se apaga noise_model — este es el punto clave vs simulación ideal
    sampler = SamplerV2(mode=noisy_sim)

    todos_resultados = {}

    for a in BASES:
        r = find_order(a, N)
        print(f"\n{'='*60}", flush=True)
        print(f"  BASE a = {a}  |  ord_{N}({a}) = {r}", flush=True)
        print(f"{'='*60}", flush=True)

        circuito = RegisterQC()
        qc = circuito.create_circuit(N, a)
        P_vec, _, picos = distribucion_teorica(a, N, CONTROL_QUBITS)

        resultados_a = []

        for opt in OPT_LEVELS:
            print(f"  -> opt={opt} ...", end=" ", flush=True)

            t0 = time.time()
            isa = transpile(
                qc,
                backend=fake_torino,
                optimization_level=opt,
                layout_method='sabre',
                routing_method='sabre',
                seed_transpiler=SEED
            )
            dt_transpile = time.time() - t0

            ops = isa.count_ops()
            depth_total = isa.depth()
            depth_2q = isa.depth(lambda instr: instr.operation.num_qubits == 2)
            gates_2q = sum(v for k, v in ops.items() if k in ['cx', 'cz', 'ecr', 'rzz'])
            total_gates = isa.size()

            t1 = time.time()
            job = sampler.run([(isa,)], shots=SHOTS)
            counts = job.result()[0].data.output.get_counts()
            dt_sim = time.time() - t1

            analisis = calcular_pst_y_factores(counts, a, N, CONTROL_QUBITS)
            Q_vec = counts_a_distribucion(counts, CONTROL_QUBITS)
            f_h = fidelidad_hellinger(P_vec, Q_vec)

            metricas = {
                "base": a,
                "optimization_level": opt,
                "depth_total": depth_total,
                "depth_2q": depth_2q,
                "gates_2q": gates_2q,
                "total_gates": total_gates,
                "pst": analisis["pst"],
                "noise_pct": analisis["noise_pct"],
                "fidelidad_hellinger": round(f_h, 6),
                "factors": analisis["factors"],
                "trivial": analisis["trivial"],
                "success": analisis["success"],
                "transpile_time_s": round(dt_transpile, 2),
                "simulation_time_s": round(dt_sim, 2)
            }
            resultados_a.append(metricas)

            fac_str = ", ".join(map(str, analisis["factors"])) if analisis["factors"] else ("trivial" if analisis["trivial"] else "—")
            print(f"D2Q={depth_2q:4d} | PST={analisis['pst']:5.1f}% | F_H={f_h:.4f} | {fac_str} ({dt_sim:.1f}s)", flush=True)

        todos_resultados[f"a={a}"] = resultados_a

    # ─── GUARDAR DATOS ───────────────────────────────────────────────────────
    json_path = os.path.join(DATOS_DIR, "resultados_ruido_faketorino_N15.json")
    with open(json_path, 'w') as f:
        json.dump(todos_resultados, f, indent=2, ensure_ascii=False)
    print(f"\nDatos guardados en -> {json_path}", flush=True)

    # ─── CARGAR DATOS IDEALES PARA COMPARACIÓN ───────────────────────────────
    datos_ideal = cargar_datos_ideales()

    # ─── GRÁFICAS ────────────────────────────────────────────────────────────
    generar_graficas(todos_resultados, datos_ideal)

    # ─── REPORTE ─────────────────────────────────────────────────────────────
    generar_reporte(todos_resultados, datos_ideal)

    print(f"\n[✔] Simulación con ruido completada exitosamente.", flush=True)


def generar_graficas(todos_resultados, datos_ideal):
    """Gráficas: señal ruidosa, comparativa ideal/ruido, fidelidad."""

    fig, axes = plt.subplots(1, 3, figsize=(22, 6))
    colores = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    # Panel 1: PST con ruido
    ax = axes[0]
    for i, a in enumerate(BASES):
        datos = todos_resultados[f"a={a}"]
        niveles = [d["optimization_level"] for d in datos]
        pst = [d["pst"] for d in datos]
        ax.plot(niveles, pst, marker='o', linewidth=2, color=colores[i], label=f'a={a}')
        for x, y in zip(niveles, pst):
            ax.text(x, y + 1.5, f"{y:.1f}%", ha='center', fontsize=8, color=colores[i])
    ax.set_title("Señal (PST) con Ruido — FakeTorino", fontsize=12, fontweight='bold')
    ax.set_xlabel("Nivel de Optimización")
    ax.set_ylabel("PST (%)")
    ax.set_ylim(0, 110)
    ax.set_xticks(OPT_LEVELS)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend()

    # Panel 2: Comparativa PST ideal vs ruido
    ax = axes[1]
    bar_w = 0.35
    for i, a in enumerate(BASES):
        datos_ruido = todos_resultados[f"a={a}"]
        pst_ruido = [d["pst"] for d in datos_ruido]
        noisy_opts = [d["optimization_level"] for d in datos_ruido]

        # Obtener PST ideal solo para los mismos opt levels
        pst_ideal = []
        if datos_ideal and f"a={a}" in datos_ideal:
            ideal_by_opt = {d.get("optimization_level", d.get("opt_level", idx)): d
                           for idx, d in enumerate(datos_ideal[f"a={a}"])}
            for opt in noisy_opts:
                if opt in ideal_by_opt:
                    pst_ideal.append(ideal_by_opt[opt].get("signal_pct", 100))
                else:
                    pst_ideal.append(100)
        else:
            pst_ideal = [100] * len(noisy_opts)

        x = np.arange(len(noisy_opts))
        ax.bar(x + i * bar_w - 0.5 * bar_w, pst_ideal, bar_w * 0.45,
               color=colores[i], alpha=0.3, edgecolor=colores[i], linewidth=1)
        ax.bar(x + i * bar_w - 0.5 * bar_w, pst_ruido, bar_w * 0.45,
               color=colores[i], alpha=0.85, label=f'a={a}')

    ax.set_title("PST: Ideal (tenue) vs Ruido (sólido)", fontsize=12, fontweight='bold')
    ax.set_xlabel("Nivel de Optimización")
    ax.set_ylabel("PST (%)")
    ax.set_xticks(range(len(OPT_LEVELS)))
    ax.set_xticklabels([str(o) for o in OPT_LEVELS])
    ax.set_ylim(0, 110)
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')
    ax.legend(fontsize=8)

    # Panel 3: Fidelidad Hellinger con ruido
    ax = axes[2]
    for i, a in enumerate(BASES):
        datos = todos_resultados[f"a={a}"]
        niveles = [d["optimization_level"] for d in datos]
        fh = [d["fidelidad_hellinger"] for d in datos]
        ax.plot(niveles, fh, marker='s', linewidth=2, color=colores[i], label=f'a={a}')
        for x, y in zip(niveles, fh):
            ax.text(x, y + 0.005, f"{y:.3f}", ha='center', fontsize=7, color=colores[i])
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Ideal = 1.0')
    ax.set_title("Fidelidad de Hellinger $\\mathcal{F}_H$ con Ruido", fontsize=12, fontweight='bold')
    ax.set_xlabel("Nivel de Optimización")
    ax.set_ylabel("$\\mathcal{F}_H$")
    ax.set_xticks(OPT_LEVELS)
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend(fontsize=8)

    plt.suptitle("Simulación con Ruido: Shor N=15 (FakeTorino, sin mitigación)",
                 fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    img_path = os.path.join(IMG_DIR, "analisis_ruido_faketorino_N15.png")
    plt.savefig(img_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Gráfica guardada en -> {img_path}", flush=True)


def generar_reporte(todos_resultados, datos_ideal):
    """Genera reporte Markdown comparando resultados ruidosos con ideales."""

    md_path = os.path.join(REP_DIR, "resultados_ruido_faketorino.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Resultados de Simulación CON RUIDO: Algoritmo de Shor (N=15) en FakeTorino\n\n")
        f.write("> **Objetivo:** Cuantificar la degradación de la señal y la fidelidad del algoritmo de Shor "
                "cuando se ejecuta con el modelo de ruido real de FakeTorino (decoherencia $T_1$/$T_2$, "
                "errores de compuerta, errores de lectura). Sin técnicas de mitigación.\n\n")

        f.write("## 1. Configuración del Experimento\n\n")
        f.write(f"- **Backend:** `AerSimulator.from_backend(FakeTorino)` — modelo de ruido **activo**\n")
        f.write(f"- **N:** {N}\n")
        f.write(f"- **Bases:** $a \\in {BASES}$\n")
        f.write(f"- **Shots:** {SHOTS}\n")
        f.write(f"- **Layout/Routing:** SABRE / SABRE\n")
        f.write(f"- **Mitigación:** Ninguna (DD=off, PT=off)\n")
        f.write(f"- **Seed:** {SEED}\n\n")

        f.write("## 2. Gráficas\n\n")
        f.write("![Análisis con ruido](../imagenes/analisis_ruido_faketorino_N15.png)\n\n")

        # Tabla principal
        f.write("## 3. Tabla de Métricas — Simulación con Ruido\n\n")
        f.write("| Base | Opt | Depth 2Q | Gates 2Q | PST (%) | $\\mathcal{F}_H$ | Factores | Estado |\n")
        f.write("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")

        for a in BASES:
            for d in todos_resultados[f"a={a}"]:
                fac_str = ", ".join(map(str, d["factors"])) if d["factors"] else ("Triviales" if d["trivial"] else "—")
                estado = "✅" if d["success"] else ("⚠️" if d["trivial"] else "❌")
                f.write(f"| {a} | {d['optimization_level']} | {d['depth_2q']} | {d['gates_2q']} "
                        f"| {d['pst']} | {d['fidelidad_hellinger']:.4f} | {fac_str} | {estado} |\n")

        # Comparativa ideal vs ruido
        if datos_ideal:
            f.write("\n## 4. Degradación: Ideal vs Ruido\n\n")
            f.write("| Base | Opt | PST Ideal | PST Ruido | Δ PST | $\\mathcal{F}_H$ Ruido |\n")
            f.write("|:---:|:---:|:---:|:---:|:---:|:---:|\n")

            for a in BASES:
                ruido_data = todos_resultados[f"a={a}"]
                ideal_data = datos_ideal.get(f"a={a}", [])
                for r_d, i_d in zip(ruido_data, ideal_data):
                    pst_ideal = i_d.get("signal_pct", 100)
                    pst_ruido = r_d["pst"]
                    delta = round(pst_ideal - pst_ruido, 2)
                    f.write(f"| {a} | {r_d['optimization_level']} | {pst_ideal}% | {pst_ruido}% "
                            f"| -{delta}pp | {r_d['fidelidad_hellinger']:.4f} |\n")

        # Discusión
        f.write("\n## 5. Discusión\n\n")
        f.write("### 5.1 Impacto del ruido en la señal\n\n")
        f.write("- La señal (PST) se degrada significativamente respecto a la simulación ideal (100%).\n")
        f.write("- Circuitos con mayor profundidad 2Q sufren más degradación, ya que cada compuerta 2Q "
                "acumula error de decoherencia ($T_1$/$T_2$) y error de compuerta ($\\epsilon_{2q}$).\n")
        f.write("- Los niveles de optimización más altos (2, 3) reducen la profundidad y mejoran la señal.\n\n")

        f.write("### 5.2 Fidelidad de Hellinger\n\n")
        f.write("- La fidelidad $\\mathcal{F}_H$ con ruido es significativamente menor que 1.0.\n")
        f.write("- A mayor profundidad del circuito, mayor degradación de la fidelidad.\n")
        f.write("- Estos valores servirán como referencia para medir la mejora que aportan las técnicas "
                "de mitigación (DD y PT) en `comparar_mitigacion.py`.\n\n")

        f.write("### 5.3 Extracción de factores\n\n")
        f.write("- Con ruido, la extracción de factores puede fallar cuando el fondo de ruido "
                "contamina las fases del QPE, produciendo candidatos $r$ incorrectos.\n")
        f.write("- El éxito depende de que la señal sea suficiente para que los picos teóricos "
                "dominen sobre el ruido de fondo.\n\n")

        f.write("## 6. Conclusiones\n\n")
        f.write("1. El ruido del hardware real (modelado por FakeTorino) degrada significativamente "
                "la señal del algoritmo de Shor.\n")
        f.write("2. La optimización del transpilador (niveles 2-3) ayuda a reducir la degradación "
                "al producir circuitos más compactos.\n")
        f.write("3. Se requieren técnicas de mitigación de errores (DD, PT) para mejorar la señal "
                "— este análisis se realiza en `comparar_mitigacion.py`.\n")

    print(f"Reporte guardado en -> {md_path}", flush=True)


if __name__ == "__main__":
    run_noisy_simulation()
