"""
histograma_picos_ruido.py

Re-ejecuta la simulación con ruido de FakeTorino (mismas semillas/config que
`ejecutar_shor_faketorino_simulacion_ruido.py`), guarda los `counts` crudos en
JSON, y genera un histograma de la estimación de fase (QPE) para cada
combinación (a, opt). El histograma muestra:
  • Picos teóricos esperados (líneas verticales punteadas)
  • Distribución ruidosa real (barras)
  • Piso de ruido visible (escala lineal con zoom + escala log opcional)

Coloca este archivo en `simulacion_con_ruido/scripts/` (junto al script original)
y ejecútalo. Usará la misma estructura de carpetas (datos/, imagenes/).

Tiempo estimado total: ~110-120 min (dominado por a=7, opt=3 → ~100 min).
"""

import os
import sys
import time
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# Repo root (igual que el script original)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from algorithm.circuit import RegisterQC
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeTorino

# ─── CONFIGURACIÓN (idéntica al script original) ───────────────────────────
N = 15
BASES = [4, 7]
OPT_LEVELS = [0, 3]
SHOTS = 512
SEED = 457
CONTROL_QUBITS = 9
DIM = 2 ** CONTROL_QUBITS  # 512

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
IMG_DIR = os.path.join(BASE_DIR, "imagenes")
os.makedirs(DATOS_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

COUNTS_JSON = os.path.join(DATOS_DIR, "counts_ruido_faketorino_N15.json")


# ─── UTILIDADES ─────────────────────────────────────────────────────────────

def find_order(a, N):
    val = 1
    for r in range(1, N):
        val = (val * a) % N
        if val == 1:
            return r
    return None


def picos_teoricos(a, N, m):
    """Picos del QPE: y_s = round(s * 2^m / r), s = 0..r-1."""
    r = find_order(a, N)
    dim = 2 ** m
    return r, [round(s * dim / r) % dim for s in range(r)]


def counts_a_probs(counts, m):
    total = sum(counts.values())
    dim = 2 ** m
    p = np.zeros(dim)
    for bs, c in counts.items():
        p[int(bs, 2)] = c / total
    return p


# ─── EJECUCIÓN ──────────────────────────────────────────────────────────────

def correr_y_guardar_counts():
    print(f"[{time.strftime('%H:%M:%S')}] Re-ejecutando simulación con ruido para histogramas...", flush=True)
    fake_torino = FakeTorino()
    noisy_sim = AerSimulator.from_backend(fake_torino)
    sampler = SamplerV2(mode=noisy_sim)

    todos = {}

    for a in BASES:
        circuito = RegisterQC()
        qc = circuito.create_circuit(N, a)
        todos[f"a={a}"] = []

        for opt in OPT_LEVELS:
            print(f"  -> a={a}, opt={opt} ...", end=" ", flush=True)
            t0 = time.time()
            isa = transpile(
                qc, backend=fake_torino,
                optimization_level=opt,
                layout_method='sabre',
                routing_method='sabre',
                seed_transpiler=SEED
            )
            job = sampler.run([(isa,)], shots=SHOTS)
            counts = job.result()[0].data.output.get_counts()
            dt = time.time() - t0
            todos[f"a={a}"].append({
                "base": a,
                "optimization_level": opt,
                "shots": SHOTS,
                "counts": dict(counts),  # dict[bitstring -> int]
                "elapsed_s": round(dt, 2)
            })
            # Guardado incremental por si la corrida es larga y se interrumpe
            with open(COUNTS_JSON, "w") as f:
                json.dump(todos, f, indent=2)
            print(f"OK ({dt:.1f}s, {len(counts)} estados únicos)", flush=True)

    print(f"\nCounts guardados en -> {COUNTS_JSON}", flush=True)
    return todos


def cargar_counts_existentes():
    """Si ya existe el JSON de counts, lo reusa sin re-simular."""
    if os.path.exists(COUNTS_JSON):
        with open(COUNTS_JSON) as f:
            return json.load(f)
    return None


# ─── GRÁFICA ────────────────────────────────────────────────────────────────

def graficar_histogramas(todos):
    """
    Layout 2x2 con un panel por combinación (a, opt).
    Eje x: índice del estado medido (0 a 2^m - 1).
    Eje y: probabilidad.
    Líneas verticales rojas punteadas: picos teóricos.
    Anotación: PST y F_H por panel.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 8.5), sharex=True)

    # Color suave para barras, rojo nítido para picos teóricos
    color_bar = "#3498db"
    color_pico = "#c0392b"

    # Para anotaciones: cargamos el JSON de métricas si existe (PST, F_H)
    metrics_path = os.path.join(DATOS_DIR, "resultados_ruido_faketorino_N15.json")
    metrics = {}
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            metrics = json.load(f)

    panel_idx = 0
    for a in BASES:
        r, ys_teo = picos_teoricos(a, N, CONTROL_QUBITS)
        prob_teo_pico = 1.0 / r

        for opt in OPT_LEVELS:
            ax = axes[panel_idx // 2, panel_idx % 2]

            # Buscar la entrada correspondiente
            entry = next(e for e in todos[f"a={a}"] if e["optimization_level"] == opt)
            probs = counts_a_probs(entry["counts"], CONTROL_QUBITS)

            # Barras: distribución ruidosa
            xs = np.arange(DIM)
            ax.bar(xs, probs, width=1.0, color=color_bar, alpha=0.85,
                   linewidth=0, label="Distribución ruidosa")

            # Líneas verticales en picos teóricos
            for y_t in ys_teo:
                ax.axvline(y_t, color=color_pico, linestyle="--",
                           linewidth=1.2, alpha=0.85, zorder=3)
            # Marca de la altura teórica esperada (1/r)
            ax.axhline(prob_teo_pico, color=color_pico, linestyle=":",
                       linewidth=1.0, alpha=0.6,
                       label=f"Altura teórica ideal = 1/{r} = {prob_teo_pico:.3f}")

            # Anotación PST / F_H si existe
            pst, fh = None, None
            if f"a={a}" in metrics:
                m_entry = next((m for m in metrics[f"a={a}"]
                                if m["optimization_level"] == opt), None)
                if m_entry:
                    pst = m_entry.get("pst")
                    fh = m_entry.get("fidelidad_hellinger")

            anot = f"$a={a}$ · opt={opt} · $r={r}$"
            if pst is not None:
                anot += f"\nPST = {pst:.1f}%   $\\mathcal{{F}}_H$ = {fh:.4f}"
            ax.text(0.985, 0.95, anot, transform=ax.transAxes,
                    ha="right", va="top", fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.35",
                              facecolor="white", edgecolor="0.7", alpha=0.92))

            ax.set_xlim(0, DIM - 1)
            ax.set_ylim(0, max(probs.max() * 1.18, prob_teo_pico * 1.18))
            ax.set_ylabel("Probabilidad")
            ax.grid(True, axis="y", linestyle="--", alpha=0.35)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=9))

            if panel_idx >= 2:
                ax.set_xlabel(r"Estado medido $y$ (registro de control, $2^9=512$)")

            panel_idx += 1

    # Leyenda compartida en la parte superior
    handles, labels = axes[0, 0].get_legend_handles_labels()
    from matplotlib.lines import Line2D
    handles.append(Line2D([0], [0], color=color_pico, linestyle="--", lw=1.4))
    labels.append("Picos teóricos $y_s = s\\,2^m/r$")
    fig.legend(handles, labels, loc="upper center", ncol=3,
               bbox_to_anchor=(0.5, 1.005), frameon=False, fontsize=10)

    fig.suptitle(
        "Histograma de la estimación de fase con ruido (FakeTorino, $N=15$)\n"
        "Picos teóricos vs. distribución ruidosa para cada $(a, \\mathrm{opt})$",
        fontsize=13, fontweight="bold", y=1.04
    )
    plt.tight_layout()

    # PNG principal (escala lineal, contraste de picos)
    out_lin = os.path.join(IMG_DIR, "histograma_picos_ruido_N15.png")
    plt.savefig(out_lin, dpi=220, bbox_inches="tight")
    print(f"Histograma (lineal) -> {out_lin}", flush=True)

    # Variante en escala logarítmica para visualizar el "piso de ruido"
    for ax in axes.flat:
        ax.set_yscale("log")
        ax.set_ylim(1e-4, 1.0)
        ax.set_ylabel("Probabilidad (escala log)")
    fig.suptitle(
        "Histograma de la estimación de fase con ruido — escala log\n"
        "(piso de ruido visible en estados teóricamente prohibidos)",
        fontsize=13, fontweight="bold", y=1.04
    )
    out_log = os.path.join(IMG_DIR, "histograma_picos_ruido_N15_log.png")
    plt.savefig(out_log, dpi=220, bbox_inches="tight")
    print(f"Histograma (log)    -> {out_log}", flush=True)

    plt.close()


# ─── MAIN ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cache = cargar_counts_existentes()
    if cache is not None and all(
        any(e["optimization_level"] == o for e in cache.get(f"a={a}", []))
        for a in BASES for o in OPT_LEVELS
    ):
        print(f"[INFO] Reusando counts existentes en {COUNTS_JSON}", flush=True)
        todos = cache
    else:
        todos = correr_y_guardar_counts()
    graficar_histogramas(todos)
    print("\n[✔] Histogramas generados.", flush=True)
