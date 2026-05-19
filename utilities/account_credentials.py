from qiskit_ibm_runtime import QiskitRuntimeService # Importación del Servicio de Ejecución en la nube de IBM

def save_ibm_quantum_account_credentials():
    """
    Función utilitaria simple para almacenar permanentemente en el sistema operativo local
    (normalmente en ~/.qiskit/qiskit-ibm.json) el Token de Acceso de tu cuenta de IBM Quantum.
    Esto evita tener que pasar el token en texto plano o cargarlo repetidamente durante experimentos.
    """
    print("Guardando credenciales de IBM Quantum...")
    
    # PEGA TU TOKEN AQUÍ ABAJO ENTRE LAS COMILLAS
    MI_TOKEN = "X5y-f8-WfgW9oYciisgl1i-wjkXLlZYbRcALz0p1ZTxV"
    
    try:
        # Llama a la API oficial para grabar un archivo de credenciales cifrado/protegido a nivel de usuario
        QiskitRuntimeService.save_account(
            channel='ibm_quantum_platform', # Indica que es para hardware cuántico (no nube empresarial classical)
            token=MI_TOKEN,
            name='ibm_quantum', # Alias interno usado después por arguments_parser
            overwrite=True # Sobrescribe si ya existía una credencial desactualizada
        )
        print("¡Éxito! Credenciales guardadas correctamente.")
    except Exception as e:
        print(f"Error: {e}")

def print_saved_accounts():
    """Imprime por consola qué cuentas o tokens han sido vinculados a esta máquina."""
    print("Cuentas guardadas en este PC:")
    print(QiskitRuntimeService.saved_accounts())

# Ejecutamos solo la función que nos interesa. Este archivo está diseñado para correrse standalone
# idealmente a mano por el usuario al configurar su entorno por primera vez.
if __name__ == "__main__":
    save_ibm_quantum_account_credentials()
    print_saved_accounts()