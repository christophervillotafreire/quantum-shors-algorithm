"""
fracciones_continuas.py

Módulo de análisis detallado de fracciones continuas con trazabilidad completa
para el post-procesamiento clásico del algoritmo de Shor.

═══════════════════════════════════════════════════════════════════════════════
ALGORITMO DE FRACCIONES CONTINUAS (Nielsen & Chuang §5.3.1, Apéndice 4)
═══════════════════════════════════════════════════════════════════════════════

Dado un resultado de medición y ∈ {0, 1, ..., 2^m - 1}, la fase estimada es:

    φ̃ = y / 2^m

El algoritmo de fracciones continuas descompone φ̃ en:

    φ̃ = a₀ + 1/(a₁ + 1/(a₂ + 1/(...)))   =  [a₀; a₁, a₂, ...]

Los convergentes p_k/q_k se calculan recursivamente (Euler):

    p_{-2} = 0,  p_{-1} = 1
    q_{-2} = 1,  q_{-1} = 0

    p_k = a_k · p_{k-1} + p_{k-2}
    q_k = a_k · q_{k-1} + q_{k-2}

El denominador q_k es candidato a período r si:
    1. 1 < q_k < N
    2. a^{q_k} ≡ 1 (mod N)

═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
from math import gcd
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from algoritmo.circuit import RegisterQC
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
N = 15
BASES = [4, 7, 11, 14]
SHOTS = 4096
SEED = 457
CONTROL_QUBITS = 9

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
REP_DIR = os.path.join(BASE_DIR, "reportes")

for d in [DATOS_DIR, REP_DIR]:
    os.makedirs(d, exist_ok=True)

# ─── FUNCIONES DE FRACCIONES CONTINUAS ───────────────────────────────────────

def descomponer_fraccion_continua(numerador, denominador):
    """
    Descompone una fracción p/q en sus coeficientes de fracción continua [a₀; a₁, a₂, ...].

    Algoritmo de Euclides extendido:
        a_k = ⌊numerador / denominador⌋
        numerador, denominador ← denominador, numerador - a_k * denominador
    """
    coeficientes = []
    while denominador != 0:
        a = numerador // denominador
        coeficientes.append(a)
        numerador, denominador = denominador, numerador - a * denominador
    return coeficientes

def calcular_convergentes(coeficientes):
    """
    Calcula los convergentes p_k/q_k a partir de los coeficientes de la fracción continua.

    Relación de recurrencia de Euler:

        p_{-2} = 0,   p_{-1} = 1
        q_{-2} = 1,   q_{-1} = 0

        p_k = a_k · p_{k-1} + p_{k-2}
        q_k = a_k · q_{k-1} + q_{k-2}

    El k-ésimo convergente es p_k/q_k, que es la mejor aproximación racional
    a la fracción original con denominador ≤ q_k.

    Returns:
        list of tuples: [(p_0, q_0), (p_1, q_1), ...]
    """
    convergentes = []

    # Semillas de la recursión de Euler
    p_prev2, q_prev2 = 0, 1   # p_{-2}, q_{-2}
    p_prev1, q_prev1 = 1, 0   # p_{-1}, q_{-1}

    for k, a_k in enumerate(coeficientes):
        p_k = a_k * p_prev1 + p_prev2
        q_k = a_k * q_prev1 + q_prev2
        convergentes.append((p_k, q_k))
        p_prev2, p_prev1 = p_prev1, p_k
        q_prev2, q_prev1 = q_prev1, q_k

    return convergentes

def analizar_fase(y, m, a, N):
    """
    Análisis completo de fracciones continuas para un resultado de medición y.

    Registra cada paso del algoritmo con trazabilidad completa:
    1. Valor medido y → fase φ̃ = y/2^m
    2. Descomposición en coeficientes [a₀; a₁, ...]
    3. Cálculo de convergentes p_k/q_k
    4. Evaluación de cada denominador como candidato a período r
    5. Extracción de factores si r es válido
    """
    dim = 2 ** m
    phase = y / dim

    # Descomponer la fase en fracción continua
    coeficientes = descomponer_fraccion_continua(y, dim)
    convergentes = calcular_convergentes(coeficientes)

    # También usar Fraction de Python para comparación
    frac_python = Fraction(phase).limit_denominator(N)

    # Evaluar cada convergente como candidato a período
    analisis_convergentes = []
    mejor_r = None
    factores = None

    for k, (p_k, q_k) in enumerate(convergentes):
        es_candidato = False
        es_periodo_valido = False
        factores_encontrados = None
        es_trivial = False
        g1_val = None
        g2_val = None

        if 1 < q_k < N:
            es_candidato = True
            if pow(a, q_k, N) == 1:
                es_periodo_valido = True
                if mejor_r is None:
                    mejor_r = q_k

                # Intentar extraer factores
                if q_k % 2 == 0:
                    g1_val = gcd(pow(a, q_k // 2) - 1, N)
                    g2_val = gcd(pow(a, q_k // 2) + 1, N)
                    if 1 < g1_val < N and 1 < g2_val < N:
                        factores_encontrados = sorted([g1_val, g2_val])
                        if factores is None:
                            factores = factores_encontrados
                    elif g1_val in (1, N) or g2_val in (1, N):
                        es_trivial = True
                        factores_encontrados = f"triviales: gcd={g1_val}, {g2_val}"

        analisis_convergentes.append({
            "k": k,
            "coeficiente_a_k": coeficientes[k] if k < len(coeficientes) else None,
            "convergente_p_k": p_k,
            "convergente_q_k": q_k,
            "fraccion": f"{p_k}/{q_k}",
            "valor_decimal": round(p_k / q_k, 8) if q_k > 0 else None,
            "es_candidato_r": es_candidato,
            "es_periodo_valido": es_periodo_valido,
            "factores": factores_encontrados,
            "es_trivial": es_trivial,
            "gcd_values": (g1_val, g2_val) if g1_val is not None else None
        })

    return {
        "y_medido": y,
        "bitstring": format(y, f'0{m}b'),
        "fase_estimada": round(phase, 8),
        "fase_fraccion": f"{y}/{dim}",
        "coeficientes_fc": coeficientes,
        "notacion_fc": f"[{coeficientes[0]}; {', '.join(map(str, coeficientes[1:]))}]" if len(coeficientes) > 1 else f"[{coeficientes[0]}]",
        "convergentes": analisis_convergentes,
        "periodo_encontrado": mejor_r,
        "factores_encontrados": factores,
        "fraccion_python_limit_denom": f"{frac_python.numerator}/{frac_python.denominator}",
        "r_python": frac_python.denominator if 1 < frac_python.denominator < N and pow(a, frac_python.denominator, N) == 1 else None
    }

def find_order(a, N):
    """Orden multiplicativo."""
    val = 1
    for r in range(1, N):
        val = (val * a) % N
        if val == 1:
            return r
    return None

# ─── EJECUCIÓN PRINCIPAL ────────────────────────────────────────────────────

def run_continued_fractions_analysis():
    print(f"[{time.strftime('%H:%M:%S')}] Análisis de fracciones continuas para Shor N={N}...\n")

    ideal_simulator = AerSimulator()
    sampler = SamplerV2(mode=ideal_simulator)

    todos_resultados = {}

    for a in BASES:
        r_teorico = find_order(a, N)
        print(f"{'='*60}")
        print(f"  Base a={a}, ord_{N}({a}) = {r_teorico}")
        print(f"{'='*60}")

        # Simulación
        circuito = RegisterQC()
        qc = circuito.create_circuit(N, a)
        isa = transpile(qc, backend=ideal_simulator, optimization_level=3, seed_transpiler=SEED)
        job = sampler.run([(isa,)], shots=SHOTS)
        counts = job.result()[0].data.output.get_counts()

        # Analizar los top resultados más frecuentes
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top_resultados = sorted_counts[:min(10, len(sorted_counts))]

        analisis_base = {
            "orden_teorico": r_teorico,
            "total_shots": SHOTS,
            "resultados_analizados": []
        }

        for bs, count in top_resultados:
            y = int(bs, 2)
            prob = count / SHOTS

            analisis = analizar_fase(y, CONTROL_QUBITS, a, N)
            analisis["conteo"] = count
            analisis["probabilidad"] = round(prob, 6)

            analisis_base["resultados_analizados"].append(analisis)

            # Imprimir cadena completa
            print(f"\n  y={y} (|{bs}⟩), prob={prob:.4f}, fase={analisis['fase_estimada']:.6f}")
            print(f"    Fracción continua: {analisis['notacion_fc']}")
            for conv in analisis["convergentes"]:
                estado = ""
                if conv["es_periodo_valido"]:
                    estado = f" ← r={conv['convergente_q_k']} VÁLIDO"
                    if conv["factores"] and isinstance(conv["factores"], list):
                        estado += f", factores={conv['factores']}"
                    elif conv["es_trivial"]:
                        estado += f", TRIVIALES ({conv['factores']})"
                elif conv["es_candidato_r"]:
                    estado = " (candidato, pero a^q ≠ 1)"
                print(f"    k={conv['k']}: p/q = {conv['fraccion']} = {conv['valor_decimal']}{estado}")

        todos_resultados[f"a={a}"] = analisis_base

    # ─── GUARDAR JSON ───
    json_path = os.path.join(DATOS_DIR, "fracciones_continuas_N15.json")

    def json_convert(o):
        if isinstance(o, tuple):
            return list(o)
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    with open(json_path, 'w') as f:
        json.dump(todos_resultados, f, indent=2, ensure_ascii=False, default=json_convert)
    print(f"\nDatos guardados en -> {json_path}")

    # ─── GENERAR REPORTE ───
    generar_reporte(todos_resultados)
    print(f"\n[✔] Análisis de fracciones continuas completado exitosamente.")


def generar_reporte(todos_resultados):
    """Genera el reporte Markdown con explicación rigurosa completa."""
    md_path = os.path.join(REP_DIR, "fracciones_continuas.md")

    with open(md_path, 'w', encoding='utf-8') as f:

        # ═════════════════════════════════════════════════════════════
        # ENCABEZADO
        # ═════════════════════════════════════════════════════════════
        f.write("# Análisis de Fracciones Continuas: Algoritmo de Shor (N=15)\n\n")
        f.write("> **Objetivo:** Documentar con rigor completo cómo el post-procesamiento clásico "
                "del algoritmo de Shor recupera los factores de $N$ a partir de los resultados "
                "cuánticos de medición. Se muestra paso a paso la cadena completa: "
                "**medición $\\to$ fase $\\to$ fracciones continuas $\\to$ período $\\to$ factores**.\n\n")

        # ═════════════════════════════════════════════════════════════
        # SECCIÓN 1 — VISIÓN GENERAL
        # ═════════════════════════════════════════════════════════════
        f.write("## 1. ¿Cómo se conecta la parte cuántica con la extracción de factores?\n\n")
        f.write("El algoritmo de Shor consta de **dos partes** que cooperan:\n\n")
        f.write("### Parte cuántica: Estimación de Fase (QPE)\n\n")
        f.write("El circuito cuántico implementa la **Estimación de Fase Cuántica** (QPE) sobre el operador "
                "unitario $U_a |y\\rangle = |ay \\bmod N\\rangle$. Los eigenvalores de $U_a$ son:\n\n")
        f.write("$$U_a |u_s\\rangle = e^{2\\pi i s/r} |u_s\\rangle, \\quad s = 0, 1, \\ldots, r-1$$\n\n")
        f.write("donde $r = \\text{ord}_N(a)$ es el **orden multiplicativo** de $a$ módulo $N$ "
                "(el menor entero positivo tal que $a^r \\equiv 1 \\pmod{N}$).\n\n")
        f.write("Al medir el registro de control (de $m$ qubits), obtenemos un valor $y$ cuya fase es:\n\n")
        f.write("$$\\tilde{\\varphi} = \\frac{y}{2^m} \\approx \\frac{s}{r}$$\n\n")
        f.write("Es decir, la medición cuántica nos da una **aproximación binaria** a la fracción $s/r$, "
                "donde $s$ es aleatorio pero $r$ es el período que necesitamos.\n\n")

        f.write("### Parte clásica: De la fase al período y de ahí a los factores\n\n")
        f.write("El problema es que conocemos $\\tilde{\\varphi} = y/2^m$ como número decimal, pero "
                "necesitamos recuperar el denominador $r$ de la fracción $s/r$. "
                "Esto se logra con el **algoritmo de fracciones continuas**.\n\n")
        f.write("Una vez que tenemos $r$, los factores de $N$ se extraen con **aritmética clásica**:\n\n")
        f.write("$$p = \\gcd\\left(a^{r/2} - 1,\\; N\\right), \\quad q = \\gcd\\left(a^{r/2} + 1,\\; N\\right)$$\n\n")
        f.write("Si $r$ es par y $a^{r/2} \\not\\equiv -1 \\pmod{N}$, entonces $p$ y $q$ son factores "
                "**no triviales** de $N$.\n\n")

        # ═════════════════════════════════════════════════════════════
        # SECCIÓN 2 — ALGORITMO DE FRACCIONES CONTINUAS
        # ═════════════════════════════════════════════════════════════
        f.write("## 2. Algoritmo de Fracciones Continuas (detalle formal)\n\n")

        f.write("### 2.1 ¿Por qué funciona?\n\n")
        f.write("El **Teorema de la Mejor Aproximación** (Nielsen & Chuang, Apéndice 4) garantiza que "
                "si $|\\tilde{\\varphi} - s/r| \\le 1/(2 \\cdot 2^m)$, entonces $s/r$ aparece como uno de los "
                "**convergentes** de la expansión en fracción continua de $\\tilde{\\varphi}$.\n\n")
        f.write("Como tenemos $m = 2n+1$ qubits de control (con $n = \\lceil \\log_2 N \\rceil$), se cumple que "
                "$2^m > 2N^2$. Esto asegura una precisión suficiente para que la fracción continua siempre "
                "recupere $s/r$ con $r < N$ (Nielsen & Chuang, Teorema 5.1).\n\n")

        f.write("### 2.2 Paso 1: Descomposición en coeficientes\n\n")
        f.write("Dada la fase $\\tilde{\\varphi} = y/2^m$, aplicamos el algoritmo de Euclides "
                "para obtener los coeficientes $[a_0; a_1, a_2, \\ldots]$ tales que:\n\n")
        f.write("$$\\frac{y}{2^m} = a_0 + \\cfrac{1}{a_1 + \\cfrac{1}{a_2 + \\cfrac{1}{\\ddots}}}$$\n\n")
        f.write("donde cada $a_k = \\lfloor \\text{numerador}_k / \\text{denominador}_k \\rfloor$, y la iteración es:\n\n")
        f.write("$$\\text{num}_{k+1} = \\text{den}_k, \\quad \\text{den}_{k+1} = \\text{num}_k - a_k \\cdot \\text{den}_k$$\n\n")

        f.write("### 2.3 Paso 2: Cálculo de convergentes\n\n")
        f.write("Los convergentes $p_k/q_k$ se calculan con la **recursión de Euler**:\n\n")
        f.write("$$p_k = a_k \\cdot p_{k-1} + p_{k-2}, \\quad q_k = a_k \\cdot q_{k-1} + q_{k-2}$$\n\n")
        f.write("con condiciones iniciales $p_{-2} = 0,\\; p_{-1} = 1,\\; q_{-2} = 1,\\; q_{-1} = 0$.\n\n")
        f.write("Cada convergente $p_k/q_k$ es la **mejor aproximación racional** a $y/2^m$ "
                "con denominador $\\le q_k$.\n\n")

        f.write("### 2.4 Paso 3: Identificación del período\n\n")
        f.write("Para cada convergente, evaluamos si el denominador $q_k$ es el período $r$:\n\n")
        f.write("1. ¿$1 < q_k < N$? → Es **candidato**\n")
        f.write("2. ¿$a^{q_k} \\equiv 1 \\pmod{N}$? → Es **período válido**\n\n")

        f.write("### 2.5 Paso 4: Extracción de factores\n\n")
        f.write("Si $r$ es par, calculamos:\n\n")
        f.write("$$a^{r/2} \\bmod N \\quad \\text{(exponenciación modular clásica)}$$\n\n")
        f.write("Luego:\n\n")
        f.write("$$p = \\gcd(a^{r/2} - 1, N), \\quad q = \\gcd(a^{r/2} + 1, N)$$\n\n")
        f.write("**¿Por qué funciona esto?** Porque $a^r \\equiv 1 \\pmod{N}$ implica:\n\n")
        f.write("$$a^r - 1 \\equiv 0 \\pmod{N} \\implies (a^{r/2} - 1)(a^{r/2} + 1) \\equiv 0 \\pmod{N}$$\n\n")
        f.write("Es decir, $N$ divide al producto $(a^{r/2} - 1)(a^{r/2} + 1)$. Si $N$ no divide "
                "a ninguno de los dos factores individualmente (es decir, $a^{r/2} \\not\\equiv \\pm 1 \\pmod{N}$), "
                "entonces $\\gcd(a^{r/2} \\pm 1, N)$ nos da factores **no triviales** de $N$.\n\n")

        # ═════════════════════════════════════════════════════════════
        # SECCIÓN 3 — RESULTADOS POR BASE (CON EJEMPLOS TRABAJADOS)
        # ═════════════════════════════════════════════════════════════
        f.write("## 3. Resultados por Base — Ejemplos Trabajados Paso a Paso\n\n")

        for a in BASES:
            datos = todos_resultados[f"a={a}"]
            r_teo = datos["orden_teorico"]
            f.write(f"### Base $a={a}$, $\\text{{ord}}_{{{N}}}({a}) = {r_teo}$\n\n")

            # Tabla resumen
            f.write("| $y$ (decimal) | Bitstring | Prob. | Fase $\\tilde{\\varphi}$ | FC | Período $r$ | Factores |\n")
            f.write("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")

            for res in datos["resultados_analizados"][:6]:
                r_str = str(res["periodo_encontrado"]) if res["periodo_encontrado"] else "—"
                f_str = "—"
                if res["factores_encontrados"] and isinstance(res["factores_encontrados"], list):
                    f_str = ", ".join(map(str, res["factores_encontrados"]))
                else:
                    for conv in res["convergentes"]:
                        if conv["es_trivial"]:
                            f_str = "triviales"
                            break
                f.write(f"| {res['y_medido']} | `{res['bitstring']}` | {res['probabilidad']:.4f} "
                        f"| {res['fase_estimada']:.6f} | {res['notacion_fc']} | {r_str} | {f_str} |\n")

            f.write("\n")

            # ─── Ejemplo trabajado paso a paso ───
            # Elegir el primer resultado con y ≠ 0
            ejemplo = None
            for res in datos["resultados_analizados"]:
                if res["y_medido"] != 0:
                    ejemplo = res
                    break

            if ejemplo is None:
                continue

            y_ej = ejemplo["y_medido"]
            phase_ej = ejemplo["fase_estimada"]
            coefs = ejemplo["coeficientes_fc"]

            f.write(f"#### Ejemplo completo: resultado de medición $y = {y_ej}$\n\n")

            # Paso 1
            f.write(f"**Paso 1 — Fase estimada:**\n\n")
            f.write(f"$$\\tilde{{\\varphi}} = \\frac{{y}}{{2^m}} = \\frac{{{y_ej}}}{{{2**CONTROL_QUBITS}}} = {phase_ej}$$\n\n")

            # Paso 2
            f.write(f"**Paso 2 — Descomposición en fracción continua:**\n\n")
            f.write(f"Aplicamos el algoritmo de Euclides a ${y_ej}/{2**CONTROL_QUBITS}$:\n\n")

            # Mostrar las iteraciones del algoritmo de Euclides
            num, den = y_ej, 2**CONTROL_QUBITS
            f.write("| Iteración | Numerador | Denominador | $a_k = \\lfloor \\text{num}/\\text{den} \\rfloor$ | Nuevo num | Nuevo den |\n")
            f.write("|:---:|:---:|:---:|:---:|:---:|:---:|\n")
            for i, ak in enumerate(coefs):
                new_num = den
                new_den = num - ak * den
                f.write(f"| {i} | {num} | {den} | **{ak}** | {new_num} | {new_den} |\n")
                num, den = new_num, new_den
            f.write(f"\nResultado: $\\tilde{{\\varphi}} = {ejemplo['notacion_fc']}$\n\n")

            # Paso 3
            f.write(f"**Paso 3 — Cálculo de convergentes (recursión de Euler):**\n\n")
            f.write("Aplicamos la recursión con semillas $p_{{-2}}=0, p_{{-1}}=1, q_{{-2}}=1, q_{{-1}}=0$:\n\n")
            f.write("| $k$ | $a_k$ | $p_k = a_k \\cdot p_{k-1} + p_{k-2}$ | $q_k = a_k \\cdot q_{k-1} + q_{k-2}$ | Convergente $p_k/q_k$ | Valor |\n")
            f.write("|:---:|:---:|:---:|:---:|:---:|:---:|\n")

            # Recompute convergents with explicit formulas for the report
            p2, q2 = 0, 1  # p_{-2}, q_{-2}
            p1, q1 = 1, 0  # p_{-1}, q_{-1}
            for i, ak in enumerate(coefs):
                pk = ak * p1 + p2
                qk = ak * q1 + q2
                p_formula = f"${ak} \\cdot {p1} + {p2} = {pk}$"
                q_formula = f"${ak} \\cdot {q1} + {q2} = {qk}$"
                val = f"${pk}/{qk}$" if qk > 0 else "∞"
                val_dec = f"= {round(pk/qk, 6)}" if qk > 0 else ""
                f.write(f"| {i} | {ak} | {p_formula} | {q_formula} | {val} {val_dec} | |\n")
                p2, p1 = p1, pk
                q2, q1 = q1, qk

            f.write("\n")

            # Paso 4
            f.write(f"**Paso 4 — Evaluación de candidatos a período $r$:**\n\n")
            f.write("| $k$ | $q_k$ | ¿$1 < q_k < N$? | ¿$a^{q_k} \\equiv 1 \\pmod{N}$? | Período válido |\n")
            f.write("|:---:|:---:|:---:|:---:|:---:|\n")
            for conv in ejemplo["convergentes"]:
                qk = conv["convergente_q_k"]
                cand = "✅ Sí" if conv["es_candidato_r"] else f"❌ No ($q_k={qk}$)"
                if conv["es_candidato_r"]:
                    a_qk_mod = pow(a, qk, N)
                    per = f"✅ Sí (${a}^{{{qk}}} \\equiv {a_qk_mod} \\pmod{{{N}}}$)" if conv["es_periodo_valido"] else f"❌ No (${a}^{{{qk}}} \\equiv {a_qk_mod} \\pmod{{{N}}}$)"
                else:
                    per = "—"
                valid = "**$r = " + str(qk) + "$**" if conv["es_periodo_valido"] else "—"
                f.write(f"| {conv['k']} | {qk} | {cand} | {per} | {valid} |\n")

            f.write("\n")

            # Paso 5 — Extracción de factores
            r_found = ejemplo["periodo_encontrado"]
            if r_found and r_found % 2 == 0:
                half_r = r_found // 2
                a_half = pow(a, half_r, N)
                g1 = gcd(a_half - 1, N)
                g2 = gcd(a_half + 1, N)

                f.write(f"**Paso 5 — Extracción de factores de $N={N}$:**\n\n")
                f.write(f"El período encontrado es $r = {r_found}$, que es **par** ✅\n\n")
                f.write(f"Calculamos la exponenciación modular clásica:\n\n")
                f.write(f"$$a^{{r/2}} \\bmod N = {a}^{{{half_r}}} \\bmod {N} = {a_half}$$\n\n")

                f.write(f"Ahora usamos la identidad $(a^{{r/2}} - 1)(a^{{r/2}} + 1) \\equiv 0 \\pmod{{N}}$:\n\n")
                f.write(f"$$({a_half} - 1)({a_half} + 1) = {a_half - 1} \\cdot {a_half + 1} = {(a_half-1)*(a_half+1)}$$\n\n")
                f.write(f"Verificación: ${(a_half-1)*(a_half+1)} = {(a_half-1)*(a_half+1) // N} \\times {N} + {(a_half-1)*(a_half+1) % N}$"
                        f" → ${(a_half-1)*(a_half+1)} \\equiv {(a_half-1)*(a_half+1) % N} \\pmod{{{N}}}$ ✅\n\n")

                f.write(f"Factores:\n\n")
                f.write(f"$$p = \\gcd({a_half - 1},\\; {N}) = \\gcd({a}^{{{half_r}}} - 1,\\; {N}) = \\boxed{{{g1}}}$$\n\n")
                f.write(f"$$q = \\gcd({a_half + 1},\\; {N}) = \\gcd({a}^{{{half_r}}} + 1,\\; {N}) = \\boxed{{{g2}}}$$\n\n")

                if 1 < g1 < N and 1 < g2 < N:
                    f.write(f"**Resultado:** $N = {g1} \\times {g2} = {g1*g2}$ → ✅ **¡Factorización exitosa!**\n\n")
                    f.write(f"El circuito cuántico midió $y={y_ej}$, de ahí extraímos $r={r_found}$, "
                            f"y con aritmética clásica obtuvimos $\\boxed{{{N} = {g1} \\times {g2}}}$.\n\n")
                else:
                    f.write(f"**Resultado:** Los factores ${g1}$ y ${g2}$ son **triviales** ($\\{{1, N\\}}$).\n\n")
                    if a % N == N - 1:
                        f.write(f"Esto ocurre porque $a = {a} \\equiv -1 \\pmod{{{N}}}$, por lo que:\n\n")
                        f.write(f"$$a^{{r/2}} = {a}^1 = {a} \\equiv -1 \\pmod{{{N}}}$$\n\n")
                        f.write(f"y entonces $\\gcd(a^{{r/2}} + 1, N) = \\gcd({a_half + 1}, {N}) = {N}$ (trivial). "
                                f"Este es un caso conocido donde el algoritmo de Shor falla y debe reintentar con otro $a$.\n\n")
            elif r_found and r_found % 2 != 0:
                f.write(f"**Paso 5:** El período $r = {r_found}$ es **impar**. No se pueden extraer factores. "
                        f"Se debe reintentar con otro valor de $a$.\n\n")

            # Caso especial y=0
            for res in datos["resultados_analizados"]:
                if res["y_medido"] == 0:
                    f.write(f"#### Caso $y = 0$\n\n")
                    f.write(f"La medición $y=0$ corresponde a la fase $\\tilde{{\\varphi}} = 0/2^m = 0$, "
                            f"que equivale a $s = 0$ en $s/r$. Este resultado **no aporta información** "
                            f"sobre el período y se descarta. En simulación ideal, ocurre con probabilidad "
                            f"$1/r = 1/{r_teo} = {round(1/r_teo, 4)}$.\n\n")
                    break

            f.write("---\n\n")

        # ═════════════════════════════════════════════════════════════
        # SECCIÓN 4 — RESUMEN DE LA CADENA COMPLETA
        # ═════════════════════════════════════════════════════════════
        f.write("## 4. Resumen: La Cadena Completa de Factorización\n\n")
        f.write("```\n")
        f.write("┌─────────────────────────────────────────────────────────────────┐\n")
        f.write("│  PARTE CUÁNTICA                                                │\n")
        f.write("│                                                                │\n")
        f.write("│  1. Preparar |1⟩ en registro target                            │\n")
        f.write("│  2. Hadamard en todos los qubits de control                    │\n")
        f.write("│  3. Aplicar C-U_{a^{2^k}} para k = 0, ..., m-1                │\n")
        f.write("│  4. Aplicar QFT⁻¹ al registro de control                      │\n")
        f.write("│  5. Medir → obtener y (entero de m bits)                       │\n")
        f.write("└───────────────────────────┬─────────────────────────────────────┘\n")
        f.write("                            │  y = resultado de medición\n")
        f.write("                            ▼\n")
        f.write("┌─────────────────────────────────────────────────────────────────┐\n")
        f.write("│  PARTE CLÁSICA                                                 │\n")
        f.write("│                                                                │\n")
        f.write("│  6. Calcular fase: φ̃ = y / 2^m                                │\n")
        f.write("│  7. Fracciones continuas: φ̃ → [a₀; a₁, ...] → convergentes   │\n")
        f.write("│  8. Identificar r: buscar q_k tal que a^{q_k} ≡ 1 (mod N)     │\n")
        f.write("│  9. Si r par: calcular gcd(a^{r/2} ± 1, N)                    │\n")
        f.write("│  10. Verificar p × q = N → ¡Factores encontrados!              │\n")
        f.write("└─────────────────────────────────────────────────────────────────┘\n")
        f.write("```\n\n")

        # ═════════════════════════════════════════════════════════════
        # SECCIÓN 5 — CONCLUSIONES
        # ═════════════════════════════════════════════════════════════
        f.write("## 5. Conclusiones\n\n")
        f.write("1. El algoritmo de fracciones continuas **recupera exitosamente** el período $r$ "
                "a partir de las fases medidas por el QPE para $a \\in \\{4, 7, 11\\}$.\n\n")
        f.write("2. La cadena completa funciona: el QPE mide $y$, la fracción continua extrae "
                "$s/r$ del valor $y/2^m$, el denominador $r$ es el período, y $\\gcd(a^{r/2} \\pm 1, N)$ "
                "da los factores $3$ y $5$ de $N = 15$.\n\n")
        f.write("3. Para $a=14$ ($a \\equiv -1 \\pmod{15}$), el período $r=2$ se encuentra correctamente, "
                "pero los factores son **triviales** ($\\{1, 15\\}$). Esto es una limitación algebraica "
                "intrínseca, no un error del circuito (ver Nielsen & Chuang §5.3.2).\n\n")
        f.write("4. La medición $y=0$ (fase $\\varphi = 0$) no aporta información sobre el período y debe "
                "descartarse. En simulación ideal ocurre con probabilidad exactamente $1/r$.\n\n")
        f.write("5. La trazabilidad completa de cada paso (Euclides → convergentes → candidatos → GCD) "
                "permite verificar rigurosamente el post-procesamiento clásico del algoritmo.\n")

    print(f"Reporte guardado en -> {md_path}")


if __name__ == "__main__":
    run_continued_fractions_analysis()
