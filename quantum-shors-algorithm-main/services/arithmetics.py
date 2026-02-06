import random
from algorithm.phase_estimation import Shor
from datetime import datetime
from math import gcd, log2
from utilities.job_results import find_nontrivial_factors, plot_a_x_mod_n
from utilities.optimal_a import get_optimal_a_for_valid_periods


class Factorizer:

    def __init__(self, is_simulation=True):
        self.is_simulation = is_simulation
        self.number = None

    @staticmethod
    def get_coprime_factors_of(number):
        n_range = range(number)
        coprime_factors = [i for i in n_range if i != 1 and gcd(i, number) == 1]
        return coprime_factors

    def factorize(self, args):
        self.number = args.number_to_factor
        random_a = args.random_a
        isa_circuits = args.isa_number
        only_coprimes = args.only_coprimes_a
        optimal_a = args.use_optimal_a
        print(f"[{datetime.now()}] - Attempting to factorize number {self.number} classically")
        if self.number % 2 == 0:
            print(f"[{datetime.now()}] - {self.number} is even. Factors: 2 and {self.number//2}")
            return

        for b in range(2, round(log2(self.number)) + 1):
            d = round(self.number ** (1/b))
            if d ** b == self.number:
                print(f"[{datetime.now()}] - {self.number} is a prime power: {d}^{b}. Factors: {d} and {d ** (b-1)}")
                return

        a_coefficients = self.get_circuits_coefficients(random_a, optimal_a, isa_circuits, only_coprimes)
        for a in a_coefficients:
            d = gcd(a, self.number)
            if d != 1:
                print(f"[{datetime.now()}] - Found factors by GCD: {d} and {self.number//d}")
                return

        print(f"[{datetime.now()}] - Attempting to factorize number {self.number} using Shor's algorithm")
        shor = Shor(self.is_simulation)
        rs, job_id , isas_info = shor.find_period(args, a_coefficients)
        if isinstance(rs, dict):
            if rs:
                factors_result = find_nontrivial_factors(self.number, rs)
                if factors_result:
                    plot_a_x_mod_n(factors_result, isas_info, job_id)
            else:
                print(f"[{datetime.now()}] - No candidates values for 'r' (order) found using Shor's algorithm")

    def get_circuits_coefficients(self, random_a, optimal_a, isa_circuits, only_coprimes):
        if random_a:
            a_coefficients = random_a
            print(f"[{datetime.now()}] - Using user's input as \"a\" coefficient: {a_coefficients}")
        elif optimal_a:
            rs_as = get_optimal_a_for_valid_periods(self.number)
            r_a = sorted(rs_as.items(), key=lambda item: item[1], reverse=True)[0]
            r = list(r_a.keys())[0]
            a_coefficients = r_a.get(r)[:1]
            ac = r_a.get(r).get(a_coefficients[0])
            factors =  ac.get('factors', None) if ac.get('factors', None) else ac.get('trivial_factors')
            print(f"[{datetime.now()}] - Using optimal \"a\"={a_coefficients[0]} for valid period r={r}, with factors: {factors}")
        elif isa_circuits:
            coprimes = self.get_coprime_factors_of(self.number)
            a_coefficients = random.sample(coprimes, k=min(isa_circuits, len(coprimes) - 1))
            print(f"[{datetime.now()}] - Using only coprime factors of {self.number} as \"a\" coefficients: ", a_coefficients)
        else:
            coprimes = self.get_coprime_factors_of(self.number)
            a_coefficients = random.sample(coprimes, k=1)
            print(f"[{datetime.now()}] - Using a randomly generated \"a\" coefficients: ", a_coefficients)
        return a_coefficients





