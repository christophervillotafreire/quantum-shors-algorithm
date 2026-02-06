from abc import ABC, abstractmethod
from qiskit_aer.primitives import SamplerV2 as AerSamplerV2
from qiskit_ibm_runtime import SamplerV2 as IbmRuntimeSamplerV2


class Sampler(ABC):

    def __init__(self, options, backend=None):
        self.options = options
        self.backend = backend

    @abstractmethod
    def get(self):
        pass


class AerSampler(Sampler):

    def get(self):
        if self.backend:
            return AerSamplerV2(options=self.options).from_backend(self.backend)
        else:
            return AerSamplerV2(options=self.options)


class IBMRuntimeSampler(Sampler):

    def get(self):
        return IbmRuntimeSamplerV2(**self.options)

