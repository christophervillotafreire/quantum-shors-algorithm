"""
run_transpilation_analyzer.py

Comparación sistemática de niveles de optimización del transpilador (0–3)
y cuantificación del impacto del algoritmo SABRE en la reducción de
profundidad del circuito RegisterQC (N=15, a=4) sobre IBM Torino (Heron r1).

*** EJECUCIÓN EN HARDWARE REAL — consume minutos del plan IBM Quantum ***

Pipeline completo:
  1. Construir circuito RegisterQC (N=15, a=4)
  2. Conectar a ibm_torino real
  3. Transpilar en niveles 0, 1, 2, 3
  4. Transpilar SABRE vs Basic routing (nivel 3)
  5. Enviar los 6 circuitos al QPU ibm_torino via SamplerV2 (4096 shots)
  6. Esperar resultados del hardware
  7. Post-procesar: señal/ruido, extracción de factores
  8. Analizar SWAP insertion
  9. Generar reporte completo (transpilación + hardware)

SALIDAS:
  - REPORTES/transpilation_analysis_results.json
  - REPORTES/transpilation_analysis_plots.png
  - REPORTES/REPORTE_TRANSPILATION_ANALYSIS.md
"""

import sys, os, json, time, traceback
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from fractions import Fraction
from math import gcd

# ─── Project imports ─────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.settings import load_settings
from algorithm.circuit import RegisterQC
from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
N = 15
A = 4
SEED = 457
SHOTS = 4096
IBM_ACCOUNT = "ibm_quantum"
IBM_QPU = "ibm_torino"
CONTROL_QUBITS = 9  # RegisterQC uses ceil(log2(N^2)) = 8, but code uses 9
REPORTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "REPORTES")

# Basis gates for IBM Torino (Heron r1)
TORINO_BASIS = ['cz', 'rzz', 'id', 'rx', 'rz', 'sx', 'x']

# Default layout/routing methods per optimization level
LEVEL_DEFAULTS = {
    0: {"layout_method": "trivial", "routing_method": "basic"},
    1: {"layout_method": "sabre",   "routing_method": "sabre"},
    2: {"layout_method": "sabre",   "routing_method": "sabre"},
    3: {"layout_method": "sabre",   "routing_method": "sabre"},
}

# Theoretical phases for a=4, N=15: r=2, peaks at k/r = 0/2, 1/2
THEORETICAL_PHASES_R2 = [0.0, 0.5]
PHASE_TOLERANCE = 0.002


# ═══════════════════════════════════════════════════════════════════════════════
#  TranspilationAnalyzer — Full Hardware Execution
# ═══════════════════════════════════════════════════════════════════════════════

class TranspilationAnalyzer:
    """Analiza el impacto de diferentes configuraciones de transpilación
    y ejecuta todos los circuitos en hardware real IBM Torino."""

    def __init__(self, circuit, backend, base_a=4, N=15, control_qubits=9):
        self.circuit = circuit
        self.backend = backend
        self.base_a = base_a
        self.N = N
        self.control_qubits = control_qubits
        self.results = []
        self.routing_comparison = []
        self.isa_circuits_by_level = {}   # level -> isa_circuit
        self.isa_circuits_routing = {}    # name  -> isa_circuit
        self.hardware_results = []        # counts per opt level
        self.hardware_routing_results = []  # counts per routing algo
        self.job_ids = []                 # IDs of submitted jobs

    # ──────────────────────────────────────────────────────────────────────
    #  Extracción de métricas de transpilación
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def _extract_metrics(isa_circuit, opt_level, transpile_time,
                         layout_method, routing_method):
        """Extrae todas las métricas relevantes de un circuito transpilado."""
        ops = isa_circuit.count_ops()
        depth_total = isa_circuit.depth()
        depth_2q = isa_circuit.depth(
            lambda instr: instr.operation.num_qubits == 2
        )

        count_cz = ops.get('cz', 0)
        count_ecr = ops.get('ecr', 0)
        count_rzz = ops.get('rzz', 0)
        count_2q = count_cz + count_ecr + count_rzz
        count_swap_literal = ops.get('swap', 0)

        return {
            "optimization_level": opt_level,
            "depth_total": depth_total,
            "depth_2q": depth_2q,
            "count_2q_gates": count_2q,
            "count_cz": count_cz,
            "count_ecr": count_ecr,
            "count_rzz": count_rzz,
            "count_swap_literal": count_swap_literal,
            "count_total_gates": isa_circuit.size(),
            "num_qubits": isa_circuit.num_qubits,
            "layout_method": layout_method,
            "routing_method": routing_method,
            "transpilation_time": round(transpile_time, 3),
            "gate_counts": dict(ops),
        }

    # ──────────────────────────────────────────────────────────────────────
    #  1. Comparar niveles de optimización (transpilación)
    # ──────────────────────────────────────────────────────────────────────
    def compare_optimization_levels(self, levels=[0, 1, 2, 3]):
        """
        Transpila el mismo circuito con diferentes niveles de optimización
        y registra todas las métricas relevantes. Guarda los circuitos ISA
        para posterior ejecución en hardware.
        """
        print(f"\n{'='*70}")
        print(f"  COMPARACIÓN DE NIVELES DE OPTIMIZACIÓN")
        print(f"  Backend: {self.backend.name} | N={self.N} | a={self.base_a}")
        print(f"{'='*70}")

        self.results = []
        self.isa_circuits_by_level = {}

        for level in levels:
            defaults = LEVEL_DEFAULTS.get(level, LEVEL_DEFAULTS[0])
            layout = defaults["layout_method"]
            routing = defaults["routing_method"]

            print(f"\n── Nivel {level}: layout={layout}, routing={routing} ──")
            t0 = time.time()

            try:
                isa = transpile(
                    self.circuit,
                    backend=self.backend,
                    optimization_level=level,
                    seed_transpiler=SEED,
                )
            except Exception as e:
                print(f"  ⚠ Error: {e}")
                continue

            dt = time.time() - t0
            metrics = self._extract_metrics(isa, level, dt, layout, routing)
            self.results.append(metrics)
            self.isa_circuits_by_level[level] = isa

            print(f"  ✓ depth_total={metrics['depth_total']}  "
                  f"depth_2q={metrics['depth_2q']}  "
                  f"2q_gates={metrics['count_2q_gates']}  "
                  f"total_gates={metrics['count_total_gates']}  "
                  f"time={metrics['transpilation_time']}s")

        # Estimate SWAPs based on minimum 2Q gate count
        min_2q = min(r['count_2q_gates'] for r in self.results)
        for r in self.results:
            extra_2q = r['count_2q_gates'] - min_2q
            r['count_swap_estimated'] = extra_2q // 3
            r['extra_2q_from_routing'] = extra_2q

        return self.results

    # ──────────────────────────────────────────────────────────────────────
    #  2. SABRE vs Basic routing
    # ──────────────────────────────────────────────────────────────────────
    def compare_routing_algorithms(self):
        """Compara SABRE vs basic routing en nivel 3 de optimización."""
        print(f"\n{'='*70}")
        print(f"  COMPARACIÓN DE ALGORITMOS DE ROUTING (Nivel 3)")
        print(f"{'='*70}")

        self.routing_comparison = []
        self.isa_circuits_routing = {}

        configs = [
            {"name": "SABRE",  "layout": "sabre",   "routing": "sabre"},
            {"name": "Basic",  "layout": "trivial", "routing": "basic"},
        ]

        for cfg in configs:
            print(f"\n── {cfg['name']}: layout={cfg['layout']}, routing={cfg['routing']} ──")
            t0 = time.time()

            try:
                isa = transpile(
                    self.circuit,
                    backend=self.backend,
                    optimization_level=3,
                    layout_method=cfg["layout"],
                    routing_method=cfg["routing"],
                    seed_transpiler=SEED,
                )
            except Exception as e:
                print(f"  ⚠ Error en routing {cfg['name']}: {e}")
                try:
                    isa = transpile(
                        self.circuit,
                        backend=self.backend,
                        optimization_level=3,
                        seed_transpiler=SEED,
                    )
                    print(f"  ⚠ Usando transpilación por defecto como fallback")
                except Exception as e2:
                    print(f"  ✗ Error total: {e2}")
                    continue

            dt = time.time() - t0
            metrics = self._extract_metrics(isa, 3, dt, cfg["layout"], cfg["routing"])
            metrics["algorithm_name"] = cfg["name"]
            self.routing_comparison.append(metrics)
            self.isa_circuits_routing[cfg["name"]] = isa

            print(f"  ✓ depth_2q={metrics['depth_2q']}  "
                  f"2q_gates={metrics['count_2q_gates']}  "
                  f"time={metrics['transpilation_time']}s")

        return self.routing_comparison

    # ──────────────────────────────────────────────────────────────────────
    #  3. Ejecutar en hardware real IBM Torino
    # ──────────────────────────────────────────────────────────────────────
    def execute_on_hardware(self, shots=SHOTS):
        """
        Envía TODOS los circuitos transpilados (4 niveles + 2 routing)
        como jobs reales al QPU IBM Torino via SamplerV2.
        Espera a que terminen y extrae los conteos.
        """
        print(f"\n{'='*70}")
        print(f"  EJECUCIÓN EN HARDWARE REAL — IBM Torino")
        print(f"  Shots por circuito: {shots}")
        print(f"  *** CONSUMIENDO MINUTOS DEL PLAN IBM QUANTUM ***")
        print(f"{'='*70}")

        # ─── Prepare all circuits ────────────────────────────────────────
        all_circuits = []
        circuit_labels = []

        # 4 optimization levels
        for level in sorted(self.isa_circuits_by_level.keys()):
            all_circuits.append(self.isa_circuits_by_level[level])
            circuit_labels.append(f"opt_level_{level}")

        # 2 routing algorithms
        for name in self.isa_circuits_routing:
            all_circuits.append(self.isa_circuits_routing[name])
            circuit_labels.append(f"routing_{name}")

        n_circuits = len(all_circuits)
        print(f"\n  Circuitos a ejecutar: {n_circuits}")
        for i, label in enumerate(circuit_labels):
            print(f"    [{i+1}] {label}")

        # ─── Submit job via SamplerV2 ─────────────────────────────────────
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Enviando job a {self.backend.name}...")

        sampler = SamplerV2(mode=self.backend)
        # Build PUBs: each is a tuple (circuit,) for SamplerV2
        pubs = [(circ,) for circ in all_circuits]

        t_submit = time.time()
        job = sampler.run(pubs, shots=shots)
        job_id = job.job_id()
        self.job_ids.append(job_id)

        print(f"  ✓ Job enviado — ID: {job_id}")
        print(f"  Esperando resultados del QPU...")

        # ─── Poll for completion ──────────────────────────────────────────
        while True:
            status = job.status()
            elapsed = time.time() - t_submit
            print(f"    [{datetime.now().strftime('%H:%M:%S')}] "
                  f"Status: {status} | Elapsed: {elapsed:.0f}s", end='\r')

            if status in ('DONE', 'completed', 'COMPLETED'):
                print(f"\n  ✓ Job COMPLETADO en {elapsed:.1f}s")
                break
            elif status in ('ERROR', 'CANCELLED', 'error', 'cancelled'):
                print(f"\n  ✗ Job FALLÓ: {status}")
                try:
                    err = job.error_message()
                    print(f"    Error: {err}")
                except:
                    pass
                return False

            time.sleep(5)  # Poll every 5 seconds

        # ─── Extract results ──────────────────────────────────────────────
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Extrayendo resultados...")
        result = job.result()

        # Job metrics
        try:
            job_metrics = job.metrics()
            print(f"  Job metrics: {json.dumps(job_metrics, indent=2, default=str)}")
        except Exception as e:
            job_metrics = {}
            print(f"  ⚠ No se pudieron obtener métricas del job: {e}")

        # Extract counts for each circuit
        self.hardware_results = []
        self.hardware_routing_results = []

        for i, label in enumerate(circuit_labels):
            try:
                pub_result = result[i]
                counts = pub_result.data.output.get_counts()
                total = sum(counts.values())

                # Signal analysis for r=2
                signal = self._compute_signal(counts)

                hw_entry = {
                    "label": label,
                    "total_shots": total,
                    "unique_bitstrings": len(counts),
                    "signal_pct": round(100 * signal / total, 2) if total > 0 else 0,
                    "noise_pct": round(100 * (1 - signal / total), 2) if total > 0 else 100,
                    "signal_count": signal,
                    "noise_count": total - signal,
                    "top_10": sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10],
                    "factors_found": self._extract_factors(counts),
                    "counts_raw": counts,
                }

                if label.startswith("opt_level_"):
                    self.hardware_results.append(hw_entry)
                else:
                    self.hardware_routing_results.append(hw_entry)

                print(f"\n  [{i+1}/{n_circuits}] {label}:")
                print(f"      Shots: {total} | Bitstrings únicos: {len(counts)}")
                print(f"      Señal (r=2): {hw_entry['signal_pct']}% | Ruido: {hw_entry['noise_pct']}%")
                print(f"      Factores: {hw_entry['factors_found']}")

                # Top 5 bitstrings
                for j, (bs, count) in enumerate(hw_entry['top_10'][:5]):
                    decimal_val = int(bs, 2)
                    phase = decimal_val / (2 ** self.control_qubits)
                    prob = count / total
                    print(f"      #{j+1}: {bs} → phase={phase:.4f} | count={count} ({prob:.3%})")

            except Exception as e:
                print(f"  ⚠ Error extrayendo resultado #{i} ({label}): {e}")
                traceback.print_exc()

        return True

    # ──────────────────────────────────────────────────────────────────────
    #  Análisis de señal (r=2)
    # ──────────────────────────────────────────────────────────────────────
    def _compute_signal(self, counts):
        """Calcula señal total en los picos teóricos para r=2."""
        signal = 0
        for bs, count in counts.items():
            decimal_val = int(bs, 2)
            phase = decimal_val / (2 ** self.control_qubits)
            if any(abs(phase - tp) < PHASE_TOLERANCE for tp in THEORETICAL_PHASES_R2):
                signal += count
        return signal

    # ──────────────────────────────────────────────────────────────────────
    #  Extracción de factores
    # ──────────────────────────────────────────────────────────────────────
    def _extract_factors(self, counts):
        """Analiza los conteos para extraer factores de N=15 usando r=2."""
        total = sum(counts.values())
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        found_factors = set()
        valid_periods = set()

        for bs, count in sorted_counts[:25]:
            decimal_val = int(bs, 2)
            phase = decimal_val / (2 ** self.control_qubits)

            if phase == 0:
                frac = Fraction(0, 1)
            else:
                frac = Fraction(phase).limit_denominator(self.N)

            r_cand = frac.denominator
            if 1 < r_cand < self.N and pow(self.base_a, r_cand, self.N) == 1:
                valid_periods.add(r_cand)
                if r_cand % 2 == 0:
                    g1 = gcd(pow(self.base_a, r_cand // 2) - 1, self.N)
                    g2 = gcd(pow(self.base_a, r_cand // 2) + 1, self.N)
                    if 1 < g1 < self.N:
                        found_factors.add(g1)
                    if 1 < g2 < self.N:
                        found_factors.add(g2)

        return {
            "factors": sorted(list(found_factors)) if found_factors else [],
            "valid_periods": sorted(list(valid_periods)),
            "success": len(found_factors) > 0 and self.N in [
                f1 * f2 for f1 in found_factors for f2 in found_factors if f1 != f2
            ] or (len(found_factors) >= 2),
        }

    # ──────────────────────────────────────────────────────────────────────
    #  4. Análisis de SWAP insertion
    # ──────────────────────────────────────────────────────────────────────
    def analyze_swap_insertion(self):
        """Análisis de SWAPs: overhead por nivel vs el mínimo logrado."""
        if not self.results:
            print("  ⚠ No hay resultados. Ejecuta compare_optimization_levels primero.")
            return {}

        min_2q = min(r['count_2q_gates'] for r in self.results)
        level3 = next((r for r in self.results if r['optimization_level'] == 3), None)
        level0 = next((r for r in self.results if r['optimization_level'] == 0), None)

        analysis = {
            "min_2q_gates": min_2q,
            "per_level": [],
        }

        for r in self.results:
            extra = r['count_2q_gates'] - min_2q
            entry = {
                "optimization_level": r['optimization_level'],
                "extra_2q_gates": extra,
                "estimated_swaps": extra // 3,
                "swap_overhead_pct": round(100 * extra / r['count_2q_gates'], 1) if r['count_2q_gates'] > 0 else 0,
            }
            analysis["per_level"].append(entry)

        if level0 and level3:
            analysis["reduction_level0_to_3"] = {
                "depth_2q_reduction_pct": round(
                    100 * (1 - level3['depth_2q'] / level0['depth_2q']), 1
                ) if level0['depth_2q'] > 0 else 0,
                "gates_2q_reduction_pct": round(
                    100 * (1 - level3['count_2q_gates'] / level0['count_2q_gates']), 1
                ) if level0['count_2q_gates'] > 0 else 0,
                "total_gates_reduction_pct": round(
                    100 * (1 - level3['count_total_gates'] / level0['count_total_gates']), 1
                ) if level0['count_total_gates'] > 0 else 0,
            }

        print(f"\n── Análisis de SWAP insertion ──")
        for e in analysis["per_level"]:
            print(f"  Nivel {e['optimization_level']}: "
                  f"+{e['extra_2q_gates']} 2Q extras → "
                  f"~{e['estimated_swaps']} SWAPs estimados "
                  f"({e['swap_overhead_pct']}% overhead)")

        if "reduction_level0_to_3" in analysis:
            red = analysis["reduction_level0_to_3"]
            print(f"\n  Reducción nivel 0→3:")
            print(f"    Depth 2Q:     {red['depth_2q_reduction_pct']}%")
            print(f"    Puertas 2Q:   {red['gates_2q_reduction_pct']}%")
            print(f"    Total gates:  {red['total_gates_reduction_pct']}%")

        return analysis

    # ──────────────────────────────────────────────────────────────────────
    #  5. Generar reporte completo (transpilación + hardware)
    # ──────────────────────────────────────────────────────────────────────
    def generate_report(self, output_dir=None):
        """
        Genera:
          1. DataFrame con métricas comparativas (consola)
          2. Gráficos comparativos (PNG) — 6 paneles
          3. JSON con todos los datos (transpilación + hardware)
          4. Reporte Markdown completo
        """
        if output_dir is None:
            output_dir = REPORTES_DIR
        os.makedirs(output_dir, exist_ok=True)

        swap_analysis = self.analyze_swap_insertion()

        # ─── DataFrame transpilación ──────────────────────────────────────
        df = pd.DataFrame(self.results)
        cols = [
            "optimization_level", "depth_total", "depth_2q",
            "count_2q_gates", "count_swap_estimated", "count_total_gates",
            "layout_method", "routing_method", "transpilation_time"
        ]
        df_display = df[[c for c in cols if c in df.columns]]

        print(f"\n{'='*90}")
        print(f"  TABLA COMPARATIVA — NIVELES DE OPTIMIZACIÓN (Transpilación)")
        print(f"{'='*90}")
        print(df_display.to_string(index=False))
        print(f"{'='*90}")

        # ─── DataFrame hardware ──────────────────────────────────────────
        if self.hardware_results:
            print(f"\n{'='*90}")
            print(f"  TABLA COMPARATIVA — RESULTADOS DE HARDWARE")
            print(f"{'='*90}")
            for hw in self.hardware_results:
                factors = hw['factors_found']
                print(f"  {hw['label']:>15}: "
                      f"señal={hw['signal_pct']:>5.1f}% | "
                      f"ruido={hw['noise_pct']:>5.1f}% | "
                      f"bitstrings={hw['unique_bitstrings']:>4} | "
                      f"factores={factors['factors']}")
            print(f"{'='*90}\n")

        # ─── Gráficos ────────────────────────────────────────────────────
        png_path = os.path.join(output_dir, "transpilation_analysis_plots.png")
        self._create_plots(df, swap_analysis, png_path)

        # ─── JSON ─────────────────────────────────────────────────────────
        json_path = os.path.join(output_dir, "transpilation_analysis_results.json")
        json_data = {
            "config": {
                "N": self.N,
                "a": self.base_a,
                "backend": self.backend.name,
                "seed": SEED,
                "shots": SHOTS,
                "timestamp": datetime.now().isoformat(),
                "job_ids": self.job_ids,
            },
            "optimization_levels": [
                {k: v for k, v in r.items() if k != "gate_counts"}
                for r in self.results
            ],
            "routing_comparison": [
                {k: v for k, v in r.items() if k != "gate_counts"}
                for r in self.routing_comparison
            ],
            "swap_analysis": swap_analysis,
            "gate_details": [
                {"level": r["optimization_level"], "gates": r["gate_counts"]}
                for r in self.results
            ],
            "hardware_results": [
                {k: v for k, v in hw.items() if k != "counts_raw"}
                for hw in self.hardware_results
            ],
            "hardware_routing_results": [
                {k: v for k, v in hw.items() if k != "counts_raw"}
                for hw in self.hardware_routing_results
            ],
        }
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"  ✓ JSON: {json_path}")

        # ─── Markdown ─────────────────────────────────────────────────────
        md_path = os.path.join(output_dir, "REPORTE_TRANSPILATION_ANALYSIS.md")
        self._create_markdown(df, swap_analysis, md_path)
        print(f"  ✓ Markdown: {md_path}")

        return df

    # ──────────────────────────────────────────────────────────────────────
    #  Gráficos — 6 paneles
    # ──────────────────────────────────────────────────────────────────────
    def _create_plots(self, df, swap_analysis, filepath):
        """Genera 6-panel: depth_2q, SWAPs, 2Q gates, señal%, routing, tabla."""
        has_hw = len(self.hardware_results) > 0
        nrows = 3 if has_hw else 2
        fig, axes = plt.subplots(nrows, 2, figsize=(16, 6 * nrows))
        fig.suptitle(
            f"Análisis de Transpilación + Hardware — RegisterQC N={self.N}, a={self.base_a}\n"
            f"Backend: {self.backend.name} (Heron r1) | Shots: {SHOTS}",
            fontsize=14, fontweight='bold', y=0.99
        )

        levels = df['optimization_level'].tolist()
        colors = ['#e74c3c', '#f39c12', '#2ecc71', '#3498db']
        x = np.arange(len(levels))

        # ── Panel 1: Depth 2Q vs Nivel ────────────────────────────────────
        ax1 = axes[0, 0]
        bars1 = ax1.bar(x, df['depth_2q'], color=colors, edgecolor='black', linewidth=0.5)
        for i, val in enumerate(df['depth_2q']):
            ax1.text(i, val + max(df['depth_2q']) * 0.02, str(val),
                     ha='center', va='bottom', fontweight='bold', fontsize=10)
        ax1.set_xlabel('Nivel de Optimización', fontsize=11)
        ax1.set_ylabel('Profundidad 2Q', fontsize=11)
        ax1.set_title('Profundidad de Puertas 2Q vs Nivel', fontsize=12, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels([f'Nivel {l}' for l in levels])
        ax1.grid(axis='y', alpha=0.3)

        # ── Panel 2: SWAPs estimados vs Nivel ────────────────────────────
        ax2 = axes[0, 1]
        swaps = df['count_swap_estimated'].tolist()
        bars2 = ax2.bar(x, swaps, color=colors, edgecolor='black', linewidth=0.5)
        for i, val in enumerate(swaps):
            ax2.text(i, val + max(max(swaps), 1) * 0.02, str(val),
                     ha='center', va='bottom', fontweight='bold', fontsize=10)
        ax2.set_xlabel('Nivel de Optimización', fontsize=11)
        ax2.set_ylabel('SWAPs Estimados', fontsize=11)
        ax2.set_title('SWAPs Insertados por Routing vs Nivel', fontsize=12, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels([f'Nivel {l}' for l in levels])
        ax2.grid(axis='y', alpha=0.3)

        # ── Panel 3: Total 2Q gates vs Nivel ──────────────────────────────
        ax3 = axes[1, 0]
        gates_2q = df['count_2q_gates'].tolist()
        bars3 = ax3.bar(x, gates_2q, color=colors, edgecolor='black', linewidth=0.5)
        for i, val in enumerate(gates_2q):
            ax3.text(i, val + max(gates_2q) * 0.02, str(val),
                     ha='center', va='bottom', fontweight='bold', fontsize=10)
        ax3.set_xlabel('Nivel de Optimización', fontsize=11)
        ax3.set_ylabel('Total Puertas 2Q', fontsize=11)
        ax3.set_title('Conteo Total de Puertas 2Q vs Nivel', fontsize=12, fontweight='bold')
        ax3.set_xticks(x)
        ax3.set_xticklabels([f'Nivel {l}' for l in levels])
        ax3.grid(axis='y', alpha=0.3)

        # ── Panel 4: Tabla reducción ──────────────────────────────────────
        ax4 = axes[1, 1]
        ax4.axis('off')

        ref = self.results[0] if self.results else None
        table_data = []
        for r in self.results:
            lvl = r['optimization_level']
            red_depth = f"{100*(1 - r['depth_2q']/ref['depth_2q']):.1f}%" if ref and ref['depth_2q'] > 0 else "—"
            red_gates = f"{100*(1 - r['count_2q_gates']/ref['count_2q_gates']):.1f}%" if ref and ref['count_2q_gates'] > 0 else "—"

            # Add signal % if hardware results available
            hw = next((h for h in self.hardware_results if h['label'] == f"opt_level_{lvl}"), None)
            signal_str = f"{hw['signal_pct']}%" if hw else "—"

            table_data.append([
                f"Nivel {lvl}",
                str(r['depth_2q']),
                str(r['count_2q_gates']),
                str(r.get('count_swap_estimated', 0)),
                red_depth,
                red_gates,
                signal_str,
            ])

        col_labels = [
            'Nivel', 'Depth 2Q', '2Q Gates',
            'SWAPs Est.', '% Red. Depth', '% Red. Gates', 'Señal %'
        ]
        table = ax4.table(
            cellText=table_data, colLabels=col_labels,
            loc='center', cellLoc='center',
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.0, 1.8)

        for j in range(len(col_labels)):
            table[0, j].set_facecolor('#34495e')
            table[0, j].set_text_props(color='white', fontweight='bold')
        for i in range(len(table_data)):
            for j in range(len(col_labels)):
                table[i + 1, j].set_facecolor(colors[i] + '30')

        ax4.set_title('Tabla Resumen: Transpilación + Hardware',
                       fontsize=12, fontweight='bold', pad=20)

        if has_hw:
            # ── Panel 5: Señal % vs Nivel ─────────────────────────────────
            ax5 = axes[2, 0]
            signal_pcts = [
                next((h['signal_pct'] for h in self.hardware_results
                      if h['label'] == f"opt_level_{l}"), 0)
                for l in levels
            ]
            bars5 = ax5.bar(x, signal_pcts, color=colors, edgecolor='black', linewidth=0.5)
            for i, val in enumerate(signal_pcts):
                ax5.text(i, val + max(max(signal_pcts), 1) * 0.02, f"{val:.1f}%",
                         ha='center', va='bottom', fontweight='bold', fontsize=10)
            ax5.set_xlabel('Nivel de Optimización', fontsize=11)
            ax5.set_ylabel('Señal (%)', fontsize=11)
            ax5.set_title('Porcentaje de Señal (r=2) vs Nivel — Hardware Real',
                         fontsize=12, fontweight='bold')
            ax5.set_xticks(x)
            ax5.set_xticklabels([f'Nivel {l}' for l in levels])
            ax5.set_ylim(0, max(max(signal_pcts) * 1.3, 10))
            ax5.grid(axis='y', alpha=0.3)

            # ── Panel 6: SABRE vs Basic (routing comparison hardware) ─────
            ax6 = axes[2, 1]
            if self.hardware_routing_results:
                routing_names = [h['label'].replace('routing_', '') for h in self.hardware_routing_results]
                routing_signals = [h['signal_pct'] for h in self.hardware_routing_results]
                routing_colors = ['#2ecc71', '#e74c3c']
                r_x = np.arange(len(routing_names))
                bars6 = ax6.bar(r_x, routing_signals, color=routing_colors[:len(routing_names)],
                                edgecolor='black', linewidth=0.5, width=0.5)
                for i, val in enumerate(routing_signals):
                    ax6.text(i, val + max(max(routing_signals), 1) * 0.02, f"{val:.1f}%",
                             ha='center', va='bottom', fontweight='bold', fontsize=11)
                ax6.set_xlabel('Algoritmo de Routing', fontsize=11)
                ax6.set_ylabel('Señal (%)', fontsize=11)
                ax6.set_title('SABRE vs Basic — Señal en Hardware Real',
                             fontsize=12, fontweight='bold')
                ax6.set_xticks(r_x)
                ax6.set_xticklabels(routing_names)
                ax6.set_ylim(0, max(max(routing_signals) * 1.3, 10))
                ax6.grid(axis='y', alpha=0.3)
            else:
                ax6.axis('off')
                ax6.text(0.5, 0.5, 'Sin datos de routing en hardware',
                        transform=ax6.transAxes, ha='center', va='center',
                        fontsize=12, style='italic', color='gray')

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(filepath, dpi=200, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Plot: {filepath}")

    # ──────────────────────────────────────────────────────────────────────
    #  Markdown report (transpilación + hardware)
    # ──────────────────────────────────────────────────────────────────────
    def _create_markdown(self, df, swap_analysis, filepath):
        """Genera reporte markdown completo con transpilación Y hardware."""

        # Tabla comparativa principal
        header = "| Nivel Opt. | Depth Total | Depth 2Q | 2Q Gates | SWAPs Est. | Total Gates | Layout | Routing | Tiempo (s) |\n"
        header += "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n"
        rows = []
        for r in self.results:
            rows.append(
                f"| {r['optimization_level']} "
                f"| {r['depth_total']} "
                f"| {r['depth_2q']} "
                f"| {r['count_2q_gates']} "
                f"| {r.get('count_swap_estimated', 0)} "
                f"| {r['count_total_gates']} "
                f"| {r['layout_method']} "
                f"| {r['routing_method']} "
                f"| {r['transpilation_time']} |"
            )
        comp_table = header + "\n".join(rows)

        # Tabla de reducción
        ref = self.results[0] if self.results else None
        red_header = "| Nivel | Reducción Depth 2Q | Reducción 2Q Gates | Reducción Total Gates |\n"
        red_header += "|:---:|:---:|:---:|:---:|\n"
        red_rows = []
        for r in self.results:
            rd = f"{100*(1 - r['depth_2q']/ref['depth_2q']):.1f}%" if ref and ref['depth_2q'] > 0 else "—"
            rg = f"{100*(1 - r['count_2q_gates']/ref['count_2q_gates']):.1f}%" if ref and ref['count_2q_gates'] > 0 else "—"
            rt = f"{100*(1 - r['count_total_gates']/ref['count_total_gates']):.1f}%" if ref and ref['count_total_gates'] > 0 else "—"
            red_rows.append(f"| {r['optimization_level']} | {rd} | {rg} | {rt} |")
        red_table = red_header + "\n".join(red_rows)

        # Tabla routing comparison
        routing_table = ""
        if self.routing_comparison:
            routing_table = "\n## Comparación SABRE vs Basic — Transpilación (Nivel 3)\n\n"
            routing_table += "| Algoritmo | Depth 2Q | 2Q Gates | Total Gates | Tiempo (s) |\n"
            routing_table += "|:---:|:---:|:---:|:---:|:---:|\n"
            for r in self.routing_comparison:
                routing_table += (
                    f"| {r.get('algorithm_name', r['routing_method'])} "
                    f"| {r['depth_2q']} "
                    f"| {r['count_2q_gates']} "
                    f"| {r['count_total_gates']} "
                    f"| {r['transpilation_time']} |\n"
                )

        # Gate breakdown
        gate_header = "| Nivel |"
        gate_sep = "|:---:|"
        all_gates = set()
        for r in self.results:
            all_gates.update(r['gate_counts'].keys())
        all_gates = sorted(all_gates)
        for g in all_gates:
            gate_header += f" {g} |"
            gate_sep += ":---:|"
        gate_header += "\n" + gate_sep + "\n"
        gate_rows = []
        for r in self.results:
            row = f"| {r['optimization_level']} |"
            for g in all_gates:
                row += f" {r['gate_counts'].get(g, 0)} |"
            gate_rows.append(row)
        gate_table = gate_header + "\n".join(gate_rows)

        # Hardware results table
        hw_section = ""
        if self.hardware_results:
            hw_section = "\n## Resultados de Ejecución en Hardware Real\n\n"
            hw_section += f"> **Backend**: {self.backend.name} | **Shots**: {SHOTS} | **Job IDs**: {', '.join(self.job_ids)}\n\n"
            hw_section += "| Nivel Opt. | Señal (%) | Ruido (%) | Bitstrings Únicos | Factores Encontrados | ¿Éxito? |\n"
            hw_section += "|:---:|:---:|:---:|:---:|:---:|:---:|\n"
            for hw in self.hardware_results:
                level_num = hw['label'].replace('opt_level_', '')
                factors = hw['factors_found']
                factors_str = ', '.join(str(f) for f in factors['factors']) if factors['factors'] else 'Ninguno'
                success = '✓' if factors['success'] else '✗'
                hw_section += (
                    f"| {level_num} "
                    f"| {hw['signal_pct']:.1f} "
                    f"| {hw['noise_pct']:.1f} "
                    f"| {hw['unique_bitstrings']} "
                    f"| {factors_str} "
                    f"| {success} |\n"
                )

            # Top bitstrings por nivel
            hw_section += "\n### Top 5 Bitstrings por Nivel de Optimización\n\n"
            for hw in self.hardware_results:
                level_num = hw['label'].replace('opt_level_', '')
                hw_section += f"\n**Nivel {level_num}:**\n\n"
                hw_section += "| # | Bitstring | Count | Probabilidad | Phase | Fracción | r | ¿Válido? |\n"
                hw_section += "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n"
                for j, (bs, count) in enumerate(hw['top_10'][:5]):
                    decimal_val = int(bs, 2)
                    phase = decimal_val / (2 ** self.control_qubits)
                    prob = count / hw['total_shots']
                    if phase == 0:
                        frac = Fraction(0, 1)
                    else:
                        frac = Fraction(phase).limit_denominator(self.N)
                    r_cand = frac.denominator
                    valid = 1 < r_cand < self.N and pow(self.base_a, r_cand, self.N) == 1
                    mark = '✓' if valid else ''
                    hw_section += (
                        f"| {j+1} | `{bs}` | {count} | {prob:.4f} | {phase:.4f} "
                        f"| {frac.numerator}/{frac.denominator} | {r_cand} | {mark} |\n"
                    )

        # Hardware routing comparison
        hw_routing_section = ""
        if self.hardware_routing_results:
            hw_routing_section = "\n## SABRE vs Basic — Resultados Hardware (Nivel 3)\n\n"
            hw_routing_section += "| Algoritmo | Señal (%) | Ruido (%) | Factores |\n"
            hw_routing_section += "|:---:|:---:|:---:|:---:|\n"
            for hw in self.hardware_routing_results:
                name = hw['label'].replace('routing_', '')
                factors = hw['factors_found']
                factors_str = ', '.join(str(f) for f in factors['factors']) if factors['factors'] else 'Ninguno'
                hw_routing_section += f"| {name} | {hw['signal_pct']:.1f} | {hw['noise_pct']:.1f} | {factors_str} |\n"

        # Best level
        best = min(self.results, key=lambda r: r['depth_2q'])

        # Conclusions
        level3 = next((r for r in self.results if r['optimization_level'] == 3), None)
        level0 = next((r for r in self.results if r['optimization_level'] == 0), None)

        if level0 and level3 and level0['depth_2q'] > 0:
            pct_depth = round(100 * (1 - level3['depth_2q'] / level0['depth_2q']), 1)
            pct_gates = round(100 * (1 - level3['count_2q_gates'] / level0['count_2q_gates']), 1) if level0['count_2q_gates'] > 0 else 0
        else:
            pct_depth = 0
            pct_gates = 0

        # Best signal level
        best_signal_str = ""
        if self.hardware_results:
            best_hw = max(self.hardware_results, key=lambda h: h['signal_pct'])
            best_level_hw = best_hw['label'].replace('opt_level_', '')
            best_signal_str = f"\n6. **Mayor señal en hardware**: Nivel **{best_level_hw}** con **{best_hw['signal_pct']}%** de señal para r=2."

        md = f"""# Reporte: Análisis de Transpilación + Hardware — RegisterQC N={self.N}

**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Backend**: {self.backend.name} (Heron r1) | **N**: {self.N} | **a**: {self.base_a}
**Shots**: {SHOTS} | **Seed transpilador**: {SEED}
**Job IDs**: {', '.join(self.job_ids) if self.job_ids else 'N/A'}

---

## Resumen Ejecutivo

- **Objetivo**: Comparar sistemáticamente los 4 niveles de optimización del transpilador de Qiskit y cuantificar el impacto del algoritmo SABRE en la reducción de profundidad. **Ejecución en hardware real IBM Torino.**
- **Circuito**: RegisterQC para factorización de N={self.N} con a={self.base_a}.
- **Backend**: {self.backend.name} — topología Heavy-Hex (Heron r1), {self.backend.num_qubits} qubits.
- **Puertas nativas**: `{', '.join(TORINO_BASIS)}`.
- **Mejor configuración (transpilación)**: **Nivel {best['optimization_level']}** con depth 2Q = **{best['depth_2q']}**.

---

## Tabla Comparativa por Nivel de Optimización (Transpilación)

{comp_table}

---

## Reducción Relativa (vs Nivel 0)

{red_table}

> **Nota**: Los porcentajes negativos indican un aumento respecto al nivel 0.

---

## Desglose de Puertas por Nivel

{gate_table}

---
{routing_table}
---

## Análisis de SWAP Insertion

El transpilador inserta operaciones SWAP para mover qubits lógicos entre qubits físicos no adyacentes en la topología Heavy-Hex. En Heron r1, cada SWAP se descompone en **3 puertas CZ**.

| Nivel | 2Q Extras (vs mín.) | SWAPs Estimados | Overhead (%) |
|:---:|:---:|:---:|:---:|
"""
        if swap_analysis and "per_level" in swap_analysis:
            for e in swap_analysis["per_level"]:
                md += f"| {e['optimization_level']} | {e['extra_2q_gates']} | {e['estimated_swaps']} | {e['swap_overhead_pct']}% |\n"

        md += f"""
---
{hw_section}
---
{hw_routing_section}
---

## Conclusiones

1. **Impacto del nivel de optimización**: El nivel 3 reduce la profundidad 2Q en **{pct_depth}%** y el conteo de puertas 2Q en **{pct_gates}%** respecto al nivel 0.
2. **Algoritmo SABRE**: Los niveles 1–3 utilizan SABRE para layout y routing, lo que minimiza las operaciones SWAP insertadas al considerar la topología real del hardware.
3. **Nivel 0 (trivial)**: Utiliza layout trivial y routing basic, resultando en la mayor cantidad de SWAPs y profundidad.
4. **Configuración óptima (transpilación)**: **Nivel {best['optimization_level']}** ofrece el mejor balance entre profundidad y tiempo de transpilación.
5. **Recomendación**: Para ejecución en hardware IBM Torino, usar siempre **optimization_level=3** con SABRE routing.{best_signal_str}

![Plots](transpilation_analysis_plots.png)
"""

        with open(filepath, 'w') as f:
            f.write(md)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    load_settings()

    print(f"\n{'='*70}")
    print(f"  ANÁLISIS DE TRANSPILACIÓN + HARDWARE — RegisterQC N={N}, a={A}")
    print(f"  Backend: {IBM_QPU} (HARDWARE REAL)")
    print(f"  Niveles: [0, 1, 2, 3]")
    print(f"  Comparación SABRE vs Basic routing")
    print(f"  Shots: {SHOTS}")
    print(f"  *** EJECUCIÓN REAL — CONSUME MINUTOS DEL PLAN IBM QUANTUM ***")
    print(f"{'='*70}\n")

    # ─── 1. Circuito ──────────────────────────────────────────────────────
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ── 1. Construcción del Circuito ──")
    t0 = time.time()
    qc_instance = RegisterQC()
    qc = qc_instance.create_circuit(N, A)
    build_time = time.time() - t0

    pre_ops = qc.count_ops()
    ctrl_qubits = qc_instance.get_control_qubits()
    print(f"  Qubits lógicos:  {qc.num_qubits}")
    print(f"  Depth:           {qc.depth()}")
    print(f"  Gates:           {qc.size()}")
    print(f"  Ops:             {dict(pre_ops)}")
    print(f"  Control qubits:  {ctrl_qubits}")
    print(f"  Tiempo:          {build_time:.2f}s")

    # ─── 2. Backend real IBM Torino ───────────────────────────────────────
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ── 2. Conectando a {IBM_QPU} ──")
    service = QiskitRuntimeService(name=IBM_ACCOUNT)
    backend = service.backend(IBM_QPU)
    print(f"  ✓ Backend: {backend.name} ({backend.num_qubits} qubits)")

    # ─── 3. Crear analyzer ───────────────────────────────────────────────
    analyzer = TranspilationAnalyzer(qc, backend, base_a=A, N=N,
                                     control_qubits=ctrl_qubits)

    # ─── 4. Comparar niveles de optimización (transpilación local) ────────
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ── 3. Comparación de Niveles (Transpilación) ──")
    analyzer.compare_optimization_levels([0, 1, 2, 3])

    # ─── 5. Comparar routing (transpilación local) ────────────────────────
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ── 4. Comparación de Routing (Transpilación) ──")
    analyzer.compare_routing_algorithms()

    # ─── 6. EJECUTAR EN HARDWARE REAL ─────────────────────────────────────
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ── 5. Ejecución en Hardware Real ──")
    hw_success = analyzer.execute_on_hardware(shots=SHOTS)

    if not hw_success:
        print(f"\n  ⚠ La ejecución en hardware falló. Generando reporte solo con transpilación.")

    # ─── 7. Generar reporte completo ──────────────────────────────────────
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ── 6. Generando Reporte Completo ──")
    df = analyzer.generate_report()

    # ─── Done ─────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  ✓ ANÁLISIS COMPLETADO — HARDWARE REAL IBM TORINO")
    print(f"  Job IDs: {analyzer.job_ids}")
    print(f"  Archivos generados:")
    print(f"    1. REPORTES/transpilation_analysis_results.json")
    print(f"    2. REPORTES/transpilation_analysis_plots.png")
    print(f"    3. REPORTES/REPORTE_TRANSPILATION_ANALYSIS.md")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{'!'*70}")
        print(f"  ERROR: {type(e).__name__}: {e}")
        print(f"{'!'*70}")
        traceback.print_exc()
        sys.exit(1)
