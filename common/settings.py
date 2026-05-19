import yaml # Importa la librería PyYAML para procesar archivos de configuración en formato YAML
from pathlib import Path # Librería estandar para manejar rutas de archivos de forma segura y multiplataforma


# Variable global (privada al módulo por el guión bajo) para mantener la configuración cargada en memoria RAM
_settings = None


def load_settings(config_path: str = "common/settings.yaml"):
    """
    Carga la configuración desde un archivo YAML hacia la variable global `_settings`.
    Debe ser llamada usualmente una sola vez al inicio de la ejecución del programa principal (ej. app.py o main.py).
    """
    global _settings
    settings_file = Path(config_path)
    
    # Verifica que el archivo de configuración realmente exista antes de intentar abrirlo
    if not settings_file.exists():
        raise FileNotFoundError(f"Settings file not found: {config_path}")

    # Abre el archivo en modo lectura ('r') y lo convierte a un diccionario de Python usando safe_load
    with settings_file.open("r") as f:
        _settings = yaml.safe_load(f)


def get_settings():
    """Retorna el diccionario completo con toda la configuración cargada."""
    if _settings is None:
        # Previene errores si se intenta leer la configuración antes de inicializarla
        raise ValueError("Settings not loaded. Call load_settings() first.")
    return _settings


def get_settings_value_for_key(key: str, default=None):
    """
    Obtiene un valor específico de configuración usando 'dot notation' o notación de puntos por clave.
    Ejemplo: get_settings_value_for_key('ibm_qpus.ibm_torino.basis_gates')
    Busca dentro del diccionario anidado capa por capa devolviendo el valor final.
    """
    if _settings is None:
        raise ValueError("Settings not loaded. Call load_settings() first.")

    # Separa la cadena por cada punto encontrando la ruta del diccionario anidado
    keys = key.split(".")
    value = _settings
    
    # Itera iterativamente adentrándose en el diccionario con cada sub-clave
    for k in keys:
        value = value.get(k, default)
        # Si en algún punto una sub-clave no existe, devuelve de inmediato el valor 'default' (usualmente None)
        if value is default:
            break
            
    return value