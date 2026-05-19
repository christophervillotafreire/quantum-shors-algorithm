"""
═══════════════════════════════════════════════════════════════════════════════
Estudio Exhaustivo — Shor N=15 (RegisterQC) — Alineado con Objetivos del TG
═══════════════════════════════════════════════════════════════════════════════
Fases:
  1. Simulación Ideal (AerSimulator, sin ruido)
  2. Simulación Ruidosa (FakeKyiv, Eagle r3)
  3. Hardware Real (ibm_torino, Heron r1) — si hay créditos

Objetivos del TG cubiertos:
  OE1: Transpilación (opt_level, layout, routing, approx_degree)
  OE2: Pre-cómputo clásico de bases `a` (6 coprimas)
  OE3: Mitigación de errores (DD + PT) en Fake Backends y hardware real
  OE4: Cuantificar degradación señal ideal → ruidosa → real

Uso:
  python run_study_batch.py                    # Fases 1+2 (local, sin créditos)
  python run_study_batch.py --include-hardware # Fases 1+2+3 (requiere IBM creds)
"""
import sys, os, json, time, gc, copy, argparse
import numpy as np
from datetime import datetime
from math import gcd
from fractions import Fraction

sys.path.insert(0, '.')
from common.settings import load_settings, get_settings_value_for_key
from algorithm.circuit import RegisterQC

from qiskit_ibm_runtime import fake_provider
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2 as AerSamplerV2

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
N = 15
SEED = 457
IDEAL_SHOTS = 4096
NOISY_SHOTS = 1024
HARDWARE_SHOTS = 4096

# Config base (óptima conocida)
BASE_CONFIG = {
    'a': 4, 'opt_level': 3, 'approx_degree': 0.7,
    'layout_method': 'sabre', 'routing_method': 'sabre',
    'pt_enable_gates': True, 'pt_enable_measure': False,
    'dd_enable': False, 'dd_sequence': 'XY4',
}

# Theoretical expected results for N=15
VALID_BASES = [2, 4, 7, 8, 11, 13]
EXPECTED_ORDERS = {2: 4, 4: 2, 7: 4, 8: 4, 11: 2, 13: 4}
EXPECTED_FACTORS = (3, 5)

OUTPUT_DIR = "outputs/study_results"
PLOTS_DIR = f"{OUTPUT_DIR}/plots"

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)


def create_circuit(a):
    """Create RegisterQC circuit for N=15 with given base a."""
    circuit_obj = RegisterQC()
    qc = circuit_obj.create_circuit(N, a)
    control_qubits = circuit_obj.get_control_qubits()
    target_qubits = circuit_obj.target_qubits
    return qc, control_qubits, target_qubits


def transpile_circuit(qc, backend, opt_level=3, approx_degree=0.7,
                      layout_method='sabre', routing_method='sabre'):
    """Transpile circuit to target backend."""
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=opt_level,
        seed_transpiler=SEED,
        layout_method=layout_method,
        routing_method=routing_method,
        approximation_degree=approx_degree,
    )
    isa = pm.run(qc)
    return isa


def get_isa_stats(isa):
    """Get transpiled circuit statistics."""
    ops = isa.count_ops()
    return {
        'total_gates': isa.size(),
        'depth': isa.depth(),
        'depth_2q': isa.depth(lambda x: x.operation.num_qubits == 2),
        'num_qubits': isa.num_qubits,
        'ecr': ops.get('ecr', 0),
        'cz': ops.get('cz', 0),
        'rz': ops.get('rz', 0),
        'sx': ops.get('sx', 0),
        'x': ops.get('x', 0),
        'rx': ops.get('rx', 0),
        '2q_gates': ops.get('ecr', 0) + ops.get('cz', 0),
    }


def run_ideal_simulation(isa, shots=IDEAL_SHOTS):
    """Run ideal (noiseless) simulation on AerSimulator."""
    sampler = AerSamplerV2()
    job = sampler.run([isa], shots=shots)
    result = job.result()
    counts = dict(result[0].data.output.get_counts())
    return counts


def run_noisy_simulation(isa, fake_backend, shots=NOISY_SHOTS):
    """Run noisy simulation using FakeKyiv noise model."""
    noisy_be = AerSimulator.from_backend(fake_backend, method='automatic')
    noisy_sampler = AerSamplerV2.from_backend(noisy_be)
    job = noisy_sampler.run([isa], shots=shots)
    result = job.result()
    counts = dict(result[0].data.output.get_counts())
    return counts


def analyze_signal(counts, control_qubits, a):
    """Analyze signal: compute PST, extract factors via continued fractions."""
    total = sum(counts.values())
    r_expected = EXPECTED_ORDERS[a]
    n_peaks = r_expected
    peaks = [int(2**control_qubits / n_peaks * i) for i in range(n_peaks)]

    # Signal = sum of counts at theoretical peaks
    signal_counts = 0
    peak_details = []
    for pk in peaks:
        bs = format(pk, f'0{control_qubits}b')
        cnt = counts.get(bs, 0)
        signal_counts += cnt
        peak_details.append({
            'peak_decimal': pk, 'bitstring': bs,
            'count': cnt, 'expected_prob': round(1/n_peaks, 4),
            'observed_prob': round(cnt/total, 4) if total > 0 else 0
        })

    signal_pct = round(signal_counts / total * 100, 2) if total > 0 else 0
    noise_pct = round(100 - signal_pct, 2)

    # Continued fractions for factor extraction
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    candidates_r = []
    for bs, c in sorted_counts[:10]:
        d = int(bs, 2)
        phase = d / 2**control_qubits
        frac = Fraction(phase).limit_denominator(N)
        r = frac.denominator
        valid = N > r > 1 and pow(a, r, N) == 1
        if valid and r not in candidates_r:
            candidates_r.append(r)

    # Extract factors
    factors = None
    r_used = None
    for r in sorted(candidates_r):
        if r % 2:
            continue
        p = gcd(a**(r//2) - 1, N)
        q = gcd(a**(r//2) + 1, N)
        if p not in [1, N] and q not in [1, N] and p * q == N:
            factors = (p, q)
            r_used = r
            break

    # Fidelity (classical Bhattacharyya coefficient)
    # Ideal distribution: uniform over r peaks
    ideal_dist = np.zeros(2**control_qubits)
    for pk in peaks:
        ideal_dist[pk] = 1.0 / n_peaks
    obs_dist = np.zeros(2**control_qubits)
    for bs, c in counts.items():
        obs_dist[int(bs, 2)] = c / total
    fidelity = float(np.sum(np.sqrt(ideal_dist * obs_dist))**2)

    return {
        'signal_pct': signal_pct,
        'noise_pct': noise_pct,
        'fidelity': round(fidelity, 4),
        'r_expected': r_expected,
        'r_found': r_used,
        'candidates_r': candidates_r,
        'factors': list(factors) if factors else None,
        'factors_correct': factors is not None and set(factors) == set(EXPECTED_FACTORS),
        'peak_details': peak_details,
        'total_shots': total,
        'unique_outcomes': len(counts),
    }


def run_single_config(config, fake_backend, run_noisy=True):
    """Run one configuration: create circuit, transpile, simulate ideal+noisy."""
    a = config['a']
    log(f"  Config: a={a}, opt={config['opt_level']}, approx={config['approx_degree']}, "
        f"layout={config['layout_method']}, routing={config['routing_method']}, "
        f"PT={'ON' if config['pt_enable_gates'] else 'OFF'}, "
        f"DD={'ON' if config['dd_enable'] else 'OFF'}")

    # 1. Create circuit
    qc, cq, tq = create_circuit(a)

    # 2. Transpile to FakeKyiv topology
    t0 = time.time()
    isa = transpile_circuit(
        qc, fake_backend,
        opt_level=config['opt_level'],
        approx_degree=config['approx_degree'],
        layout_method=config['layout_method'],
        routing_method=config['routing_method'],
    )
    transpile_time = time.time() - t0

    # 3. ISA stats
    stats = get_isa_stats(isa)

    # 4. Ideal simulation
    t0 = time.time()
    ideal_counts = run_ideal_simulation(isa, shots=IDEAL_SHOTS)
    ideal_time = time.time() - t0
    ideal_analysis = analyze_signal(ideal_counts, cq, a)

    result = {
        'config': config.copy(),
        'N': N,
        'control_qubits': cq,
        'target_qubits': tq,
        'total_qubits': qc.num_qubits,
        'transpile_time_s': round(transpile_time, 2),
        'isa_stats': stats,
        'ideal': {
            'time_s': round(ideal_time, 2),
            'shots': IDEAL_SHOTS,
            **ideal_analysis,
        },
    }

    # 5. Noisy simulation (optional)
    if run_noisy:
        t0 = time.time()
        noisy_counts = run_noisy_simulation(isa, fake_backend, shots=NOISY_SHOTS)
        noisy_time = time.time() - t0
        noisy_analysis = analyze_signal(noisy_counts, cq, a)
        result['noisy_fakekyiv'] = {
            'time_s': round(noisy_time, 2),
            'shots': NOISY_SHOTS,
            **noisy_analysis,
        }

    gc.collect()
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# STUDY DEFINITIONS (alineados con Objetivos del TG)
# ═══════════════════════════════════════════════════════════════════════════════
def get_study_configs():
    """Return all study configurations grouped by study name."""
    studies = {}

    # A1: approximation_degree sweep (OE1 + OE4)
    studies['A1_approx_degree'] = []
    for ad in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        cfg = BASE_CONFIG.copy()
        cfg['approx_degree'] = ad
        cfg['study'] = 'A1_approx_degree'
        cfg['study_variable'] = 'approx_degree'
        cfg['study_value'] = ad
        studies['A1_approx_degree'].append(cfg)

    # A2: optimization_level sweep (OE1)
    studies['A2_opt_level'] = []
    for ol in [0, 1, 2, 3]:
        cfg = BASE_CONFIG.copy()
        cfg['opt_level'] = ol
        # opt_level 0 defaults to trivial/basic
        if ol == 0:
            cfg['layout_method'] = 'trivial'
            cfg['routing_method'] = 'basic'
        cfg['study'] = 'A2_opt_level'
        cfg['study_variable'] = 'opt_level'
        cfg['study_value'] = ol
        studies['A2_opt_level'].append(cfg)

    # A3: Bases a sweep (OE2)
    studies['A3_bases'] = []
    for a in VALID_BASES:
        cfg = BASE_CONFIG.copy()
        cfg['a'] = a
        cfg['study'] = 'A3_bases'
        cfg['study_variable'] = 'a'
        cfg['study_value'] = a
        studies['A3_bases'].append(cfg)

    # A3_ref: Bases with approx=1.0 reference (OE2 + OE4)
    studies['A3_ref_no_approx'] = []
    for a in VALID_BASES:
        cfg = BASE_CONFIG.copy()
        cfg['a'] = a
        cfg['approx_degree'] = 1.0
        cfg['study'] = 'A3_ref_no_approx'
        cfg['study_variable'] = 'a'
        cfg['study_value'] = a
        studies['A3_ref_no_approx'].append(cfg)

    # A4: layout_method sweep (OE1)
    studies['A4_layout'] = []
    for lm in ['trivial', 'dense', 'sabre']:
        cfg = BASE_CONFIG.copy()
        cfg['layout_method'] = lm
        cfg['study'] = 'A4_layout'
        cfg['study_variable'] = 'layout_method'
        cfg['study_value'] = lm
        studies['A4_layout'].append(cfg)

    # A5: routing_method sweep (OE1)
    studies['A5_routing'] = []
    for rm in ['basic', 'sabre', 'stochastic']:
        cfg = BASE_CONFIG.copy()
        cfg['routing_method'] = rm
        cfg['study'] = 'A5_routing'
        cfg['study_variable'] = 'routing_method'
        cfg['study_value'] = rm
        studies['A5_routing'].append(cfg)

    # A6_A7: DD/PT mitigation combinations (OE3)
    studies['A6_A7_mitigation'] = []
    mitigation_combos = [
        {'pt_enable_gates': False, 'dd_enable': False, 'label': 'Sin mitigación'},
        {'pt_enable_gates': True,  'dd_enable': False, 'label': 'Solo PT'},
        {'pt_enable_gates': False, 'dd_enable': True,  'label': 'Solo DD (XY4)'},
        {'pt_enable_gates': True,  'dd_enable': True,  'label': 'PT + DD (XY4)'},
    ]
    for combo in mitigation_combos:
        cfg = BASE_CONFIG.copy()
        cfg['pt_enable_gates'] = combo['pt_enable_gates']
        cfg['dd_enable'] = combo['dd_enable']
        cfg['dd_sequence'] = 'XY4'
        cfg['study'] = 'A6_A7_mitigation'
        cfg['study_variable'] = 'mitigation'
        cfg['study_value'] = combo['label']
        studies['A6_A7_mitigation'].append(cfg)

    return studies


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 & 2: Local simulations
# ═══════════════════════════════════════════════════════════════════════════════
def run_local_studies():
    """Execute all ideal + FakeKyiv noisy simulations."""
    log("═══ FASE 1+2: Simulaciones Ideales + Ruidosas (FakeKyiv) ═══")

    # Initialize FakeKyiv
    log("Inicializando FakeKyiv backend...")
    fake_be = fake_provider.FakeKyiv()
    log(f"  FakeKyiv: {fake_be.num_qubits} qubits, Eagle r3")

    studies = get_study_configs()
    all_results = {}

    total_configs = sum(len(cfgs) for cfgs in studies.values())
    log(f"Total configuraciones a ejecutar: {total_configs}")

    config_num = 0
    for study_name, configs in studies.items():
        log(f"\n{'─'*60}")
        log(f"Estudio: {study_name} ({len(configs)} configs)")
        log(f"{'─'*60}")
        study_results = []

        for cfg in configs:
            config_num += 1
            log(f"\n[{config_num}/{total_configs}] Ejecutando...")
            try:
                result = run_single_config(cfg, fake_be, run_noisy=True)
                study_results.append(result)

                # Quick summary
                ideal_sig = result['ideal']['signal_pct']
                noisy_sig = result.get('noisy_fakekyiv', {}).get('signal_pct', 'N/A')
                depth_2q = result['isa_stats']['depth_2q']
                log(f"  ✓ depth_2q={depth_2q}, ideal_signal={ideal_sig}%, "
                    f"noisy_signal={noisy_sig}%")
            except Exception as e:
                log(f"  ✗ ERROR: {e}")
                study_results.append({
                    'config': cfg.copy(), 'error': str(e)
                })

        all_results[study_name] = study_results

    return all_results


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Hardware Real (ibm_torino)
# ═══════════════════════════════════════════════════════════════════════════════
def run_hardware_studies():
    """Execute selected configs on ibm_torino hardware via main.py framework."""
    log("═══ FASE 3: Hardware Real — IBM Torino ═══")

    import configparser

    base_ini_path = os.path.join(os.path.dirname(__file__),
                                 'config_torino_v1_a4.ini')

    if not os.path.exists(base_ini_path):
        log(f"✗ No se encontró {base_ini_path}, saltando Fase 3")
        return {}

    # Define hardware configs to run
    hw_configs = []

    # A2: opt_level on hardware (opt=0,1,2 — opt=3 already exists)
    for ol in [0, 1, 2]:
        hw_configs.append({
            'name': f'A2_opt{ol}_hw',
            'study': 'A2_opt_level_hw',
            'overrides': {
                'transpiler_optimization_level': str(ol),
                'transpiler_layout_method': 'trivial' if ol == 0 else 'sabre',
                'transpiler_routing_method': 'basic' if ol == 0 else 'sabre',
            }
        })

    # A3: bases on hardware (a=2,8,11,13 — a=4,7 already exist)
    for a in [2, 8, 11, 13]:
        hw_configs.append({
            'name': f'A3_a{a}_hw',
            'study': 'A3_bases_hw',
            'overrides': {
                'random_a': str(a),
            }
        })

    # A6/A7: mitigation on hardware
    mitigation_hw = [
        {'name': 'A7_no_mitigation_hw', 'study': 'A6_A7_mitigation_hw',
         'overrides': {
             'sampler_pt_enable_gates': 'false',
             'sampler_pt_enable_measure': 'false',
             'sampler_dynamical_decoupling': 'false',
         }},
        {'name': 'A7_pt_only_hw', 'study': 'A6_A7_mitigation_hw',
         'overrides': {
             'sampler_pt_enable_gates': 'true',
             'sampler_pt_enable_measure': 'false',
             'sampler_dynamical_decoupling': 'false',
         }},
        {'name': 'A6_dd_only_hw', 'study': 'A6_A7_mitigation_hw',
         'overrides': {
             'sampler_pt_enable_gates': 'false',
             'sampler_pt_enable_measure': 'false',
             'sampler_dynamical_decoupling': 'true',
             'sampler_dd_sequence_type': 'XY4',
         }},
        {'name': 'A7_pt_dd_hw', 'study': 'A6_A7_mitigation_hw',
         'overrides': {
             'sampler_pt_enable_gates': 'true',
             'sampler_pt_enable_measure': 'false',
             'sampler_dynamical_decoupling': 'true',
             'sampler_dd_sequence_type': 'XY4',
         }},
    ]
    hw_configs.extend(mitigation_hw)

    log(f"Total configs hardware: {len(hw_configs)}")
    log(f"Estimación QPU: ~{len(hw_configs) * 3}s quantum time")

    # Generate config files and run via main.py
    hw_results = {}
    config_dir = os.path.join(OUTPUT_DIR, 'hw_configs')
    os.makedirs(config_dir, exist_ok=True)

    for i, hw_cfg in enumerate(hw_configs):
        log(f"\n[{i+1}/{len(hw_configs)}] {hw_cfg['name']}")

        # Read base config
        config = configparser.ConfigParser()
        config.read(base_ini_path)

        # Apply overrides
        for key, val in hw_cfg['overrides'].items():
            for section in config.sections():
                if config.has_option(section, key):
                    config.set(section, key, val)
                    break
            else:
                # Key not found in any section, add to general
                if key.startswith('transpiler'):
                    config.set('transpiler', key, val)
                elif key.startswith('sampler'):
                    config.set('sampler', key, val)
                else:
                    config.set('general', key, val)

        # Write config file
        cfg_path = os.path.join(config_dir, f'{hw_cfg["name"]}.ini')
        with open(cfg_path, 'w') as f:
            config.write(f)

        log(f"  Config guardada en: {cfg_path}")
        log(f"  Ejecutando: python main.py --config {cfg_path}")

        # Run via main.py framework
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, 'main.py', '--config', cfg_path],
                capture_output=True, text=True, timeout=300,
                cwd=os.path.dirname(__file__)
            )
            if result.returncode == 0:
                log(f"  ✓ Job enviado exitosamente")
            else:
                log(f"  ✗ Error: {result.stderr[-500:]}")
            hw_results[hw_cfg['name']] = {
                'study': hw_cfg['study'],
                'config_path': cfg_path,
                'overrides': hw_cfg['overrides'],
                'returncode': result.returncode,
                'stdout_tail': result.stdout[-1000:] if result.stdout else '',
                'stderr_tail': result.stderr[-500:] if result.stderr else '',
            }
        except subprocess.TimeoutExpired:
            log(f"  ✗ Timeout (>300s)")
            hw_results[hw_cfg['name']] = {
                'study': hw_cfg['study'],
                'error': 'timeout'
            }
        except Exception as e:
            log(f"  ✗ Error: {e}")
            hw_results[hw_cfg['name']] = {
                'study': hw_cfg['study'],
                'error': str(e)
            }

    return hw_results


# ═══════════════════════════════════════════════════════════════════════════════
# PLOTS
# ═══════════════════════════════════════════════════════════════════════════════
def generate_plots(all_results):
    """Generate all comparative plots for the study."""
    log("\n═══ Generando gráficos comparativos ═══")

    plt.rcParams.update({
        'font.size': 11, 'font.family': 'sans-serif',
        'axes.titlesize': 13, 'axes.labelsize': 11,
        'figure.dpi': 150, 'savefig.dpi': 150,
        'figure.facecolor': 'white',
    })

    # ── Plot 1: Signal% vs approx_degree (OE1 + OE4) ──
    if 'A1_approx_degree' in all_results:
        fig, ax = plt.subplots(figsize=(10, 6))
        data = [r for r in all_results['A1_approx_degree'] if 'error' not in r]
        x = [r['config']['approx_degree'] for r in data]
        y_ideal = [r['ideal']['signal_pct'] for r in data]
        y_noisy = [r['noisy_fakekyiv']['signal_pct'] for r in data]

        ax.plot(x, y_ideal, 'o-', color='#2196F3', linewidth=2, markersize=8,
                label='Ideal (AerSimulator)', zorder=5)
        ax.plot(x, y_noisy, 's-', color='#FF5722', linewidth=2, markersize=8,
                label='FakeKyiv (Ruidoso)', zorder=5)
        ax.set_xlabel('Approximation Degree')
        ax.set_ylabel('Señal (%)')
        ax.set_title('Señal vs Grado de Aproximación — Shor N=15, a=4\n(OE1: Impacto de transpilación)')
        ax.legend(framealpha=0.9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/01_signal_vs_approx_degree.png")
        plt.close()
        log("  ✓ 01_signal_vs_approx_degree.png")

    # ── Plot 2: Depth 2Q vs approx_degree ──
    if 'A1_approx_degree' in all_results:
        fig, ax = plt.subplots(figsize=(10, 6))
        data = [r for r in all_results['A1_approx_degree'] if 'error' not in r]
        x = [r['config']['approx_degree'] for r in data]
        y_depth = [r['isa_stats']['depth_2q'] for r in data]

        ax.bar(x, y_depth, width=0.07, color='#4CAF50', edgecolor='#2E7D32', alpha=0.85)
        ax.set_xlabel('Approximation Degree')
        ax.set_ylabel('Profundidad 2Q (depth_2q)')
        ax.set_title('Profundidad del Circuito vs Grado de Aproximación — Shor N=15, a=4\n(OE1: Costo de transpilación)')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/02_depth2q_vs_approx_degree.png")
        plt.close()
        log("  ✓ 02_depth2q_vs_approx_degree.png")

    # ── Plot 3: Signal% vs opt_level (OE1) ──
    if 'A2_opt_level' in all_results:
        fig, ax = plt.subplots(figsize=(10, 6))
        data = [r for r in all_results['A2_opt_level'] if 'error' not in r]
        x = [r['config']['opt_level'] for r in data]
        y_ideal = [r['ideal']['signal_pct'] for r in data]
        y_noisy = [r['noisy_fakekyiv']['signal_pct'] for r in data]

        bar_w = 0.35
        x_pos = np.arange(len(x))
        ax.bar(x_pos - bar_w/2, y_ideal, bar_w, label='Ideal', color='#2196F3',
               edgecolor='#1565C0', alpha=0.85)
        ax.bar(x_pos + bar_w/2, y_noisy, bar_w, label='FakeKyiv',
               color='#FF5722', edgecolor='#BF360C', alpha=0.85)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([f'Opt {v}' for v in x])
        ax.set_ylabel('Señal (%)')
        ax.set_title('Señal vs Nivel de Optimización — Shor N=15, a=4\n(OE1: SABRE vs Trivial)')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 105)
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/03_signal_vs_opt_level.png")
        plt.close()
        log("  ✓ 03_signal_vs_opt_level.png")

    # ── Plot 4: Depth 2Q vs opt_level ──
    if 'A2_opt_level' in all_results:
        fig, ax = plt.subplots(figsize=(10, 6))
        data = [r for r in all_results['A2_opt_level'] if 'error' not in r]
        x = [r['config']['opt_level'] for r in data]
        y = [r['isa_stats']['depth_2q'] for r in data]

        colors = ['#ef5350', '#FFA726', '#66BB6A', '#42A5F5']
        ax.bar(range(len(x)), y, color=colors, edgecolor='#333', alpha=0.85)
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels([f'Opt {v}' for v in x])
        ax.set_ylabel('Profundidad 2Q')
        ax.set_title('Profundidad 2Q vs Nivel de Optimización — Shor N=15, a=4')
        ax.grid(True, alpha=0.3, axis='y')
        for i, (xi, yi) in enumerate(zip(range(len(x)), y)):
            ax.text(xi, yi + 5, str(yi), ha='center', fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/04_depth2q_vs_opt_level.png")
        plt.close()
        log("  ✓ 04_depth2q_vs_opt_level.png")

    # ── Plot 5: Signal% vs base a (OE2) ──
    if 'A3_bases' in all_results:
        fig, ax = plt.subplots(figsize=(12, 6))
        data = [r for r in all_results['A3_bases'] if 'error' not in r]
        x_labels = [f"a={r['config']['a']}\n(r={EXPECTED_ORDERS[r['config']['a']]})" for r in data]
        y_ideal = [r['ideal']['signal_pct'] for r in data]
        y_noisy = [r['noisy_fakekyiv']['signal_pct'] for r in data]

        bar_w = 0.35
        x_pos = np.arange(len(data))
        ax.bar(x_pos - bar_w/2, y_ideal, bar_w, label='Ideal', color='#2196F3',
               edgecolor='#1565C0', alpha=0.85)
        ax.bar(x_pos + bar_w/2, y_noisy, bar_w, label='FakeKyiv',
               color='#FF5722', edgecolor='#BF360C', alpha=0.85)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels)
        ax.set_ylabel('Señal (%)')
        ax.set_title('Señal vs Base a — Shor N=15, config óptima\n(OE2: Impacto del pre-cómputo clásico de coeficientes)')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 105)
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/05_signal_vs_base_a.png")
        plt.close()
        log("  ✓ 05_signal_vs_base_a.png")

    # ── Plot 6: Depth 2Q vs base a ──
    if 'A3_bases' in all_results and 'A3_ref_no_approx' in all_results:
        fig, ax = plt.subplots(figsize=(12, 6))
        data_approx = [r for r in all_results['A3_bases'] if 'error' not in r]
        data_no_approx = [r for r in all_results['A3_ref_no_approx'] if 'error' not in r]

        x_labels = [f"a={r['config']['a']}" for r in data_approx]
        y_approx = [r['isa_stats']['depth_2q'] for r in data_approx]
        y_no_approx = [r['isa_stats']['depth_2q'] for r in data_no_approx]

        bar_w = 0.35
        x_pos = np.arange(len(data_approx))
        ax.bar(x_pos - bar_w/2, y_approx, bar_w, label='approx=0.7',
               color='#4CAF50', edgecolor='#2E7D32', alpha=0.85)
        ax.bar(x_pos + bar_w/2, y_no_approx, bar_w, label='approx=1.0 (exacto)',
               color='#9E9E9E', edgecolor='#616161', alpha=0.85)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels)
        ax.set_ylabel('Profundidad 2Q')
        ax.set_title('Profundidad 2Q vs Base a — Con y sin aproximación\n(OE2: Complejidad del circuito por coeficiente)')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/06_depth2q_vs_base_a.png")
        plt.close()
        log("  ✓ 06_depth2q_vs_base_a.png")

    # ── Plot 7: Layout comparison (OE1) ──
    if 'A4_layout' in all_results:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        data = [r for r in all_results['A4_layout'] if 'error' not in r]
        labels = [r['config']['layout_method'] for r in data]
        depth = [r['isa_stats']['depth_2q'] for r in data]
        signal = [r['noisy_fakekyiv']['signal_pct'] for r in data]

        colors = ['#ef5350', '#66BB6A', '#42A5F5']
        ax1.bar(labels, depth, color=colors[:len(labels)], edgecolor='#333', alpha=0.85)
        ax1.set_ylabel('Profundidad 2Q')
        ax1.set_title('Profundidad 2Q por Layout')
        ax1.grid(True, alpha=0.3, axis='y')

        ax2.bar(labels, signal, color=colors[:len(labels)], edgecolor='#333', alpha=0.85)
        ax2.set_ylabel('Señal (%)')
        ax2.set_title('Señal (FakeKyiv) por Layout')
        ax2.set_ylim(0, 105)
        ax2.grid(True, alpha=0.3, axis='y')

        fig.suptitle('Comparación de Layout Methods — Shor N=15, a=4\n(OE1: Trivial vs Dense vs SABRE)',
                     fontsize=13, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/07_layout_comparison.png")
        plt.close()
        log("  ✓ 07_layout_comparison.png")

    # ── Plot 8: Routing comparison (OE1) ──
    if 'A5_routing' in all_results:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        data = [r for r in all_results['A5_routing'] if 'error' not in r]
        labels = [r['config']['routing_method'] for r in data]
        depth = [r['isa_stats']['depth_2q'] for r in data]
        signal = [r['noisy_fakekyiv']['signal_pct'] for r in data]

        colors = ['#ef5350', '#42A5F5', '#FFA726']
        ax1.bar(labels, depth, color=colors[:len(labels)], edgecolor='#333', alpha=0.85)
        ax1.set_ylabel('Profundidad 2Q')
        ax1.set_title('Profundidad 2Q por Routing')
        ax1.grid(True, alpha=0.3, axis='y')

        ax2.bar(labels, signal, color=colors[:len(labels)], edgecolor='#333', alpha=0.85)
        ax2.set_ylabel('Señal (%)')
        ax2.set_title('Señal (FakeKyiv) por Routing')
        ax2.set_ylim(0, 105)
        ax2.grid(True, alpha=0.3, axis='y')

        fig.suptitle('Comparación de Routing Methods — Shor N=15, a=4\n(OE1: Basic vs SABRE vs Stochastic)',
                     fontsize=13, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/08_routing_comparison.png")
        plt.close()
        log("  ✓ 08_routing_comparison.png")

    # ── Plot 9: Mitigation comparison (OE3) ──
    if 'A6_A7_mitigation' in all_results:
        fig, ax = plt.subplots(figsize=(10, 6))
        data = [r for r in all_results['A6_A7_mitigation'] if 'error' not in r]
        labels = [r['config']['study_value'] for r in data]
        signal = [r['noisy_fakekyiv']['signal_pct'] for r in data]
        fidelity = [r['noisy_fakekyiv']['fidelity'] for r in data]

        x_pos = np.arange(len(labels))
        bar_w = 0.35
        bars1 = ax.bar(x_pos - bar_w/2, signal, bar_w, label='Señal (%)',
                       color='#FF5722', edgecolor='#BF360C', alpha=0.85)
        ax2 = ax.twinx()
        bars2 = ax2.bar(x_pos + bar_w/2, fidelity, bar_w, label='Fidelidad',
                        color='#2196F3', edgecolor='#1565C0', alpha=0.85)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, rotation=15, ha='right')
        ax.set_ylabel('Señal (%)', color='#FF5722')
        ax2.set_ylabel('Fidelidad', color='#2196F3')
        ax.set_ylim(0, 105)
        ax2.set_ylim(0, 1.05)
        ax.set_title('Impacto de Mitigación de Errores — Shor N=15, a=4, FakeKyiv\n(OE3: DD y Pauli Twirling)')
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/09_mitigation_comparison.png")
        plt.close()
        log("  ✓ 09_mitigation_comparison.png")

    # ── Plot 10: Combined degradation summary (OE4) ──
    if 'A3_bases' in all_results:
        fig, ax = plt.subplots(figsize=(12, 7))
        data = [r for r in all_results['A3_bases'] if 'error' not in r]

        x_labels = [f"a={r['config']['a']}" for r in data]
        sig_ideal = [r['ideal']['signal_pct'] for r in data]
        sig_noisy = [r['noisy_fakekyiv']['signal_pct'] for r in data]
        degradation = [i - n for i, n in zip(sig_ideal, sig_noisy)]

        x_pos = np.arange(len(data))
        bar_w = 0.25

        ax.bar(x_pos - bar_w, sig_ideal, bar_w, label='Ideal', color='#4CAF50',
               edgecolor='#2E7D32', alpha=0.85)
        ax.bar(x_pos, sig_noisy, bar_w, label='FakeKyiv (Ruidoso)', color='#FF5722',
               edgecolor='#BF360C', alpha=0.85)
        ax.bar(x_pos + bar_w, degradation, bar_w, label='Degradación',
               color='#9E9E9E', edgecolor='#616161', alpha=0.85)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels)
        ax.set_ylabel('Señal (%)')
        ax.set_title('Degradación de Señal: Ideal → Ruidoso — Shor N=15\n(OE4: Cuantificar brecha ideal vs real)')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 105)
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/10_degradation_summary.png")
        plt.close()
        log("  ✓ 10_degradation_summary.png")

    log("  ═══ Gráficos generados exitosamente ═══")


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════
def generate_report(all_results, hw_results=None):
    """Generate comprehensive markdown report."""
    log("\n═══ Generando reporte markdown ═══")

    lines = []
    lines.append("# Reporte — Estudio Exhaustivo Shor N=15 (RegisterQC)")
    lines.append(f"\n**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Backend simulación**: FakeKyiv (Eagle r3, 127 qubits)")
    lines.append(f"**Circuito**: RegisterQC | **N**: 15 | **Shots ideal**: {IDEAL_SHOTS} | **Shots ruidoso**: {NOISY_SHOTS}")
    lines.append(f"\n---\n")

    # Summary table
    lines.append("## Resumen Ejecutivo\n")
    total_configs = sum(len(v) for v in all_results.values())
    total_errors = sum(1 for v in all_results.values() for r in v if 'error' in r)
    lines.append(f"| Métrica | Valor |")
    lines.append(f"|---------|:-----:|")
    lines.append(f"| Configs ejecutadas | **{total_configs}** |")
    lines.append(f"| Configs exitosas | **{total_configs - total_errors}** |")
    lines.append(f"| Configs con error | **{total_errors}** |")
    if hw_results:
        lines.append(f"| Configs hardware (ibm_torino) | **{len(hw_results)}** |")
    lines.append(f"\n---\n")

    # Per-study results
    study_titles = {
        'A1_approx_degree': 'A1: Barrido de approximation_degree (OE1)',
        'A2_opt_level': 'A2: Barrido de optimization_level (OE1)',
        'A3_bases': 'A3: Barrido de bases a — con approx=0.7 (OE2)',
        'A3_ref_no_approx': 'A3 ref: Barrido de bases a — con approx=1.0 (referencia)',
        'A4_layout': 'A4: Comparación de layout_method (OE1)',
        'A5_routing': 'A5: Comparación de routing_method (OE1)',
        'A6_A7_mitigation': 'A6/A7: Mitigación de errores DD + PT (OE3)',
    }

    for study_name, results in all_results.items():
        title = study_titles.get(study_name, study_name)
        lines.append(f"## {title}\n")

        valid = [r for r in results if 'error' not in r]
        if not valid:
            lines.append("*Todas las configuraciones fallaron.*\n")
            continue

        # Build table
        has_noisy = any('noisy_fakekyiv' in r for r in valid)

        if study_name in ['A4_layout', 'A5_routing']:
            lines.append("| Variable | Depth 2Q | 2Q Gates | Señal Ideal (%) | Señal FakeKyiv (%) | Fidelidad |")
            lines.append("|----------|:--------:|:--------:|:--------------:|:------------------:|:---------:|")
            for r in valid:
                var = r['config']['study_value']
                d2q = r['isa_stats']['depth_2q']
                g2q = r['isa_stats']['2q_gates']
                si = r['ideal']['signal_pct']
                sn = r.get('noisy_fakekyiv', {}).get('signal_pct', '—')
                fi = r.get('noisy_fakekyiv', {}).get('fidelity', '—')
                lines.append(f"| {var} | {d2q} | {g2q} | {si} | {sn} | {fi} |")
        elif study_name == 'A6_A7_mitigation':
            lines.append("| Combinación | Señal Ideal (%) | Señal FakeKyiv (%) | Fidelidad | Factores |")
            lines.append("|-------------|:--------------:|:------------------:|:---------:|:--------:|")
            for r in valid:
                label = r['config']['study_value']
                si = r['ideal']['signal_pct']
                sn = r.get('noisy_fakekyiv', {}).get('signal_pct', '—')
                fi = r.get('noisy_fakekyiv', {}).get('fidelity', '—')
                fac = r.get('noisy_fakekyiv', {}).get('factors', None)
                fac_str = f"{fac[0]}×{fac[1]}" if fac else "No encontrados"
                lines.append(f"| {label} | {si} | {sn} | {fi} | {fac_str} |")
        else:
            header_var = valid[0]['config']['study_variable'] if valid else 'Variable'
            lines.append(f"| {header_var} | Depth 2Q | 2Q Gates | Señal Ideal (%) | Señal FakeKyiv (%) | Fidelidad | Factores |")
            lines.append(f"|{'---'*1}|:--------:|:--------:|:--------------:|:------------------:|:---------:|:--------:|")
            for r in valid:
                var = r['config']['study_value']
                d2q = r['isa_stats']['depth_2q']
                g2q = r['isa_stats']['2q_gates']
                si = r['ideal']['signal_pct']
                sn = r.get('noisy_fakekyiv', {}).get('signal_pct', '—')
                fi = r.get('noisy_fakekyiv', {}).get('fidelity', '—')
                fac = r.get('noisy_fakekyiv', {}).get('factors', None)
                fac_str = f"{fac[0]}×{fac[1]}" if fac else "No encontrados"
                lines.append(f"| {var} | {d2q} | {g2q} | {si} | {sn} | {fi} | {fac_str} |")

        lines.append("")

        # Add plot reference
        plot_map = {
            'A1_approx_degree': ['01_signal_vs_approx_degree.png', '02_depth2q_vs_approx_degree.png'],
            'A2_opt_level': ['03_signal_vs_opt_level.png', '04_depth2q_vs_opt_level.png'],
            'A3_bases': ['05_signal_vs_base_a.png', '06_depth2q_vs_base_a.png'],
            'A4_layout': ['07_layout_comparison.png'],
            'A5_routing': ['08_routing_comparison.png'],
            'A6_A7_mitigation': ['09_mitigation_comparison.png'],
        }
        if study_name in plot_map:
            for plot in plot_map[study_name]:
                lines.append(f"![{plot}](plots/{plot})\n")

        lines.append("---\n")

    # Degradation summary (OE4)
    lines.append("## Degradación de Señal: Ideal → FakeKyiv (OE4)\n")
    lines.append("![Degradación](plots/10_degradation_summary.png)\n")

    if 'A3_bases' in all_results:
        valid_bases = [r for r in all_results['A3_bases'] if 'error' not in r]
        if valid_bases:
            lines.append("| Base a | ord(a,15) | Señal Ideal | Señal FakeKyiv | Degradación | Fidelidad |")
            lines.append("|:------:|:---------:|:-----------:|:--------------:|:-----------:|:---------:|")
            for r in valid_bases:
                a = r['config']['a']
                order = EXPECTED_ORDERS[a]
                si = r['ideal']['signal_pct']
                sn = r['noisy_fakekyiv']['signal_pct']
                deg = round(si - sn, 1)
                fi = r['noisy_fakekyiv']['fidelity']
                lines.append(f"| {a} | {order} | {si}% | {sn}% | {deg}% | {fi} |")
    lines.append("")

    # Hardware results section
    if hw_results:
        lines.append("---\n")
        lines.append("## Resultados Hardware Real — IBM Torino (Heron r1)\n")
        lines.append("| Config | Estudio | Estado |")
        lines.append("|--------|---------|:------:|")
        for name, res in hw_results.items():
            status = "✓ Enviado" if res.get('returncode') == 0 else f"✗ {res.get('error', 'Error')}"
            lines.append(f"| {name} | {res['study']} | {status} |")
        lines.append("\n> [!NOTE]")
        lines.append("> Los resultados de hardware real se procesan asincrónicamente. Ver outputs de cada job para resultados detallados.")
        lines.append("")

    # Existing hardware results
    lines.append("---\n")
    lines.append("## Datos Existentes de Hardware Real (ejecutados previamente)\n")
    lines.append("| a | Depth 2Q | Señal (%) | Factores | Job ID |")
    lines.append("|:-:|:--------:|:---------:|:--------:|--------|")
    lines.append("| 14 | 117 | 82.8 | 1, 15 (trivial) | `d672j2pv6o8c73d4ufqg` |")
    lines.append("| 7 | 244 | 67.5 | **3, 5** ✓ | `d672p6gqbmes739ertc0` |")
    lines.append("| 4 | 116 | 84.7 | **3, 5** ✓ | `d673l15bujdc73cvejag` |")
    lines.append("")

    # Write report
    report_path = f"{OUTPUT_DIR}/REPORTE_ESTUDIO_EXHAUSTIVO.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(lines))
    log(f"  ✓ Reporte guardado en: {report_path}")

    return report_path


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description='Estudio Exhaustivo Shor N=15')
    parser.add_argument('--include-hardware', action='store_true',
                        help='Incluir Fase 3: ejecución en ibm_torino (requiere créditos IBM)')
    parser.add_argument('--hardware-only', action='store_true',
                        help='Ejecutar solo Fase 3 (asume que Fases 1+2 ya se ejecutaron)')
    args = parser.parse_args()

    load_settings()
    ensure_dirs()

    log("═" * 70)
    log("ESTUDIO EXHAUSTIVO — Shor N=15 (RegisterQC)")
    log(f"Alineado con Objetivos del Trabajo de Grado")
    log("═" * 70)

    all_results = {}
    hw_results = {}

    if not args.hardware_only:
        # Phases 1 + 2
        t_start = time.time()
        all_results = run_local_studies()
        t_total = time.time() - t_start
        log(f"\n═══ Fases 1+2 completadas en {t_total:.1f}s ({t_total/60:.1f} min) ═══")

        # Save intermediate results
        results_path = f"{OUTPUT_DIR}/study_all_results.json"
        with open(results_path, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        log(f"Resultados guardados en: {results_path}")

        # Generate plots
        generate_plots(all_results)
    else:
        # Load previous results if available
        results_path = f"{OUTPUT_DIR}/study_all_results.json"
        if os.path.exists(results_path):
            with open(results_path, 'r') as f:
                all_results = json.load(f)
            log(f"Resultados previos cargados desde: {results_path}")

    if args.include_hardware or args.hardware_only:
        # Phase 3
        hw_results = run_hardware_studies()

        # Save hardware results
        hw_path = f"{OUTPUT_DIR}/study_hardware_results.json"
        with open(hw_path, 'w') as f:
            json.dump(hw_results, f, indent=2, default=str)
        log(f"Resultados hardware guardados en: {hw_path}")

    # Generate report
    generate_report(all_results, hw_results if hw_results else None)

    log("\n" + "═" * 70)
    log("ESTUDIO COMPLETADO")
    log("═" * 70)
    log(f"  Resultados JSON: {OUTPUT_DIR}/study_all_results.json")
    log(f"  Gráficos:        {PLOTS_DIR}/")
    log(f"  Reporte:         {OUTPUT_DIR}/REPORTE_ESTUDIO_EXHAUSTIVO.md")
    if hw_results:
        log(f"  Hardware JSON:   {OUTPUT_DIR}/study_hardware_results.json")
        log(f"  Hardware configs: {OUTPUT_DIR}/hw_configs/")


if __name__ == '__main__':
    main()
