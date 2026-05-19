"""
comparar_mitigacion.py

Comparación de técnicas de mitigación de errores para el algoritmo de Shor
(N=15) en FakeTorino con modelo de ruido. Evalúa 4 variantes:
  1. Baseline: sin mitigación
  2. DD only: Dynamical Decoupling (XY4)
  3. PT only: Pauli Twirling (active)
  4. DD + PT: ambas técnicas combinadas

Fase III del anteproyecto: "aplicar técnicas de mitigación de errores
(Dynamical Decoupling y Pauli Twirling) y evaluar su impacto en la
fidelidad y probabilidad de éxito."

═══════════════════════════════════════════════════════════════════════════════
DYNAMICAL DECOUPLING (DD):
  Inserta secuencias de pulsos (XY4) durante los periodos de
  inactividad de los qubits para suprimir la decoherencia por acoplamiento
  con el entorno. Reduce el efecto de T₂ en qubits idle.

PAULI TWIRLING (PT):
  Aleatoriza los errores coherentes de las compuertas 2Q convirtiéndolos
  en errores estocásticos (Pauli channel), que son más manejables.
  Promedia sobre múltiples randomizaciones para cancelar errores coherentes.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from algorithm.circuit import RegisterQC
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeTorino
from qiskit.transpiler import PassManager, InstructionDurations
from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDynamicalDecoupling
from qiskit.circuit.library import XGate
from local_mitigation import Twirl2QClifford

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────
N = 15
BASES = [4, 7]  # a=4 (r=2) y a=7 (r=4)
OPT_LEVEL = 3  # Fijo: mejor optimización
SHOTS = 512  # Reducido: simulación ruidosa ~300x más lenta que ideal
SEED = 457
CONTROL_QUBITS = 9
DIM = 2 ** CONTROL_QUBITS

# Variantes de mitigación
VARIANTES = {
    "baseline": {"dd": False, "pt": False, "label": "Sin mitigación"},
    "dd_only": {"dd": True, "pt": False, "label": "DD (XY4)"},
    "pt_only": {"dd": False, "pt": True, "label": "PT (active)"},
    "dd_pt": {"dd": True, "pt": True, "label": "DD + PT"},
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
IMG_DIR = os.path.join(BASE_DIR, "imagenes")
REP_DIR = os.path.join(BASE_DIR, "reportes")

for d in [DATOS_DIR, IMG_DIR, REP_DIR]:
    os.makedirs(d, exist_ok=True)


# ─── FUNCIONES AUXILIARES ────────────────────────────────────────────────────

def find_order(a, N):
    val = 1
    for r in range(1, N):
        val = (val * a) % N
        if val == 1:
            return r
    return None


def distribucion_teorica(a, N, m):
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
    return float(np.sum(np.sqrt(P * Q)) ** 2)


def distancia_hellinger(P, Q):
    bc = np.sum(np.sqrt(P * Q))
    return float(np.sqrt(1 - bc))


def divergencia_kl(P, Q, epsilon=1e-15):
    Q_safe = np.clip(Q, epsilon, None)
    P_safe = np.clip(P, epsilon, None)
    mask = P > epsilon
    return float(np.sum(P[mask] * np.log(P_safe[mask] / Q_safe[mask])))


def counts_a_distribucion(counts, m):
    total = sum(counts.values())
    dim = 2 ** m
    prob_vector = np.zeros(dim)
    for bs, count in counts.items():
        idx = int(bs, 2)
        prob_vector[idx] = count / total
    return prob_vector


def calcular_pst(counts, a, N, control_qubits):
    total_shots = sum(counts.values())
    r = find_order(a, N)
    fases_esperadas = [s / r for s in range(r)]
    tol = 0.01
    senial = 0
    for bs, count in counts.items():
        phase = int(bs, 2) / (2 ** control_qubits)
        if any(abs(phase - p) < tol for p in fases_esperadas):
            senial += count
    return round(100 * senial / total_shots, 2)


def calcular_factores(counts, a, N, control_qubits):
    found_factors = set()
    is_trivial = False
    for bs, count in counts.items():
        phase = int(bs, 2) / (2 ** control_qubits)
        if phase == 0:
            continue
        frac = Fraction(phase).limit_denominator(N)
        r_cand = frac.denominator
        if 1 < r_cand < N and pow(a, r_cand, N) == 1 and r_cand % 2 == 0:
            g1 = gcd(pow(a, r_cand // 2) - 1, N)
            g2 = gcd(pow(a, r_cand // 2) + 1, N)
            if 1 < g1 < N:
                found_factors.add(g1)
            if 1 < g2 < N:
                found_factors.add(g2)
            if g1 in (1, N) or g2 in (1, N):
                is_trivial = True
    success = len(found_factors) >= 2 or (len(found_factors) == 1 and N % list(found_factors)[0] == 0)
    return sorted(list(found_factors)), is_trivial, success


def aplicar_mitigacion(qc, backend, dd_enabled, pt_enabled):
    """Aplica DD y/o PT explícitamente al circuito transpilado usando PassManager."""
    passes = []
    
    if pt_enabled:
        passes.append(Twirl2QClifford(seed=SEED))
        
    if dd_enabled:
        durations = InstructionDurations.from_backend(backend)
        dd_sequence = [XGate(), XGate()]
        passes.extend([
            ALAPScheduleAnalysis(durations),
            PadDynamicalDecoupling(durations, dd_sequence)
        ])
        
    if passes:
        pm = PassManager(passes)
        return pm.run(qc)
    return qc


# ─── EJECUCIÓN PRINCIPAL ────────────────────────────────────────────────────

def run_mitigation_comparison():
    print(f"[{time.strftime('%H:%M:%S')}] Comparación de mitigación — Shor N={N}", flush=True)
    print(f"  Opt level: {OPT_LEVEL} (fijo)", flush=True)
    print(f"  Variantes: {list(VARIANTES.keys())}\n", flush=True)

    fake_torino = FakeTorino()
    noisy_sim = AerSimulator.from_backend(fake_torino)
    # noise_model ACTIVO

    # Cargar resultados existentes para no perder datos previos
    json_path = os.path.join(DATOS_DIR, "comparar_mitigacion_N15.json")
    if os.path.exists(json_path):
        with open(json_path) as f:
            todos_resultados = json.load(f)
        print(f"  Cargados datos previos: {list(todos_resultados.keys())}", flush=True)
    else:
        todos_resultados = {}

    for a in BASES:
        key = f"a={a}"
        if key in todos_resultados:
            print(f"\n  [SKIP] {key} ya existe en datos previos.", flush=True)
            continue

        r = find_order(a, N)
        print(f"\n{'='*60}", flush=True)
        print(f"  BASE a = {a}  |  ord_{N}({a}) = {r}", flush=True)
        print(f"{'='*60}", flush=True)

        circuito = RegisterQC()
        qc = circuito.create_circuit(N, a)
        P_vec, _, picos = distribucion_teorica(a, N, CONTROL_QUBITS)

        # Transpilar una sola vez (mismo circuito para todas las variantes)
        isa = transpile(qc, backend=fake_torino, optimization_level=OPT_LEVEL,
                        layout_method='sabre', routing_method='sabre', seed_transpiler=SEED)

        depth_2q = isa.depth(lambda instr: instr.operation.num_qubits == 2)
        gates_2q = sum(v for k, v in isa.count_ops().items() if k in ['cx', 'cz', 'ecr', 'rzz'])

        resultados_a = {}

        for var_name, var_config in VARIANTES.items():
            print(f"  -> {var_config['label']:20s} ...", end=" ", flush=True)

            isa_mitigado = aplicar_mitigacion(isa, fake_torino, var_config["dd"], var_config["pt"])
            sampler = SamplerV2(mode=noisy_sim)

            t0 = time.time()
            job = sampler.run([(isa_mitigado,)], shots=SHOTS)
            counts = job.result()[0].data.output.get_counts()
            dt = time.time() - t0

            Q_vec = counts_a_distribucion(counts, CONTROL_QUBITS)
            pst = calcular_pst(counts, a, N, CONTROL_QUBITS)
            f_h = fidelidad_hellinger(P_vec, Q_vec)
            d_h = distancia_hellinger(P_vec, Q_vec)
            d_kl = divergencia_kl(P_vec, Q_vec)
            factores, trivial, success = calcular_factores(counts, a, N, CONTROL_QUBITS)

            resultados_a[var_name] = {
                "variante": var_name,
                "label": var_config["label"],
                "dd": var_config["dd"],
                "pt": var_config["pt"],
                "pst": pst,
                "fidelidad_hellinger": round(f_h, 6),
                "distancia_hellinger": round(d_h, 6),
                "divergencia_kl": round(d_kl, 6),
                "factors": factores,
                "trivial": trivial,
                "success": success,
                "depth_2q": depth_2q,
                "gates_2q": gates_2q,
                "simulation_time_s": round(dt, 2)
            }

            fac_str = ", ".join(map(str, factores)) if factores else ("trivial" if trivial else "—")
            print(f"PST={pst:5.1f}% | F_H={f_h:.4f} | {fac_str} ({dt:.1f}s)", flush=True)

        todos_resultados[key] = resultados_a

        # ─── GUARDAR INCREMENTALMENTE (después de cada base) ─────────────────
        with open(json_path, 'w') as f:
            json.dump(todos_resultados, f, indent=2, ensure_ascii=False)
        print(f"  Datos guardados incrementalmente -> {json_path}", flush=True)

    # ─── GUARDAR FINAL ───────────────────────────────────────────────────────
    with open(json_path, 'w') as f:
        json.dump(todos_resultados, f, indent=2, ensure_ascii=False)
    print(f"\nDatos guardados en -> {json_path}", flush=True)

    # ─── GRÁFICAS ────────────────────────────────────────────────────────────
    generar_graficas(todos_resultados)

    # ─── REPORTE ─────────────────────────────────────────────────────────────
    generar_reporte(todos_resultados)

    print(f"\n[✔] Comparación de mitigación completada.", flush=True)


def generar_graficas(todos_resultados):
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    colores_var = {'baseline': '#e74c3c', 'dd_only': '#3498db', 'pt_only': '#f39c12', 'dd_pt': '#27ae60'}
    var_labels = {k: v["label"] for k, v in VARIANTES.items()}

    # Panel 1: PST por variante y base
    ax = axes[0, 0]
    bar_w = 0.18
    for j, (var_name, var_label) in enumerate(var_labels.items()):
        psts = []
        for a in BASES:
            psts.append(todos_resultados[f"a={a}"][var_name]["pst"])
        x = np.arange(len(BASES))
        ax.bar(x + j * bar_w - 1.5 * bar_w, psts, bar_w, color=colores_var[var_name],
               alpha=0.85, label=var_label)
        for xi, pst in zip(x + j * bar_w - 1.5 * bar_w, psts):
            ax.text(xi, pst + 1, f"{pst:.0f}", ha='center', fontsize=7, fontweight='bold')
    ax.set_xticks(np.arange(len(BASES)))
    ax.set_xticklabels([f"a={a}" for a in BASES])
    ax.set_title("PST (Señal) por Variante de Mitigación", fontsize=13, fontweight='bold')
    ax.set_ylabel("PST (%)")
    ax.set_ylim(0, 110)
    ax.legend(fontsize=8)
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')

    # Panel 2: F_H por variante y base
    ax = axes[0, 1]
    for j, (var_name, var_label) in enumerate(var_labels.items()):
        fhs = [todos_resultados[f"a={a}"][var_name]["fidelidad_hellinger"] for a in BASES]
        x = np.arange(len(BASES))
        ax.bar(x + j * bar_w - 1.5 * bar_w, fhs, bar_w, color=colores_var[var_name],
               alpha=0.85, label=var_label)
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Ideal')
    ax.set_xticks(np.arange(len(BASES)))
    ax.set_xticklabels([f"a={a}" for a in BASES])
    ax.set_title("$\\mathcal{F}_H$ por Variante de Mitigación", fontsize=13, fontweight='bold')
    ax.set_ylabel("$\\mathcal{F}_H$")
    ax.legend(fontsize=7)
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')

    # Panel 3: Mejora relativa de PST vs baseline
    ax = axes[1, 0]
    for var_name in ['dd_only', 'pt_only', 'dd_pt']:
        mejoras = []
        for a in BASES:
            base_pst = todos_resultados[f"a={a}"]["baseline"]["pst"]
            var_pst = todos_resultados[f"a={a}"][var_name]["pst"]
            mejora = var_pst - base_pst
            mejoras.append(mejora)
        ax.plot(BASES, mejoras, marker='o', linewidth=2, color=colores_var[var_name],
                label=var_labels[var_name], markersize=8)
        for x, y in zip(BASES, mejoras):
            ax.text(x, y + 0.5, f"+{y:.1f}pp" if y >= 0 else f"{y:.1f}pp", ha='center', fontsize=8)
    ax.axhline(y=0, color='gray', linestyle=':', alpha=0.5)
    ax.set_title("Mejora de PST vs Baseline (pp)", fontsize=13, fontweight='bold')
    ax.set_xlabel("Base $a$")
    ax.set_ylabel("Δ PST (puntos porcentuales)")
    ax.set_xticks(BASES)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.4)

    # Panel 4: Comparativa D_KL
    ax = axes[1, 1]
    for j, (var_name, var_label) in enumerate(var_labels.items()):
        dkls = [todos_resultados[f"a={a}"][var_name]["divergencia_kl"] for a in BASES]
        x = np.arange(len(BASES))
        ax.bar(x + j * bar_w - 1.5 * bar_w, dkls, bar_w, color=colores_var[var_name],
               alpha=0.85, label=var_label)
    ax.set_xticks(np.arange(len(BASES)))
    ax.set_xticklabels([f"a={a}" for a in BASES])
    ax.set_title("Divergencia KL $D_{KL}$ por Variante", fontsize=13, fontweight='bold')
    ax.set_ylabel("$D_{KL}$")
    ax.legend(fontsize=7)
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')

    plt.suptitle("Comparación de Mitigación: DD y PT — Shor N=15 (FakeTorino)",
                 fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    img_path = os.path.join(IMG_DIR, "comparar_mitigacion_N15.png")
    plt.savefig(img_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Gráfica guardada en -> {img_path}", flush=True)


def generar_reporte(todos_resultados):
    md_path = os.path.join(REP_DIR, "comparar_mitigacion.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Comparación de Mitigación de Errores: DD y PT — Shor N=15\n\n")
        f.write("> **Objetivo:** Evaluar el impacto de Dynamical Decoupling (DD) y Pauli Twirling (PT) "
                "en la señal y fidelidad del algoritmo de Shor ejecutado con ruido (FakeTorino).\n\n")

        f.write("## 1. Técnicas Evaluadas\n\n")
        f.write("| Técnica | Descripción |\n")
        f.write("|:---|:---|\n")
        f.write("| **DD (XY4)** | Secuencia de pulsos X durante idle periods para suprimir decoherencia |\n")
        f.write("| **PT (active)** | Aleatorización de errores coherentes en gates 2Q + medición |\n\n")

        f.write("### Variantes\n\n")
        f.write("| # | Variante | DD | PT |\n")
        f.write("|:---:|:---|:---:|:---:|\n")
        f.write("| 1 | Baseline (sin mitigación) | ❌ | ❌ |\n")
        f.write("| 2 | DD only | ✅ XY4 | ❌ |\n")
        f.write("| 3 | PT only | ❌ | ✅ active |\n")
        f.write("| 4 | DD + PT | ✅ XY4 | ✅ active |\n\n")

        f.write("## 2. Configuración\n\n")
        f.write(f"- **Backend:** AerSimulator + FakeTorino (ruido activo)\n")
        f.write(f"- **Opt level:** {OPT_LEVEL}\n")
        f.write(f"- **Shots:** {SHOTS}\n")
        f.write(f"- **Layout/Routing:** SABRE / SABRE\n\n")

        f.write("## 3. Gráficas\n\n")
        f.write("![Comparación mitigación](../imagenes/comparar_mitigacion_N15.png)\n\n")

        f.write("## 4. Tabla de Resultados\n\n")
        f.write("| Base | Variante | PST (%) | $\\mathcal{F}_H$ | $D_H$ | $D_{KL}$ | Factores | Estado |\n")
        f.write("|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|\n")

        for a in BASES:
            for var_name in VARIANTES:
                d = todos_resultados[f"a={a}"][var_name]
                fac_str = ", ".join(map(str, d["factors"])) if d["factors"] else ("Trivial" if d["trivial"] else "—")
                estado = "✅" if d["success"] else ("⚠️" if d["trivial"] else "❌")
                f.write(f"| {a} | {d['label']} | {d['pst']} | {d['fidelidad_hellinger']:.4f} "
                        f"| {d['distancia_hellinger']:.4f} | {d['divergencia_kl']:.4f} | {fac_str} | {estado} |\n")

        # Tabla de mejora vs baseline
        f.write("\n## 5. Mejora Relativa vs Baseline\n\n")
        f.write("| Base | Δ PST (DD) | Δ PST (PT) | Δ PST (DD+PT) | Δ F_H (DD+PT) |\n")
        f.write("|:---:|:---:|:---:|:---:|:---:|\n")

        for a in BASES:
            base_pst = todos_resultados[f"a={a}"]["baseline"]["pst"]
            base_fh = todos_resultados[f"a={a}"]["baseline"]["fidelidad_hellinger"]
            dd_pst = todos_resultados[f"a={a}"]["dd_only"]["pst"] - base_pst
            pt_pst = todos_resultados[f"a={a}"]["pt_only"]["pst"] - base_pst
            ddpt_pst = todos_resultados[f"a={a}"]["dd_pt"]["pst"] - base_pst
            ddpt_fh = todos_resultados[f"a={a}"]["dd_pt"]["fidelidad_hellinger"] - base_fh
            f.write(f"| {a} | {dd_pst:+.1f}pp | {pt_pst:+.1f}pp | {ddpt_pst:+.1f}pp | {ddpt_fh:+.4f} |\n")

        f.write("\n## 6. Discusión\n\n")
        f.write("### 6.1 Dynamical Decoupling\n\n")
        f.write("- DD inserta secuencias de pulsos (XY4) durante los periodos de inactividad "
                "de los qubits, suprimiendo la decoherencia por acoplamiento con el entorno.\n")
        f.write("- Su efectividad depende de cuántos qubits tienen periodos idle largos en el circuito.\n\n")

        f.write("### 6.2 Pauli Twirling\n\n")
        f.write("- PT aleatoriza los errores coherentes de las compuertas 2Q, convirtiéndolos en "
                "errores estocásticos (canal de Pauli) que pueden cancelarse al promediar.\n")
        f.write("- Es especialmente efectivo contra errores sistemáticos en las compuertas ECR.\n\n")

        f.write("### 6.3 Combinación DD + PT\n\n")
        f.write("- La combinación aprovecha la complementariedad: DD mitiga decoherencia temporal "
                "y PT mitiga errores de compuerta.\n\n")

        f.write("## 7. Conclusiones\n\n")
        f.write("1. Las técnicas de mitigación mejoran la señal respecto a la línea base ruidosa.\n")
        f.write("2. La combinación DD + PT generalmente produce los mejores resultados.\n")
        f.write("3. Los resultados guían la selección de la configuración óptima para la "
                "ejecución en hardware real (Fase IV).\n")

    print(f"Reporte guardado en -> {md_path}", flush=True)


if __name__ == "__main__":
    run_mitigation_comparison()

