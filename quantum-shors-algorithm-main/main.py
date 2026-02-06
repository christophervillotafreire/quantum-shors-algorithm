import sys
from algorithm import circuit
from datetime import datetime
from common.settings import load_settings, get_settings_value_for_key
from utilities.job_results import process_job_results
from utilities.arguments_parser import CommandLineParser, ConfigurationIni, JobIdArgsValidator
from services.arithmetics import Factorizer


def main():

    load_settings()
    parser = CommandLineParser()
    parser.add_arguments()
    args = parser.parse_arguments()
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
        args = parser.parse_arguments()

    if args.job_id:
        job_args_validator = JobIdArgsValidator(args)
        try:
            job_args_validator.validate_ibm_account_name()
            process_job_results(args.job_id, args.ibm_account_name)
        except ValueError as e:
            print(f"[{datetime.now()}] - Error: {e}")
            sys.exit(1)
    else:
        if (args.backend_class == 'fakeprov' and
                args.ibm_quantum_processor in ['ibm_aachen', 'ibm_brussels', 'ibm_strasbourg']):
            print(f"[{datetime.now()}] - IBM quantum processor {args.ibm_quantum_processor} doesn't have implemented a fake provider")
            sys.exit(1)
        try:
            factorizer = Factorizer(is_simulation=False) if args.backend_class == 'ibmqpu' else Factorizer()
            factorizer.factorize(args)
        except KeyboardInterrupt as e:
            print(f"[{datetime.now()}] - Stop current processing request by user")
            sys.exit(1)




if __name__ == '__main__':
    main()