"""
ejecutar_shor_faketorino_ideal.py

Este script ejecuta la simulación IDEAL (sin modelo de ruido) del algoritmo de Shor
para N=15 utilizando las bases a ∈ [4, 7, 11, 14]. Emplea la topología y basis gates
de FakeTorino (133 qubits) para evaluar el impacto de los niveles de optimización (0-3)
en la profundidad del circuito y la métrica de éxito, de acuerdo al anteproyecto de grado.
"""

import os
import sys
import time
import json
from math import gcd
from fractions import Fraction
import numpy as np
import matplotlib.pyplot as plt

# Configuración de rutas
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from algoritmo.circuit import RegisterQC
from qiskit import transpile
from qiskit_ibm_runtime.fake_provider import FakeTorino
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
N = 15
BASES = [4, 7, 11, 14]
OPT_LEVELS = [0, 1, 2, 3]
SHOTS = 4096
SEED = 457
CONTROL_QUBITS = 9

# Directorios de salida
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
IMG_DIR = os.path.join(BASE_DIR, "imagenes")
REP_DIR = os.path.join(BASE_DIR, "reportes")

for d in [DATOS_DIR, IMG_DIR, REP_DIR]:
    os.makedirs(d, exist_ok=True)

# ─── FUNCIONES DE ANÁLISIS ───────────────────────────────────────────────────

def extraccion_factores(counts, a, N, control_qubits):
    """
    Extrae factores utilizando la aproximación de fracciones continuas clásica.
    
    Nota sobre factores triviales (Nielsen & Chuang §5.3.2):
    Cuando a ≡ -1 (mod N), el orden es r=2, pero gcd(a^(r/2)±1, N) = {1, N},
    que son factores triviales. Esto ocurre para a=14 con N=15 ya que 14 ≡ -1 (mod 15).
    El algoritmo cuántico funciona correctamente (encuentra r=2), pero la extracción
    clásica de factores falla por propiedad algebraica intrínseca.
    """
    total_shots = sum(counts.values())
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    
    found_factors = set()
    trivial_factors_found = set()
    valid_periods = set()
    senio = 0
    ruido = 0
    is_trivial = False
    
    # Se conoce que para a={4,11,14} r=2 (fases 0.0, 0.5) y para a=7 r=4 (0.0, 0.25, 0.5, 0.75)
    fases_esperadas = [0.0, 0.5] if a in [4, 11, 14] else [0.0, 0.25, 0.5, 0.75]
    tol = 0.01

    for bs, count in sorted_counts:
        decimal_val = int(bs, 2)
        phase = decimal_val / (2 ** control_qubits)
        
        if any(abs(phase - p) < tol for p in fases_esperadas):
            senio += count
        else:
            ruido += count

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
                else:
                    trivial_factors_found.add(g1)
                if 1 < g2 < N:
                    found_factors.add(g2)
                else:
                    trivial_factors_found.add(g2)
                # Detectar caso trivial: a ≡ -1 (mod N)
                if g1 in (1, N) or g2 in (1, N):
                    is_trivial = True
                
    success = (len(found_factors) >= 2) or (len(found_factors) == 1 and N % list(found_factors)[0] == 0)
    
    return {
        "factors": sorted(list(found_factors)),
        "trivial_factors": is_trivial,
        "periods_found": sorted(list(valid_periods)),
        "signal_pct": round(100 * senio / total_shots, 2),
        "noise_pct": round(100 * ruido / total_shots, 2),
        "success": success,
        "note": f"a={a} ≡ -1 (mod {N}): factores triviales {{1, {N}}}" if is_trivial and not found_factors else ""
    }

# ─── MAIN EXECUTION ─────────────────────────────────────────────────────────

def run_simulation():
    print(f"[{time.strftime('%H:%M:%S')}] Iniciando simulación ideal de Shor en FakeTorino N={N}...")
    
    fake_backend = FakeTorino()
    # Usamos AerSimulator pero sin agregar noise_model (simulación IDEAL)
    # Solo adoptamos el coupling_map y basis_gates para que la topología sea idéntica al hardware
    ideal_simulator = AerSimulator.from_backend(fake_backend)
    
    # Nos aseguramos de forzar que no haya modelo de ruido (ideal)
    ideal_simulator.set_options(noise_model=None)
    
    sampler = SamplerV2(mode=ideal_simulator)
    
    todos_los_resultados = {}
    
    for a in BASES:
        print(f"\n{'='*50}")
        print(f"[{time.strftime('%H:%M:%S')}] BASE a = {a}")
        circuito_shor = RegisterQC()
        qc = circuito_shor.create_circuit(15, a)
        
        resultados_a = []
        
        for opt in OPT_LEVELS:
            print(f"  -> Transpilando nivel {opt}...")
            t0 = time.time()
            isa_circuit = transpile(
                qc,
                backend=ideal_simulator,
                optimization_level=opt,
                seed_transpiler=SEED
            )
            dt = time.time() - t0
            
            ops = isa_circuit.count_ops()
            depth_total = isa_circuit.depth()
            depth_2q = isa_circuit.depth(lambda instr: instr.operation.num_qubits == 2)
            c2q = ops.get('cz', 0) + ops.get('ecr', 0)
            
            print(f"  -> Ejecutando en AerSimulator (SamplerV2)...")
            job = sampler.run([(isa_circuit,)], shots=SHOTS)
            pub_result = job.result()[0]
            counts = pub_result.data.output.get_counts()
            
            analisis = extraccion_factores(counts, a, N, CONTROL_QUBITS)
            
            metricas = {
                "optimization_level": opt,
                "transpile_time_s": round(dt, 2),
                "depth_total": depth_total,
                "depth_2q": depth_2q,
                "gates_2q": c2q,
                "total_gates": isa_circuit.size(),
                "signal_pct": analisis["signal_pct"],
                "noise_pct": analisis["noise_pct"],
                "factors_found": analisis["factors"],
                "trivial_factors": analisis["trivial_factors"],
                "periods_found": analisis["periods_found"],
                "success": analisis["success"],
                "note": analisis["note"]
            }
            resultados_a.append(metricas)
            print(f"     [Nivel {opt}] Depth 2Q: {depth_2q} | 2Q Gates: {c2q} | Señal: {metricas['signal_pct']}% | Factores: {metricas['factors_found']}")
            
        todos_los_resultados[f"a={a}"] = resultados_a

    # ─── GUARDA DATOS JSON ────────────────────────
    json_path = os.path.join(DATOS_DIR, "resultados_ideal_faketorino_N15.json")
    with open(json_path, 'w') as f:
        json.dump(todos_los_resultados, f, indent=2, ensure_ascii=False)
    print(f"\nDatos guardados en -> {json_path}")

    # ─── GENERACIÓN DE GRÁFICA COMPARATIVA ────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    colores = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
    
    for i, a in enumerate(BASES):
        datos = todos_los_resultados[f"a={a}"]
        niveles = [d["optimization_level"] for d in datos]
        senales = [d["signal_pct"] for d in datos]
        depths = [d["depth_2q"] for d in datos]
        
        ax1.plot(niveles, senales, marker='o', linewidth=2, color=colores[i], label=f"Base a={a}")
        ax2.plot(niveles, depths, marker='s', linewidth=2, color=colores[i], label=f"Base a={a}")
        
        # Anotaciones
        for x, y in zip(niveles, senales):
            ax1.text(x, y + 2, f"{y}%", ha='center', fontsize=9, color=colores[i])
        for x, y in zip(niveles, depths):
            ax2.text(x, y + (max(depths)*0.02), f"{y}", ha='center', fontsize=9, color=colores[i])

    ax1.set_title("Porcentaje de Señal Ideal vs. Nivel de Optimización", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Nivel de Optimización", fontsize=11)
    ax1.set_ylabel("Señal (%)", fontsize=11)
    ax1.set_ylim(0, 110)
    ax1.set_xticks(OPT_LEVELS)
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()
    
    ax2.set_title("Profundidad 2Q vs. Nivel de Optimización", fontsize=12, fontweight='bold')
    ax2.set_xlabel("Nivel de Optimización", fontsize=11)
    ax2.set_ylabel("Profundidad (Compuertas 2Q)", fontsize=11)
    ax2.set_xticks(OPT_LEVELS)
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend()
    
    plt.suptitle("Análisis Ideal de Shor (N=15) con Topología de FakeTorino", fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    img_path = os.path.join(IMG_DIR, "analisis_ideal_faketorino_N15.png")
    plt.savefig(img_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Gráfica guardada en -> {img_path}")

    # ─── GENERACIÓN DE REPORTE MARKDOWN ───────────
    md_path = os.path.join(REP_DIR, "resultados_ideal_faketorino.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Resultados de Simulación Ideal: Algoritmo de Shor (N=15) en FakeTorino\n\n")
        f.write("> **Objetivo:** Evaluar el impacto de la transpilación (topología de FakeTorino) y los niveles de optimización en la profundidad del circuito y la probabilidad de éxito de señales puras (sin ruido térmico), según la Fase III del anteproyecto.\n\n")
        f.write("## 1. Gráficas Comparativas\n\n")
        f.write("![Señal y Profundidad ideal en FakeTorino](../imagenes/analisis_ideal_faketorino_N15.png)\n\n")
        
        f.write("## 2. Tabla de Métricas por Base (a)\n\n")
        f.write("| Base | Nivel Opt. | Depth 2Q | Compuertas 2Q | Señal (%) | Ruido (%) | Factores Extraídos | Éxito |\n")
        f.write("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")
        
        for a in BASES:
            for d in todos_los_resultados[f"a={a}"]:
                if d["factors_found"]:
                    fatores_str = ", ".join(map(str, d["factors_found"]))
                elif d.get("trivial_factors", False):
                    fatores_str = "Triviales {1, N}"
                else:
                    fatores_str = "Ninguno"
                exito = "✅" if d["success"] else ("⚠️ trivial" if d.get("trivial_factors") else "❌")
                f.write(f"| {a} | {d['optimization_level']} | {d['depth_2q']} | {d['gates_2q']} | {d['signal_pct']} | {d['noise_pct']} | {fatores_str} | {exito} |\n")
        
        f.write("\n## 3. Discusión Técnica\n")
        f.write("- Al tratarse de una **simulación ideal** (sin modelo de decoherencia $T_1/T_2$ o error en compuertas), la fidelidad y la señal (%) deberían mantenerse cercanas al 100% independientemente de la profundidad. Cualquier pérdida se debe a la dispersión intrínseca del QPE.\n")
        f.write("- La simulación sobre la topología de *FakeTorino* sí nos permite contrastar cuántos SWAPs y compuertas `ECR` son introducidas lógicamente por el ruteo hacia la topología Heavy-Hex en comparación a una topología \"todos-con-todos\" subyacente de un simulador genérico.\n")
        f.write(f"- Las bases evaluadas fueron las calculadas teóricamente como óptimas: $a \\in {BASES}$.\n")
        f.write("\n## 4. Nota sobre $a=14$ y factores triviales\n")
        f.write("- Para $a=14 \\equiv -1 \\pmod{15}$, el orden encontrado es $r=2$, lo cual es correcto.\n")
        f.write("- Sin embargo, $\\gcd(14^{2/2} - 1, 15) = \\gcd(13, 15) = 1$ y $\\gcd(14^{2/2} + 1, 15) = \\gcd(15, 15) = 15$.\n")
        f.write("- Ambos resultados son **factores triviales** $\\{1, N\\}$. Esto es una propiedad algebraica intrínseca: cuando $a \\equiv -1 \\pmod{N}$, el algoritmo de Shor siempre produce factores triviales (ver Nielsen \\& Chuang §5.3.2).\n")
        f.write("- La parte cuántica del algoritmo funciona correctamente — el QPE mide las fases $0.0$ y $0.5$ con señal 100%.\n")
        
    print(f"Reporte guardado en -> {md_path}")
    print("\n[✔] Tarea completada exitosamente.")

if __name__ == "__main__":
    run_simulation()
