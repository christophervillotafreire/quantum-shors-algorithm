from datetime import datetime
from qiskit.transpiler import CouplingMap # Mapa de interconexiones físicas que dice qué qubit está enlazado por cable microondas al otro.
from qiskit.transpiler.passes import SabreLayout # Enrutador heurístico estocástico y muy avanzado (SABRE), vital para el ruido en profundidad (Niveles CNOTs).
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager as pass_manager # Generador de pases de compilación oficial por fases 
from qiskit_ibm_transpiler.transpiler_service import TranspilerService # Transpilador impulsado por IA de la API de la nube (Si se deseara usar)



class Transpiler:
    """
    Clase envoltoria que controla la "Compilación Cuántica" (Transpilación) del circuito.
    Toma las funciones lógicas y unitarias limpias sin restriccciones de nuestro código (`circuit.py`), 
    y las despedaza reensamblándolas para que quepan y se ajusten en la topología torcida y con severas limitantes geométricas de un Chip Real de HW (Creando el ISA).
    """

    def __init__(self, transpiler_params, optimization_params, backend):
        self.isas_stats = {} # Diccionario donde se almacena el conteo de compuertas nativas al finalizar (Instruction Set Architecture Stats)
        self.transpiler_params = transpiler_params # Ej: Niveles de optimización (0, 1, 2, 3), Métodos para desarmar "b_mod_n gate", seeds
        self.sabre_optimization = optimization_params.pop('sabre_optimization', False)
        self.optimization_params = optimization_params # Hiperparámetros profundos iterativos del SABRE local loop
        self.backend = backend

    def transpile(self, a, qc, initial_layout):
        """
        Método núcleo de compilación. Genera un PassManager que sabe cómo adaptar circuitos para el backend asociado.
        Destroza nuestras compuertas lógicas (como Toffolis/CCX) en compuertas de uno y dos qubits (CX, ECR, RZ).
        """
        if initial_layout:
            pm = pass_manager(**self.transpiler_params, initial_layout=initial_layout)
        else:
            pm = pass_manager(**self.transpiler_params)
            
        # Si nuestra configuración dictó que sobrescribiéramos SABRE, interceptamos el flujo de pases:
        if self.sabre_optimization:
            print(f"[{datetime.now()}] - Optimizing layout and routing countermeasures with custom SABRE parameters. Params: {self.optimization_params}")
            sl = self.get_sabre_layout()
            # En el PresetPassManager, index=2 corresponde a las capas de Layout (ubicar a dónde va qué lógico -> al qubit real físico).
            # Aquí inyectamos y forzamos nuestra semilla de ensayos SABRE estricta.
            if sl is not None and pm.layout is not None:
                pm.layout.replace(index=2, passes=sl)
            else:
                print(f"[{datetime.now()}] - WARNING: Skipping SABRE layout replacement: pm.layout or SabreLayout not available for this backend (ideal/simulator backends may not support this). SABRE is already configured via layout_method/routing_method params.")
        
        print(f"[{datetime.now()}] - Transpilation process started for circuit created with a={a} coefficient")
        # Corre el flujo transpilación en la QPU o target. Esto puede tomar horas si se usan algoritmos heurísticos en matrices muy grandes.
        isa = pm.run(qc)
        print(f"[{datetime.now()}] - Transpilation process ended for circuit created with a={a} coefficient")
        
        # Una vez obtenido el circuito final y "feo" (pero funcional para hardware), salvamos e integramos sus estadísticas de profundidad/SWAPs.
        self.isas_stats[str(a)] = self.get_isa_statistics(isa)
        return isa

    def service_transpile(self, a, qc):
        """Alternativa si se usa la suscripción a los servicios de IBM impulsados por IA predictiva Cloud."""
        cloud_transpiler_service = TranspilerService(
            optimization_level=self.transpiler_params.get('optimization_leve'),
            qiskit_transpile_options=self.transpiler_params,
            ai="true"
        )
        isa = cloud_transpiler_service.run(qc)
        self.isas_stats[str(a)] = self.get_isa_statistics(isa)
        return isa

    def get_sabre_layout(self):
        """
        Constructor de la clase heurística estocástica de búsqueda local SABRE.
        Toma el mapa físico del laberinto conectivo del hardware (`CouplingMap`) y ejecuta sus hiperparámetros (intentos iteracionales múltiples).
        """
        try:
            cmap = CouplingMap(self.backend.configuration().coupling_map)
            seed = self.transpiler_params['seed_transpiler']
            sl = SabreLayout(coupling_map=cmap, seed=seed, **self.optimization_params)
            return sl
        except (AttributeError, Exception) as e:
            print(f"[{datetime.now()}] - WARNING: Could not build SabreLayout (backend may not expose coupling_map): {e}")
            return None

    def get_isa_statistics(self, isa):
        """
        Analizador de Hardware. Entra un circuito compilado ("Instruction Set Architecture") y extrae:
        - Total de compuertas (Lógicas rotaciones puras frente a cuántas de 2-qubits ruidosas).
        - Profundidad (Longitud del camino crítico o máxima retención encadenada de tiempo de los qubits).
        A mayor profundidad/compuertas de dos qubits, mayor desastre T1/T2 coherencia e inviabilidad en el mundo físico NISQ.
        """
        basis_gates = self.transpiler_params['basis_gates'] # (ej. cx, id, rz, sx, x)
        statistics = {gate: isa.count_ops().get(gate, 0) for gate in basis_gates if gate != 'id'}
        statistics.update(total_gates=isa.size()) # La suma de cada simple pulso.
        statistics.update(circuit_depth=isa.depth(lambda x: x.operation.num_qubits == 2)) # Lambda filtra para contar la "gravedad de profundidad entrelazada" que realmente duele al hardware = 2qubits entangle
        return statistics

    def print_isa_statistics(self):
        """Desdoble puramente visual a la consola CLI útil para el científico de datos observador iterando perfiles de Qubits"""
        for a, statistics in self.isas_stats.items():
            print(f"[{datetime.now()}] - Statistics for circuit created with a={a} coefficient:")
            for key in statistics.keys():
                if key in ['ecr', 'cz', 'rzz']:
                    print(f"[{datetime.now()}] - Two-qubit {key.upper()} gates: {statistics[key]}")
                elif key == 'total_gates':
                    print(f"[{datetime.now()}] - Total number of gates: {statistics[key]}")
                elif key == 'circuit_depth':
                    print(f"[{datetime.now()}] - Circuit depth: {statistics[key]}")
                else:
                    print(f"[{datetime.now()}] - Single-qubit {key.upper()} gates: {statistics[key]}")

    def get_isas_stats(self):
        return self.isas_stats

    def set_isas(self, isas):
        # Permite cargar un diccionario si en memoria en un paso previo el usuario ya tenía su ISA para obviar el compile.
        for a, isa in isas.items():
            self.isas_stats[str(a)] = self.get_isa_statistics(isa)

