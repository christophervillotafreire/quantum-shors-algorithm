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
    """Guarda localmente las métricas extraídas puras del hardware (ISA) asociadas a una ID en formato JSON"""
    # for WINDOWS replace below path with:
    # {BASE_DIR}\\outputs\\{isas_stats['settings']['ibm_qpu']}\\{job_id}\\isas_stats.json
    file_path = f"{BASE_DIR}/outputs/{isas_stats['settings']['ibm_qpu']}/{job_id}/isas_stats.json"
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(isas_stats, file, indent=4)


def read_isas_info(ibm_qpu, job_id):
    """Recupera estadísticas ISA previas de un ensayo de corrida ya terminado"""
    # for WINDOWS replace below path with:
    # {BASE_DIR}\\outputs\\{ibm_qpu}\\{job_id}\\isas_stats.json
    with open(f"{BASE_DIR}/outputs/{ibm_qpu}/{job_id}/isas_stats.json", 'r') as file:
        return json.load(file)


def find_nontrivial_factors(number, rs):
    """
    Núcleo del POST-Procesamiento de Shor (Paso Final Clásico).
    Toma los sospechosos periodos "r" deducidos del circuito cuántico e intenta
    aplicar la fórmula de factorización p,q = gcd(a^(r/2) ± 1, N).
    """
    results = {}
    for a, rs in rs.items():
        r = sorted(rs)[0] if rs else None
        if r:
            print(f"[{datetime.now()}] - Checking period r = {r}")
            # Si a pesar de todo el esfuerzo cuántico "r" resultó ser impar (ej: 3, 5, 7)... Fracasamos. 
            # La matemática de Euler prohíbe el cálculo pues a^(r/2) daría una fracción en el exponente.
            if r % 2 != 0:
                print(f"[{datetime.now()}] - Period {r} is odd. Non-trivial factors can't be calculated")
                continue
                
            # Intento de Factorización (Raíces de la Unidad)
            p = gcd(a ** (r // 2) - 1, number)
            q = gcd(a ** (r // 2) + 1, number)
            
            # Filtro: A veces la ecuación devuelve [1, 15] como factores de 15. Esto es inútil (triviales)
            trivial_factors = [1, number]
            if p in trivial_factors or q in trivial_factors:
                print(f"[{datetime.now()}] - Trivial factors found: {p}, {q}")
                continue
                
            # Éxito rotundo: p * q logran restaurar el N Original exitosamente
            if p*q == number:
                print(f"[{datetime.now()}] - Founded factors of {number}: {p} and {q}")
                results[a] = {'r': r, 'factors': [p, q]}
                continue
                
    if not results:
        print(f"[{datetime.now()}] - No non-trivial factors found for number {number}")
    return results


def get_candidate_rs(number, control_qubits, phases_max_top_number, results):
    """
    Subrutina Crucial Pos-Cuántica (Fracciones Continuas).
    Lee el histograma ruidoso escupido por el IBM Quantum (sus mediciones binarias).
    """
    candidates = {}
    for result in results:
        a = result[0]
        counts = result[1]
        rs = []
        
        # Ordenamos los estados binarios que más impacto/frecuencia tuvieron en el simulador
        counts_sorted = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:phases_max_top_number]
        for (bit_string, count) in counts_sorted:
            # Convierte la medición |010...100> binaria a un decimal puro
            decimal = int(bit_string, 2)
            
            # Se aproxima al decimal fraccionario del oráculo original ( FASE = medida / 2^n )
            phase = decimal / 2**control_qubits
            
            # MAGIA FRACCIONAL CONTINUADA: El denonimador "r" limitando N se aproxima como el PERIODO cuántico
            fraction = Fraction(phase).limit_denominator(number)
            s, r = fraction.numerator, fraction.denominator
            
            # Se comprueba rápidamente si "r" cumple la ley fundamental a^r mod N == 1
            if r not in rs and number > r > 1 == pow(a, r, number):
                rs.append(r)
        candidates[a] = rs
    print(f"[{datetime.now()}] - Candidates period r(s) for each \"a\" coefficient: {candidates}")
    return candidates


def plot_results_distribution(results, isas_stats, job_id, candidates_rs):
    """
    Graficador de Matplotlib exhaustivo.
    Dibuja los histogramas de probabilidad P(x) y añade una enorme leyenda dinámica lateral
    conteniendo TODAS las estadísticas pasadas de transpiler, sampler, hardware físico, y ruteo utilizadas, 
    muy útil para papers y análisis comparativo estricto visual.
    """
    for result in results:
        a = result[0]
        stats_key = str(a)
        counts = result[1]
        
        # Lectura engorrosa por llaves en el diccionario
        number = get_stats_key_value(isas_stats, 'settings.number_to_factor')
        control_qubits = get_stats_key_value(isas_stats, 'settings.control_qubits')
        shots = get_stats_key_value(isas_stats, 'settings.shots')
        backend = get_stats_key_value(isas_stats, 'settings.backend')
        ibm_qpu = get_stats_key_value(isas_stats, 'settings.ibm_qpu')
        
        rs = sorted(candidates_rs.get(a, []))
        r = rs[0] if rs else None
        
        # Algoritmo experimental externo para ponderar cuánto ruido hubo destruyendo picos perfectos
        noise = calculate_noise_percentage(counts, r, control_qubits, shots) if r else None
        
        # Preparamos el Eje X con los estados normalizados
        dist = np.zeros((2**control_qubits))
        xdist = np.arange(len(dist)) / 2**control_qubits
        
        # Ponderación Eje Y
        for x in counts.keys():
            dist[int(x, 2)] = counts[x] / shots
            
        plt.figure(figsize=(8, 5))
        plt.plot(xdist, dist)
        
        # Título Condicional
        title = f"N={number}, a={a}, shots={shots}, period={r}" if r else f"N={number}, a={a}, shots={shots}, period not found"
        plt.title(title, fontsize=16)
        plt.xlabel("Measurement Outcome Normalized (Decimal)", fontsize=14)
        plt.ylabel("Probability", fontsize=14)
        
        # Inyección super densa y descriptiva de las mitigaciones usadas
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
                          
        # Compilación de Hardware
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
    """
    Gráfica puramente matemática didáctica de "demostración".
    Genera el serrucho o senoidal perfecta donde el humano puede ver repetirse visualmente (a^x MOD N)
    hasta que pega con 1 cíclicamente (confirmando el periodo "r" cuántico visualmente).
    """
    for a, result in factors_result.items():
        r = result['r']
        x_values = range(0, 2 * r + 1) # Despliega hasta dos tramos enteros del periodo
        number = get_stats_key_value(isas_stats, 'settings.number_to_factor')
        y_values = [pow(a, x, number) for x in x_values] # (a^x mod N) Evaluación pura.
        
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
    """Genera la imagen PNG canónica de líneas de partitura (nuestro circuito lógico original)."""
    file_name = f"{ibm_qpu}_quantum_circuit_N{number}_a{a}.png"
    # for WINDOWS replace below path with:
    # {BASE_DIR}\\outputs\\{ibm_qpu}\\{job_id}\\{file_name}
    file_path = f"{BASE_DIR}/outputs/{ibm_qpu}/{job_id}/{file_name}"
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
        
    # Usa Matplotlib embebido de Qiskit para dibujar. Fold=-1 impide cortes multipágina para matrices enormes.
    qc.draw(output='mpl', filename=file_path, idle_wires=False, fold=-1)
    print(f"[{datetime.now()}] - Circuit diagram saved to '{file_path}'")


def plot_physical_circuit_layout(isa, a, number, backend, ibm_qpu, job_id):
    """
    Extrae la telaraña de conexiones donde se muestra exactamente en qué qubits físicos de la QPU
    se rutearon nuestros qubits virtuales y cómo se interconectan con compuertas SWAPs por colores.
    """
    file_name = f"{ibm_qpu}_physical_circuit_layout_N{number}_a{a}.png"
    # for WINDOWS replace below path with:
    # {BASE_DIR}\\outputs\\{ibm_qpu}\\{job_id}\\{file_name}
    file_path = f"{BASE_DIR}/outputs/{ibm_qpu}/{job_id}/{file_name}"
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    try:
        layout = plot_circuit_layout(isa, backend, view="physical")
        layout.savefig(file_path)
        print(f"[{datetime.now()}] - Physical circuit layout saved to '{file_path}'")
    except Exception as e:
        print(f"[{datetime.now()}] - Warning: Could not plot physical circuit layout. Error: {e}")


def save_transpiled_isa(isa, a, number, ibm_qpu):
    """Guarda (Serialize) en binario un circuito transpilado masivo .QPY para evadir sobrecompilaciones."""
    file_name = f"{ibm_qpu}_transpiled_isa_N{number}_a{a}.qpy"
    # {BASE_DIR}\outputs\\{ibm_qpu}\\only_stats\\{file_name}
    file_path = f"{BASE_DIR}/outputs/{ibm_qpu}/only_stats/{file_name}"
    with open(file_path, "wb") as f:
        qpy.dump(isa, f)


def get_transpiled_isa(a, number, ibm_qpu):
    """Retorna a la RAM matriz .QPY binaria de disco duro."""
    file_name = f"{ibm_qpu}_transpiled_isa_N{number}_a{a}.qpy"
    # {BASE_DIR}\\outputs\\{ibm_qpu}\\only_stats\\{file_name}
    file_path = f"{BASE_DIR}/outputs/{ibm_qpu}/only_stats/{file_name}"
    with open(file_path, "rb") as f:
        return qpy.load(f)[0]


def get_stats_key_value(isas_stats, stat_key, default=None):
    """Lector anidado de JSon que extrae info con notación dot string formated."""
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
    """
    Rutina heurística inventada por el autor para sacar un '% De Falla Pura Cuántica'.
    Si el histograma tiene disparos dispersos fuera de los picos que debían apuntar exactamente a fraccciones de 'r', 
    son contabilizados y expuestos para ilustrar qué tan roto llegó el entrelazamiento por la decoherencia HW.
    """
    valid_counts = 0
    step = (2 ** control_qubits) / r # Saltos perfectos donde debería haber barras/picos de prob
    peaks = [int(step * i) for i in range(r)]
    for peak in peaks:
        valid_counts += result.get(format(peak, f'0{control_qubits}b'), 0)
    invalid_counts = (shots - valid_counts) / shots # noise (basura ambiental o desalineación X gate)
    invalid_counts_r = round(round(invalid_counts, 3) * 100, 2)
    return invalid_counts_r


def process_job_results(job_id, ibm_account_name):
    """
    Orquestador Final: Asume que un trabajo fue inyectado horas atrás en la nube de IBM.
    Llama a los servidores, descarga, empaqueta su diccionario, dispara la matemática de 
    fracciones continuas y manda graficar de golpe todo el resultado visual del Experimento en las carpetas Locales.
    """
    service = QiskitRuntimeService(name=ibm_account_name)
    job = service.job(job_id)
    print(f"[{datetime.now()}] - Waiting for job ({job_id}) to finish...")
    while not job.done():
        pass # Spin lock pasivo esperando contestación asíncrona (A veces dura 3 días en Cola la nube)
        
    print(f"[{datetime.now()}] - Job done, processing results ...")
    print(f"[{datetime.now()}] - Job metrics: {job.metrics()}")
    print(f"[{datetime.now()}] - Job logs: {job.logs()}")
    print(f"[{datetime.now()}] - Job properties: {job.properties(refresh=True)}")
    
    # Extraemos información vital para nombrar archivos y cruzar metadatos cruzando la config original.
    ibm_qpu = job.backend().name
    isas_stats = read_isas_info(ibm_qpu, job_id)
    a_coefficients = get_stats_key_value(isas_stats, 'settings.a_coefficients')
    number = get_stats_key_value(isas_stats, 'settings.number_to_factor')
    control_qubits = get_stats_key_value(isas_stats, 'settings.control_qubits')
    phases_max_top_number = get_stats_key_value(isas_stats, 'settings.phases_max_top_number')
    
    # Desempaqueta y aplana los dicts nativos del Primitivo V2
    result = job.result()
    results = [{k: v for k, v in res.data.output.get_counts().items()} for res in result]
    results = list(zip(a_coefficients, results))
    
    # Procesar Clásicamente buscando Periodos/Factores...
    candidates_rs = get_candidate_rs(number, control_qubits, phases_max_top_number, results)
    plot_results_distribution(results, isas_stats, job_id, candidates_rs) # Gráfico 1: Barras/Estado Real NISQ
    
    factors_result = find_nontrivial_factors(number, candidates_rs)
    if factors_result:
        plot_a_x_mod_n(factors_result, isas_stats, job_id) # Gráfico 2: Exito Matemático de Función Inversa



