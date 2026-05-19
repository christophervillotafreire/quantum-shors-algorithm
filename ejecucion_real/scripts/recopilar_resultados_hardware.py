"""
═══════════════════════════════════════════════════════════════════════════════
Recolección y Análisis de Resultados Hardware — Estudio Exhaustivo Shor N=15
═══════════════════════════════════════════════════════════════════════════════
Recoge los resultados de los 10 jobs enviados a IBM Torino, los analiza
con la misma función analyze_signal del estudio, y actualiza:
  - study_hardware_results.json
  - study_all_results.json (con campo 'hw_ibm_torino')
  - REPORTE_ESTUDIO_EXHAUSTIVO.md (con secciones de hardware)
  - Plots (con barras de hardware)
═══════════════════════════════════════════════════════════════════════════════
"""
import sys, os, json, time
import numpy as np
from datetime import datetime
from math import gcd
from fractions import Fraction

sys.path.insert(0, '.')
from common.settings import load_settings

from qiskit_ibm_runtime import QiskitRuntimeService

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
N = 15
VALID_BASES = [2, 4, 7, 8, 11, 13]
EXPECTED_ORDERS = {2: 4, 4: 2, 7: 4, 8: 4, 11: 2, 13: 4}
EXPECTED_FACTORS = (3, 5)

OUTPUT_DIR = "outputs/study_results"
PLOTS_DIR = f"{OUTPUT_DIR}/plots"

# ─── Job mapping: job_id → metadata ──────────────────────────────────────────
# All 10 new jobs from the exhaustive study
HW_JOBS = {
    # A3: Bases sweep (OE2)
    'd6aghkvg4t5c7383774g': {
        'study': 'A3_bases_hw', 'label': 'A3: a=2',
        'a': 2, 'opt_level': 3, 'pt': True, 'dd': False,
        'study_match': 'A3_bases', 'match_key': 'a', 'match_value': 2,
    },
    'd6aghrvg4t5c738377b0': {
        'study': 'A3_bases_hw', 'label': 'A3: a=8',
        'a': 8, 'opt_level': 3, 'pt': True, 'dd': False,
        'study_match': 'A3_bases', 'match_key': 'a', 'match_value': 8,
    },
    'd6agi07g4t5c738377f0': {
        'study': 'A3_bases_hw', 'label': 'A3: a=11',
        'a': 11, 'opt_level': 3, 'pt': True, 'dd': False,
        'study_match': 'A3_bases', 'match_key': 'a', 'match_value': 11,
    },
    'd6agi5954hss73b673gg': {
        'study': 'A3_bases_hw', 'label': 'A3: a=13',
        'a': 13, 'opt_level': 3, 'pt': True, 'dd': False,
        'study_match': 'A3_bases', 'match_key': 'a', 'match_value': 13,
    },
    # A6/A7: Mitigation sweep (OE3)
    'd6agiah7ce2c73fe8no0': {
        'study': 'A6_A7_mitigation_hw', 'label': 'A6/A7: Sin mitigación',
        'a': 4, 'opt_level': 3, 'pt': False, 'dd': False,
        'study_match': 'A6_A7_mitigation', 'match_key': 'study_value',
        'match_value': 'Sin mitigación',
    },
    'd6agiesnsg9c7397rug0': {
        'study': 'A6_A7_mitigation_hw', 'label': 'A6/A7: Solo DD',
        'a': 4, 'opt_level': 3, 'pt': False, 'dd': True,
        'study_match': 'A6_A7_mitigation', 'match_key': 'study_value',
        'match_value': 'Solo DD (XY4)',
    },
    'd6agik97ce2c73fe8o20': {
        'study': 'A6_A7_mitigation_hw', 'label': 'A6/A7: PT+DD',
        'a': 4, 'opt_level': 3, 'pt': True, 'dd': True,
        'study_match': 'A6_A7_mitigation', 'match_key': 'study_value',
        'match_value': 'PT + DD (XY4)',
    },
    'd6kuc3ofh9oc73em9bi0': {
        'study': 'A6_A7_mitigation_hw', 'label': 'A6/A7: Solo PT',
        'a': 4, 'opt_level': 3, 'pt': True, 'dd': False,
        'study_match': 'A6_A7_mitigation', 'match_key': 'study_value',
        'match_value': 'Solo PT',
    },
    # A2: Optimization level sweep (OE1)
    'd6agiong4t5c73837880': {
        'study': 'A2_opt_level_hw', 'label': 'A2: opt=0',
        'a': 4, 'opt_level': 0, 'pt': True, 'dd': False,
        'study_match': 'A2_opt_level', 'match_key': 'opt_level',
        'match_value': 0,
    },
    'd6agiu97ce2c73fe8obg': {
        'study': 'A2_opt_level_hw', 'label': 'A2: opt=1',
        'a': 4, 'opt_level': 1, 'pt': True, 'dd': False,
        'study_match': 'A2_opt_level', 'match_key': 'opt_level',
        'match_value': 1,
    },
    'd6agj2p7ce2c73fe8ohg': {
        'study': 'A2_opt_level_hw', 'label': 'A2: opt=2',
        'a': 4, 'opt_level': 2, 'pt': True, 'dd': False,
        'study_match': 'A2_opt_level', 'match_key': 'opt_level',
        'match_value': 2,
    },
}

# Previous hardware jobs (already analyzed, for reference in report)
PREVIOUS_HW_JOBS = {
    'd672j2pv6o8c73d4ufqg': {'a': 14, 'label': 'a=14 (prev)', 'signal_pct': 82.8, 'factors': [1, 15]},
    'd672p6gqbmes739ertc0': {'a': 7, 'label': 'a=7 (prev)', 'signal_pct': 67.5, 'factors': [3, 5]},
    'd673l15bujdc73cvejag': {'a': 4, 'label': 'a=4 PT=ON (prev)', 'signal_pct': 84.7, 'factors': [3, 5]},
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def analyze_signal(counts, control_qubits, a):
    """Analyze signal: compute PST, extract factors via continued fractions.
    Same function as in run_study_batch.py."""
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


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Retrieve results from IBM
# ═══════════════════════════════════════════════════════════════════════════════
def retrieve_hw_results():
    """Connect to IBM Quantum and retrieve results for all 10 jobs."""
    log("═══ Conectando a IBM Quantum ═══")
    service = QiskitRuntimeService(name='ibm_quantum')
    log("  ✓ Conectado")

    hw_results = {}

    for job_id, meta in HW_JOBS.items():
        log(f"\n  Recuperando {meta['label']} — job {job_id}...")
        try:
            job = service.job(job_id)
            status = job.status()
            log(f"    Status: {status}")

            if str(status) not in ['JobStatus.DONE', 'DONE']:
                log(f"    ⚠ Job no completado, saltando. Status={status}")
                hw_results[job_id] = {
                    **meta,
                    'status': str(status),
                    'error': 'Job not done',
                }
                continue

            # Get results
            result = job.result()
            # Extract counts — each pub result
            pub_result = result[0]
            counts = dict(pub_result.data.output.get_counts())

            # Read isas_stats for control_qubits
            isas_path = f"outputs/ibm_torino/{job_id}/isas_stats.json"
            with open(isas_path, 'r') as f:
                isas_stats = json.load(f)
            control_qubits = isas_stats['settings']['control_qubits']
            a = meta['a']

            # Analyze signal
            analysis = analyze_signal(counts, control_qubits, a)

            hw_results[job_id] = {
                **meta,
                'status': 'DONE',
                'control_qubits': control_qubits,
                'shots': analysis['total_shots'],
                'counts_top10': dict(sorted(counts.items(),
                                            key=lambda x: x[1],
                                            reverse=True)[:10]),
                'analysis': analysis,
                'depth_2q': isas_stats['csa'][str(a)]['circuit_depth'],
                'cz_gates': isas_stats['csa'][str(a)]['cz'],
                'total_gates': isas_stats['csa'][str(a)]['total_gates'],
            }

            sig = analysis['signal_pct']
            fid = analysis['fidelity']
            fac = analysis['factors']
            log(f"    ✓ signal={sig}%, fidelity={fid}, factors={fac}")

        except Exception as e:
            log(f"    ✗ Error: {e}")
            hw_results[job_id] = {
                **meta,
                'status': 'ERROR',
                'error': str(e),
            }

    return hw_results


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Update study_all_results.json
# ═══════════════════════════════════════════════════════════════════════════════
def update_all_results(hw_results):
    """Inject hw_ibm_torino data into study_all_results.json."""
    log("\n═══ Actualizando study_all_results.json ═══")

    results_path = f"{OUTPUT_DIR}/study_all_results.json"
    with open(results_path, 'r') as f:
        all_results = json.load(f)

    injected = 0
    for job_id, hw in hw_results.items():
        if hw.get('status') != 'DONE':
            continue

        study_match = hw.get('study_match')
        match_key = hw.get('match_key')
        match_value = hw.get('match_value')

        if study_match not in all_results:
            log(f"  ⚠ Estudio {study_match} no encontrado en all_results")
            continue

        # Find matching config in all_results
        for result in all_results[study_match]:
            if 'error' in result:
                continue
            cfg = result.get('config', {})
            cfg_value = cfg.get(match_key)

            # Handle numeric comparison (opt_level can be float/int)
            if isinstance(match_value, (int, float)) and isinstance(cfg_value, (int, float)):
                matched = abs(cfg_value - match_value) < 0.01
            else:
                matched = cfg_value == match_value

            if matched:
                result['hw_ibm_torino'] = {
                    'job_id': job_id,
                    'shots': hw['analysis']['total_shots'],
                    **hw['analysis'],
                }
                injected += 1
                log(f"  ✓ Inyectado HW en {study_match}/{match_key}={match_value}")
                break
        else:
            log(f"  ⚠ No match found for {hw['label']} in {study_match}")

    # Save updated results
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    log(f"  ═══ {injected} resultados HW inyectados en study_all_results.json ═══")

    return all_results


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Regenerate plots with hardware data
# ═══════════════════════════════════════════════════════════════════════════════
def generate_plots_with_hw(all_results, hw_results):
    """Regenerate plots including hardware results as a third bar."""
    log("\n═══ Regenerando gráficos con datos hardware ═══")

    plt.rcParams.update({
        'font.size': 11, 'font.family': 'sans-serif',
        'axes.titlesize': 13, 'axes.labelsize': 11,
        'figure.dpi': 150, 'savefig.dpi': 150,
        'figure.facecolor': 'white',
    })

    # Build hw lookup: (study, match_value) → analysis
    hw_lookup = {}
    for job_id, hw in hw_results.items():
        if hw.get('status') != 'DONE':
            continue
        key = (hw['study_match'], hw['match_value'])
        hw_lookup[key] = hw

    # ── Plot 3: Signal% vs opt_level (OE1) — NOW WITH HW ──
    if 'A2_opt_level' in all_results:
        fig, ax = plt.subplots(figsize=(12, 6))
        data = [r for r in all_results['A2_opt_level'] if 'error' not in r]
        x = [r['config']['opt_level'] for r in data]
        y_ideal = [r['ideal']['signal_pct'] for r in data]
        y_noisy = [r['noisy_fakekyiv']['signal_pct'] for r in data]
        y_hw = []
        for r in data:
            ol = r['config']['opt_level']
            hw_data = r.get('hw_ibm_torino')
            y_hw.append(hw_data['signal_pct'] if hw_data else None)

        bar_w = 0.25
        x_pos = np.arange(len(x))
        ax.bar(x_pos - bar_w, y_ideal, bar_w, label='Ideal (AerSim)',
               color='#2196F3', edgecolor='#1565C0', alpha=0.85)
        ax.bar(x_pos, y_noisy, bar_w, label='FakeKyiv (Ruidoso)',
               color='#FF5722', edgecolor='#BF360C', alpha=0.85)

        # Hardware bars (only where available)
        hw_vals = [v if v is not None else 0 for v in y_hw]
        hw_colors = ['#4CAF50' if v is not None else '#EEEEEE' for v in y_hw]
        hw_edges = ['#2E7D32' if v is not None else '#CCCCCC' for v in y_hw]
        bars_hw = ax.bar(x_pos + bar_w, hw_vals, bar_w, label='IBM Torino (HW)',
                         color=hw_colors, edgecolor=hw_edges, alpha=0.85)
        # Add value labels on HW bars
        for i, (xi, yi) in enumerate(zip(x_pos, y_hw)):
            if yi is not None:
                ax.text(xi + bar_w, yi + 1, f'{yi}%', ha='center',
                        fontsize=8, fontweight='bold', color='#2E7D32')

        ax.set_xticks(x_pos)
        ax.set_xticklabels([f'Opt {v}' for v in x])
        ax.set_ylabel('Señal (%)')
        ax.set_title('Señal vs Nivel de Optimización — Shor N=15, a=4\n'
                      '(OE1: Ideal → FakeKyiv → IBM Torino)')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 115)
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/03_signal_vs_opt_level.png")
        plt.close()
        log("  ✓ 03_signal_vs_opt_level.png (con HW)")

    # ── Plot 5: Signal% vs base a (OE2) — NOW WITH HW ──
    if 'A3_bases' in all_results:
        fig, ax = plt.subplots(figsize=(14, 7))
        data = [r for r in all_results['A3_bases'] if 'error' not in r]
        x_labels = [f"a={r['config']['a']}\n(r={EXPECTED_ORDERS[r['config']['a']]})"
                    for r in data]
        y_ideal = [r['ideal']['signal_pct'] for r in data]
        y_noisy = [r['noisy_fakekyiv']['signal_pct'] for r in data]
        y_hw = []
        for r in data:
            hw_data = r.get('hw_ibm_torino')
            y_hw.append(hw_data['signal_pct'] if hw_data else None)

        bar_w = 0.25
        x_pos = np.arange(len(data))
        ax.bar(x_pos - bar_w, y_ideal, bar_w, label='Ideal (AerSim)',
               color='#2196F3', edgecolor='#1565C0', alpha=0.85)
        ax.bar(x_pos, y_noisy, bar_w, label='FakeKyiv (Ruidoso)',
               color='#FF5722', edgecolor='#BF360C', alpha=0.85)

        hw_vals = [v if v is not None else 0 for v in y_hw]
        hw_colors = ['#4CAF50' if v is not None else '#EEEEEE' for v in y_hw]
        hw_edges = ['#2E7D32' if v is not None else '#CCCCCC' for v in y_hw]
        ax.bar(x_pos + bar_w, hw_vals, bar_w, label='IBM Torino (HW)',
               color=hw_colors, edgecolor=hw_edges, alpha=0.85)
        for i, (xi, yi) in enumerate(zip(x_pos, y_hw)):
            if yi is not None:
                ax.text(xi + bar_w, yi + 1, f'{yi}%', ha='center',
                        fontsize=8, fontweight='bold', color='#2E7D32')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels)
        ax.set_ylabel('Señal (%)')
        ax.set_title('Señal vs Base a — Shor N=15, config óptima\n'
                      '(OE2: Ideal → FakeKyiv → IBM Torino)')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 115)
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/05_signal_vs_base_a.png")
        plt.close()
        log("  ✓ 05_signal_vs_base_a.png (con HW)")

    # ── Plot 9: Mitigation comparison (OE3) — NOW WITH HW ──
    if 'A6_A7_mitigation' in all_results:
        fig, ax = plt.subplots(figsize=(12, 7))
        data = [r for r in all_results['A6_A7_mitigation'] if 'error' not in r]
        labels = [r['config']['study_value'] for r in data]
        sig_noisy = [r['noisy_fakekyiv']['signal_pct'] for r in data]
        y_hw = []
        for r in data:
            hw_data = r.get('hw_ibm_torino')
            y_hw.append(hw_data['signal_pct'] if hw_data else None)

        x_pos = np.arange(len(labels))
        bar_w = 0.3

        ax.bar(x_pos - bar_w/2, sig_noisy, bar_w, label='FakeKyiv (Ruidoso)',
               color='#FF5722', edgecolor='#BF360C', alpha=0.85)

        hw_vals = [v if v is not None else 0 for v in y_hw]
        hw_colors = ['#4CAF50' if v is not None else '#EEEEEE' for v in y_hw]
        hw_edges = ['#2E7D32' if v is not None else '#CCCCCC' for v in y_hw]
        ax.bar(x_pos + bar_w/2, hw_vals, bar_w, label='IBM Torino (HW)',
               color=hw_colors, edgecolor=hw_edges, alpha=0.85)

        for i, (xi, yi) in enumerate(zip(x_pos, y_hw)):
            if yi is not None:
                ax.text(xi + bar_w/2, yi + 1, f'{yi}%', ha='center',
                        fontsize=9, fontweight='bold', color='#2E7D32')
        for i, (xi, yi) in enumerate(zip(x_pos, sig_noisy)):
            ax.text(xi - bar_w/2, yi + 1, f'{yi}%', ha='center',
                    fontsize=9, fontweight='bold', color='#BF360C')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, rotation=15, ha='right')
        ax.set_ylabel('Señal (%)')
        ax.set_title('Impacto de Mitigación de Errores — Shor N=15, a=4\n'
                      '(OE3: FakeKyiv vs IBM Torino)')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 115)
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/09_mitigation_comparison.png")
        plt.close()
        log("  ✓ 09_mitigation_comparison.png (con HW)")

    # ── Plot 10: Degradation summary (OE4) — NOW WITH HW ──
    if 'A3_bases' in all_results:
        fig, ax = plt.subplots(figsize=(14, 7))
        data = [r for r in all_results['A3_bases'] if 'error' not in r]

        x_labels = [f"a={r['config']['a']}" for r in data]
        sig_ideal = [r['ideal']['signal_pct'] for r in data]
        sig_noisy = [r['noisy_fakekyiv']['signal_pct'] for r in data]
        sig_hw = []
        for r in data:
            hw_data = r.get('hw_ibm_torino')
            sig_hw.append(hw_data['signal_pct'] if hw_data else None)

        x_pos = np.arange(len(data))
        bar_w = 0.2

        ax.bar(x_pos - bar_w*1.5, sig_ideal, bar_w, label='Ideal',
               color='#4CAF50', edgecolor='#2E7D32', alpha=0.85)
        ax.bar(x_pos - bar_w*0.5, sig_noisy, bar_w, label='FakeKyiv',
               color='#FF5722', edgecolor='#BF360C', alpha=0.85)

        hw_vals = [v if v is not None else 0 for v in sig_hw]
        hw_colors = ['#2196F3' if v is not None else '#EEEEEE' for v in sig_hw]
        hw_edges = ['#1565C0' if v is not None else '#CCCCCC' for v in sig_hw]
        ax.bar(x_pos + bar_w*0.5, hw_vals, bar_w, label='IBM Torino (HW)',
               color=hw_colors, edgecolor=hw_edges, alpha=0.85)

        # Degradation bars
        deg_vals = []
        for i in range(len(data)):
            if sig_hw[i] is not None:
                deg_vals.append(sig_ideal[i] - sig_hw[i])
            else:
                deg_vals.append(sig_ideal[i] - sig_noisy[i])
        ax.bar(x_pos + bar_w*1.5, deg_vals, bar_w, label='Degradación (Ideal→HW)',
               color='#9E9E9E', edgecolor='#616161', alpha=0.85)

        # Value labels
        for i, xi in enumerate(x_pos):
            if sig_hw[i] is not None:
                ax.text(xi + bar_w*0.5, sig_hw[i] + 1, f'{sig_hw[i]}%',
                        ha='center', fontsize=7, fontweight='bold', color='#1565C0')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels)
        ax.set_ylabel('Señal (%)')
        ax.set_title('Degradación de Señal: Ideal → FakeKyiv → IBM Torino — Shor N=15\n'
                      '(OE4: Cuantificar brecha ideal vs ruidoso vs hardware real)')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 115)
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/10_degradation_summary.png")
        plt.close()
        log("  ✓ 10_degradation_summary.png (con HW)")

    # ── NEW Plot 11: Hardware probability distributions for all bases ──
    hw_bases_jobs = {jid: hw for jid, hw in hw_results.items()
                     if hw.get('study') == 'A3_bases_hw' and hw.get('status') == 'DONE'}
    if hw_bases_jobs:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        axes = axes.flatten()
        bases_sorted = sorted(hw_bases_jobs.items(), key=lambda x: x[1]['a'])

        for idx, (jid, hw) in enumerate(bases_sorted):
            if idx >= 4:
                break
            ax = axes[idx]
            a = hw['a']
            analysis = hw['analysis']
            peaks_info = analysis['peak_details']

            # Build bar chart for peaks
            peak_labels = [f"{p['bitstring']}\n({p['peak_decimal']})" for p in peaks_info]
            peak_probs = [p['observed_prob'] for p in peaks_info]
            expected = [p['expected_prob'] for p in peaks_info]

            x_pk = np.arange(len(peaks_info))
            w = 0.35
            ax.bar(x_pk - w/2, expected, w, label='Esperado', color='#2196F3',
                   alpha=0.6, edgecolor='#1565C0')
            ax.bar(x_pk + w/2, peak_probs, w, label='Observado (HW)', color='#4CAF50',
                   alpha=0.85, edgecolor='#2E7D32')

            ax.set_xticks(x_pk)
            ax.set_xticklabels(peak_labels, fontsize=8)
            ax.set_ylabel('Probabilidad')
            sig = analysis['signal_pct']
            fac = analysis['factors']
            fac_str = f"{fac[0]}×{fac[1]}" if fac else "No encontrados"
            ax.set_title(f"a={a} | Señal={sig}% | Factores={fac_str}",
                         fontsize=11, fontweight='bold')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3, axis='y')

        fig.suptitle('Distribución en Picos Teóricos — IBM Torino Hardware\n'
                     'Shor N=15 (RegisterQC, opt=3, approx=0.7)',
                     fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{PLOTS_DIR}/11_hw_peak_distributions.png")
        plt.close()
        log("  ✓ 11_hw_peak_distributions.png (NUEVO)")

    log("  ═══ Gráficos actualizados ═══")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: Generate updated report
# ═══════════════════════════════════════════════════════════════════════════════
def generate_updated_report(all_results, hw_results):
    """Regenerate REPORTE_ESTUDIO_EXHAUSTIVO.md with hardware data."""
    log("\n═══ Regenerando reporte con datos hardware ═══")

    lines = []
    lines.append("# Reporte — Estudio Exhaustivo Shor N=15 (RegisterQC)")
    lines.append(f"\n**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("**Backend simulación**: FakeKyiv (Eagle r3, 127 qubits)")
    lines.append("**Hardware real**: IBM Torino (Heron r1, 133 qubits)")
    lines.append("**Circuito**: RegisterQC | **N**: 15 | **Shots ideal**: 4096 | "
                 "**Shots ruidoso**: 1024 | **Shots HW**: 4096")
    lines.append("\n---\n")

    # ── Resumen Ejecutivo ──
    lines.append("## Resumen Ejecutivo\n")
    total_sim = sum(len(v) for v in all_results.values())
    total_errors = sum(1 for v in all_results.values() for r in v if 'error' in r)
    hw_done = sum(1 for hw in hw_results.values() if hw.get('status') == 'DONE')
    hw_factors_ok = sum(1 for hw in hw_results.values()
                        if hw.get('status') == 'DONE' and
                        hw.get('analysis', {}).get('factors_correct', False))

    lines.append("| Métrica | Valor |")
    lines.append("|---------|:-----:|")
    lines.append(f"| Configs simuladas (ideal + FakeKyiv) | **{total_sim}** |")
    lines.append(f"| Configs exitosas (simulación) | **{total_sim - total_errors}** |")
    lines.append(f"| Jobs hardware (IBM Torino) | **{hw_done}** |")
    lines.append(f"| Jobs HW con factores correctos (3×5) | **{hw_factors_ok}/{hw_done}** |")
    lines.append("\n---\n")

    # ── Study tables ──
    study_titles = {
        'A1_approx_degree': ('A1: Barrido de approximation_degree (OE1)', False),
        'A2_opt_level': ('A2: Barrido de optimization_level (OE1)', True),
        'A3_bases': ('A3: Barrido de bases a — con approx=0.7 (OE2)', True),
        'A3_ref_no_approx': ('A3 ref: Barrido de bases a — con approx=1.0 (referencia)', False),
        'A4_layout': ('A4: Comparación de layout_method (OE1)', False),
        'A5_routing': ('A5: Comparación de routing_method (OE1)', False),
        'A6_A7_mitigation': ('A6/A7: Mitigación de errores DD + PT (OE3)', True),
    }

    plot_map = {
        'A1_approx_degree': ['01_signal_vs_approx_degree.png',
                             '02_depth2q_vs_approx_degree.png'],
        'A2_opt_level': ['03_signal_vs_opt_level.png',
                         '04_depth2q_vs_opt_level.png'],
        'A3_bases': ['05_signal_vs_base_a.png', '06_depth2q_vs_base_a.png'],
        'A4_layout': ['07_layout_comparison.png'],
        'A5_routing': ['08_routing_comparison.png'],
        'A6_A7_mitigation': ['09_mitigation_comparison.png'],
    }

    for study_name, results in all_results.items():
        title_info = study_titles.get(study_name)
        if not title_info:
            continue
        title, has_hw = title_info
        lines.append(f"## {title}\n")

        valid = [r for r in results if 'error' not in r]
        if not valid:
            lines.append("*Todas las configuraciones fallaron.*\n")
            continue

        # Build table with HW column if applicable
        if study_name in ['A4_layout', 'A5_routing']:
            lines.append("| Variable | Depth 2Q | 2Q Gates | Señal Ideal (%) "
                         "| Señal FakeKyiv (%) | Fidelidad |")
            lines.append("|----------|:--------:|:--------:|:--------------:"
                         "|:------------------:|:---------:|")
            for r in valid:
                var = r['config']['study_value']
                d2q = r['isa_stats']['depth_2q']
                g2q = r['isa_stats']['2q_gates']
                si = r['ideal']['signal_pct']
                sn = r.get('noisy_fakekyiv', {}).get('signal_pct', '—')
                fi = r.get('noisy_fakekyiv', {}).get('fidelity', '—')
                lines.append(f"| {var} | {d2q} | {g2q} | {si} | {sn} | {fi} |")

        elif study_name == 'A6_A7_mitigation':
            lines.append("| Combinación | Señal Ideal (%) | Señal FakeKyiv (%) "
                         "| **Señal HW (%)** | Fidelidad FK | Fidelidad HW | Factores HW |")
            lines.append("|-------------|:--------------:|:------------------:"
                         "|:----------------:|:------------:|:------------:|:----------:|")
            for r in valid:
                label = r['config']['study_value']
                si = r['ideal']['signal_pct']
                sn = r.get('noisy_fakekyiv', {}).get('signal_pct', '—')
                fi_fk = r.get('noisy_fakekyiv', {}).get('fidelity', '—')
                hw = r.get('hw_ibm_torino')
                if hw:
                    sh = hw['signal_pct']
                    fi_hw = hw['fidelity']
                    fac = hw.get('factors')
                    fac_str = f"{fac[0]}×{fac[1]}" if fac else "No encontrados"
                else:
                    sh, fi_hw, fac_str = '—', '—', '—'
                lines.append(f"| {label} | {si} | {sn} | **{sh}** | "
                             f"{fi_fk} | {fi_hw} | {fac_str} |")

        elif has_hw:
            # A2_opt_level and A3_bases
            header_var = valid[0]['config']['study_variable'] if valid else 'Variable'
            lines.append(f"| {header_var} | Depth 2Q | 2Q Gates | Señal Ideal (%) "
                         f"| Señal FakeKyiv (%) | **Señal HW (%)** | Fidelidad HW | Factores HW |")
            lines.append(f"|---|:--------:|:--------:|:--------------:"
                         f"|:------------------:|:----------------:|:------------:|:----------:|")
            for r in valid:
                var = r['config']['study_value']
                d2q = r['isa_stats']['depth_2q']
                g2q = r['isa_stats']['2q_gates']
                si = r['ideal']['signal_pct']
                sn = r.get('noisy_fakekyiv', {}).get('signal_pct', '—')
                hw = r.get('hw_ibm_torino')
                if hw:
                    sh = hw['signal_pct']
                    fi_hw = hw['fidelity']
                    fac = hw.get('factors')
                    fac_str = f"{fac[0]}×{fac[1]}" if fac else "No encontrados"
                else:
                    sh, fi_hw, fac_str = '—', '—', '—'
                lines.append(f"| {var} | {d2q} | {g2q} | {si} | {sn} | "
                             f"**{sh}** | {fi_hw} | {fac_str} |")
        else:
            # No HW data — standard table
            header_var = valid[0]['config']['study_variable'] if valid else 'Variable'
            lines.append(f"| {header_var} | Depth 2Q | 2Q Gates | Señal Ideal (%) "
                         f"| Señal FakeKyiv (%) | Fidelidad | Factores |")
            lines.append(f"|---|:--------:|:--------:|:--------------:"
                         f"|:------------------:|:---------:|:--------:|")
            for r in valid:
                var = r['config']['study_value']
                d2q = r['isa_stats']['depth_2q']
                g2q = r['isa_stats']['2q_gates']
                si = r['ideal']['signal_pct']
                sn = r.get('noisy_fakekyiv', {}).get('signal_pct', '—')
                fi = r.get('noisy_fakekyiv', {}).get('fidelity', '—')
                fac = r.get('noisy_fakekyiv', {}).get('factors', None)
                fac_str = f"{fac[0]}×{fac[1]}" if fac else "No encontrados"
                lines.append(f"| {var} | {d2q} | {g2q} | {si} | {sn} | "
                             f"{fi} | {fac_str} |")

        lines.append("")

        # Add plot references
        if study_name in plot_map:
            for plot in plot_map[study_name]:
                lines.append(f"![{plot}](plots/{plot})\n")

        lines.append("---\n")

    # ═══ Hardware Results Section ═══
    lines.append("## Resultados Hardware Real — IBM Torino (Heron r1)\n")
    lines.append("> [!IMPORTANT]")
    lines.append("> Todos los resultados de hardware fueron ejecutados en el procesador "
                 "**IBM Torino** (Heron r1, 133 qubits) con 4096 shots por job.\n")

    # Table of all HW results
    lines.append("### Resumen de Jobs Hardware\n")
    lines.append("| Job ID | Estudio | Config | Depth 2Q | Señal (%) | "
                 "Fidelidad | Factores |")
    lines.append("|--------|---------|--------|:--------:|:---------:|"
                 ":---------:|:--------:|")

    for job_id, hw in sorted(hw_results.items(), key=lambda x: x[1].get('label', '')):
        if hw.get('status') != 'DONE':
            lines.append(f"| `{job_id}` | {hw.get('study', '?')} | "
                         f"{hw.get('label', '?')} | — | — | — | Error: {hw.get('error', '?')} |")
            continue
        a = hw['analysis']
        fac = a.get('factors')
        fac_str = f"**{fac[0]}×{fac[1]}** ✓" if fac and a['factors_correct'] else \
                  f"{fac[0]}×{fac[1]}" if fac else "No encontrados"
        lines.append(f"| `{job_id}` | {hw['study']} | {hw['label']} | "
                     f"{hw['depth_2q']} | {a['signal_pct']} | "
                     f"{a['fidelity']} | {fac_str} |")

    # Add previous jobs
    lines.append("\n### Jobs Ejecutados Previamente\n")
    lines.append("| Job ID | a | Señal (%) | Factores |")
    lines.append("|--------|:-:|:---------:|:--------:|")
    for jid, prev in PREVIOUS_HW_JOBS.items():
        fac = prev['factors']
        fac_str = f"**{fac[0]}×{fac[1]}** ✓" if set(fac) == {3, 5} else f"{fac[0]}, {fac[1]}"
        lines.append(f"| `{jid}` | {prev['a']} | {prev['signal_pct']} | {fac_str} |")
    lines.append("")

    # ═══ Degradation 3-level section (OE4) ═══
    lines.append("---\n")
    lines.append("## Degradación de Señal: Ideal → FakeKyiv → IBM Torino (OE4)\n")
    lines.append("![Degradación](plots/10_degradation_summary.png)\n")

    if 'A3_bases' in all_results:
        valid_bases = [r for r in all_results['A3_bases'] if 'error' not in r]
        if valid_bases:
            lines.append("| Base a | ord(a,15) | Señal Ideal | Señal FakeKyiv | "
                         "**Señal HW** | Degrad. Ideal→FK | Degrad. Ideal→HW | Fidelidad HW |")
            lines.append("|:------:|:---------:|:-----------:|:--------------:|"
                         ":------------:|:----------------:|:----------------:|:------------:|")
            for r in valid_bases:
                a = r['config']['a']
                order = EXPECTED_ORDERS[a]
                si = r['ideal']['signal_pct']
                sn = r['noisy_fakekyiv']['signal_pct']
                deg_fk = round(si - sn, 1)
                hw = r.get('hw_ibm_torino')
                if hw:
                    sh = hw['signal_pct']
                    deg_hw = round(si - sh, 1)
                    fi_hw = hw['fidelity']
                    lines.append(f"| {a} | {order} | {si}% | {sn}% | "
                                 f"**{sh}%** | {deg_fk}% | **{deg_hw}%** | {fi_hw} |")
                else:
                    lines.append(f"| {a} | {order} | {si}% | {sn}% | "
                                 f"— | {deg_fk}% | — | — |")
    lines.append("")

    # ═══ Peak distribution plot ═══
    lines.append("### Distribución de Picos — Hardware\n")
    lines.append("![Peak distributions](plots/11_hw_peak_distributions.png)\n")

    # ═══ Conclusiones ═══
    lines.append("---\n")
    lines.append("## Conclusiones\n")

    lines.append("### OE1: Transpilación\n")
    # Get A2 hw results
    a2_hw = {hw['opt_level']: hw for hw in hw_results.values()
             if hw.get('study') == 'A2_opt_level_hw' and hw.get('status') == 'DONE'}
    if a2_hw:
        lines.append("Se confirma en **hardware real** que el nivel de optimización es crítico:\n")
        for ol in sorted(a2_hw.keys()):
            hw = a2_hw[ol]
            sig = hw['analysis']['signal_pct']
            fac = hw['analysis']['factors']
            fac_str = f"{fac[0]}×{fac[1]}" if fac else "No encontrados"
            lines.append(f"- **opt={ol}**: Señal HW = {sig}%, Factores = {fac_str}")
        lines.append("")

    lines.append("### OE2: Bases `a` en Hardware\n")
    a3_hw = {hw['a']: hw for hw in hw_results.values()
             if hw.get('study') == 'A3_bases_hw' and hw.get('status') == 'DONE'}
    if a3_hw:
        lines.append("Resultados de las 4 bases ejecutadas en IBM Torino:\n")
        for a_val in sorted(a3_hw.keys()):
            hw = a3_hw[a_val]
            sig = hw['analysis']['signal_pct']
            fac = hw['analysis']['factors']
            fac_str = f"**{fac[0]}×{fac[1]}** ✓" if fac and hw['analysis']['factors_correct'] \
                      else (f"{fac[0]}×{fac[1]}" if fac else "No encontrados")
            lines.append(f"- **a={a_val}** (r={EXPECTED_ORDERS[a_val]}): "
                         f"Señal = {sig}%, Factores = {fac_str}")
        lines.append("")

    lines.append("### OE3: Mitigación en Hardware\n")
    a67_hw = [(hw['label'], hw) for hw in hw_results.values()
              if hw.get('study') == 'A6_A7_mitigation_hw' and hw.get('status') == 'DONE']
    if a67_hw:
        lines.append("Comparación de mitigación de errores en hardware real:\n")
        for label, hw in sorted(a67_hw):
            sig = hw['analysis']['signal_pct']
            fac = hw['analysis']['factors']
            fac_str = f"**{fac[0]}×{fac[1]}** ✓" if fac and hw['analysis']['factors_correct'] \
                      else (f"{fac[0]}×{fac[1]}" if fac else "No encontrados")
            lines.append(f"- **{label}**: Señal HW = {sig}%, Factores = {fac_str}")
        lines.append("")

    lines.append("### OE4: Degradación General\n")
    if a3_hw:
        sigs = [hw['analysis']['signal_pct'] for hw in a3_hw.values()]
        avg_sig = round(sum(sigs) / len(sigs), 1)
        best_a = max(a3_hw.items(), key=lambda x: x[1]['analysis']['signal_pct'])
        worst_a = min(a3_hw.items(), key=lambda x: x[1]['analysis']['signal_pct'])
        lines.append(f"- **Promedio señal HW**: {avg_sig}% (sobre {len(a3_hw)} bases)")
        lines.append(f"- **Mejor base HW**: a={best_a[0]} ({best_a[1]['analysis']['signal_pct']}%)")
        lines.append(f"- **Peor base HW**: a={worst_a[0]} ({worst_a[1]['analysis']['signal_pct']}%)")
        total_fac = sum(1 for hw in a3_hw.values() if hw['analysis']['factors_correct'])
        lines.append(f"- **Factorización exitosa**: {total_fac}/{len(a3_hw)} bases")
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
    load_settings()

    log("═" * 70)
    log("RECOLECCIÓN DE RESULTADOS HARDWARE — Estudio Exhaustivo Shor N=15")
    log("═" * 70)

    # Phase 1: Retrieve from IBM
    hw_results = retrieve_hw_results()

    # Save raw hardware results
    hw_path = f"{OUTPUT_DIR}/study_hardware_results.json"
    with open(hw_path, 'w') as f:
        json.dump(hw_results, f, indent=2, default=str)
    log(f"\n✓ Resultados HW guardados en: {hw_path}")

    # Summary
    done = sum(1 for hw in hw_results.values() if hw.get('status') == 'DONE')
    log(f"\n═ RESUMEN: {done}/{len(hw_results)} jobs recuperados exitosamente ═")
    for jid, hw in hw_results.items():
        if hw.get('status') == 'DONE':
            a = hw['analysis']
            fac = a['factors']
            fac_str = f"{fac[0]}×{fac[1]}" if fac else "—"
            log(f"  {hw['label']:30s} signal={a['signal_pct']:5.1f}%  "
                f"fidelity={a['fidelity']:.4f}  factors={fac_str}")

    # Phase 2: Update study_all_results.json
    all_results = update_all_results(hw_results)

    # Phase 3: Regenerate plots
    generate_plots_with_hw(all_results, hw_results)

    # Phase 4: Regenerate report
    generate_updated_report(all_results, hw_results)

    log("\n" + "═" * 70)
    log("RECOLECCIÓN COMPLETADA")
    log("═" * 70)
    log(f"  Hardware JSON:    {hw_path}")
    log(f"  All results:      {OUTPUT_DIR}/study_all_results.json")
    log(f"  Plots:            {PLOTS_DIR}/")
    log(f"  Reporte:          {OUTPUT_DIR}/REPORTE_ESTUDIO_EXHAUSTIVO.md")


if __name__ == '__main__':
    main()
