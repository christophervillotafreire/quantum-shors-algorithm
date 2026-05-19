import random
from algorithm.phase_estimation import Shor
from datetime import datetime
from math import gcd, log2
from utilities.job_results import find_nontrivial_factors, plot_a_x_mod_n
from utilities.optimal_a import get_optimal_a_for_valid_periods


class Factorizer:
    """
    Clase que encapsula toda la envoltura clásica del algoritmo de Shor.
    Shor no es puramente cuántico; comienza con reducciones clásicas para descartar casos triviales
    y termina con posprocesamiento clásico de fracciones continuas.
    """

    def __init__(self, is_simulation=True):
        self.is_simulation = is_simulation
        self.number = None # El N que queremos factorizar

    @staticmethod
    def get_coprime_factors_of(number):
        """Genera una lista exhaustiva de todos los posibles números 'a' que son coprimos relativos de N."""
        n_range = range(number)
        coprime_factors = [i for i in n_range if i != 1 and gcd(i, number) == 1]
        return coprime_factors

    def factorize(self, args):
        """
        Método iterativo principal que aplica paso a paso el protocolo completo de Shor.
        Aquí es donde inician todas las validaciones antes de gastar recursos cuánticos costosos.
        """
        self.number = args.number_to_factor
        random_a = args.random_a
        isa_circuits = args.isa_number
        only_coprimes = args.only_coprimes_a
        optimal_a = args.use_optimal_a
        print(f"[{datetime.now()}] - Attempting to factorize number {self.number} classically")
        
        # Paso 1 Clásico: ¿Es par? Entonces el factor 2 es obvio. Retornar y abortar sin usar cuántica.
        if self.number % 2 == 0:
            print(f"[{datetime.now()}] - {self.number} is even. Factors: 2 and {self.number//2}")
            return

        # Paso 2 Clásico: ¿Es una potencia prima del tipo N = x^y ? 
        # Calculado logarítmicamente descarta también iterar complejos polinomialmente.
        for b in range(2, round(log2(self.number)) + 1):
            d = round(self.number ** (1/b))
            if d ** b == self.number:
                print(f"[{datetime.now()}] - {self.number} is a prime power: {d}^{b}. Factors: {d} and {d ** (b-1)}")
                return

        # Busca los predictores óptimos o aleatorios según parámetros (Elige los 'a')
        a_coefficients = self.get_circuits_coefficients(random_a, optimal_a, isa_circuits, only_coprimes)
        for a in a_coefficients:
            # Paso 3 Clásico: Por pura suerte, ¿el Factor Común Máximo (GCD) que elegimos ya nos dio la respuesta? (Difícil pero posible matemáticamente y ahorra recursos)
            d = gcd(a, self.number)
            if d != 1:
                print(f"[{datetime.now()}] - Found factors by GCD: {d} and {self.number//d}")
                return

        # Paso 4: Nada funcionó desde la parte clásica. Vamos a la Subrutina Cuántica.
        print(f"[{datetime.now()}] - Attempting to factorize number {self.number} using Shor's algorithm")
        shor = Shor(self.is_simulation) # Instanciamos el orquestador Cuántico (Phase Estimation)
        
        # Ejecuta la Estimación de Fase para todos nuestros factores primos 'a' precalculados. Nos traerá posibles Periodos ("rs")
        rs, job_id , isas_info = shor.find_period(args, a_coefficients)
        
        # Entramos a la fase de post-procesamiento
        if isinstance(rs, dict):
            if rs:
                # Paso 5 Clásico: Usa las conjeturas de "r" para evaluar matemáticamente p = gcd(a^(r/2) ± 1, N) extrayendo factibilidad
                factors_result = find_nontrivial_factors(self.number, rs)
                if factors_result:
                    plot_a_x_mod_n(factors_result, isas_info, job_id)
            else:
                print(f"[{datetime.now()}] - No candidates values for 'r' (order) found using Shor's algorithm")

    def get_circuits_coefficients(self, random_a, optimal_a, isa_circuits, only_coprimes):
        """
        Subrutina que gestiona CÓMO obtener la 'a' que iteraremos. 
        En la teoría de Shor esto es al azar, pero la tesis prueba escenarios donde 
        utilizamos herramientas de inyección óptima de 'a' para evitar periodos impares inválidos por la matemática de Euler.
        """
        if random_a:
            a_coefficients = random_a
            print(f"[{datetime.now()}] - Using user's input as \"a\" coefficient: {a_coefficients}")
        elif optimal_a:
            # Usar una heurística matemática que pre-calcula los factores ideales que aseguran 
            # un periodo de retroceso corto y par, útil para la escasez de los recursos NISQ (Hardware pequeño)
            rs_as = get_optimal_a_for_valid_periods(self.number)
            r_a = sorted(rs_as.items(), key=lambda item: item[1], reverse=True)[0]
            r = list(r_a.keys())[0]
            a_coefficients = r_a.get(r)[:1]
            ac = r_a.get(r).get(a_coefficients[0])
            factors =  ac.get('factors', None) if ac.get('factors', None) else ac.get('trivial_factors')
            print(f"[{datetime.now()}] - Using optimal \"a\"={a_coefficients[0]} for valid period r={r}, with factors: {factors}")
        elif isa_circuits:
            # Selecciona aletoriamente múltiples co-primos para ensamblarlos por lote
            coprimes = self.get_coprime_factors_of(self.number)
            a_coefficients = random.sample(coprimes, k=min(isa_circuits, len(coprimes) - 1))
            print(f"[{datetime.now()}] - Using only coprime factors of {self.number} as \"a\" coefficients: ", a_coefficients)
        else:
            # Elección estándar canónica teórica de 1 solo co-primo aleatorio.
            coprimes = self.get_coprime_factors_of(self.number)
            a_coefficients = random.sample(coprimes, k=1)
            print(f"[{datetime.now()}] - Using a randomly generated \"a\" coefficients: ", a_coefficients)
        return a_coefficients





