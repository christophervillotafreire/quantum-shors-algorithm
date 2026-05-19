from abc import ABC, abstractmethod # Módulos para clases abstractas y requerir métodos en subclases
from qiskit_aer import AerSimulator # Simulador local de alto rendimiento de Qiskit
from qiskit_ibm_runtime import fake_provider, QiskitRuntimeService # Proveedores de IBM: QPU real por nube y Fake Providers
from common.settings import get_settings_value_for_key # Función traída de settings.py para leer los parámetros del YAML

class Backend(ABC):
    """
    Clase base abstracta de tipo Interfaz/Protocolo (Patrón de diseño Strategy / Factory).
    Define la estructura que todas las variantes de acceso al hardware o simulador cuántico deben poseer.
    """

    def __init__(self, ibm_qpu, ibm_account_name, fractional_gates):
        # Datos esenciales para ubicar y configurar un chip o simulador exacto
        self.ibm_qpu = ibm_qpu # Nombre del hardware (Ej: "ibm_torino", "ibmq_mumbai")
        self.ibm_account_name = ibm_account_name # Identificador del canal/cuenta registrada de IBM Quantum
        self.fractional_gates = fractional_gates # Flag para activar optimizaciones modernas de IBM con compuertas fraccionales (angulares no limitadas a base)

    def get_ibm_qpu_backend(self):
        """
        Método auxiliar para conectarse directamente a la nube de IBM vía Internet y 
        retornar el objeto físico de la QPU específica (Backend remoto real).
        """
        service = QiskitRuntimeService(name=self.ibm_account_name)
        backend =  service.backend(self.ibm_qpu, use_fractional_gates=self.fractional_gates)
        return backend

    @abstractmethod
    def get(self):
        """
        Método que toda subclase debe implementar pasándole la responsabilidad. 
        Debe retornar el objeto final listo para ejecutar o transpilado según su respectiva clase.
        """
        pass


class IdealAerSimulator(Backend):
    """
    Simulador local completamente ideal: No tiene en cuenta ruido, coherencia, ni topología. 
    (Sirve como control matemático basal en caso ideal, compuertas unitarias puras).
    """

    def get(self):
        return AerSimulator()


class AerSimFromBackend(Backend):
    """
    Simulador local avanzado pero inicializado con los modelos térmicos (T1, T2) paramétricos
    y matrices de interferencia de lectura (readout error) que existan en el Backend en tiempo real real.
    """

    def get(self):
        # Descarga la telemetría actual y fresquita en vivo del computador real
        ibm_backend = self.get_ibm_qpu_backend()
        # Modela la simulación para que se comporte como ese hardware (method matrix_product_state maneja alto entrelazamiento emulado)
        return AerSimulator.from_backend(ibm_backend, method='matrix_product_state')


class FakeProvider(Backend):
    """
    Simulador Estático usando un Proveedor Fake (FakeTorino, FakeMumbai, etc).
    IBM empaqueta fotos (snapshots) desactualizadas pero fijas de su hardware de 133, 127 o 27 qubits.
    No requiere internet para ejecutarse.
    """

    def get(self):
        # Utiliza la función interactiva global de settings para averiguar qué falso backend usar
        # Por ejemplo buscaría en config YAML: ibm_qpus -> ibm_torino -> fake_class : "FakeTorino"
        fake_backend = get_settings_value_for_key(f"ibm_qpus.{self.ibm_qpu}.fake_class")
        # Usa getattr para auto-instanciar desde la librería fake_provider de qiskit dinámicamente
        return getattr(fake_provider, fake_backend)()


class IbmQpu(Backend):
    """Ejecutor Directo en Hardware Físico en vivo en las instalaciones de computación cuántica de IBM."""

    def get(self):
        # Simplemente delega sin simulación intermedia a la conexión directa por nube
        return self.get_ibm_qpu_backend()


