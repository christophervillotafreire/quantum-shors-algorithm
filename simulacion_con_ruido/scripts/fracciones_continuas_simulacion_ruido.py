"""
fracciones_continuas_ruido.py

Análisis del post-procesamiento clásico de fracciones continuas aplicado
a resultados RUIDOSOS del algoritmo de Shor (N=15). Documenta cómo el ruido
genera fases espúreas que contaminan la extracción de períodos y factores.

Se ejecuta con la mejor configuración de mitigación (DD+PT, opt=3) para
mostrar el post-procesamiento en condiciones realistas.

Referencia: Nielsen & Chuang §5.3 — Continued Fractions & Order Finding.
"""

import os
import sys
import time
import json
import numpy as np
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
OPT_LEVEL = 3
SHOTS = 512  # Reducido: simulación ruidosa ~300x más lenta que ideal
SEED = 457
CONTROL_QUBITS = 9
DIM = 2 ** CONTROL_QUBITS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
REP_DIR = os.path.join(BASE_DIR, "reportes")

for d in [DATOS_DIR, REP_DIR]:
    os.makedirs(d, exist_ok=True)


# ─── FUNCIONES ───────────────────────────────────────────────────────────────

def find_order(a, N):
    val = 1
    for r in range(1, N):
        val = (val * a) % N
        if val == 1:
            return r
    return None


def analizar_medicion(decimal_val, a, N, m):
    """
    Analiza una medición individual del QPE:
    decimal_val → fase → fracción continua → candidato r → factores.
    """
    phase = decimal_val / (2 ** m)
    r_real = find_order(a, N)

    # Fracción continua
    frac = Fraction(phase).limit_denominator(N)
    r_cand = frac.denominator
    s_cand = frac.numerator

    # Verificar si es un período válido
    es_periodo_valido = (1 < r_cand < N and pow(a, r_cand, N) == 1)

    # Verificar si la fase es teóricamente esperada
    fases_esperadas = [s / r_real for s in range(r_real)]
    es_fase_esperada = any(abs(phase - p) < 0.01 for p in fases_esperadas)

    # Factores
    factores = []
    trivial = False
    if es_periodo_valido and r_cand % 2 == 0:
        g1 = gcd(pow(a, r_cand // 2) - 1, N)
        g2 = gcd(pow(a, r_cand // 2) + 1, N)
        if 1 < g1 < N:
            factores.append(g1)
        if 1 < g2 < N:
            factores.append(g2)
        if g1 in (1, N) or g2 in (1, N):
            trivial = True

    return {
        "decimal": decimal_val,
        "bitstring": format(decimal_val, f'0{m}b'),
        "phase": round(phase, 6),
        "fraction": f"{s_cand}/{r_cand}",
        "r_candidate": r_cand,
        "r_real": r_real,
        "es_periodo_valido": es_periodo_valido,
        "es_fase_esperada": es_fase_esperada,
        "factores": factores,
        "trivial": trivial,
        "clasificacion": "señal" if es_fase_esperada else "ruido"
    }

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


def run_analysis():
    print(f"[{time.strftime('%H:%M:%S')}] Fracciones continuas CON RUIDO — Shor N={N}", flush=True)
    print(f"  Configuración: DD+PT, opt={OPT_LEVEL}\n", flush=True)

    fake_torino = FakeTorino()
    noisy_sim = AerSimulator.from_backend(fake_torino)

    # Mejor mitigación: DD + PT
    sampler = SamplerV2(mode=noisy_sim)

    json_path = os.path.join(DATOS_DIR, "fracciones_continuas_ruido_N15.json")
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
        print(f"  BASE a = {a}  |  r = {r}", flush=True)
        print(f"{'='*60}", flush=True)

        circuito = RegisterQC()
        qc = circuito.create_circuit(N, a)
        isa = transpile(qc, backend=fake_torino, optimization_level=OPT_LEVEL,
                        layout_method='sabre', routing_method='sabre', seed_transpiler=SEED)
                        
        isa_mitigado = aplicar_mitigacion(isa, fake_torino, dd_enabled=True, pt_enabled=True)

        job = sampler.run([(isa_mitigado,)], shots=SHOTS)
        counts = job.result()[0].data.output.get_counts()

        # Analizar las mediciones más frecuentes (top 15)
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        total = sum(counts.values())

        mediciones_analizadas = []
        factores_globales = set()
        senial_total = 0
        ruido_total = 0

        for bs, count in sorted_counts[:15]:
            decimal_val = int(bs, 2)
            analisis = analizar_medicion(decimal_val, a, N, CONTROL_QUBITS)
            analisis["count"] = count
            analisis["prob_pct"] = round(100 * count / total, 2)
            mediciones_analizadas.append(analisis)

            if analisis["es_fase_esperada"]:
                senial_total += count
            else:
                ruido_total += count

            for f in analisis["factores"]:
                factores_globales.add(f)

        # Contar señal/ruido total (todas las mediciones)
        r_real = find_order(a, N)
        fases_esperadas = [s / r_real for s in range(r_real)]
        senial_all = sum(
            count for bs, count in counts.items()
            if any(abs(int(bs, 2) / DIM - p) < 0.01 for p in fases_esperadas)
        )

        resultado_a = {
            "base": a,
            "r_real": r,
            "fases_esperadas": [round(s / r, 4) for s in range(r)],
            "mediciones_top15": mediciones_analizadas,
            "pst_total": round(100 * senial_all / total, 2),
            "factores_extraidos": sorted(list(factores_globales)),
            "success": len(factores_globales) >= 2 or (len(factores_globales) == 1 and N % list(factores_globales)[0] == 0)
        }
        todos_resultados[key] = resultado_a

        # Imprimir resumen
        print(f"  PST: {resultado_a['pst_total']:.1f}%", flush=True)
        print(f"  Factores extraídos: {resultado_a['factores_extraidos']}", flush=True)
        print(f"  Top 5 mediciones:", flush=True)
        for m in mediciones_analizadas[:5]:
            print(f"    |{m['bitstring']}⟩ = {m['decimal']:3d}  φ={m['phase']:.4f}  "
                  f"≈{m['fraction']:>5s}  r={m['r_candidate']}  "
                  f"{'✓ señal' if m['clasificacion']=='señal' else '✗ ruido'}  "
                  f"({m['prob_pct']:.1f}%)", flush=True)

        # Guardar incrementalmente
        with open(json_path, 'w') as f:
            json.dump(todos_resultados, f, indent=2, ensure_ascii=False)
        print(f"  Datos guardados incrementalmente -> {json_path}", flush=True)

    # ─── GUARDAR FINAL ───────────────────────────────────────────────────────
    with open(json_path, 'w') as f:
        json.dump(todos_resultados, f, indent=2, ensure_ascii=False)
    print(f"\nDatos guardados en -> {json_path}", flush=True)

    # ─── REPORTE ─────────────────────────────────────────────────────────────
    generar_reporte(todos_resultados)
    print(f"\n[✔] Análisis de fracciones continuas con ruido completado.", flush=True)


def generar_reporte(todos_resultados):
    md_path = os.path.join(REP_DIR, "fracciones_continuas_ruido.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Fracciones Continuas con Ruido: Post-Procesamiento de Shor (N=15)\n\n")
        f.write("> **Objetivo:** Analizar cómo el ruido afecta la extracción de factores "
                "vía fracciones continuas. Se ejecuta con DD+PT (mejor mitigación) para "
                "mostrar el post-procesamiento en condiciones realistas.\n\n")

        f.write("## 1. Configuración\n\n")
        f.write(f"- **Backend:** FakeTorino (ruido activo)\n")
        f.write(f"- **Mitigación:** DD (XpXm) + PT (active)\n")
        f.write(f"- **Opt level:** {OPT_LEVEL}\n")
        f.write(f"- **Shots:** {SHOTS}\n\n")

        f.write("## 2. Método de Fracciones Continuas\n\n")
        f.write("Para cada medición $y$ del QPE:\n")
        f.write("1. Calcular la fase: $\\varphi = y / 2^m$\n")
        f.write("2. Aproximar por fracción continua: $\\varphi \\approx s/r$ con $r < N$\n")
        f.write("3. Verificar: $a^r \\equiv 1 \\pmod{N}$?\n")
        f.write("4. Si $r$ par: $\\gcd(a^{r/2} \\pm 1, N) \\to$ factores\n\n")
        f.write("**Con ruido**, aparecen mediciones espúreas ($y$ que no corresponden a "
                "ninguna fase teórica $s/r$), generando candidatos $r$ falsos.\n\n")

        for a in BASES:
            d = todos_resultados[f"a={a}"]
            r = d["r_real"]
            f.write(f"## 3.{BASES.index(a)+1} Base $a = {a}$ ($r = {r}$)\n\n")
            f.write(f"**Fases esperadas:** {d['fases_esperadas']}\n\n")
            f.write(f"**PST:** {d['pst_total']}% | **Factores:** {d['factores_extraidos']} | "
                    f"**Éxito:** {'✅' if d['success'] else '❌'}\n\n")

            f.write("| # | Bitstring | $y$ | $\\varphi$ | Aprox. | $r$ cand. | Válido | Tipo | Prob. |\n")
            f.write("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")

            for i, m in enumerate(d["mediciones_top15"], 1):
                valido = "✓" if m["es_periodo_valido"] else "✗"
                tipo = "señal" if m["clasificacion"] == "señal" else "**ruido**"
                f.write(f"| {i} | `{m['bitstring']}` | {m['decimal']} | {m['phase']:.4f} "
                        f"| {m['fraction']} | {m['r_candidate']} | {valido} | {tipo} | {m['prob_pct']}% |\n")

            f.write("\n")

            # Interpretación específica
            if a == 14:
                f.write(f"> ⚠️ **Nota:** Para $a=14 \\equiv -1 \\pmod{{15}}$, "
                        f"$r=2$ produce factores triviales $\\{{1, 15\\}}$.\n\n")

        f.write("## 4. Impacto del Ruido en la Extracción de Factores\n\n")
        f.write("- **Fases espúreas:** El ruido genera mediciones en posiciones $y$ que no "
                "corresponden a ningún múltiplo de $2^m/r$, produciendo fracciones continuas "
                "con denominadores incorrectos.\n")
        f.write("- **Candidatos $r$ falsos:** Estas fases espúreas generan candidatos $r$ que "
                "no satisfacen $a^r \\equiv 1 \\pmod{N}$ (filtrados por la verificación clásica).\n")
        f.write("- **Robustez:** A pesar del ruido, si la señal (PST) es suficiente, "
                "los picos teóricos dominan y la extracción de factores sigue siendo exitosa.\n")
        f.write("- **DD+PT ayuda:** La mitigación de errores concentra más probabilidad "
                "en los picos teóricos, mejorando la tasa de éxito de la extracción.\n")

    print(f"Reporte guardado en -> {md_path}", flush=True)


if __name__ == "__main__":
    run_analysis()
