from datetime import datetime
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import SabreLayout
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager as pass_manager
from qiskit_ibm_transpiler.transpiler_service import TranspilerService



class Transpiler:

    def __init__(self, transpiler_params, optimization_params, backend):
        self.isas_stats = {} # Instruction Set Architecture
        self.transpiler_params = transpiler_params
        self.sabre_optimization = optimization_params.pop('sabre_optimization', False)
        self.optimization_params = optimization_params
        self.backend = backend

    def transpile(self, a, qc, initial_layout):
        if initial_layout:
            pm = pass_manager(**self.transpiler_params, initial_layout=initial_layout)
        else:
            pm = pass_manager(**self.transpiler_params)
        if self.sabre_optimization:
            print(f"[{datetime.now()}] - Optimizing layout and routing with SABRE. Params: {self.optimization_params}")
            sl = self.get_sabre_layout()
            pm.layout.replace(index=2, passes=sl)
        print(f"[{datetime.now()}] - Transpilation process started for circuit created with a={a} coefficient")
        isa = pm.run(qc)
        print(f"[{datetime.now()}] - Transpilation process ended for circuit created with a={a} coefficient")
        self.isas_stats[str(a)] = self.get_isa_statistics(isa)
        return isa

    def service_transpile(self, a, qc):
        cloud_transpiler_service = TranspilerService(
            optimization_level=self.transpiler_params.get('optimization_leve'),
            qiskit_transpile_options=self.transpiler_params,
            ai="true"
        )
        isa = cloud_transpiler_service.run(qc)
        self.isas_stats[str(a)] = self.get_isa_statistics(isa)
        return isa

    def get_sabre_layout(self):
        cmap = CouplingMap(self.backend.configuration().coupling_map)
        seed = self.transpiler_params['seed_transpiler']
        sl = SabreLayout(coupling_map=cmap, seed=seed, **self.optimization_params)
        return sl

    def get_isa_statistics(self, isa):
        basis_gates = self.transpiler_params['basis_gates']
        statistics = {gate: isa.count_ops().get(gate, 0) for gate in basis_gates if gate != 'id'}
        statistics.update(total_gates=isa.size())
        statistics.update(circuit_depth=isa.depth(lambda x: x.operation.num_qubits == 2))
        return statistics

    def print_isa_statistics(self):
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
        for a, isa in isas.items():
            self.isas_stats[str(a)] = self.get_isa_statistics(isa)

