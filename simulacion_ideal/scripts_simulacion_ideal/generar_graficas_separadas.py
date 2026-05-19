"""
Genera las dos gráficas separadas solicitadas:
  1) analisis_ideal_puro_solo_N15.png
     - Subplot 1: Señal Ideal Pura (all-to-all)
     - Subplot 2: Profundidad 2Q Puro

  2) analisis_ideal_faketorino_overhead_N15.png
     - Subplot 1: Porcentaje de Señal Ideal (FakeTorino)
     - Subplot 2: Profundidad 2Q (FakeTorino)
     - Subplot 3: Overhead del Routing (Torino/Puro)

Lee los JSON canónicos:
  - /mnt/project/resultados_ideal_puro_N15.json
  - /mnt/project/resultados_ideal_faketorino_N15.json
"""

import json
import os
import matplotlib.pyplot as plt

# ─── CONFIG ───────────────────────────────────────
BASES = [4, 7, 11, 14]
OPT_LEVELS = [0, 1, 2, 3]
COLORES = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

DATOS_PURO = "/mnt/project/resultados_ideal_puro_N15.json"
DATOS_TORINO = "/mnt/project/resultados_ideal_faketorino_N15.json"
OUT_DIR = "/mnt/user-data/outputs"
os.makedirs(OUT_DIR, exist_ok=True)

# ─── CARGA DE DATOS ───────────────────────────────
with open(DATOS_PURO, 'r') as f:
    datos_puro = json.load(f)
with open(DATOS_TORINO, 'r') as f:
    datos_torino = json.load(f)


# ══════════════════════════════════════════════════
# IMAGEN 1: SIMULACIÓN IDEAL PURA (solo all-to-all)
# ══════════════════════════════════════════════════
fig1, axes1 = plt.subplots(1, 2, figsize=(16, 6))
ax1, ax2 = axes1

for i, a in enumerate(BASES):
    datos_a = datos_puro[f"a={a}"]
    niveles = [d["optimization_level"] for d in datos_a]
    senales = [d["signal_pct"] for d in datos_a]
    depths = [d["depth_2q"] for d in datos_a]

    # Panel 1: Señal Ideal Pura
    ax1.plot(niveles, senales, marker='o', linewidth=2,
             color=COLORES[i], label=f"a={a}")
    for x, y in zip(niveles, senales):
        ax1.text(x, y + 1.5, f"{y}%", ha='center', fontsize=9,
                 color=COLORES[i])

    # Panel 2: Profundidad 2Q Puro
    ax2.plot(niveles, depths, marker='o', linewidth=2,
             color=COLORES[i], label=f"a={a}")
    for x, y in zip(niveles, depths):
        ax2.text(x, y + 6, f"{y}", ha='center', fontsize=9,
                 color=COLORES[i])

ax1.set_title("Señal Ideal Pura (all-to-all)", fontsize=12, fontweight='bold')
ax1.set_xlabel("Nivel de Optimización", fontsize=11)
ax1.set_ylabel("Señal (%)", fontsize=11)
ax1.set_ylim(0, 110)
ax1.set_xticks(OPT_LEVELS)
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend()

ax2.set_title("Profundidad 2Q Puro (all-to-all)",
              fontsize=12, fontweight='bold')
ax2.set_xlabel("Nivel de Optimización", fontsize=11)
ax2.set_ylabel("Profundidad (Compuertas 2Q)", fontsize=11)
ax2.set_xticks(OPT_LEVELS)
ax2.grid(True, linestyle='--', alpha=0.6)
ax2.legend()

plt.suptitle("Simulación Ideal Pura: Shor N=15 (AerSimulator all-to-all)",
             fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()

out1 = os.path.join(OUT_DIR, "analisis_ideal_puro_solo_N15.png")
plt.savefig(out1, dpi=200, bbox_inches='tight')
plt.close(fig1)
print(f"[OK] Guardada: {out1}")


# ══════════════════════════════════════════════════
# IMAGEN 2: FAKETORINO + OVERHEAD
# ══════════════════════════════════════════════════
fig2, axes2 = plt.subplots(1, 3, figsize=(22, 6))
ax1, ax2, ax3 = axes2

for i, a in enumerate(BASES):
    datos_a = datos_torino[f"a={a}"]
    niveles = [d["optimization_level"] for d in datos_a]
    senales = [d["signal_pct"] for d in datos_a]
    depths = [d["depth_2q"] for d in datos_a]

    # Panel 1: Señal Ideal FakeTorino
    ax1.plot(niveles, senales, marker='o', linewidth=2,
             color=COLORES[i], label=f"Base a={a}")
    for x, y in zip(niveles, senales):
        ax1.text(x, y + 2, f"{y}%", ha='center', fontsize=9,
                 color=COLORES[i])

    # Panel 2: Profundidad 2Q FakeTorino
    ax2.plot(niveles, depths, marker='s', linewidth=2,
             color=COLORES[i], label=f"Base a={a}")
    # Escalamos la anotación al rango observado
    y_offset = max(depths) * 0.02 if max(depths) > 0 else 5
    for x, y in zip(niveles, depths):
        ax2.text(x, y + y_offset, f"{y}", ha='center', fontsize=9,
                 color=COLORES[i])

ax1.set_title("Porcentaje de Señal Ideal vs. Nivel de Optimización",
              fontsize=12, fontweight='bold')
ax1.set_xlabel("Nivel de Optimización", fontsize=11)
ax1.set_ylabel("Señal (%)", fontsize=11)
ax1.set_ylim(0, 110)
ax1.set_xticks(OPT_LEVELS)
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend()

ax2.set_title("Profundidad 2Q vs. Nivel de Optimización",
              fontsize=12, fontweight='bold')
ax2.set_xlabel("Nivel de Optimización", fontsize=11)
ax2.set_ylabel("Profundidad (Compuertas 2Q)", fontsize=11)
ax2.set_xticks(OPT_LEVELS)
ax2.grid(True, linestyle='--', alpha=0.6)
ax2.legend()

# Panel 3: Overhead del Routing (Torino/Puro) — barras agrupadas por opt.
ancho = 0.2
for i, a in enumerate(BASES):
    datos_p = datos_puro[f"a={a}"]
    datos_t = datos_torino[f"a={a}"]
    ratios = []
    for dp, dt in zip(datos_p, datos_t):
        if dp["depth_2q"] > 0:
            ratios.append(round(dt["depth_2q"] / dp["depth_2q"], 2))
        else:
            ratios.append(0)
    x_pos = [n + i * ancho for n in OPT_LEVELS]
    ax3.bar(x_pos, ratios, width=ancho, color=COLORES[i],
            label=f"a={a}", edgecolor='white', linewidth=0.5)
    for x, r in zip(x_pos, ratios):
        ax3.text(x, r + 0.05, f"{r:.1f}x", ha='center',
                 fontsize=8, fontweight='bold')

ax3.set_title("Overhead del Routing (Torino/Puro)",
              fontsize=12, fontweight='bold')
ax3.set_xlabel("Nivel de Optimización", fontsize=11)
ax3.set_ylabel("Ratio Profundidad 2Q", fontsize=11)
ax3.set_xticks([n + 1.5 * ancho for n in OPT_LEVELS])
ax3.set_xticklabels(OPT_LEVELS)
ax3.axhline(y=1, color='gray', linestyle=':', alpha=0.6)
ax3.legend(fontsize=9)
ax3.grid(True, linestyle='--', alpha=0.4, axis='y')

plt.suptitle("Análisis Ideal de Shor (N=15) con Topología de FakeTorino",
             fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()

out2 = os.path.join(OUT_DIR, "analisis_ideal_faketorino_overhead_N15.png")
plt.savefig(out2, dpi=200, bbox_inches='tight')
plt.close(fig2)
print(f"[OK] Guardada: {out2}")

print("\nListo. Gráficas generadas correctamente.")
