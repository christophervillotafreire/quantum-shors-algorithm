import numpy as np

from qiskit import QuantumRegister, QuantumCircuit, transpile
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import TransformationPass
from qiskit.circuit.library import XGate, YGate, ZGate, IGate, RZGate, SXGate, CXGate
from qiskit.quantum_info import Clifford, Pauli

class Twirl2QClifford(TransformationPass):
    """
    A simplified Pauli Twirling pass for 2Q Clifford gates (CX, CZ, ECR).
    In real hardware this is done by inserting random Pauli gates before
    and after the 2Q gate such that the overall logical operation remains the same.
    """
    def __init__(self, seed=None):
        super().__init__()
        self.rng = np.random.default_rng(seed)
        self.basis_gates = ['cx', 'id', 'rz', 'sx', 'x', 'ecr', 'cz']

    def run(self, dag: DAGCircuit):
        nodes_to_twirl = [node for node in dag.two_qubit_ops() if node.op.name in ['cx', 'cz', 'ecr']]
        
        for node in nodes_to_twirl:
            idx = self.rng.integers(0, 16)
            p1_char = "IXYZ"[idx // 4]
            p2_char = "IXYZ"[idx % 4]
            
            p_in = Pauli(p1_char + p2_char) 
            
            gate_cliff = Clifford(node.op)
            p_out = p_in.evolve(gate_cliff)
            
            p_in_x = p_in.x
            p_in_z = p_in.z
            
            def get_pauli_gate(x, z):
                if x and z: return YGate()
                if x: return XGate()
                if z: return ZGate()
                return IGate()
                
            p_in_gate0 = get_pauli_gate(p_in_x[0], p_in_z[0])
            p_in_gate1 = get_pauli_gate(p_in_x[1], p_in_z[1])
            
            p_out_gate0 = get_pauli_gate(p_out.x[0], p_out.z[0])
            p_out_gate1 = get_pauli_gate(p_out.x[1], p_out.z[1])
            
            mini_qc = QuantumCircuit(2)
            
            # apply P_in
            if not isinstance(p_in_gate0, IGate):
                mini_qc.append(p_in_gate0, [0])
            if not isinstance(p_in_gate1, IGate):
                mini_qc.append(p_in_gate1, [1])
                
            # apply U
            mini_qc.append(node.op, [0, 1])
            
            # apply P_out 
            if not isinstance(p_out_gate0, IGate):
                mini_qc.append(p_out_gate0, [0])
            if not isinstance(p_out_gate1, IGate):
                mini_qc.append(p_out_gate1, [1])
                
            # Transpile the mini circuit to only use basis gates
            mini_qc_transpiled = transpile(mini_qc, basis_gates=self.basis_gates, optimization_level=1)
                
            from qiskit.converters import circuit_to_dag
            replacement_dag = circuit_to_dag(mini_qc_transpiled)
            
            # Verify wires
            wires_dict = {
                replacement_dag.qubits[0]: node.qargs[0],
                replacement_dag.qubits[1]: node.qargs[1]
            }
            
            # DAG node substitution
            dag.substitute_node_with_dag(node, replacement_dag, wires=wires_dict)
            
        return dag
