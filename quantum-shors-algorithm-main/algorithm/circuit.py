import numpy as np
from abc import ABC, abstractmethod
from math import log2, ceil
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import QFT, UnitaryGate, IntegerComparator



class QCircuit(ABC):

    def __init__(self):
        self.control_qubits = None
        self.target_qubits = None

    def calculate_and_set_control_qubits_number(self, number_to_factor):
        n = self.calculate_and_set_target_qubits_number(number_to_factor)
        self.control_qubits = 2 * n + 1
        return self.control_qubits

    def calculate_and_set_target_qubits_number(self, number_to_factor):
        self.target_qubits = ceil(log2(number_to_factor))
        return self.target_qubits

    def get_control_qubits(self):
        return self.control_qubits

    def set_control_qubits(self, control_qubits):
        self.control_qubits = control_qubits

    def b_mod_n(self, b, number_to_factor):
        """
        a = coprime factor to "number_to_factor"
        k = range (0 ... control_qubits)
        b = a ** (2 ** k) mod number_to_factor
        number_to_factor = number to factor
        """
        target_qubits = self.target_qubits
        permutation_matrix = np.full((2 ** target_qubits, 2 ** target_qubits), 0)
        for x in range(number_to_factor): permutation_matrix[b * x % number_to_factor][x] = 1
        for x in range(number_to_factor, 2 ** target_qubits): permutation_matrix[x][x] = 1
        unitary_gate = UnitaryGate(permutation_matrix)
        unitary_gate.name = f"{b}_mod_{number_to_factor}"
        return unitary_gate


    @abstractmethod
    def create_circuit(self, number_to_factor, a):
        pass


class RegisterQC(QCircuit):

    def create_circuit(self, number_to_factor, a):
        if self.control_qubits is None:
            self.calculate_and_set_control_qubits_number(number_to_factor)
        if self.target_qubits is None:
            self.calculate_and_set_target_qubits_number(number_to_factor)
        control_register = QuantumRegister(self.control_qubits, name="control")
        output_register = ClassicalRegister(self.control_qubits, name="output")
        target_register = QuantumRegister(self.target_qubits, name="target")

        qc = QuantumCircuit(control_register, target_register, output_register)
        qc.x(target_register[0])
        for index, qubit in enumerate(control_register):
            qc.h(qubit)
            b = pow(a, 2**index, number_to_factor)
            qc.compose(self.b_mod_n(b, number_to_factor).control(), qubits=[qubit] + list(target_register), inplace=True)
        qc.compose(QFT(self.control_qubits, inverse=True), qubits=control_register, inplace=True)
        qc.measure(control_register, output_register)
        return qc


class ControlledMultiplierQC(QCircuit):

    def create_circuit(self, number_to_factor, a):
        if self.control_qubits is None:
            self.calculate_and_set_control_qubits_number(number_to_factor)
        if self.target_qubits is None:
            self.calculate_and_set_target_qubits_number(number_to_factor)

        ancilla_qubits = 2 * number_to_factor + 1  # Ancilla qubits for modular arithmetic.

        # Step 2: Initialize quantum and classical registers
        # Define registers for counting qubits, target state, ancilla, and classical measurement.
        counting = QuantumRegister(self.control_qubits, 'control')
        target = QuantumRegister(self.target_qubits, 'target')
        ancilla = QuantumRegister(ancilla_qubits, 'ancilla')
        classical = ClassicalRegister(self.control_qubits, 'output')
        qc = QuantumCircuit(counting, target, ancilla, classical)

        # Step 3: Build the quantum circuit
        # Apply Hadamard gates to counting qubits to create superposition.
        for q in range(self.control_qubits):
            qc.h(counting[q])
        # Initialize target register to |1> (for modular exponentiation starting point).
        qc.x(target[0])
        # Apply controlled modular exponentiation for each counting qubit.
        for j in range(self.control_qubits):
            power = 2 ** j
            qc = self.apply_controlled_modular_exponentiation(qc, counting[j], target, ancilla, a, power, number_to_factor)
        # Apply inverse Quantum Fourier Transform to extract phase information.
        qc.append(QFT(self.control_qubits, do_swaps=False).inverse(), counting)
        # Measure the counting qubits into the classical register.
        qc.measure(counting, classical)
        return qc

    def apply_controlled_modular_exponentiation(self, circuit, control_qubit, target_register, ancilla_register, a, power, number):
        # Helper function to apply controlled modular exponentiation a^power mod N.
        a_power = pow(a, power, number)  # Precompute a^power mod N classically.
        circuit = self.controlled_modular_multiply(circuit, control_qubit, target_register, ancilla_register, a_power, number)
        return circuit

    def controlled_modular_multiply(self, circuit, control_qubit, target_register, ancilla_register, a, N):
        # Implement controlled modular multiplication: |x> -> |ax mod N> if control is 1.
        n = len(target_register)
        # Split ancilla register into parts for product, temporary storage, comparison, and subtraction.
        ancilla_product = ancilla_register[:n]
        ancilla_temp = ancilla_register[n:2 * n - 1]
        ancilla_compare = ancilla_register[2 * n - 1]
        ancilla_sub = ancilla_register[2 * n]
        a_binary = bin(a)[2:].zfill(n)  # Binary representation of a, padded to n bits.

        # Multiply target by a using controlled additions.
        for i in range(n):
            if a_binary[n - 1 - i] == '1':  # For each '1' bit in a.
                for j in range(n):
                    if j >= i:
                        # Controlled addition of target shifted by i into ancilla_product.
                        circuit.ccx(control_qubit, target_register[j - i], ancilla_product[j])

        # Compare ancilla_product with N to check if subtraction is needed.
        comparator = IntegerComparator(n, value=N, geq=True).to_gate()
        circuit.append(comparator, list(ancilla_product) + list(ancilla_temp) + [ancilla_compare])

        # Subtract N from ancilla_product if it’s >= N (controlled by ancilla_compare).
        N_binary = bin(N)[2:].zfill(n)
        for i in range(n):
            if N_binary[n - 1 - i] == '1':
                circuit.cx(ancilla_compare, ancilla_sub)
                circuit.x(ancilla_product[i])
                circuit.ccx(ancilla_compare, ancilla_product[i], ancilla_sub)
                circuit.x(ancilla_product[i])

        # Copy result back to target register.
        for i in range(n):
            circuit.cx(ancilla_product[i], target_register[i])

        # Uncompute the comparator to reset ancilla qubits.
        circuit.append(comparator.inverse(), list(ancilla_product) + list(ancilla_temp) + [ancilla_compare])

        # Reset ancilla qubits to avoid entanglement.
        for i in range(n):
            circuit.reset(ancilla_product[i])
        for i in range(n - 1):
            circuit.reset(ancilla_temp[i])
        circuit.reset(ancilla_sub)

        return circuit


class SequentialQFT(QCircuit):

    def egcd(self, a, b):
        if a == 0:
            return b, 0, 1
        gcd, x1, y1 = self.egcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return gcd, x, y

    def find_multiplicative_inverse(self, a, m):
        g, x, y = self.egcd(a, m)
        if g != 1:
            raise Exception('modular inverse does not exist')
        else:
            return x % m

    """ Function to create the QFT """

    def create_QFT(self, circuit, up_reg, n, with_swaps):
        i = n - 1
        """ Apply the H gates and Cphases"""
        """ The Cphases with |angle| < threshold are not created because they do 
        nothing. The threshold is put as being 0 so all CPhases are created,
        but the clause is there so if wanted just need to change the 0 of the
        if-clause to the desired value """
        while i >= 0:
            circuit.h(up_reg[i])
            j = i - 1
            while j >= 0:
                if (np.pi) / (pow(2, (i - j))) > 0:
                    circuit.cp((np.pi) / (pow(2, (i - j))), up_reg[i], up_reg[j])
                    j = j - 1
            i = i - 1

        """ If specified, apply the Swaps at the end """
        if with_swaps == 1:
            i = 0
            while i < ((n - 1) / 2):
                circuit.swap(up_reg[i], up_reg[n - 1 - i])
                i = i + 1

    """ Function to create inverse QFT """

    def create_inverse_QFT(self, circuit, up_reg, n, with_swaps):
        """ If specified, apply the Swaps at the beggining"""
        if with_swaps == 1:
            i = 0
            while i < ((n - 1) / 2):
                circuit.swap(up_reg[i], up_reg[n - 1 - i])
                i = i + 1

        """ Apply the H gates and Cphases"""
        """ The Cphases with |angle| < threshold are not created because they do 
        nothing. The threshold is put as being 0 so all CPhases are created,
        but the clause is there so if wanted just need to change the 0 of the
        if-clause to the desired value """
        i = 0
        while i < n:
            circuit.h(up_reg[i])
            if i != n - 1:
                j = i + 1
                y = i
                while y >= 0:
                    if (np.pi) / (pow(2, (j - y))) > 0:
                        circuit.cp(- (np.pi) / (pow(2, (j - y))), up_reg[j], up_reg[y])
                        y = y - 1
            i = i + 1

    """Function that calculates the angle of a phase shift in the sequential QFT based on the binary digits of a."""
    """a represents a possile value of the classical register"""

    def getAngle(self, a, N):
        """convert the number a to a binary string with length N"""
        s = bin(int(a))[2:].zfill(N)
        angle = 0
        for i in range(0, N):
            """if the digit is 1, add the corresponding value to the angle"""
            if s[N - 1 - i] == '1':
                angle += pow(2, -(N - i))
        angle *= np.pi
        return angle

    """Function that calculates the array of angles to be used in the addition in Fourier Space"""

    def getAngles(self, a, N):
        s = bin(int(a))[2:].zfill(N)
        angles = np.zeros([N])
        for i in range(0, N):
            for j in range(i, N):
                if s[j] == '1':
                    angles[N - i - 1] += pow(2, -(j - i))
            angles[N - i - 1] *= np.pi
        return angles

    """Creation of a doubly controlled phase gate"""

    def ccphase(self, circuit, angle, ctl1, ctl2, tgt):
        circuit.cp(angle / 2, ctl1, tgt)
        circuit.cx(ctl2, ctl1)
        circuit.cp(-angle / 2, ctl1, tgt)
        circuit.cx(ctl2, ctl1)
        circuit.cp(angle / 2, ctl2, tgt)

    """Creation of the circuit that performs addition by a in Fourier Space"""
    """Can also be used for subtraction by setting the parameter inv to a value different from 0"""

    def phiADD(self, circuit, q, a, N, inv):
        angle = self.getAngles(a, N)
        for i in range(0, N):
            if inv == 0:
                circuit.p(angle[i], q[i])
                """addition"""
            else:
                circuit.p(-angle[i], q[i])
                """subtraction"""

    """Single controlled version of the phiADD circuit"""

    def cphiADD(self, circuit, q, ctl, a, n, inv):
        angle = self.getAngles(a, n)
        for i in range(0, n):
            if inv == 0:
                circuit.cp(angle[i], ctl, q[i])
            else:
                circuit.cp(-angle[i], ctl, q[i])

    """Doubly controlled version of the phiADD circuit"""

    def ccphiADD(self, circuit, q, ctl1, ctl2, a, n, inv):
        angle = self.getAngles(a, n)
        for i in range(0, n):
            if inv == 0:
                self.ccphase(circuit, angle[i], ctl1, ctl2, q[i])
            else:
                self.ccphase(circuit, -angle[i], ctl1, ctl2, q[i])

    """Circuit that implements doubly controlled modular addition by a"""

    def ccphiADDmodN(self, circuit, q, ctl1, ctl2, aux, a, N, n):
        self.ccphiADD(circuit, q, ctl1, ctl2, a, n, 0)
        self.phiADD(circuit, q, N, n, 1)
        self.create_inverse_QFT(circuit, q, n, 0)
        circuit.cx(q[n - 1], aux)
        self.create_QFT(circuit, q, n, 0)
        self.cphiADD(circuit, q, aux, N, n, 0)

        self.ccphiADD(circuit, q, ctl1, ctl2, a, n, 1)
        self.create_inverse_QFT(circuit, q, n, 0)
        circuit.x(q[n - 1])
        circuit.cx(q[n - 1], aux)
        circuit.x(q[n - 1])
        self.create_QFT(circuit, q, n, 0)
        self.ccphiADD(circuit, q, ctl1, ctl2, a, n, 0)

    """Circuit that implements the inverse of doubly controlled modular addition by a"""

    def ccphiADDmodN_inv(self, circuit, q, ctl1, ctl2, aux, a, N, n):
        self.ccphiADD(circuit, q, ctl1, ctl2, a, n, 1)
        self.create_inverse_QFT(circuit, q, n, 0)
        circuit.x(q[n - 1])
        circuit.cx(q[n - 1], aux)
        circuit.x(q[n - 1])
        self.create_QFT(circuit, q, n, 0)
        self.ccphiADD(circuit, q, ctl1, ctl2, a, n, 0)
        self.cphiADD(circuit, q, aux, N, n, 1)
        self.create_inverse_QFT(circuit, q, n, 0)
        circuit.cx(q[n - 1], aux)
        self.create_QFT(circuit, q, n, 0)
        self.phiADD(circuit, q, N, n, 0)
        self.ccphiADD(circuit, q, ctl1, ctl2, a, n, 1)

    """Circuit that implements single controlled modular multiplication by a"""
    def controlled_mult_mod_n(self, circuit, ctl, q, aux, a, N, n):
        self.create_QFT(circuit, aux, n + 1, 0)
        for i in range(0, n):
            self.ccphiADDmodN(circuit, aux, q[i], ctl, aux[n + 1], (2 ** i) * a % N, N, n + 1)
        self.create_inverse_QFT(circuit, aux, n + 1, 0)

        for i in range(0, n):
            circuit.cswap(ctl, q[i], aux[i])

        a_inv = self.find_multiplicative_inverse(a, N)
        self.create_QFT(circuit, aux, n + 1, 0)
        i = n - 1
        while i >= 0:
            self.ccphiADDmodN_inv(circuit, aux, q[i], ctl, aux[n + 1], pow(2, i) * a_inv % N, N, n + 1)
            i -= 1
        self.create_inverse_QFT(circuit, aux, n + 1, 0)

    def create_circuit(self, number_to_factor, a):
        if self.target_qubits is None:
            self.calculate_and_set_target_qubits_number(number_to_factor)
        n = self.target_qubits
        """auxiliary quantum register used in addition and multiplication"""
        aux = QuantumRegister(n + 2)
        """single qubit where the sequential QFT is performed"""
        up_reg = QuantumRegister(1)
        """quantum register where the multiplications are made"""
        down_reg = QuantumRegister(n)
        """classical register where the measured values of the sequential QFT are stored"""
        up_classic = ClassicalRegister(2 * n)
        """classical bit used to reset the state of the top qubit to 0 if the previous measurement was 1"""
        c_aux = ClassicalRegister(1)

        """ Create Quantum Circuit """
        qc = QuantumCircuit(down_reg, up_reg, aux, up_classic, c_aux)

        """ Initialize down register to 1"""
        qc.x(down_reg[0])

        """ Cycle to create the Sequential QFT, measuring qubits and applying the right gates according to measurements """
        for i in range(0, 2 * n):
            """reset the top qubit to 0 if the previous measurement was 1"""
            qc.x(up_reg).c_if(c_aux, 1)
            qc.h(up_reg)
            self.controlled_mult_mod_n(qc, up_reg[0], down_reg, aux, a ** (2 **  i), number_to_factor, n)
            """cycle through all possible values of the classical register and apply the corresponding conditional phase shift"""
            for j in range(0, 2 ** i):
                """the phase shift is applied if the value of the classical register matches j exactly"""
                qc.p(self.getAngle(j, i), up_reg[0]).c_if(up_classic, j)
            qc.h(up_reg)
            qc.measure(up_reg[0], up_classic[i])
            qc.measure(up_reg[0], c_aux[0])

        return qc

