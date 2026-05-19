from abc import ABC, abstractmethod
from qiskit_aer.primitives import SamplerV2 as AerSamplerV2
from qiskit_ibm_runtime import SamplerV2 as IbmRuntimeSamplerV2


class Sampler(ABC):
    """
    Clase abstracta base para primitivas "Sampler" (Muestreador) siguiendo el Patrón Diseño Factory (al igual que backend.py).
    La primitiva SamplerV2 es el nuevo estándar de Qiskit > 1.0 para ejecutar circuitos y extraer 
    la distribución probabilística de conteos (Histogramas y probabilidades de estados binarios clásicos |00>, |01>, |10>...).
    Sirve como puente unificador: el resto de la aplicación y PhaseEstimation llama a methods().run() sin importarle 
    si por detrás es Hardware Real o el Simulador Local AER.
    """

    def __init__(self, options, backend=None):
        self.options = options # Opciones subyacentes (Mitigaciones, Pauli Twirling, DD, Num. repeticiones "shots")
        self.backend = backend # El backend ya aprovisionado y transpilado de backend.py

    @abstractmethod
    def get(self):
        """Retorna el objeto Sampler ya inicializado con las opciones de corrección correspondientes."""
        pass


class AerSampler(Sampler):
    """Sampler para correr sobre la CPU/GPU de nuestra computadora de manera local."""

    def get(self):
        backend = self.backend if self.backend else self.options.get('mode')
        if backend:
            try:
                # Forza simulaciones masivas de entrelazamiento usando el algortimo tensor matrix_product_state, 
                # que soporta el cuello de botella que ahoga los computadores estándar al superar ~20 qubits.
                backend.set_options(method="matrix_product_state")
            except:
                pass
            return AerSamplerV2.from_backend(backend)
        else:
            return AerSamplerV2()


class IBMRuntimeSampler(Sampler):
    """Sampler para comunicarse a través de Internet al Session Runtime e inyectar trabajos en cola de Paga de IBM Hardware."""

    def get(self):
        # Desempaqueta todos los argumentos de mitigación, shots y demás con el operador doble asterisco **options
        return IbmRuntimeSamplerV2(**self.options)

