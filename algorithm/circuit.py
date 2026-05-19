import numpy as np # Importa NumPy para manejar matrices matemáticas y arreglos
from abc import ABC, abstractmethod # Importa clases base abstractas y el decorador abstractmethod para definir interfaces
from math import log2, ceil # Importa el logaritmo en base 2 y la función techo (redondeo hacia arriba)
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister # Importa clases de Qiskit para crear circuitos, y registros cuánticos y clásicos
from qiskit.circuit.library import QFT, UnitaryGate # Importa la Transformada de Fourier Cuántica (QFT) y compuertas unitarias personalizadas

class QCircuit(ABC):
    """
    Clase base abstracta (ABC) para circuitos cuánticos.
    Proporciona métodos comunes para calcular la cantidad de qubits necesarios
    y construir compuertas de multiplicación modular, además de definir la interfaz
    para la creación del circuito de Shor.
    """

    def __init__(self):
        # Inicializa los atributos que almacenarán la cantidad de qubits
        self.control_qubits = None # Qubits para el registro de fase (evaluación de la QPE)
        self.target_qubits = None # Qubits para el registro de trabajo (donde ocurre la multiplicación)

    def calculate_and_set_control_qubits_number(self, number_to_factor):
        """Calcula el número de qubits necesarios para el registro de control."""
        # Primero calcula cuántos qubits se necesitan para el registro objetivo (n)
        n = self.calculate_and_set_target_qubits_number(number_to_factor)
        # La teoría del algoritmo de Shor normalmente sugiere 2n qubits de control para una precisión
        # idónea, aquí se usa 2n + 1 (o similar heurística empírica)
        self.control_qubits = 2 * n + 1
        return self.control_qubits

    def calculate_and_set_target_qubits_number(self, number_to_factor):
        """Calcula el número de qubits necesarios para representar el número a factorizar (N)."""
        # log2(N) nos da los bits requeridos fraccionales, ceil() redondea hacia arriba al entero más cercano
        self.target_qubits = ceil(log2(number_to_factor))
        return self.target_qubits

    def get_control_qubits(self):
        # Devuelve la cantidad de qubits asignados al registro de control
        return self.control_qubits

    def set_control_qubits(self, control_qubits):
        # Permite asignar manualmente la cantidad de qubits de control
        self.control_qubits = control_qubits

    def b_mod_n(self, b, number_to_factor):
        """
        Construye una compuerta unitaria que representa la operación de 
        multiplicación modular constante: |x> -> | (b * x) mod N >
        
        a = factor coprimo aleatorio menor a "number_to_factor"
        k = índice del qubit de control en rango (0 ... control_qubits-1)
        b = a ** (2 ** k) mod number_to_factor (el valor constante del multiplicador para este paso)
        number_to_factor = el número N que se desea factorizar
        """
        # Obtenemos el número de qubits de nuestro registro objetivo
        target_qubits = self.target_qubits
        
        # Creamos una matriz llena de ceros de tamaño 2^n x 2^n (donde n = target_qubits)
        # Esta matriz contendrá la tabla de permutación que define al operador unitario
        permutation_matrix = np.full((2 ** target_qubits, 2 ** target_qubits), 0)
        
        # Para cada posible entero x de 0 a N-1, se calcula el nuevo estado como (b * x) mod N.
        # Ponemos un 1.0 en la matriz en la fila [b * x % N] y la columna [x], 
        # lo que significa que el estado base |x> transicionará a |(b * x) mod N>.
        for x in range(number_to_factor): 
            permutation_matrix[b * x % number_to_factor][x] = 1
            
        # Para los estados de base cuyos valores sean N o mayores (estados no utilizados por valores espurios de qubits),
        # los mantenemos intactos (mapeándolos sobre sí mismos). Por lo tanto ponemos un 1 en la diagonal.
        for x in range(number_to_factor, 2 ** target_qubits): 
            permutation_matrix[x][x] = 1
            
        # Con la matriz completa, instanciaremos una Compuerta Unitaria personalizada de Qiskit
        unitary_gate = UnitaryGate(permutation_matrix)
        # Le asignamos un nombre a la compuerta, lo que es útil y visible al dibujar el circuito
        unitary_gate.name = f"{b}_mod_{number_to_factor}"
        return unitary_gate


    @abstractmethod
    def create_circuit(self, number_to_factor, a):
        # Método abstracto, obliga a todas las clases que hereden de QCircuit
        # a implementar su propia lógica principal para construir el circuito
        pass


class RegisterQC(QCircuit):
    """
    Clase hija que hereda de QCircuit.
    Implementa de manera concreta la creación de los pasos del Circuito Algorítmico de Shor
    utilizando estimación de fase cuántica (QPE).
    """

    def create_circuit(self, number_to_factor, a):
        # Si aún no se han calculado dinámicamente, se calculan los requerimientos de qubits
        if self.control_qubits is None:
            self.calculate_and_set_control_qubits_number(number_to_factor)
        if self.target_qubits is None:
            self.calculate_and_set_target_qubits_number(number_to_factor)
            
        # 1. Se define el Registro Cuántico de Control (t qubits para dar precisión a la estimación fase)
        control_register = QuantumRegister(self.control_qubits, name="control")
        # 2. Se define el Registro Clásico ("output") para guardar los bits finales al medir el registro de control
        output_register = ClassicalRegister(self.control_qubits, name="output")
        # 3. Se define el Registro Cuántico Objetivo (donde ocurrirán las operaciones |x * a^(2^i) mod N>)
        target_register = QuantumRegister(self.target_qubits, name="target")

        # Inicializa un objeto de Circuito Cuántico que ensambla todos estos registros definidos
        qc = QuantumCircuit(control_register, target_register, output_register)
        
        # Aplica una compuerta Pauli-X (NOT) sobre el primer qubit del registro objetivo (registro en base LSB o el primer índice).
        # Esto inicializa el registro objetivo en el estado superpuesto |1> en lugar del estado base inicial |0>
        # (debido a que empezamos evaluando 1 * a^x mod N, y si inicializamos en cero, 0 * cualquier cosa da 0)
        qc.x(target_register[0])
        
        # Iteramos secuencialmente sobre cada qubit en el registro de control (indexado desde el menos al más significativo usualmente)
        for index, qubit in enumerate(control_register):
            # Paso 1: Aplicar compuerta Hadamard (H) al qubit de control actual, 
            # colocándolo en un estado de igual superposición para la Estimación de Fase (QPE).
            qc.h(qubit)
            
            # Paso 2: Calcular clásicamente la constante `b` que corresponde a: a^(2^index) mod N.
            # Esta es la optimización clásica que evitará que tengamos que usar millones de compuertas cuánticas.
            b = pow(a, 2**index, number_to_factor)
            
            # Paso 3: Obtenemos nuestra compuerta unitaria b_mod_n() usando el módulo 'b' precalculado.
            # Volvemos a la compuerta una "compuerta controlada" añadiendo .control().
            # La componemos al circuito ( qc.compose ) especificando que estará controlada por el actual `qubit`
            # y actuará sobre la totalidad de los qubits del `target_register`.
            qc.compose(self.b_mod_n(b, number_to_factor).control(), qubits=[qubit] + list(target_register), inplace=True)
            
        # Una vez realizada toda la exponenciación modular controlada, pasamos al paso de interferencia.
        # Aplicamos la Transformada de Fourier Cuántica Inversa (IQFT) utilizando todo el registro de control.
        # Esto es vital para cambiar la base, extraer la fase y obtener una estimación del periodo "r" encubierto en los amplitudes.
        qc.compose(QFT(self.control_qubits, inverse=True), qubits=control_register, inplace=True)
        
        # Realizamos mediciones (colapso del estado cuántico) de cada uno de los qubits en el registro de control,
        # transfiriendo las salidas binarias (0s y 1s) al registro clásico para poder observarse y procesarse luego.
        qc.measure(control_register, output_register)
        
        # Finalmente, se retorna el objeto circuito completamente moldeado y listo para correr en el backend elegido.
        return qc




