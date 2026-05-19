from qiskit_ibm_runtime import QiskitRuntimeService
from fractions import Fraction
from math import gcd

service = QiskitRuntimeService(name='ibm_quantum')
job = service.job('d673l15bujdc73cvejag')
print('STATUS:', job.status())
print('METRICS:', job.metrics())

result = job.result()
pub_result = result[0]
counts_raw = pub_result.data.output.get_counts()
total_shots = sum(counts_raw.values())
print(f'Total shots: {total_shots}')
print(f'Unique bitstrings: {len(counts_raw)}')

sorted_counts = sorted(counts_raw.items(), key=lambda x: x[1], reverse=True)

control_qubits = 9
N = 15
a = 4
print(f'\n--- TOP 25 BITSTRINGS (N={N}, a={a}, {control_qubits} control qubits) ---')
print(f'{"#":>3} | {"Bitstring":>12} | {"Count":>6} | {"Prob":>6} | {"Phase":>8} | {"Fraction":>10} | {"r":>4} | Valid')
print('-' * 80)

for i, (bs, count) in enumerate(sorted_counts[:25]):
    decimal_val = int(bs, 2)
    phase = decimal_val / (2**control_qubits)
    prob = count / total_shots
    
    if phase == 0:
        frac = Fraction(0, 1)
    else:
        frac = Fraction(phase).limit_denominator(N)
    
    r_cand = frac.denominator
    valid = 1 < r_cand < N and pow(a, r_cand, N) == 1
    
    if valid:
        g1 = gcd(pow(a, r_cand//2) - 1, N)
        g2 = gcd(pow(a, r_cand//2) + 1, N)
        non_triv = 1 < g1 < N or 1 < g2 < N
        factors = f'  -> {g1}, {g2}' + (' ★' if non_triv else ' (trivial)')
    else:
        factors = ''
    
    mark = '✓' if valid else ''
    print(f'{i+1:>3} | {bs:>12} | {count:>6} | {prob:.4f} | {phase:.4f} | {frac.numerator}/{frac.denominator}{"":>{8-len(str(frac.numerator)+"/"+str(frac.denominator))}} | {r_cand:>4} | {mark}{factors}')

# Signal analysis for r=2 (expected for a=4 mod 15: 4^1=4, 4^2=1 -> r=2)
# Peaks at 0/2 (0) and 1/2 (0.5)
print(f'\n--- SIGNAL ANALYSIS ---')
theoretical_phases_r2 = [0, 0.5]
signal_r2 = 0
for bs, count in counts_raw.items():
    decimal_val = int(bs, 2)
    phase = decimal_val / (2**control_qubits)
    if any(abs(phase - tp) < 0.002 for tp in theoretical_phases_r2):
        signal_r2 += count
print(f'Signal (r=2 peaks: 0, 1/2): {signal_r2} ({100*signal_r2/total_shots:.1f}%)')
print(f'Noise (r=2): {total_shots - signal_r2} ({100*(total_shots - signal_r2)/total_shots:.1f}%)')

# Factor analysis for r=2
r = 2
print(f'\n--- FACTOR ANALYSIS (r={r}) ---')
print(f'For a={a}, r={r}: a^(r/2) = {a}^{r//2} = {pow(a, r//2)} = {pow(a, r//2, N)} mod {N}')
g1 = gcd(pow(a, r//2) - 1, N)
g2 = gcd(pow(a, r//2) + 1, N)
print(f'gcd({pow(a, r//2)}-1, {N}) = gcd({pow(a, r//2)-1}, {N}) = {g1}')
print(f'gcd({pow(a, r//2)}+1, {N}) = gcd({pow(a, r//2)+1}, {N}) = {g2}')
if 1 < g1 < N and 1 < g2 < N:
    print(f'★ FACTORS FOUND: {g1} × {g2} = {g1*g2} ★')
elif 1 < g1 < N:
    print(f'★ FACTOR FOUND: {g1}, {N//g1} ★')
elif 1 < g2 < N:
    print(f'★ FACTOR FOUND: {g2}, {N//g2} ★')
else:
    print(f'Trivial factors only')
