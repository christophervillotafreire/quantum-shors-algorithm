from math import gcd


def find_order(a, number_to_factor):
    """
    Función matemática clásica para hallar fuerza bruta el orden multiplicativo 'r' (el periodo).
    Es decir, busca el valor mínimo entero 'r' tal que (a^r) MOD N == 1.
    Ej: Para a=2, N=15.  2^1%15=2, 2^2%15=4, 2^3%15=8, 2^4%15=1. Por lo tanto r=4.
    """      
    value = 1
    for r in range(1, number_to_factor):
        value = (value * a) % number_to_factor
        if value == 1:
            return r
    return None


def a_coefficients_producing_smallest_r(number_to_factor):
    """
    Dado un N, barre matemáticamente todos los pre-condicionales válidos y extrae
    los "coprimos a" mapeados a los "periodos r" que producen.
    Devuelve un diccionario inverso donde dict[r] = lista_de_a_coeficientes_que_lo_producen.
    """
    r_as = {}
    for a in range(2, number_to_factor): # Excluye el 1 obviamente
        if gcd(a, number_to_factor) == 1: # Sólo si son co-primos ('a' no factoriza ya trivialmente 'N')
            r = find_order(a, number_to_factor)
            if r in r_as:
                r_as.get(r).append(a)
            else:
                r_as[r] = [a]
    return r_as


def get_optimal_a_for_valid_periods(number):
    """
    Heurística propuesta central del programa:
    El algoritmo de Shor es vulnerable si escoges al azar un coeficiente 'a' cuyo 
    periodo colapsado 'r' resulta ser "impar". (Euler demuestra que un periodo impar no descompone).
    
    Esta función hace trampa y clásicamente evalúa para un N los periodos, forzando la
    devolución única de coeficientes 'a' que garantizan periodos 'r' pares ('r % 2 != 0'); 
    además asegurándose de que el resultado algebraico conduzca a Factores No-Triviales verdaderos.
    """
    r_as = a_coefficients_producing_smallest_r(number)
    print(r_as)
    results = {}
    for r, a_s in r_as.items():
        # Regla de oro algebraica del Algoritmo Shor: Si r es impar, Falla y se debe abortar.
        if r % 2 != 0:
            continue
            
        results[r]= {}
        for a in a_s:
            # Replicamos el posprocesamiento clásico aquí anticipadamente para validarlos
            p = gcd(a ** (r // 2) - 1, number)
            q = gcd(a ** (r // 2) + 1, number)
            trivial_factors = [1, number]
            if p in trivial_factors or q in trivial_factors:
                results[r][a] = {'number': number, 'trivial_factors': [p, q]}
                continue
            if p*q == number:
                results[r][a] = {'number': number, 'factors': [p, q]}
                continue
    return results if results else None


def check_if_all_rs_are_power_of_two(rs):
    """
    Operación a nivel de Bits (r & (r - 1) == 0). 
    Un truco computacional que rápidamente confirma verdadero SI TODOS los candidatos
    r entregados resultan ser potencias directas perfectas de 2 (ej: 2, 4, 8, 16).
    """
    all_powers_of_two = True
    for r in rs:
        if not (r & (r - 1)) == 0:
            all_powers_of_two = False
            break
    return all_powers_of_two


def check_if_some_rs_are_power_of_two(rs):
    """Filtro a nivel de bits que captura la lista de cuáles periodos específicos son potencias de 2"""
    power_of_2 = []
    for r in rs:
        if (r & (r - 1)) == 0:
            power_of_2.append(r)
    return power_of_2


def find_power_of_2_periods_for_range(number):
    """
    Herramienta de depuración y experimentación analítica del investigador.
    Barre factores desde 15 hasta N buscando cuáles periodos "r" generados pertenecen a potencias de 2.
    Esto es relevante porque la Transformada de Fourier Cuántica (QFT) es infaliblemente precisa
    sólo si el periodo a inferir calza exactamente en fracciones o potencias del espacio base 2 de la fase.
    De otro modo ocurren colas sucias o fugas en el histograma.
    """
    for n in range(15, number + 1):
        rs_as = get_optimal_a_for_valid_periods(n)
        rs = list(rs_as.keys())
        all_rs_p2 = check_if_all_rs_are_power_of_two(rs)
        if all_rs_p2:
            print(f"For number {n}, all the periods 'r' are power of 2: {rs}")
        else:
            some_rs_p2 = check_if_some_rs_are_power_of_two(rs)
            if some_rs_p2:
                some_rs_p2.sort()
                lr = some_rs_p2[0]
                print(f"For number {n}, some periods 'r' are power of 2: {some_rs_p2}. For period {lr}, the 'a' coefficients are: {list(rs_as.get(lr).keys())}")
            else:
                print(f"Number {n}, doesn't have power of 2 periods (r)")
