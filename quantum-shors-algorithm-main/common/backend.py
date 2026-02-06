from abc import ABC, abstractmethod
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import fake_provider, QiskitRuntimeService
from common.settings import get_settings_value_for_key

class Backend(ABC):

    def __init__(self, ibm_qpu, ibm_account_name, fractional_gates):
        self.ibm_qpu = ibm_qpu
        self.ibm_account_name = ibm_account_name
        self.fractional_gates = fractional_gates

    def get_ibm_qpu_backend(self):
        service = QiskitRuntimeService(name=self.ibm_account_name)
        backend =  service.backend(self.ibm_qpu, use_fractional_gates=self.fractional_gates)
        return backend

    @abstractmethod
    def get(self):
        pass


class IdealAerSimulator(Backend):

    def get(self):
        return AerSimulator()


class AerSimFromBackend(Backend):

    def get(self):
        ibm_backend = self.get_ibm_qpu_backend()
        return AerSimulator.from_backend(ibm_backend)


class FakeProvider(Backend):

    def get(self):
        fake_backend = get_settings_value_for_key(f"ibm_qpus.{self.ibm_qpu}.fake_class")
        return getattr(fake_provider, fake_backend)()


class IbmQpu(Backend):

    def get(self):
        return self.get_ibm_qpu_backend()

