import sys
from algorithm import circuit
from datetime import datetime
from common.settings import load_settings, get_settings_value_for_key
from utilities.job_results import process_job_results
from utilities.arguments_parser import CommandLineParser, ConfigurationIni, JobIdArgsValidator
from services.arithmetics import Factorizer


def main():
    """
    Punto de Entrada Principal (Entrypoint) de la Aplicación.
    Aquí es donde arranca la ejecución del proyecto completo. Su labor principal es interceptar
    qué es lo que quiere hacer el usuario, cargar la configuración subyacente y luego delegar 
    el trabajo a los administradores de ejecución correctos (Factorizer o Recuperador de Jobs).
    """

    # 1. Carga las variables maestras base del proyecto (settings.yaml)
    load_settings()
    
    # 2. Prepara la terminal (CLI) para recibir instrucciones personalizadas (--help)
    parser = CommandLineParser()
    parser.add_arguments()
    args = parser.parse_arguments()
    
    # 3. Interceptor de Configuración Masiva
    # Si el usuario mandó la bandera --config, ignorará (sobre-escribirá) la terminal e inflará
    # los args con lo que contenga el archivo .ini de la ruta provista.
    config_ini = ConfigurationIni()
    check = config_ini.check()
    if check:
        try:
            config_ini.load(args.config)
        except FileNotFoundError:
            print(f"[{datetime.now()}] - Config ini file not found, neither path nor default "
                  f"location provided successfully. Using command-line args only.")
            sys.exit(1)
        defaults = config_ini.create_defaults()
        parser.set_defaults(defaults)
        args = parser.parse_arguments() # Re-parsear inyectándole la base nueva INI

    # 4. Enrutamiento Lógico (Fork principal del comportamiento)
    if args.job_id:
        # BIFURCACIÓN A: MODO "RECUPERACIÓN NUBE"
        # El usuario no quiere ejecutar Shor, quiere descargar los resultados de horas atrás
        # de un trabajo ya agendado en la IBM Hardware y que acaba de terminar.
        job_args_validator = JobIdArgsValidator(args)
        try:
            job_args_validator.validate_ibm_account_name()
            # Descarga de la nube, desencripta y pasa a procesar las fracciones continuas
            process_job_results(args.job_id, args.ibm_account_name)
        except ValueError as e:
            print(f"[{datetime.now()}] - Error: {e}")
            sys.exit(1)
    else:
        # BIFURCACIÓN B: MODO "EJECUTAR SHOR" (Flujo Normal)
        # El usuario pide correr Shor desde cero.
        try:
            # Bandera vital: Avisale al factorizador clásico si queremos simularlo veloz localmente
            # o si tendrá que preparar el código para chocar frontalmente contra una QPU física real de IBM.
            factorizer = Factorizer(is_simulation=False) if args.backend_class == 'ibmqpu' else Factorizer()
            
            # Delega el flujo inyectando todas las opciones tecleadas en la consola
            factorizer.factorize(args)
        except KeyboardInterrupt as e:
            # Control por si el investigador aborta manualmente presionando CTRL + C
            print(f"[{datetime.now()}] - Stop current processing request by user")
            sys.exit(1)




if __name__ == '__main__':
    main()