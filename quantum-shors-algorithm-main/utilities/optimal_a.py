from math import gcd


def find_order(a, number_to_factor):      # buscar funcion inversa (dado el r(2,4) devolver la lista de as)
    value = 1
    for r in range(1, number_to_factor):
        value = (value * a) % number_to_factor
        if value == 1:
            return r
    return None


def a_coefficients_producing_smallest_r(number_to_factor):
    r_as = {}
    for a in range(2, number_to_factor):
        if gcd(a, number_to_factor) == 1:
            r = find_order(a, number_to_factor)
            if r in r_as:
                r_as.get(r).append(a)
            else:
                r_as[r] = [a]
    return r_as


def get_optimal_a_for_valid_periods(number):
    r_as = a_coefficients_producing_smallest_r(number)
    print(r_as)
    results = {}
    for r, a_s in r_as.items():
        if r % 2 != 0:
            continue
        results[r]= {}
        for a in a_s:
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
    all_powers_of_two = True
    for r in rs:
        if not (r & (r - 1)) == 0:
            all_powers_of_two = False
            break
    return all_powers_of_two


def check_if_some_rs_are_power_of_two(rs):
    power_of_2 = []
    for r in rs:
        if (r & (r - 1)) == 0:
            power_of_2.append(r)
    return power_of_2


def find_power_of_2_periods_for_range(number):
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
