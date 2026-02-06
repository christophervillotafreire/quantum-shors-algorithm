import argparse
import configparser
import sys
from typing import Literal, Union
from common.settings import get_settings_value_for_key
from qiskit.transpiler.preset_passmanagers.plugin import list_stage_plugins
from qiskit.transpiler.passes import unitary_synthesis_plugin_names


class CommandLineParser:

    def __init__(self):
        self.parser = argparse.ArgumentParser(description='Process command line arguments.')
        self.args = None

    @staticmethod
    def int_or_auto(value: str) -> Union[int, Literal['auto']]:
        if value == 'auto':
            return 'auto'
        try:
            return int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"'{value}' must be an integer or 'auto'")

    def add_arguments(self):

        # Get list of configurable values from settings.yaml file
        circuit_classes = list(get_settings_value_for_key('circuit_classes').keys())
        ibm_qpus = list(get_settings_value_for_key('ibm_qpus').keys())
        ibm_account_names = get_settings_value_for_key('ibm_account_names')
        backend_classes = list(get_settings_value_for_key('backend_classes').keys())
        sampler_classes = list(get_settings_value_for_key('sampler_classes').keys())
        transpiler_optimization_levels = get_settings_value_for_key('transpiler.optimization_levels')
        transpiler_seed = get_settings_value_for_key('transpiler.seed')
        transpiler_approx_degrees = get_settings_value_for_key('transpiler.approximation_degrees')
        transpiler_unitary_synthesis_methods = unitary_synthesis_plugin_names()
        transpiler_layout_methods = list_stage_plugins('layout')
        transpiler_routing_methods = list_stage_plugins('routing')
        transpiler_translation_methods = list_stage_plugins('translation')
        transpiler_pass_planning_methods = list_stage_plugins('scheduling')
        dynamical_decoupling_sequence_types = get_settings_value_for_key('sampler.dynamical_decoupling.sequence_types')
        dynamical_decoupling_extra_slack_distributions = get_settings_value_for_key(
            'sampler.dynamical_decoupling.extra_slack_distributions')
        dynamical_decoupling_scheduling_methods = get_settings_value_for_key('sampler.dynamical_decoupling.scheduling_methods')
        pauli_twirling_strategies = get_settings_value_for_key('sampler.pauli_twirling.strategies')

        # General arguments
        self.parser.add_argument('-n', "--number-to-factor", metavar="NUMBER", type=int,
                                 help='Number to factor')
        self.parser.add_argument('--config', type=str, default=None,
                                 help='Path to config.ini file, if no path is provided a default config.ini file will be'
                                      'expect to exist in the root of the repository)')
        self.parser.add_argument('-a', "--random-a", nargs='+', type=int, default=[], help="List of "
                                "space-separated integers that represents the \"a\" coefficients used to find the period"
                                " of the number to factor (default)")
        self.parser.add_argument('-m', "--phases-max-top-number", metavar="NUMBER", type=int, default=5,
                                 help='Maximum number of top phases counts to consider when searching for the period "r" (default: 5)')
        self.parser.add_argument("--only-coprimes-a", action="store_true",
                                 help="Only use coprimes values for a(s) when sampling more than one circuit "
                                      "generated (default: \"False\")")
        self.parser.add_argument("--use-optimal-a", action="store_true",
                                 help="Set the value of 'a' coefficient to the optimal value for circuit depth reduction (default: \"False\")")
        self.parser.add_argument("--only-isas-stats", action="store_true",
                                 help="Only transpile the circuits corresponding to each \"a\" coefficient, NOT running "
                                      "the sampler (default: \"False\")")
        self.parser.add_argument('-q', "--control-qubits", metavar="NUMBER", type=int, default=0,
                                 help='Number of control qubits to use in the Shor\'s algorithm circuit (default)')
        self.parser.add_argument('-i', "--isa-number", metavar="NUMBER", type=int, default=1,
                                 help='Number of randomly selected a(s) used as coefficients for generating the '
                                      'circuits to be executed in one job (default: 1)')
        self.parser.add_argument('-c', "--circuit-class", choices=circuit_classes, default=circuit_classes[0],
                                 help=f"Type of circuit class to instantiate (default: \"{circuit_classes[0]}\")")
        self.parser.add_argument('-w', "--ibm-account-name", choices=ibm_account_names, default=ibm_account_names[0],
                                 help=f"IBM web channel interface to utilize (default: \"{ibm_account_names[0]}\")")
        self.parser.add_argument('-p', "--ibm-quantum-processor", choices=ibm_qpus, default=ibm_qpus[0],
                                 help=f"IBM Quantum Processor to use (default: \"{ibm_qpus[0]}\")")
        self.parser.add_argument('-b', "--backend-class", choices=backend_classes, default=backend_classes[0],
                                 help=f"Type of backend class to use (default: \"{backend_classes[0]}\")")
        self.parser.add_argument('-s', "--sampler-class", choices=sampler_classes, default=sampler_classes[1],
                                 help=f"Type of sampler class to use (default: \"{sampler_classes[1]}\")")
        self.parser.add_argument('-j', "--job-id", metavar="STRING" ,type=str, default=None,
                                 help='Retrieve results for specified job id')
        self.parser.add_argument("--verbose", action="store_true",
                                 help="Console output verbose mode (default: \"False\")")
        self.parser.add_argument("--first-kyiv", action="store_true",
                                 help="Transpile first using FakeKyiv provider then pass the output layout to the actual"
                                      " target configured in the .ini file (default: \"False\")")
        self.parser.add_argument("--kyiv-circuit", action="store_true",
                                 help="Set the original circuit created for Kyiv for N=51 and a=4, to later pass this "
                                      "circuit to be transpiled for any of the allowed QPUs (Brisbane, Brussels, "
                                      "Strasbourg, Sherbrooke) (default: \"False\")")
        self.parser.add_argument("--from-isas", action="store_true",
                                 help="Get the ISA(s) to sample from the pre-transpiled circuits for certain QPU, number"
                                      " to factor, and 'a' coefficient configured in the .ini file (default: \"False\")")
        self.parser.add_argument("--backend-use-fractional-gates", action="store_true",
                                help="Set when the use of fractional gates is intended for transpilation. Remember that "
                                     "this option only will work with Heron r3 QPU types (ibm_aachen, ibm_torino), and "
                                     "that the '--transpiler-translation-method' need also be set to 'ibm_fractional' "
                                     "value (default: \"False\")")
        # Transpiler arguments
        self.parser.add_argument('-tol', "--transpiler-optimization-level", type=float,
                                 choices=transpiler_optimization_levels, default=transpiler_optimization_levels[-1],
                                 help=f"Transpiler optimization level (default: \"{transpiler_optimization_levels[-1]}\")")
        self.parser.add_argument('-ts', "--transpiler-seed", type=int, default=transpiler_seed, metavar="NUMBER",
                                 help=f"Transpiler seed (default: \"{transpiler_seed}\")")
        self.parser.add_argument('-tad', "--transpiler-approximation-degree", type=float,
                                 choices=transpiler_approx_degrees, default=transpiler_approx_degrees[-1],
                                 help=f"Transpiler approximation degree (default: \"{transpiler_approx_degrees[-1]}\")")
        self.parser.add_argument('-tum', "--transpiler-unitary-method",
                                 choices=transpiler_unitary_synthesis_methods, default=transpiler_unitary_synthesis_methods[1],
                                 help=f"Transpiler unitary synthesis method (default: \"{transpiler_unitary_synthesis_methods[1]}\")")
        self.parser.add_argument('-tlm', "--transpiler-layout-method", choices=transpiler_layout_methods,
                                 default=transpiler_layout_methods[2],
                                 help=f"Transpiler layout method (default: \"{transpiler_layout_methods[2]}\")")
        self.parser.add_argument('-trm', "--transpiler-routing-method", choices=transpiler_routing_methods,
                                 default=transpiler_routing_methods[3],
                                 help=f"Transpiler routing method (default: \"{transpiler_routing_methods[3]}\")")
        self.parser.add_argument('-ttm', "--transpiler-translation-method", choices=transpiler_translation_methods,
                                 default=transpiler_translation_methods[-1],
                                 help=f"Transpiler translation method (default: \"{transpiler_translation_methods[-1]}\")")
        self.parser.add_argument('-tpm', "--transpiler-pass-planning-method", choices=transpiler_pass_planning_methods,
                                 default=transpiler_pass_planning_methods[0],
                                 help=f"Transpiler pass planning method (default \"{transpiler_pass_planning_methods[0]}\")")
        # Sampler arguments
        self.parser.add_argument('-ssn', "--sampler-shots-number", metavar="NUMBER", type=int, default=500,
                                 help="Sampler shots number (default: 500)")
        self.parser.add_argument('-sde', "--sampler-dynamical-decoupling", action="store_true",
                                 help="Enable sampler dynamical decoupling (default: \"False\")")
        self.parser.add_argument('-sdx', "--sampler-dd-sequence-type", choices=dynamical_decoupling_sequence_types,
                                 default=dynamical_decoupling_sequence_types[0],
                                 help=f"Sampler dynamical decoupling sequence type (default: "
                                      f"\"{dynamical_decoupling_sequence_types[0]}\")")
        self.parser.add_argument('-sdd', "--sampler-dd-slack-dist", choices=dynamical_decoupling_extra_slack_distributions,
                                 default=dynamical_decoupling_extra_slack_distributions[0],
                                 help=f"Sampler dynamical decoupling extra slack distribution (default: "
                                      f"\"{dynamical_decoupling_extra_slack_distributions[0]}\")")
        self.parser.add_argument('-sds', "--sampler-dd-scheduling-method", choices=dynamical_decoupling_scheduling_methods,
                                 default=dynamical_decoupling_scheduling_methods[0],
                                 help=f"Sampler dynamical decoupling scheduling method (default: "
                                      f"\"{dynamical_decoupling_scheduling_methods[0]}\")")
        self.parser.add_argument('-sdr', "--sampler-dd-skip-reset-qubits", action="store_true",
                                 help="Sampler dynamical decoupling skip reset qubits (default: \"False\")")
        self.parser.add_argument('-spe', "--sampler-pt-enable-gates", action="store_true",
                                 help="Sampler Pauli twirling enable gates (default: \"False\")")
        self.parser.add_argument('-spm', "--sampler-pt-enable-measure", action="store_true",
                                 help="Sampler Pauli twirling enable measures (default: \"False\")")
        self.parser.add_argument('-spn', "--sampler-pt-number-randomizations", metavar="[NUMBER|'auto']",
                                 default='auto', type=self.int_or_auto,
                                 help="Sampler Pauli twirling number of randomizations, as an integer or 'auto' (default: \"auto\")")
        self.parser.add_argument('-spr', "--sampler-pt-shots-randomization", metavar="[NUMBER|'auto']",
                                 default='auto', type=self.int_or_auto,
                                 help="Sampler Pauli twirling shots per randomizations, as an integer or 'auto' (default: \"auto\")")
        self.parser.add_argument('-sps', "--sampler-pt-strategy", choices=pauli_twirling_strategies,
                                 default=pauli_twirling_strategies[2],
                                 help=f"Sampler Pauli twirling strategy (default: \"{pauli_twirling_strategies[2]}\")")
        # SABRE optimization parameters
        self.parser.add_argument("--sabre-optimization", action="store_true",
                                 help="Use SABRE optimizations for transpilation (default: \"False\")")
        self.parser.add_argument('-omi', "--sabre-max-iterations", metavar="NUMBER", type=int, default=8,
                                 help="SABRE optimization max iterations number (default: 8)")
        self.parser.add_argument('-olt', "--sabre-layout-trials", metavar="NUMBER", type=int, default=200,
                                 help="SABRE optimization layout trials number (default: 200)")
        self.parser.add_argument('-ost', "--sabre-swap-trials", metavar="NUMBER", type=int, default=200,
                                 help="SABRE optimization swap trials number (default: 200)")

        return self.parser

    def parse_arguments(self):
        self.args = self.parser.parse_args()
        return self.args

    def set_defaults(self, defaults):
        self.parser.set_defaults(**defaults)


class ConfigurationIni:

    def __init__(self):
        self.config_parser = configparser.ConfigParser()

    @staticmethod
    def check():
        check = False
        for i, arg in enumerate(sys.argv):
            if arg == '--config':
                check = True
                break
        return check

    def load(self, config_file):
        self.config_parser.read(config_file)

    def create_defaults(self):
        defaults = {}
        if 'general' in self.config_parser:
            defaults.update(dict(self.config_parser['general']))
        if 'transpiler' in self.config_parser:
            defaults.update(dict(self.config_parser['transpiler']))
        if 'sampler' in self.config_parser:
            defaults.update(dict(self.config_parser['sampler']))
        if 'sabre' in self.config_parser:
            defaults.update(dict(self.config_parser['sabre']))
        for key, value in defaults.items():
            if value in ['true', 'false']:
                defaults[key] = value.lower() == 'true'
            if key == "random_a":
                defaults[key] = [int(a_s) for a_s in value.split(',') if a_s != '0']

        return defaults


class JobIdArgsValidator:

    def __init__(self, args):
        self.args = args

    def validate_ibm_account_name(self):
        if not self.args.ibm_account_name:
            raise ValueError("IBM Account name was not provided.")


