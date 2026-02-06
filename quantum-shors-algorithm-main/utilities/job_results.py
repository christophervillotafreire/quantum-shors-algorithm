import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from math import gcd
from qiskit import qpy
from qiskit.visualization import plot_circuit_layout
from qiskit_ibm_runtime import QiskitRuntimeService


BASE_DIR = Path(__file__).resolve().parent.parent


def write_isas_info(job_id, isas_stats):
    # for WINDOWS replace below path with:
    # {BASE_DIR}\\outputs\\{isas_stats['settings']['ibm_qpu']}\\{job_id}\\isas_stats.json
    file_path = f"{BASE_DIR}/outputs/{isas_stats['settings']['ibm_qpu']}/{job_id}/isas_stats.json"
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(isas_stats, file, indent=4)


def read_isas_info(ibm_qpu, job_id):
    # for WINDOWS replace below path with:
    # {BASE_DIR}\\outputs\\{ibm_qpu}\\{job_id}\\isas_stats.json
    with open(f"{BASE_DIR}/outputs/{ibm_qpu}/{job_id}/isas_stats.json", 'r') as file:
        return json.load(file)


def find_nontrivial_factors(number, rs):
    results = {}
    for a, rs in rs.items():
        r = sorted(rs)[0] if rs else None
        if r:
            print(f"[{datetime.now()}] - Checking period r = {r}")
            if r % 2 != 0:
                print(f"[{datetime.now()}] - Period {r} is odd. Non-trivial factors can't be calculated")
                continue
            p = gcd(a ** (r // 2) - 1, number)
            q = gcd(a ** (r // 2) + 1, number)
            trivial_factors = [1, number]
            if p in trivial_factors or q in trivial_factors:
                print(f"[{datetime.now()}] - Trivial factors found: {p}, {q}")
                continue
            if p*q == number:
                print(f"[{datetime.now()}] - Founded factors of {number}: {p} and {q}")
                results[a] = {'r': r, 'factors': [p, q]}
                continue
    if not results:
        print(f"[{datetime.now()}] - No non-trivial factors found for number {number}")
    return results


def get_candidate_rs(number, control_qubits, phases_max_top_number, results):
    candidates = {}
    for result in results:
        a = result[0]
        counts = result[1]
        rs = []
        counts_sorted = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:phases_max_top_number]
        for (bit_string, count) in counts_sorted:
            decimal = int(bit_string, 2)
            phase = decimal / 2**control_qubits
            fraction = Fraction(phase).limit_denominator(number)
            s, r = fraction.numerator, fraction.denominator
            if r not in rs and number > r > 1 == pow(a, r, number):
                rs.append(r)
        candidates[a] = rs
    print(f"[{datetime.now()}] - Candidates period r(s) for each \"a\" coefficient: {candidates}")
    return candidates


def plot_results_distribution(results, isas_stats, job_id, candidates_rs):
    for result in results:
        a = result[0]
        stats_key = str(a)
        counts = result[1]
        number = get_stats_key_value(isas_stats, 'settings.number_to_factor')
        control_qubits = get_stats_key_value(isas_stats, 'settings.control_qubits')
        shots = get_stats_key_value(isas_stats, 'settings.shots')
        backend = get_stats_key_value(isas_stats, 'settings.backend')
        ibm_qpu = get_stats_key_value(isas_stats, 'settings.ibm_qpu')
        rs = sorted(candidates_rs.get(a, []))
        r = rs[0] if rs else None
        noise = calculate_noise_percentage(counts, r, control_qubits, shots) if r else None
        dist = np.zeros((2**control_qubits))
        xdist = np.arange(len(dist)) / 2**control_qubits
        for x in counts.keys():
            dist[int(x, 2)] = counts[x] / shots
        plt.figure(figsize=(8, 5))
        plt.plot(xdist, dist)
        title = f"N={number}, a={a}, shots={shots}, period={r}" if r else f"N={number}, a={a}, shots={shots}, period not found"
        plt.title(title, fontsize=16)
        plt.xlabel("Measurement Outcome Normalized (Decimal)", fontsize=14)
        plt.ylabel("Probability", fontsize=14)
        legend_entries = ["TRANSPILER PARAMS",
                          f"Optimization level: {get_stats_key_value(isas_stats, 'settings.optimization_level')}",
                          f"Approximation degree: {get_stats_key_value(isas_stats, 'settings.approximation_degree')}",
                          f"Layout method: {get_stats_key_value(isas_stats, 'settings.layout_method')}",
                          f"Routing method: {get_stats_key_value(isas_stats, 'settings.routing_method')}",
                          f"Translation method: {get_stats_key_value(isas_stats, 'settings.translation_method')}",
                          "",
                          "OPTIMIZATION PARAMS",
                          f"SABRE optimization: {get_stats_key_value(isas_stats, 'settings.sabre_optimization')}",
                          "",
                          "SAMPLER PARAMS",
                          f"Dynamical decoupling: {get_stats_key_value(isas_stats, 'settings.dynamical_decoupling')}",
                          f"Pauli Twirling: {get_stats_key_value(isas_stats, 'settings.pauli_twirling')}",
                          "",
                          "CIRCUIT STATISTICS"]
        for key in isas_stats['csa'][stats_key].keys():
            value = get_stats_key_value(isas_stats, f"csa.{stats_key}.{key}")
            if key in ['ecr', 'cz', 'rzz']:
                legend_entries.append(f"Two-qubit {key.upper()} gates: {value}")
            elif key == 'total_gates':
                legend_entries.append(f"Total number of gates: {value}")
            elif key == 'circuit_depth':
                legend_entries.append(f"Circuit depth: {value}")
            else:
                legend_entries.append(f"Single-qubit {key.upper()} gates: {value}")
        if noise:
            legend_entries.extend(["","MEASUREMENTS STATISTICS", f"Noise percentage: {noise}%"])
        handles = [mlines.Line2D([], [], color='none', label=entry) for entry in legend_entries]
        plt.legend(handles=handles, bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8, frameon=True,
                   framealpha=0.9, edgecolor='black', borderpad=0.3, labelspacing=0.3, handlelength=0)
        plt.tight_layout()
        file_name = f"prob_dist_N{number}_a{a}_backend_{backend}.png"
        # for WINDOWS replace below path with:
        # {BASE_DIR}\\outputs\\{ibm_qpu}\\{job_id}\\{file_name}
        path = f"{BASE_DIR}/outputs/{ibm_qpu}/{job_id}/{file_name}"
        plt.savefig(path)
        plt.close()
        print(f"[{datetime.now()}] - Probability distribution saved in '{path}'")


def plot_a_x_mod_n(factors_result, isas_stats, job_id):
    for a, result in factors_result.items():
        r = result['r']
        x_values = range(0, 2 * r + 1)
        number = get_stats_key_value(isas_stats, 'settings.number_to_factor')
        y_values = [pow(a, x, number) for x in x_values]
        plt.figure(figsize=(15, 8))
        plt.plot(x_values, y_values, marker='o', color='orange')
        plt.title(f"a^x mod N (N={number}, a={a})", fontsize=16)
        plt.xlabel("x", fontsize=14)
        plt.ylabel(f"{a}^x mod {number}", fontsize=14)
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        plt.grid(True)
        plt.tight_layout()
        ibm_qpu = get_stats_key_value(isas_stats, 'settings.ibm_qpu')
        file_name = f"ax_mod_N{number}_a{a}.png"
        # for WINDOWS replace below path with:
        # {BASE_DIR}\\outputs\\{ibm_qpu}\\{job_id}\\{file_name}
        file_path = f"{BASE_DIR}/outputs/{ibm_qpu}/{job_id}/{file_name}"
        plt.savefig(file_path)
        plt.close()
        print(f"[{datetime.now()}] - a^x mod N plot saved as in '{file_path}'")


def plot_quantum_circuit(a, number, qc, ibm_qpu, job_id):
    file_name = f"{ibm_qpu}_quantum_circuit_N{number}_a{a}.png"
    # for WINDOWS replace below path with:
    # {BASE_DIR}\\outputs\\{ibm_qpu}\\{job_id}\\{file_name}
    file_path = f"{BASE_DIR}/outputs/{ibm_qpu}/{job_id}/{file_name}"
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    qc.draw(output='mpl', filename=file_path, idle_wires=False, fold=-1)
    print(f"[{datetime.now()}] - Circuit diagram saved to '{file_path}'")


def plot_physical_circuit_layout(isa, a, number, backend, ibm_qpu, job_id):
    file_name = f"{ibm_qpu}_physical_circuit_layout_N{number}_a{a}.png"
    # for WINDOWS replace below path with:
    # {BASE_DIR}\\outputs\\{ibm_qpu}\\{job_id}\\{file_name}
    file_path = f"{BASE_DIR}/outputs/{ibm_qpu}/{job_id}/{file_name}"
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    layout = plot_circuit_layout(isa, backend, view="physical")
    layout.savefig(file_path)
    print(f"[{datetime.now()}] - Physical circuit layout saved to '{file_path}'")


def save_transpiled_isa(isa, a, number, ibm_qpu):
    file_name = f"{ibm_qpu}_transpiled_isa_N{number}_a{a}.qpy"
    # {BASE_DIR}\outputs\\{ibm_qpu}\\only_stats\\{file_name}
    file_path = f"{BASE_DIR}/outputs/{ibm_qpu}/only_stats/{file_name}"
    with open(file_path, "wb") as f:
        qpy.dump(isa, f)


def get_transpiled_isa(a, number, ibm_qpu):
    file_name = f"{ibm_qpu}_transpiled_isa_N{number}_a{a}.qpy"
    # {BASE_DIR}\\outputs\\{ibm_qpu}\\only_stats\\{file_name}
    file_path = f"{BASE_DIR}/outputs/{ibm_qpu}/only_stats/{file_name}"
    with open(file_path, "rb") as f:
        return qpy.load(f)[0]


def get_stats_key_value(isas_stats, stat_key, default=None):
    keys = stat_key.split(".")
    value = isas_stats
    for k in keys:
        if k not in value:
            raise ValueError(f"No {k} info found")
        value = value.get(k, default)
        if value is default:
            break
    return value


def calculate_noise_percentage(result, r, control_qubits, shots):
    valid_counts = 0
    step = (2 ** control_qubits) / r
    peaks = [int(step * i) for i in range(r)]
    for peak in peaks:
        valid_counts += result.get(format(peak, f'0{control_qubits}b'), 0)
    invalid_counts = (shots - valid_counts) / shots # noise
    invalid_counts_r = round(round(invalid_counts, 3) * 100, 2)
    return invalid_counts_r


def process_job_results(job_id, ibm_account_name):
    service = QiskitRuntimeService(name=ibm_account_name)
    job = service.job(job_id)
    print(f"[{datetime.now()}] - Waiting for job ({job_id}) to finish...")
    while not job.done():
        pass
    print(f"[{datetime.now()}] - Job done, processing results ...")
    print(f"[{datetime.now()}] - Job metrics: {job.metrics()}")
    print(f"[{datetime.now()}] - Job logs: {job.logs()}")
    print(f"[{datetime.now()}] - Job properties: {job.properties(refresh=True)}")
    ibm_qpu = job.backend().name
    isas_stats = read_isas_info(ibm_qpu, job_id)
    a_coefficients = get_stats_key_value(isas_stats, 'settings.a_coefficients')
    number = get_stats_key_value(isas_stats, 'settings.number_to_factor')
    control_qubits = get_stats_key_value(isas_stats, 'settings.control_qubits')
    phases_max_top_number = get_stats_key_value(isas_stats, 'settings.phases_max_top_number')
    result = job.result()
    results = [{k: v for k, v in res.data.output.get_counts().items()} for res in result]
    results = list(zip(a_coefficients, results))
    candidates_rs = get_candidate_rs(number, control_qubits, phases_max_top_number, results)
    plot_results_distribution(results, isas_stats, job_id, candidates_rs)
    factors_result = find_nontrivial_factors(number, candidates_rs)
    if factors_result:
        plot_a_x_mod_n(factors_result, isas_stats, job_id)



