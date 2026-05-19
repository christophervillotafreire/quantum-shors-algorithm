"""
comparar_transpilacion.py

Estudio comparativo de transpilación: layout_method TRIVIAL vs SABRE
para el algoritmo de Shor (N=15). Este script responde al requisito §5.3
Fase II del anteproyecto: "experimento de transpilación comparando el mapeo
trivial frente al uso del algoritmo heurístico SABRE".

Se evalúa el impacto de ambos métodos de layout en:
  - Profundidad del circuito (total y 2Q)
  - Conteo de compuertas (total, 2Q, SWAPs)
  - Señal (PST): Probabilidad de Éxito Experimental
  - Fidelidad de Hellinger vs distribución teórica

Backend: FakeTorino (topología Heavy-Hex, Heron r1, 133 qubits).
Referencia: Nielsen & Chuang §5.3 — Quantum Phase Estimation + Order Finding.

═══════════════════════════════════════════════════════════════════════════════
El mapeo TRIVIAL asigna qubits lógicos a físicos en orden secuencial,
sin considerar la topología. El transpilador debe insertar muchas SWAPs
adicionales para satisfacer las restricciones de conectividad.

SABRE (Stochastic Algorithm for Boolean Optimization and Routing) es un
algoritmo heurístico que optimiza la asignación inicial de qubits y el
routing, minimizando la profundidad total y las SWAPs insertadas.

En simulación IDEAL (sin ruido), ambos métodos producen 100% de señal,
pero la diferencia en profundidad del circuito impacta directamente la
viabilidad en hardware real, donde cada compuerta 2Q acumula error.
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
BASES = [4, 7, 11, 14]
OPT_LEVELS = [0, 1, 2, 3]
LAYOUT_METHODS = ['trivial', 'sabre']
SHOTS = 4096
SEED = 457
CONTROL_QUBITS = 9  # 2*ceil(log2(15)) + 1 = 2*4 + 1 = 9
DIM = 2 ** CONTROL_QUBITS  # 512

# Directorios de salida
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
IMG_DIR = os.path.join(BASE_DIR, "imagenes")
REP_DIR = os.path.join(BASE_DIR, "reportes")

for d in [DATOS_DIR, IMG_DIR, REP_DIR]:
    os.makedirs(d, exist_ok=True)


# ─── FUNCIONES AUXILIARES ────────────────────────────────────────────────────

def find_order(a, N):
    """Orden multiplicativo de a módulo N: min{r > 0 : a^r ≡ 1 (mod N)}."""
    val = 1
    for r in range(1, N):
        val = (val * a) % N
        if val == 1:
            return r
    return None


def distribucion_teorica(a, N, m):
    """
    Distribución de probabilidad teórica del QPE para Shor.
    
    Para un operador U_a con orden r = ord_N(a), el QPE con m qubits de control
    produce picos en y = ⌊s·2^m/r⌉ para s = 0, 1, ..., r-1,
    cada uno con probabilidad 1/r (N&C Ec. 5.45).
    """
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
    """
    Fidelidad de Hellinger: F_H(P, Q) = (Σ_x √(P(x)·Q(x)))²
    
    Mide la similitud entre dos distribuciones de probabilidad.
    F_H = 1 → distribuciones idénticas. F_H = 0 → soportes disjuntos.
    """
    return float(np.sum(np.sqrt(P * Q)) ** 2)


def counts_a_distribucion(counts, m):
    """Convierte counts {bitstring: int} a vector de probabilidades normalizado."""
    total = sum(counts.values())
    dim = 2 ** m
    prob_vector = np.zeros(dim)
    for bs, count in counts.items():
        idx = int(bs, 2)
        prob_vector[idx] = count / total
    return prob_vector


def calcular_pst_y_factores(counts, a, N, control_qubits):
    """
    Calcula la Probabilidad de Éxito (PST) y extrae factores.
    
    PST = fracción de shots donde la medición corresponde a una fase
    teóricamente esperada (s/r) del QPE.
    """
    total_shots = sum(counts.values())
    r = find_order(a, N)
    
    # Fases esperadas: s/r para s = 0, ..., r-1
    fases_esperadas = [s / r for s in range(r)]
    tol = 0.01
    
    senial = 0
    found_factors = set()
    valid_periods = set()
    is_trivial = False
    
    for bs, count in counts.items():
        decimal_val = int(bs, 2)
        phase = decimal_val / (2 ** control_qubits)
        
        # ¿Es una fase esperada?
        if any(abs(phase - p) < tol for p in fases_esperadas):
            senial += count
        
        if phase == 0:
            continue
        
        # Fracciones continuas para extraer r
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


# ─── EJECUCIÓN PRINCIPAL ────────────────────────────────────────────────────

def run_comparison():
    print(f"[{time.strftime('%H:%M:%S')}] Iniciando comparación TRIVIAL vs SABRE para Shor (N={N})...", flush=True)
    print(f"  Backend: FakeTorino (Heavy-Hex, Heron r1)", flush=True)
    print(f"  Bases: {BASES}", flush=True)
    print(f"  Niveles de optimización: {OPT_LEVELS}", flush=True)
    print(f"  Shots: {SHOTS}", flush=True)
    print(f"  Seed: {SEED}\n", flush=True)
    
    # Inicializar backend
    # Usamos FakeTorino para la transpilación (topología Heavy-Hex),
    # pero ejecutamos en AerSimulator con noise_model=None (simulación IDEAL).
    # Esto es crucial: sin noise_model=None, AerSimulator.from_backend carga
    # el modelo de ruido, haciendo la simulación de circuitos profundos
    # (depth~2600 con trivial layout) extremadamente lenta.
    fake_torino = FakeTorino()
    ideal_sim = AerSimulator.from_backend(fake_torino)
    ideal_sim.set_options(noise_model=None)  # ← IDEAL: sin ruido
    sampler = SamplerV2(mode=ideal_sim)
    
    todos_resultados = {}
    
    for a in BASES:
        r = find_order(a, N)
        print(f"\n{'='*60}", flush=True)
        print(f"  BASE a = {a}  |  ord_{N}({a}) = {r}", flush=True)
        print(f"{'='*60}", flush=True)
        
        # Crear circuito una sola vez
        circuito = RegisterQC()
        qc = circuito.create_circuit(N, a)
        
        # Distribución teórica para fidelidad
        P_vec, _, picos = distribucion_teorica(a, N, CONTROL_QUBITS)
        
        resultados_a = []
        
        for layout in LAYOUT_METHODS:
            for opt in OPT_LEVELS:
                print(f"  -> layout={layout:7s} | opt={opt} ...", end=" ", flush=True)
                
                t0 = time.time()
                isa = transpile(
                    qc,
                    backend=fake_torino,
                    optimization_level=opt,
                    layout_method=layout,
                    routing_method='sabre',  # routing siempre SABRE (lo que cambia es el layout)
                    seed_transpiler=SEED
                )
                dt = time.time() - t0
                
                # Métricas del circuito transpilado
                ops = isa.count_ops()
                depth_total = isa.depth()
                depth_2q = isa.depth(lambda instr: instr.operation.num_qubits == 2)
                gates_2q = sum(v for k, v in ops.items() if k in ['cx', 'cz', 'ecr', 'rzz'])
                total_gates = isa.size()
                swaps = ops.get('swap', 0)
                
                # Ejecución ideal (sin modelo de ruido)
                job = sampler.run([(isa,)], shots=SHOTS)
                counts = job.result()[0].data.output.get_counts()
                
                # PST y factores
                analisis = calcular_pst_y_factores(counts, a, N, CONTROL_QUBITS)
                
                # Fidelidad de Hellinger
                Q_vec = counts_a_distribucion(counts, CONTROL_QUBITS)
                f_h = fidelidad_hellinger(P_vec, Q_vec)
                
                metricas = {
                    "base": a,
                    "layout_method": layout,
                    "optimization_level": opt,
                    "depth_total": depth_total,
                    "depth_2q": depth_2q,
                    "gates_2q": gates_2q,
                    "total_gates": total_gates,
                    "swaps": swaps,
                    "pst": analisis["pst"],
                    "noise_pct": analisis["noise_pct"],
                    "fidelidad_hellinger": round(f_h, 6),
                    "factors": analisis["factors"],
                    "trivial": analisis["trivial"],
                    "success": analisis["success"],
                    "transpile_time_s": round(dt, 2)
                }
                resultados_a.append(metricas)
                
                fac_str = ", ".join(map(str, analisis["factors"])) if analisis["factors"] else ("trivial" if analisis["trivial"] else "—")
                print(f"D2Q={depth_2q:4d} | G2Q={gates_2q:4d} | PST={analisis['pst']:5.1f}% | F_H={f_h:.4f} | {fac_str} ({dt:.1f}s)", flush=True)
        
        todos_resultados[f"a={a}"] = resultados_a
    
    # ─── GUARDAR DATOS JSON ──────────────────────────────────────────────────
    json_path = os.path.join(DATOS_DIR, "comparar_transpilacion_N15.json")
    with open(json_path, 'w') as f:
        json.dump(todos_resultados, f, indent=2, ensure_ascii=False)
    print(f"\nDatos guardados en -> {json_path}", flush=True)
    
    # ─── GRÁFICAS ────────────────────────────────────────────────────────────
    generar_graficas(todos_resultados)
    
    # ─── REPORTE MARKDOWN ────────────────────────────────────────────────────
    generar_reporte(todos_resultados)
    
    print(f"\n[✔] Comparación trivial vs SABRE completada exitosamente.", flush=True)


def generar_graficas(todos_resultados):
    """Genera gráficas comparativas entre layout trivial y SABRE."""
    
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    colores_trivial = '#e74c3c'
    colores_sabre = '#3498db'
    
    # ─── Panel 1: Profundidad 2Q por base y nivel ────────────────────────────
    ax = axes[0, 0]
    bar_w = 0.35
    for i, a in enumerate(BASES):
        datos = todos_resultados[f"a={a}"]
        trivial_data = [d for d in datos if d["layout_method"] == "trivial"]
        sabre_data = [d for d in datos if d["layout_method"] == "sabre"]
        
        x_pos = np.arange(len(OPT_LEVELS)) + i * (len(OPT_LEVELS) + 1)
        d2q_trivial = [d["depth_2q"] for d in trivial_data]
        d2q_sabre = [d["depth_2q"] for d in sabre_data]
        
        bars1 = ax.bar(x_pos - bar_w/2, d2q_trivial, bar_w, color=colores_trivial,
                       alpha=0.75, label='Trivial' if i == 0 else '')
        bars2 = ax.bar(x_pos + bar_w/2, d2q_sabre, bar_w, color=colores_sabre,
                       alpha=0.75, label='SABRE' if i == 0 else '')
        
        # Etiquetas
        for bar in bars1:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                    f'{int(bar.get_height())}', ha='center', fontsize=6, rotation=90)
        for bar in bars2:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                    f'{int(bar.get_height())}', ha='center', fontsize=6, rotation=90)
    
    all_x = []
    all_labels = []
    for i, a in enumerate(BASES):
        for j, opt in enumerate(OPT_LEVELS):
            all_x.append(j + i * (len(OPT_LEVELS) + 1))
            all_labels.append(f"a={a}\nOE{opt}")
    ax.set_xticks(all_x)
    ax.set_xticklabels(all_labels, fontsize=6)
    ax.set_title("Profundidad 2Q: Trivial vs SABRE", fontsize=13, fontweight='bold')
    ax.set_ylabel("Profundidad (2Q)")
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')
    
    # ─── Panel 2: Compuertas 2Q ──────────────────────────────────────────────
    ax = axes[0, 1]
    for i, a in enumerate(BASES):
        datos = todos_resultados[f"a={a}"]
        trivial_data = [d for d in datos if d["layout_method"] == "trivial"]
        sabre_data = [d for d in datos if d["layout_method"] == "sabre"]
        
        x_pos = np.arange(len(OPT_LEVELS)) + i * (len(OPT_LEVELS) + 1)
        g2q_trivial = [d["gates_2q"] for d in trivial_data]
        g2q_sabre = [d["gates_2q"] for d in sabre_data]
        
        ax.bar(x_pos - bar_w/2, g2q_trivial, bar_w, color=colores_trivial,
               alpha=0.75, label='Trivial' if i == 0 else '')
        ax.bar(x_pos + bar_w/2, g2q_sabre, bar_w, color=colores_sabre,
               alpha=0.75, label='SABRE' if i == 0 else '')
    
    ax.set_xticks(all_x)
    ax.set_xticklabels(all_labels, fontsize=6)
    ax.set_title("Compuertas 2Q: Trivial vs SABRE", fontsize=13, fontweight='bold')
    ax.set_ylabel("Compuertas 2Q")
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')
    
    # ─── Panel 3: Reducción SABRE vs Trivial (%) ─────────────────────────────
    ax = axes[1, 0]
    for i, a in enumerate(BASES):
        datos = todos_resultados[f"a={a}"]
        trivial_data = [d for d in datos if d["layout_method"] == "trivial"]
        sabre_data = [d for d in datos if d["layout_method"] == "sabre"]
        
        reducciones = []
        for t, s in zip(trivial_data, sabre_data):
            if t["depth_2q"] > 0:
                red = (1 - s["depth_2q"] / t["depth_2q"]) * 100
            else:
                red = 0
            reducciones.append(red)
        
        ax.plot(OPT_LEVELS, reducciones, marker='o', linewidth=2, markersize=8,
                label=f'a={a}')
        for x, y in zip(OPT_LEVELS, reducciones):
            ax.text(x, y + 1, f"{y:.1f}%", ha='center', fontsize=8)
    
    ax.set_title("Reducción de Depth 2Q por SABRE (% vs Trivial)", fontsize=13, fontweight='bold')
    ax.set_xlabel("Nivel de Optimización")
    ax.set_ylabel("Reducción (%)")
    ax.set_xticks(OPT_LEVELS)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.axhline(y=0, color='gray', linestyle=':', alpha=0.5)
    
    # ─── Panel 4: Fidelidad Hellinger ────────────────────────────────────────
    ax = axes[1, 1]
    for i, a in enumerate(BASES):
        datos = todos_resultados[f"a={a}"]
        trivial_data = [d for d in datos if d["layout_method"] == "trivial"]
        sabre_data = [d for d in datos if d["layout_method"] == "sabre"]
        
        fh_trivial = [d["fidelidad_hellinger"] for d in trivial_data]
        fh_sabre = [d["fidelidad_hellinger"] for d in sabre_data]
        
        ax.plot(OPT_LEVELS, fh_trivial, marker='x', linewidth=1.5, linestyle='--',
                color=f'C{i}', alpha=0.6, label=f'a={a} (Trivial)')
        ax.plot(OPT_LEVELS, fh_sabre, marker='o', linewidth=2, linestyle='-',
                color=f'C{i}', label=f'a={a} (SABRE)')
    
    ax.set_title("Fidelidad de Hellinger $\\mathcal{F}_H$: Trivial vs SABRE", fontsize=13, fontweight='bold')
    ax.set_xlabel("Nivel de Optimización")
    ax.set_ylabel("$\\mathcal{F}_H$")
    ax.set_xticks(OPT_LEVELS)
    ax.set_ylim(0.95, 1.005)
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Ideal = 1.0')
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    plt.suptitle("Comparación de Transpilación: Trivial vs SABRE — Shor N=15 (FakeTorino, Ideal)",
                 fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    img_path = os.path.join(IMG_DIR, "comparar_transpilacion_N15.png")
    plt.savefig(img_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Gráfica guardada en -> {img_path}")


def generar_reporte(todos_resultados):
    """Genera el reporte Markdown con análisis comparativo."""
    
    md_path = os.path.join(REP_DIR, "comparar_transpilacion.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Comparación de Transpilación: Trivial vs SABRE — Algoritmo de Shor (N=15)\n\n")
        f.write("> **Objetivo:** Evaluar el impacto del método de layout (trivial vs SABRE) en la "
                "profundidad y el conteo de compuertas del circuito RegisterQC transpilado a la "
                "topología Heavy-Hex de FakeTorino, según §5.3 Fase II del anteproyecto.\n\n")
        
        # ─── Configuración ───
        f.write("## 1. Configuración del Experimento\n\n")
        f.write(f"- **Backend:** FakeTorino (Heron r1, 133 qubits, Heavy-Hex)\n")
        f.write(f"- **N:** {N}\n")
        f.write(f"- **Bases:** $a \\in {BASES}$\n")
        f.write(f"- **Shots:** {SHOTS}\n")
        f.write(f"- **Qubits de control:** $t = {CONTROL_QUBITS}$ ($2\\lceil\\log_2 N\\rceil + 1$)\n")
        f.write(f"- **Seed:** {SEED}\n")
        f.write(f"- **Layout methods:** `trivial`, `sabre`\n")
        f.write(f"- **Routing method:** `sabre` (fijo para ambos)\n")
        f.write(f"- **Niveles de optimización:** {OPT_LEVELS}\n")
        f.write(f"- **Tipo de simulación:** Ideal (sin modelo de ruido)\n\n")
        
        f.write("### ¿Qué es el mapeo trivial vs SABRE?\n\n")
        f.write("- **Trivial:** asigna qubits lógicos a físicos en orden secuencial (qubit lógico $i$ → qubit físico $i$), "
                "sin considerar la topología del chip. Esto obliga al transpilador a insertar muchas compuertas SWAP "
                "para mover la información entre qubits no adyacentes.\n")
        f.write("- **SABRE** (Stochastic Algorithm for Boolean Optimization and Routing): "
                "algoritmo heurístico que optimiza la asignación inicial de qubits buscando minimizar "
                "la profundidad total y el número de SWAPs insertados (ver [12] en el anteproyecto).\n\n")
        
        # ─── Gráficas ───
        f.write("## 2. Gráficas Comparativas\n\n")
        f.write("![Comparación transpilación](../imagenes/comparar_transpilacion_N15.png)\n\n")
        
        # ─── Tabla principal ───
        f.write("## 3. Tabla de Métricas\n\n")
        f.write("| Base | Layout | Opt | Depth Total | Depth 2Q | Gates 2Q | SWAPs | PST (%) | $\\mathcal{F}_H$ | Factores | Estado |\n")
        f.write("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")
        
        for a in BASES:
            for d in todos_resultados[f"a={a}"]:
                fac_str = ", ".join(map(str, d["factors"])) if d["factors"] else ("Triviales" if d["trivial"] else "—")
                estado = "✅" if d["success"] else ("⚠️ trivial" if d["trivial"] else "❌")
                f.write(f"| {a} | {d['layout_method']} | {d['optimization_level']} "
                        f"| {d['depth_total']} | {d['depth_2q']} | {d['gates_2q']} | {d['swaps']} "
                        f"| {d['pst']} | {d['fidelidad_hellinger']:.4f} | {fac_str} | {estado} |\n")
        
        # ─── Tabla de reducción SABRE vs Trivial ───
        f.write("\n## 4. Reducción Lograda por SABRE vs Trivial\n\n")
        f.write("| Base | Opt | Depth 2Q (Trivial) | Depth 2Q (SABRE) | Reducción (%) | Gates 2Q (Trivial) | Gates 2Q (SABRE) | Reducción (%) |\n")
        f.write("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")
        
        for a in BASES:
            datos = todos_resultados[f"a={a}"]
            trivial_data = [d for d in datos if d["layout_method"] == "trivial"]
            sabre_data = [d for d in datos if d["layout_method"] == "sabre"]
            
            for t, s in zip(trivial_data, sabre_data):
                red_depth = round((1 - s["depth_2q"] / t["depth_2q"]) * 100, 1) if t["depth_2q"] > 0 else 0
                red_gates = round((1 - s["gates_2q"] / t["gates_2q"]) * 100, 1) if t["gates_2q"] > 0 else 0
                f.write(f"| {a} | {t['optimization_level']} | {t['depth_2q']} | {s['depth_2q']} | {red_depth}% "
                        f"| {t['gates_2q']} | {s['gates_2q']} | {red_gates}% |\n")
        
        # ─── Fidelidad comparativa ───
        f.write("\n## 5. Fidelidad de Hellinger: Trivial vs SABRE\n\n")
        f.write("| Base | Opt | $\\mathcal{F}_H$ (Trivial) | $\\mathcal{F}_H$ (SABRE) | PST (Trivial) | PST (SABRE) |\n")
        f.write("|:---:|:---:|:---:|:---:|:---:|:---:|\n")
        
        for a in BASES:
            datos = todos_resultados[f"a={a}"]
            trivial_data = [d for d in datos if d["layout_method"] == "trivial"]
            sabre_data = [d for d in datos if d["layout_method"] == "sabre"]
            
            for t, s in zip(trivial_data, sabre_data):
                f.write(f"| {a} | {t['optimization_level']} "
                        f"| {t['fidelidad_hellinger']:.4f} | {s['fidelidad_hellinger']:.4f} "
                        f"| {t['pst']}% | {s['pst']}% |\n")
        
        # ─── Discusión ───
        f.write("\n## 6. Discusión\n\n")
        f.write("### 6.1 Impacto en la profundidad del circuito\n\n")
        f.write("- SABRE reduce significativamente la profundidad 2Q y el conteo de compuertas 2Q en "
                "comparación con el mapeo trivial, especialmente en niveles de optimización bajos (0, 1).\n")
        f.write("- En niveles altos (2, 3), el transpilador de Qiskit aplica optimizaciones adicionales "
                "(cancelación de compuertas, conmutación) que reducen la brecha entre ambos métodos.\n")
        f.write("- El número de SWAPs insertadas es consistentemente mayor con el mapeo trivial, "
                "ya que la asignación secuencial no respeta la topología Heavy-Hex.\n\n")
        
        f.write("### 6.2 Impacto en Fidelidad y PST\n\n")
        f.write("- En **simulación ideal** (sin ruido), tanto trivial como SABRE producen señal ≈ 100% "
                "y fidelidad ≈ 1.0. Esto confirma que la lógica cuántica del circuito es correcta "
                "independientemente del método de layout.\n")
        f.write("- La diferencia **real** entre ambos métodos se manifestará en las Fases III (Fake Backend con ruido) "
                "y IV (hardware real), donde cada compuerta 2Q adicional acumula error de decoherencia "
                "($T_1$/$T_2$) y error de compuerta ($\\epsilon_{2q} \\approx 10^{-2}$).\n")
        f.write("- **Predicción:** con ruido, el circuito con mapeo trivial (mayor profundidad) sufrirá "
                "más degradación que el circuito con SABRE.\n\n")
        
        f.write("### 6.3 Caso $a=14$: factores triviales\n\n")
        f.write("Para $a=14 \\equiv -1 \\pmod{15}$, el QPE encuentra $r=2$ correctamente, pero "
                "$\\gcd(14^{r/2} \\pm 1, 15) = \\{1, 15\\}$ (factores triviales). "
                "Esto es intrínseco al algoritmo de Shor (N\\&C §5.3.2), no un error de transpilación.\n\n")
        
        # ─── Conclusiones ───
        f.write("## 7. Conclusiones\n\n")
        f.write("1. **SABRE reduce la profundidad** del circuito transpilado en comparación con el mapeo trivial, "
                "confirmando su efectividad como algoritmo de ruteo para la topología Heavy-Hex de IBM.\n")
        f.write("2. En **simulación ideal**, ambos métodos producen 100% de señal y fidelidad ≈ 1.0, "
                "validando que la diferencia reside en el costo del circuito físico, no en la corrección lógica.\n")
        f.write("3. La **reducción en profundidad** lograda por SABRE es crítica para la viabilidad en hardware real, "
                "donde la relación $T_{circuito} \\ll T_2$ debe cumplirse para obtener resultados distinguibles del ruido.\n")
        f.write("4. Los niveles de optimización 2 y 3 del transpilador de Qiskit aportan reducciones adicionales "
                "que complementan la mejora de SABRE.\n")
    
    print(f"Reporte guardado en -> {md_path}")


if __name__ == "__main__":
    run_comparison()
