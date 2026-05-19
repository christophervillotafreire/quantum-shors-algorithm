import copy
import gc # Garbage Collector para liberar memoria en simulaciones pesadas
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
    """
    Clase principal que orquesta la ejecución del algoritmo de Shor.
    Se encarga de configurar el backend, generar los circuitos cuánticos,
    transpilarlos (compilarlos) para el hardware específico (o simulador),
    y ejecutar el muestreo (sampling) para realizar la Estimación de Fase Cuántica (QPE).
    """

    def __init__(self, is_simulation):
        # Indica si se correrá en un simulador local (ideal/ruido) o en un backend en la nube
        self.is_simulation = is_simulation
        # Variables que almacenarán los objetos y parámetros de ejecución
        self.backend = None # El dispositivo cuántico o simulador subyacente
        self.sampler = None # Primitiva Sampler de Qiskit Runtime (ejecuta y mide circuitos)
        self.transpiler_params = None # Parámetros para reducir la profundidad del circuito
        self.sampler_params = None # Opciones de mitigación de errores para el hardware
        self.optimization_params = None # Opciones personalizadas de ruteo y asignación tipo SABRE

    def find_period(self, args, a_coefficients):
        """
        Método central que ejecuta la búsqueda de periodo cuántico (QPE) subyacente a Shor.
        Recibe los argumentos de consola de ejecución y la lista de coeficientes primos relativos 'a'.
        """
        number = args.number_to_factor # El número N que intentamos factorizar
        control_qubits = args.control_qubits # Número de qubits para la precisión de la estimación de fase
        
        # Obtiene dinámicamente la clase que construirá el circuito (Ej: RegisterQC)
        circuit_class = get_settings_value_for_key(f"circuit_classes.{args.circuit_class}")
        circuit_object = getattr(circuit, circuit_class)()
        
        # Si el usuario definió manualmente los qubits de control ideal a usar, se asientan
        if control_qubits:
            print(f"[{datetime.now()}] - Setting the number of control qubits entered by the user: {control_qubits}")
            circuit_object.set_control_qubits(control_qubits)
            
        # Extracción de variables de configuración para el hardware y experimentación
        ibm_account_name = args.ibm_account_name
        backend_class = args.backend_class
        ibm_quantum_processor = args.ibm_quantum_processor
        sampler_class = args.sampler_class
        shots = args.sampler_shots_number # Número de veces repetidas a correr para obtener un buen histograma
        phases_max_top_number = args.phases_max_top_number
        only_isas_stats = args.only_isas_stats
        from_isas = args.from_isas
        use_fractional_gates = args.backend_use_fractional_gates

        print(f"[{datetime.now()}] - Number of circuits to sample: {len(a_coefficients)}")
        print(f"[{datetime.now()}] - Number of sampler shots per circuit to test: {shots}")
        print(f"[{datetime.now()}] - Circuit class: {circuit_class}")
        print(f"[{datetime.now()}] - Backend class: {backend_class}")
        print(f"[{datetime.now()}] - IBM quantum processor: {ibm_quantum_processor}")

        print(f"[{datetime.now()}] - Creating circuit(s) ...")
        # Generación teórica ideal de los circuitos correspondientes a cada 'a'
        a_qcs = {str(a): circuit_object.create_circuit(number, a) for a in a_coefficients}
        print(f"[{datetime.now()}] - Circuit(s) created")
        gc.collect() # Libera memoria sobrante por instanciar circuitos grandes

        ibm_qpus = get_settings_value_for_key('ibm_qpus')

        i_layouts = None

        # Validación si usar compuertas fraccionales apoyadas nativamente por QPUs recientes
        if use_fractional_gates:
            fg_compatible_qpus = self.get_fg_compatible_qpus(ibm_qpus)
            fractional_gates = True if ibm_quantum_processor in fg_compatible_qpus else False
        else:
            fractional_gates = False
        print(f"[{datetime.now()}] - Setting 'use_fractional_gates' to {fractional_gates} when configuring the backend")

        # Procedimiento de configuración de componentes de IBM Qiskit
        self._set_backend_object(backend_class, ibm_quantum_processor, ibm_account_name, fractional_gates)
        self._set_transpiler_params(args)
        self._set_sampler_params(args)
        self._set_transpile_optimization_params(args)
        self._set_sampler_object(sampler_class)

        if args.verbose:
            print(f"[{datetime.now()}] - Transpiler params used when transpiling for {ibm_quantum_processor}: {self.transpiler_params}")

        # Se inicializa nuestra clase envoltorio 'Transpiler' personal
        transpiler = Transpiler(self.transpiler_params, copy.deepcopy(self.optimization_params), self.backend)
        
        # Transpilación a circuitos ISA (Instruction Set Architecture), lo que significa ajustarlos 
        # y rutiarlos obligatoriamente a las compuertas base reales de la topología física Hardware
        if from_isas and not only_isas_stats:
            # Recupera desde almacenamiento local circuitos compilados para omitir recompilación que toma horas
            isas = {str(a): get_transpiled_isa(a, number, ibm_quantum_processor) for a in a_coefficients}
            transpiler.set_isas(isas)
        else:
            isas = {}
            for a, qc in a_qcs.items():
                # Transpila efectivamente el circuito ideal usando heurísticas tipo SABRE asignando Layouts
                isas[a] = transpiler.transpile(a, qc, i_layouts[a] if i_layouts else None)
                gc.collect() # Recolección de basura paso a paso porque el transpilador consume extrema RAM
                
        if not only_isas_stats:
            if args.verbose:
                print(f"[{datetime.now()}] - Sampler params: {self.sampler_params}")
                transpiler.print_isa_statistics() # Profundidad compilada, compuertas lógicas (CX/CZ etc.)
                
            isas_stats = {'csa': transpiler.get_isas_stats()}
            control_qubits = circuit_object.get_control_qubits()
            # Mapea todos los valores y recolecciones generadas para adjuntarlos al archivo JSON final
            isas_info = self.add_settings_to_stats(isas_stats, args, control_qubits, a_coefficients)
            
            # Valida la profundidad física de los SWAPs/CNOTs para no exceder limitantes exagerados numéricos nube
            self.check_isas_depth_size(isas, isas_info)
            if isas:
                # Submisión del Job propiamente dicho a IBM Quantum Runtime Primitive o simulador en local
                job = self.sampler.run(list(isas.values()), shots=shots)
                job_id = job.job_id()
                print(f"[{datetime.now()}] - Sampler job submitted with id: {job_id}")
                
                # Trazado y dibujo del circuito tanto teórico como posicionado (Hardware Heavy-Hex etc)
                self.plot_quantum_and_physical_circuits(isas, isas_info, a_qcs, number, circuit_class,
                                                        backend_class, ibm_quantum_processor, job_id)
                                                        
                # Si estamos localmente en un simulador, procesamos sincrónicamente e interceptamos resultados de inmediato
                if self.is_simulation:
                    return self.get_simulation_results(job, a_coefficients, number, control_qubits,
                                                       phases_max_top_number, isas_info)
                                                       
                # Si fue al hardware real asincrónico (podría tomar muchas horas en cola), registramos el ID por ahora
                write_isas_info(job_id, isas_info)
            else:
                print(print(f"[{datetime.now()}] - No isas to sample"))
        else:
            # Modo sólo estadísticas: omite simulación, compila, hace dumps (.json/.pdf) e imprime profundidad y densidad
            transpiler.print_isa_statistics()
            for a in a_coefficients:
                plot_physical_circuit_layout(isas[str(a)], a, number, self.backend, ibm_quantum_processor, "only_stats")
                save_transpiled_isa(isas[str(a)], a, number, ibm_quantum_processor)
        return None, None, None

    def _set_transpiler_params(self, args):
        """
        Define las variables lógicas para compilar el circuito de Shor.
        Aquí se especifican niveles de optimización (0-3), y diferentes plugins/heurísticas
        de Qiskit para empaquetar operaciones y asignar qubits lógicos en los hilos topológicos de la realidad.
        """
        self.transpiler_params = {
            "backend": self.backend,
            "target": self.backend.target, # El Target abstrae propiedades reales con ruido simulados de FakeBackends/Físico
            "optimization_level": args.transpiler_optimization_level,
            "seed_transpiler": args.transpiler_seed, # Semilla repetición estocástica de transpilaciones heurísticas
            "basis_gates": get_settings_value_for_key(f"ibm_qpus.{args.ibm_quantum_processor}.basis_gates"), # Compuertas nativas (CX, ECR u otras)
            "approximation_degree": args.transpiler_approximation_degree,
            "unitary_synthesis_method": args.transpiler_unitary_method,
            "layout_method": args.transpiler_layout_method, # Métodos comunes: default, sabre, dense
            "routing_method": args.transpiler_routing_method, # SABRE implementa inserción optimizada de SWAP
            "translation_method": args.transpiler_translation_method
        }
        # Si corre en QPU real ibmqpu, habilita temporalmente metodologías de planeación/timing extra de mitigación
        if args.backend_class == 'ibmqpu':
            self.transpiler_params.update(scheduling_method=args.transpiler_pass_planning_method)
        else:
            self.transpiler_params.update(scheduling_method=None)

    def _set_sampler_params(self, args):
        """
        Activa y consolida parámetros en la Ejecutiva Runtime Primitive para robustecer y mitigar
        resultados durante el muestreo en hardware ruidoso o FakeBackends con perfiles de decoherencia térmicos.
        """
        self.sampler_params = {"mode": self.backend}
        features_options = {}
        
        # Dynamical Decoupling (Mitigación de mitigación T1/T2 desfasaje por relajación térmica pasiva libre):
        # Inserta trenes de pulsos vacíos para "resetear el eco de spin" limitando ruidos de espurios e interactuando localizaciones mientras inactivos
        if args.sampler_dynamical_decoupling:
            dd_options = DynamicalDecouplingOptions(enable=True, sequence_type=args.sampler_dd_sequence_type,
                                                    extra_slack_distribution=args.sampler_dd_slack_dist,
                                                    scheduling_method=args.sampler_dd_scheduling_method,
                                                    skip_reset_qubits=args.sampler_dd_skip_reset_qubits)
            features_options.update(dynamical_decoupling=dd_options)
            
        # Pauli Twirling (Mitigación del sesgo de los errores coherentes direccionales):
        # Aleatoriza la aparición del error en cadenas convirtiendo errores problemáticos y estructurados (fase/coherent) en simples canales de Pauly azarosos. Inyecta variaciones
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
        """Prepara hiperparámetros extendidos propios internos para exprimir eficiencias extrayendo Layout/Rutings tipo SABRE avanzados"""
        self.optimization_params = {
            "sabre_optimization": args.sabre_optimization, # Determina si encender SABRE extra loop
            "max_iterations": args.sabre_max_iterations, # Ciclos SABRE
            "layout_trials": args.sabre_layout_trials, # Semillas azar de ruteo base iterativo
            "swap_trials": args.sabre_swap_trials, # Búsqueda local de inserción SWAP heurísticamente
        }

    def _set_backend_object(self, backend_class, ibm_quantum_processor, ibm_web_channel, fractional_gates):
        """Obtiene una Instancia conector ya sea para SimulatorAer ruidoso/ideal, o bien inicializador Servidor IBM Hardware Real"""
        backend_class = get_settings_value_for_key(f"backend_classes.{backend_class}")
        self.backend = getattr(backend, backend_class)(ibm_quantum_processor, ibm_web_channel, fractional_gates).get()

    def _set_sampler_object(self, sampler_class):
        """Invoca a los ejecutores en forma Primitives Sampler de Qskit que estandarice respuestas"""
        sampler_class = get_settings_value_for_key(f"sampler_classes.{sampler_class}")
        self.sampler = getattr(sampling, sampler_class)(self.sampler_params).get()

    def add_settings_to_stats(self, isas_stats, args, control_qubits, a_coefficients):
        """Envuelve la sesión de configuración en un dict serializable de estadísiticas de control/transpilador"""
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
        """Copia y filtra las asignaciones (Layout) para quedarse estrictamente sólo con los registros control y target deseados."""
        new_layout = Layout()
        for physical_qubit, qubit in original_layout.get_physical_bits().items():
            if qubit._register.name in ['control', 'target']:
                new_layout.add(qubit, physical_qubit)
        return new_layout



    @staticmethod
    def get_fg_compatible_qpus(ibm_qpus):
        """Filtra y devuelve listados QPUs de IBM que soportan compuertas base angulares nativas (fractional_gates)."""
        valid_qpus = [key for key, value in ibm_qpus.items() if value.get('fractional_gates') == True]
        return valid_qpus

    @staticmethod
    def check_isas_depth_size(isas, isas_info):
        """
        Función de salvaguarda: Chequea que el circuito transpilado ISA general
        no cuente con una cantidad gigantesca desproporcionada de compuertas entrelazadoras (2-qubits).
        Si supera 100K es un Shor colosal impráctico de validar y descarta la subida.
        """
        for a in isas_info['csa'].keys():
            gates = isas_info.get('csa').get(a)
            dq_gates = gates.get('ecr', 0) or gates.get('cz', 0) or gates.get('rzz', 0)
            if dq_gates > 100000:
                print(f"[{datetime.now()}] - ISA circuit for a {a} exceeded the limit of total occurrences "
                      f"of 'double qubits' gates of 100000. Circuit not submitted for sampling")
                del isas[a]

    def plot_quantum_and_physical_circuits(self, isas, isas_info, a_qcs, number, circuit_class,
                                           backend_class, ibm_quantum_processor, job_id):
        """Solicita esquemas lógicos visuales convencionales, así como diagramación del embebido sobre el Plano Físico de ibm chip"""
        for a in isas_info['csa'].keys():
            if circuit_class != 'sequential_qft':
                plot_quantum_circuit(a, number, a_qcs[a], ibm_quantum_processor, job_id)
            if backend_class != 'ideal':
                plot_physical_circuit_layout(isas[a], a, number, self.backend, ibm_quantum_processor, job_id)

    @staticmethod
    def get_simulation_results(job, a_coefficients, number, control_qubits, phases_max_top_number, isas_info):
        """
        Encargado final de post-procesamiento. Cuando el simulador local provee las bit-strings o
        patrones de colapso de medida (Counts), recupera las densidades del histograma poblacional y
        llama al posprocesamiento Clásico (Fracciones continuas) de la Utilidad get_candidate_rs para inferir el "r".
        """
        job_id = job.job_id()
        print(f"[{datetime.now()}] - Waiting results for job id: {job_id}")
        result = job.result()
        print(f"[{datetime.now()}] - Job done, processing results ...")
        
        # Array extraído de iteraciones Count de Estados del Output Medido Clásico dict
        results = [{k: v for k, v in res.data.output.get_counts().items()} for res in result]
        results = list(zip(a_coefficients, results))
        
        # Se envía para posprocesamiento Clásico de Algoritmo de Fracciones continuas para cada factor a y adivina Períodos (rs)
        rs = get_candidate_rs(number, control_qubits, phases_max_top_number, results)
        
        # Plotea y mapea distribución de salidas exitosas en gráficos interactivos
        plot_results_distribution(results, isas_info, job_id, rs)
        return rs, job_id, isas_info


