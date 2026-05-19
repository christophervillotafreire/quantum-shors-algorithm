"""
histogramas_picos_qpe.py

Genera una figura de 4 sub-paneles (a=4, a=7, a=11, a=14) con los histogramas
de medición del registro de conteo en simulación ideal del algoritmo de Shor (N=15).

Cada sub-panel muestra:
  - La distribución de conteos observada sobre los 2^t = 512 valores posibles de y.
  - Líneas verticales punteadas en los picos teóricos y_s = floor(s · 2^t / r).
  - Las cuentas observadas anotadas sobre cada pico.
  - La probabilidad relativa p(y_s) = conteo / shots.

Los datos de conteos se leen directamente del JSON generado por el script
fracciones_continuas_simulacion_ideal.py (resultado reproducible del mismo
experimento con seed=457 y 4096 shots).

Uso:
    python histogramas_picos_qpe.py
"""

import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
N = 15
BASES = [4, 7, 11, 14]
CONTROL_QUBITS = 9
DIM = 2 ** CONTROL_QUBITS   # 512
SHOTS = 4096

# Colores consistentes con el resto de figuras del proyecto
COLORES_BASE = {
    4:  "#e74c3c",
    7:  "#3498db",
    11: "#2ecc71",
    14: "#9b59b6",
}


def find_order(a, N):
    """Orden multiplicativo: menor r > 0 tal que a^r ≡ 1 (mod N)."""
    val = 1
    for r in range(1, N):
        val = (val * a) % N
        if val == 1:
            return r
    return None


def picos_teoricos(r, t):
    """Devuelve la lista de picos teóricos y_s = round(s * 2^t / r) para s = 0,...,r-1."""
    return [int(round(s * (2 ** t) / r)) for s in range(r)]


def reconstruir_counts(datos_fc, total_shots):
    """
    Reconstruye un array de 512 posiciones con los conteos observados,
    a partir de la lista `resultados_analizados` del JSON de fracciones continuas.
    Los valores y no medidos quedan en 0.
    """
    counts = np.zeros(DIM, dtype=int)
    for r_ent in datos_fc["resultados_analizados"]:
        y = r_ent["y_medido"]
        c = r_ent["conteo"]
        counts[y] = c
    return counts


def cargar_datos(json_path):
    """Carga el JSON de fracciones_continuas_N15.json."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── GENERACIÓN DE LA FIGURA ────────────────────────────────────────────────

def generar_figura(datos_json, out_path):
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    axes = axes.flatten()

    for idx, a in enumerate(BASES):
        ax = axes[idx]
        datos_a = datos_json[f"a={a}"]
        r = datos_a["orden_teorico"]
        total = datos_a["total_shots"]
        counts = reconstruir_counts(datos_a, total)
        picos = picos_teoricos(r, CONTROL_QUBITS)
        color = COLORES_BASE[a]

        # Histograma principal: barras verticales en cada y con conteo > 0
        # Para picos perfectos con 0 conteo en el resto, usamos barras gruesas
        # en las posiciones medidas y suprimimos el fondo para claridad.
        x_eje = np.arange(DIM)
        # Dibujamos todas las posiciones con altura 0 en gris claro para
        # indicar el "soporte" teórico del registro; las posiciones medidas
        # se destacan con barras coloreadas.
        ax.bar(x_eje, counts, width=2.0, color=color, alpha=0.85,
               edgecolor="black", linewidth=0.4, zorder=3,
               label="Conteos observados")

        # Líneas verticales punteadas en los picos teóricos
        for y_s in picos:
            ax.axvline(y_s, color="black", linestyle="--",
                       linewidth=1.0, alpha=0.6, zorder=2)

        # Anotaciones con el conteo y la probabilidad sobre cada pico teórico.
        # Desplazamos ligeramente las anotaciones fuera del eje y de la caja
        # resumen (esquina superior derecha) para evitar colisiones visuales.
        y_max_plot = max(counts.max() * 1.28, 100)
        for s, y_s in enumerate(picos):
            c = counts[y_s]
            p = c / total
            etiqueta = f"y={y_s}\nn={c}\np={p:.3f}"
            # Desplazamiento horizontal: el primer pico (y=0) se etiqueta
            # ligeramente a la derecha; el último, ligeramente a la izquierda.
            if s == 0:
                dx, ha = 30, "left"
            elif s == len(picos) - 1:
                dx, ha = -30, "right"
            else:
                dx, ha = 0, "center"
            ax.annotate(
                etiqueta,
                xy=(y_s, c),
                xytext=(y_s + dx, c + y_max_plot * 0.03),
                ha=ha, va="bottom",
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.25",
                          facecolor="white", edgecolor=color,
                          linewidth=0.8, alpha=0.95),
                zorder=5,
            )

        # Caso a=14: marcar que son factores triviales
        etiqueta_trivial = ""
        if a == 14:
            etiqueta_trivial = " (factores triviales: $a \\equiv -1\\ \\mathrm{mod}\\ N$)"

        # Estética del subplot
        ax.set_title(
            f"$a = {a}$, $r = \\mathrm{{ord}}_{{15}}({a}) = {r}${etiqueta_trivial}",
            fontsize=12, fontweight="bold",
        )
        ax.set_xlabel("Resultado medido $y$ (registro de conteo)", fontsize=10)
        ax.set_ylabel(f"Conteos (de {SHOTS} shots)", fontsize=10)
        ax.set_xlim(-8, DIM + 8)
        ax.set_ylim(0, y_max_plot)
        ax.grid(True, linestyle=":", alpha=0.4, zorder=1)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=9))

        # Texto resumen con PST y picos teóricos. Lo colocamos en el centro
        # inferior del subplot para evitar colisionar con las anotaciones de
        # los picos, que ocupan la parte superior.
        prob_picos = counts[picos].sum() / total
        resumen = (
            f"Picos teóricos: $\\{{{', '.join(map(str, picos))}\\}}$    "
            f"$PST = {100*prob_picos:.1f}\\%$"
        )
        ax.text(
            0.5, 0.55, resumen,
            transform=ax.transAxes,
            ha="center", va="center",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="#f8f9fa", edgecolor="gray",
                      linewidth=0.6),
        )

    fig.suptitle(
        "Histogramas de medición del QPE en simulación ideal — "
        f"Algoritmo de Shor ($N = {N}$, $t = {CONTROL_QUBITS}$, {SHOTS} shots)",
        fontsize=14, fontweight="bold", y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[✔] Figura guardada en: {out_path}")


# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    # Configuración de rutas (se adapta automáticamente al layout del proyecto)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Ruta al JSON de fracciones continuas (ajustar si la estructura difiere)
    candidatos_json = [
        os.path.join(script_dir, "fracciones_continuas_N15.json"),
        os.path.join(script_dir, "datos", "fracciones_continuas_N15.json"),
        os.path.join(os.path.dirname(script_dir), "datos",
                     "fracciones_continuas_N15.json"),
    ]
    json_path = next((p for p in candidatos_json if os.path.exists(p)), None)
    if json_path is None:
        sys.exit(
            "[✗] No se encontró fracciones_continuas_N15.json. "
            "Ejecute primero fracciones_continuas_simulacion_ideal.py."
        )

    # Ruta de salida de la imagen
    img_dir_candidatos = [
        os.path.join(script_dir, "imagenes"),
        os.path.join(os.path.dirname(script_dir), "imagenes"),
        script_dir,
    ]
    img_dir = next((d for d in img_dir_candidatos if os.path.isdir(d)),
                   script_dir)
    out_path = os.path.join(img_dir, "histogramas_picos_qpe_N15.png")

    print(f"[→] Leyendo datos desde: {json_path}")
    datos = cargar_datos(json_path)
    generar_figura(datos, out_path)


if __name__ == "__main__":
    main()
