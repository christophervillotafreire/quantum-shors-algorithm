import copy
import gc
from algorithm import circuit
from common import backend
from common.settings import get_settings_value_for_key
from datetime import datetime
from services.transpilation import Transpiler
from services import sampling
from qiskit_ibm_runtime.options import SamplerOptions, DynamicalDecouplingOptions, TwirlingOptions
from qiskit.transpiler import Layout
from utilities.job_results import (plot_results_distribution, get_candidate_rs, write_isas_info, save_transpiled_isa,
                                   get_transpiled_isa, plot_quantum_circuit, plot_physical_circuit_layout)


class Shor:

    def __init__(self, is_simulation):
        self.is_simulation = is_simulation
        self.backend = None
        self.sampler = None
        self.transpiler_params = None
        self.sampler_params = None
        self.optimization_params = None

    def find_period(self, args, a_coefficients):
        number = args.number_to_factor
        control_qubits = args.control_qubits
        circuit_class = get_settings_value_for_key(f"circuit_classes.{args.circuit_class}")
        circuit_object = getattr(circuit, circuit_class)()
        if control_qubits:
            print(f"[{datetime.now()}] - Setting the number of control qubits entered by the user: {control_qubits}")
            circuit_object.set_control_qubits(control_qubits)
        ibm_account_name = args.ibm_account_name
        backend_class = args.backend_class
        ibm_quantum_processor = args.ibm_quantum_processor
        sampler_class = args.sampler_class
        shots = args.sampler_shots_number
        phases_max_top_number = args.phases_max_top_number
        only_isas_stats = args.only_isas_stats
        first_kyiv = args.first_kyiv
        from_isas = args.from_isas
        use_fractional_gates = args.backend_use_fractional_gates

        print(f"[{datetime.now()}] - Number of circuits to sample: {len(a_coefficients)}")
        print(f"[{datetime.now()}] - Number of sampler shots per circuit to test: {shots}")
        print(f"[{datetime.now()}] - Circuit class: {circuit_class}")
        print(f"[{datetime.now()}] - Backend class: {backend_class}")
        print(f"[{datetime.now()}] - IBM quantum processor: {ibm_quantum_processor}")

        print(f"[{datetime.now()}] - Creating circuit(s) ...")
        a_qcs = {str(a): circuit_object.create_circuit(number, a) for a in a_coefficients}
        print(f"[{datetime.now()}] - Circuit(s) created")
        gc.collect()

        ibm_qpus = get_settings_value_for_key('ibm_qpus')

        i_layouts = None
        if first_kyiv:
            kyiv_compatible_qpus = self.get_kyiv_compatible_qpus(ibm_qpus)
            if ibm_quantum_processor in kyiv_compatible_qpus:
                i_layouts = self.transpile_kyiv_first(args, a_qcs)

        if use_fractional_gates:
            fg_compatible_qpus = self.get_fg_compatible_qpus(ibm_qpus)
            fractional_gates = True if ibm_quantum_processor in fg_compatible_qpus else False
        else:
            fractional_gates = False
        print(f"[{datetime.now()}] - Setting 'use_fractional_gates' to {fractional_gates} when configuring the backend")

        self._set_backend_object(backend_class, ibm_quantum_processor, ibm_account_name, fractional_gates)
        self._set_transpiler_params(args)
        self._set_sampler_params(args)
        self._set_transpile_optimization_params(args)
        self._set_sampler_object(sampler_class)

        if args.verbose:
            print(f"[{datetime.now()}] - Transpiler params used when transpiling for {ibm_quantum_processor}: {self.transpiler_params}")

        transpiler = Transpiler(self.transpiler_params, copy.deepcopy(self.optimization_params), self.backend)
        if from_isas and not only_isas_stats:
            isas = {str(a): get_transpiled_isa(a, number, ibm_quantum_processor) for a in a_coefficients}
            transpiler.set_isas(isas)
        else:
            isas = {}
            for a, qc in a_qcs.items():
                isas[a] = transpiler.transpile(a, qc, i_layouts[a] if i_layouts else None)
                gc.collect()
        if not only_isas_stats:
            if args.verbose:
                print(f"[{datetime.now()}] - Sampler params: {self.sampler_params}")
                transpiler.print_isa_statistics()
            isas_stats = {'csa': transpiler.get_isas_stats()}
            control_qubits = circuit_object.get_control_qubits()
            isas_info = self.add_settings_to_stats(isas_stats, args, control_qubits, a_coefficients)
            self.check_isas_depth_size(isas, isas_info)
            if isas:
                job = self.sampler.run(list(isas.values()), shots=shots)
                job_id = job.job_id()
                print(f"[{datetime.now()}] - Sampler job submitted with id: {job_id}")
                self.plot_quantum_and_physical_circuits(isas, isas_info, a_qcs, number, circuit_class,
                                                        backend_class, ibm_quantum_processor, job_id)
                if self.is_simulation:
                    return self.get_simulation_results(job, a_coefficients, number, control_qubits,
                                                       phases_max_top_number, isas_info)
                write_isas_info(job_id, isas_info)
            else:
                print(print(f"[{datetime.now()}] - No isas to sample"))
        else:
            transpiler.print_isa_statistics()
            for a in a_coefficients:
                plot_physical_circuit_layout(isas[str(a)], a, number, self.backend, ibm_quantum_processor, "only_stats")
                save_transpiled_isa(isas[str(a)], a, number, ibm_quantum_processor)
        return None, None, None

    def _set_transpiler_params(self, args):
        self.transpiler_params = {
            "backend": self.backend,
            "target": self.backend.target,
            "optimization_level": args.transpiler_optimization_level,
            "seed_transpiler": args.transpiler_seed,
            "basis_gates": get_settings_value_for_key(f"ibm_qpus.{args.ibm_quantum_processor}.basis_gates"),
            "approximation_degree": args.transpiler_approximation_degree,
            "unitary_synthesis_method": args.transpiler_unitary_method,
            "layout_method": args.transpiler_layout_method,
            "routing_method": args.transpiler_routing_method,
            "translation_method": args.transpiler_translation_method
        }
        if args.backend_class == 'ibmqpu':
            self.transpiler_params.update(scheduling_method=args.transpiler_pass_planning_method)
        else:
            self.transpiler_params.update(scheduling_method=None)

    def _set_sampler_params(self, args):
        self.sampler_params = {"mode": self.backend}
        features_options = {}
        if args.sampler_dynamical_decoupling:
            dd_options = DynamicalDecouplingOptions(enable=True, sequence_type=args.sampler_dd_sequence_type,
                                                    extra_slack_distribution=args.sampler_dd_slack_dist,
                                                    scheduling_method=args.sampler_dd_scheduling_method,
                                                    skip_reset_qubits=args.sampler_dd_skip_reset_qubits)
            features_options.update(dynamical_decoupling=dd_options)
        if args.sampler_pt_enable_gates:
            pt_options = TwirlingOptions(enable_gates=True, enable_measure=args.sampler_pt_enable_measure,
                                         num_randomizations=args.sampler_pt_number_randomizations,
                                         shots_per_randomization=args.sampler_pt_shots_randomization,
                                         strategy=args.sampler_pt_strategy)
            features_options.update(twirling=pt_options)

        if features_options:
            sampler_options = SamplerOptions(**features_options)
            self.sampler_params.update(options=sampler_options)

    def _set_transpile_optimization_params(self, args):
        self.optimization_params = {
            "sabre_optimization": args.sabre_optimization,
            "max_iterations": args.sabre_max_iterations,
            "layout_trials": args.sabre_layout_trials,
            "swap_trials": args.sabre_swap_trials,
        }

    def _set_backend_object(self, backend_class, ibm_quantum_processor, ibm_web_channel, fractional_gates):
        backend_class = get_settings_value_for_key(f"backend_classes.{backend_class}")
        self.backend = getattr(backend, backend_class)(ibm_quantum_processor, ibm_web_channel, fractional_gates).get()

    def _set_sampler_object(self, sampler_class):
        sampler_class = get_settings_value_for_key(f"sampler_classes.{sampler_class}")
        self.sampler = getattr(sampling, sampler_class)(self.sampler_params).get()

    def add_settings_to_stats(self, isas_stats, args, control_qubits, a_coefficients):
        settings = {
            "number_to_factor": args.number_to_factor,
            "control_qubits": control_qubits,
            "a_coefficients": a_coefficients,
            "backend": args.backend_class,
            "ibm_qpu": args.ibm_quantum_processor,
            "shots": args.sampler_shots_number,
            "phases_max_top_number": args.phases_max_top_number,
            "optimization_level": self.transpiler_params["optimization_level"],
            "approximation_degree": self.transpiler_params["approximation_degree"],
            "layout_method": self.transpiler_params["layout_method"],
            "routing_method": self.transpiler_params["routing_method"],
            "translation_method": self.transpiler_params["translation_method"],
            "sabre_optimization": self.optimization_params["sabre_optimization"],
            "dynamical_decoupling": args.sampler_dynamical_decoupling,
            "pauli_twirling": args.sampler_pt_enable_gates,
        }
        isas_stats.update(settings=settings)
        return isas_stats

    @staticmethod
    def get_new_layout(original_layout):
        new_layout = Layout()
        for physical_qubit, qubit in original_layout.get_physical_bits().items():
            if qubit._register.name in ['control', 'target']:
                new_layout.add(qubit, physical_qubit)
        return new_layout

    @staticmethod
    def get_kyiv_compatible_qpus(ibm_qpus):
        processor_type = ibm_qpus.get('ibm_kyiv').get('type')
        valid_qpus = [key for key, value in ibm_qpus.items() if value.get('type') == processor_type]
        return valid_qpus

    def transpile_kyiv_first(self, args, a_qcs):
        print(f"[{datetime.now()}] - Obtaining initial layout by first transpiling using Fake Provider for Kyiv QPU")
        self._set_backend_object('fakeprov', 'ibm_kyiv', None)
        self._set_transpiler_params(args)
        self._set_transpile_optimization_params(args)
        print(f"[{datetime.now()}] - Transpiler params when transpiling for FakeKyiv: {self.transpiler_params}")
        transpiler = Transpiler(self.transpiler_params, copy.deepcopy(self.optimization_params), self.backend)
        isas = {a: transpiler.transpile(a, qc, None) for a, qc in a_qcs.items()}
        i_layouts = {a: self.get_new_layout(isa.layout.initial_layout) for a, isa in isas.items()}
        transpiler.print_isa_statistics()
        gc.collect()
        return i_layouts

    @staticmethod
    def get_fg_compatible_qpus(ibm_qpus):
        valid_qpus = [key for key, value in ibm_qpus.items() if value.get('fractional_gates') == True]
        return valid_qpus

    @staticmethod
    def check_isas_depth_size(isas, isas_info):
        for a in isas_info['csa'].keys():
            gates = isas_info.get('csa').get(a)
            dq_gates = gates.get('ecr', 0) or gates.get('cz', 0) or gates.get('rzz', 0)
            if dq_gates > 100000:
                print(f"[{datetime.now()}] - ISA circuit for a {a} exceeded the limit of total occurrences "
                      f"of 'double qubits' gates of 100000. Circuit not submitted for sampling")
                del isas[a]

    def plot_quantum_and_physical_circuits(self, isas, isas_info, a_qcs, number, circuit_class,
                                           backend_class, ibm_quantum_processor, job_id):
        for a in isas_info['csa'].keys():
            if circuit_class != 'sequential_qft':
                plot_quantum_circuit(a, number, a_qcs[a], ibm_quantum_processor, job_id)
            if backend_class != 'ideal':
                plot_physical_circuit_layout(isas[a], a, number, self.backend, ibm_quantum_processor, job_id)

    @staticmethod
    def get_simulation_results(job, a_coefficients, number, control_qubits, phases_max_top_number, isas_info):
        job_id = job.job_id()
        print(f"[{datetime.now()}] - Waiting results for job id: {job_id}")
        result = job.result()
        print(f"[{datetime.now()}] - Job done, processing results ...")
        results = [{k: v for k, v in res.data.output.get_counts().items()} for res in result]
        results = list(zip(a_coefficients, results))
        rs = get_candidate_rs(number, control_qubits, phases_max_top_number, results)
        plot_results_distribution(results, isas_info, job_id, rs)
        return rs, job_id, isas_info


