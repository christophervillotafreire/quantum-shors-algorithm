"""
comparacion_cruzada.py

Comparación unificada de los 3 entornos del algoritmo de Shor (N=15):
    1. Simulación Ideal (AerSimulator sin ruido)
    2. Simulación Ruidosa (FakeKyiv — Eagle r3, modelo de ruido real)
    3. Ejecución en Hardware Real (IBM Torino — Heron r1)

Este script consolida los datos de los tres entornos para generar:
    - Tabla de degradación unificada (PST, Fidelidad, Profundidad)
    - Gráficas comparativas de barras agrupadas
    - Reporte Markdown final para el trabajo de grado

Fuentes de datos:
    - Ideal + Ruidoso: ejecucion_real/datos/resultados_estudio_completo.json
    - Hardware: ejecucion_real/datos/resultados_estudio_hardware.json

═══════════════════════════════════════════════════════════════════════════════
OE4 de la propuesta: "Cuantificar la degradación de la señal cuántica
comparando los resultados experimentales frente a las simulaciones ideales,
utilizando métricas de Fidelidad y Probabilidad de Éxito."
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────
N = 15
CONTROL_QUBITS = 9

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
IMG_DIR = os.path.join(BASE_DIR, "imagenes")
REP_DIR = os.path.join(BASE_DIR, "reportes")

for d in [DATOS_DIR, IMG_DIR, REP_DIR]:
    os.makedirs(d, exist_ok=True)

# Colores del proyecto
COLORS = {
    'ideal': '#2ecc71',       # Verde
    'ruidoso': '#f39c12',     # Naranja
    'hardware': '#e74c3c',    # Rojo
    'accent': '#3498db',      # Azul
}


# ─── CARGA DE DATOS ─────────────────────────────────────────────────────────

def cargar_estudio_completo():
    """Carga datos ideal + FakeKyiv desde resultados_estudio_completo.json."""
    path = os.path.join(DATOS_DIR, "resultados_estudio_completo.json")
    with open(path) as f:
        return json.load(f)


def cargar_hardware():
    """Carga datos de hardware desde resultados_estudio_hardware.json."""
    path = os.path.join(DATOS_DIR, "resultados_estudio_hardware.json")
    with open(path) as f:
        return json.load(f)


def construir_tabla_comparacion(estudio, hw_data):
    """
    Construye la tabla de comparación cruzada.
    
    Para cada configuración que tiene datos en los 3 entornos, extrae:
    - Datos ideales (del campo 'ideal' del estudio)
    - Datos ruidosos (del campo 'noisy_fakekyiv' del estudio)
    - Datos de hardware (del campo 'hw_ibm_torino' o de hw_data)
    
    Returns:
        list[dict]: filas de la tabla de comparación
    """
    tabla = []
    
    # Recorrer las secciones del estudio completo que tienen datos de HW
    for study_name, entries in estudio.items():
        for entry in entries:
            config = entry.get("config", {})
            ideal = entry.get("ideal", {})
            noisy = entry.get("noisy_fakekyiv", {})
            hw = entry.get("hw_ibm_torino", None)
            
            # Solo incluir configs que tienen datos en los 3 entornos
            if not hw:
                continue
            if not ideal or not noisy:
                continue
            
            fila = {
                "estudio": study_name,
                "label": f"a={config.get('a', '?')}, opt={config.get('opt_level', '?')}, "
                         f"approx={config.get('approx_degree', '?')}",
                "a": config.get("a"),
                "opt_level": config.get("opt_level"),
                "approx_degree": config.get("approx_degree"),
                "dd": config.get("dd_enable", False),
                "pt": config.get("pt_enable_gates", False),
                # Transpilación
                "depth_2q": entry.get("isa_stats", {}).get("depth_2q", None),
                "gates_2q": entry.get("isa_stats", {}).get("2q_gates", None),
                # Ideal
                "pst_ideal": ideal.get("signal_pct", None),
                "f_ideal": ideal.get("fidelity", None),
                "factors_ideal": ideal.get("factors", None),
                # Ruidoso (FakeKyiv)
                "pst_ruidoso": noisy.get("signal_pct", None),
                "f_ruidoso": noisy.get("fidelity", None),
                "factors_ruidoso": noisy.get("factors", None),
                # Hardware (IBM Torino)
                "pst_hw": hw.get("signal_pct", None),
                "f_hw": hw.get("fidelity", None),
                "factors_hw": hw.get("factors", None),
                "job_id": hw.get("job_id", "—"),
                # Degradación
                "degrad_ideal_ruidoso": None,
                "degrad_ideal_hw": None,
                "degrad_ruidoso_hw": None,
            }
            
            # Calcular degradaciones
            if fila["pst_ideal"] is not None and fila["pst_ruidoso"] is not None:
                fila["degrad_ideal_ruidoso"] = round(fila["pst_ideal"] - fila["pst_ruidoso"], 2)
            if fila["pst_ideal"] is not None and fila["pst_hw"] is not None:
                fila["degrad_ideal_hw"] = round(fila["pst_ideal"] - fila["pst_hw"], 2)
            if fila["pst_ruidoso"] is not None and fila["pst_hw"] is not None:
                fila["degrad_ruidoso_hw"] = round(fila["pst_ruidoso"] - fila["pst_hw"], 2)
            
            tabla.append(fila)
    
    # Agregar datos de hardware del estudio A3 (barrido de bases) que
    # puede tener matching entries en el estudio_completo
    # Estos ya se capturaron arriba si tienen hw_ibm_torino
    
    return tabla


# ─── GRÁFICAS ────────────────────────────────────────────────────────────────

def generar_graficas(tabla):
    """Genera gráficas comparativas de los 3 entornos."""
    
    if not tabla:
        print("  ⚠ No hay datos para graficar.")
        return
    
    # Filtrar: solo configs con datos válidos en los 3 entornos
    datos_validos = [f for f in tabla if all([
        f["pst_ideal"] is not None,
        f["pst_ruidoso"] is not None,
        f["pst_hw"] is not None
    ])]
    
    if not datos_validos:
        print("  ⚠ No hay configuraciones con datos en los 3 entornos.")
        return
    
    # ─── GRÁFICA 1: PST por entorno ─────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(24, 7))
    
    labels = [f["label"] for f in datos_validos]
    pst_ideal = [f["pst_ideal"] for f in datos_validos]
    pst_ruidoso = [f["pst_ruidoso"] for f in datos_validos]
    pst_hw = [f["pst_hw"] for f in datos_validos]
    
    x = np.arange(len(labels))
    width = 0.25
    
    ax = axes[0]
    bars_i = ax.bar(x - width, pst_ideal, width, label='Ideal', 
                     color=COLORS['ideal'], edgecolor='white', linewidth=0.5)
    bars_r = ax.bar(x, pst_ruidoso, width, label='FakeKyiv (ruido)', 
                     color=COLORS['ruidoso'], edgecolor='white', linewidth=0.5)
    bars_h = ax.bar(x + width, pst_hw, width, label='IBM Torino (HW)', 
                     color=COLORS['hardware'], edgecolor='white', linewidth=0.5)
    
    # Etiquetas en barras
    for bar_group in [bars_i, bars_r, bars_h]:
        for bar in bar_group:
            h = bar.get_height()
            if h > 5:
                ax.text(bar.get_x() + bar.get_width()/2., h + 1,
                       f'{h:.0f}%', ha='center', va='bottom', fontsize=7)
    
    ax.set_title('Probabilidad de Éxito (PST)', fontsize=13, fontweight='bold')
    ax.set_ylabel('PST (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylim(0, 115)
    ax.legend(fontsize=9)
    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
    
    # ─── GRÁFICA 2: Fidelidad por entorno ───────────────────────────────
    f_ideal = [f.get("f_ideal", 0) or 0 for f in datos_validos]
    f_ruidoso = [f.get("f_ruidoso", 0) or 0 for f in datos_validos]
    f_hw = [f.get("f_hw", 0) or 0 for f in datos_validos]
    
    ax = axes[1]
    bars_i = ax.bar(x - width, f_ideal, width, label='Ideal', 
                     color=COLORS['ideal'], edgecolor='white', linewidth=0.5)
    bars_r = ax.bar(x, f_ruidoso, width, label='FakeKyiv (ruido)', 
                     color=COLORS['ruidoso'], edgecolor='white', linewidth=0.5)
    bars_h = ax.bar(x + width, f_hw, width, label='IBM Torino (HW)', 
                     color=COLORS['hardware'], edgecolor='white', linewidth=0.5)
    
    for bar_group in [bars_i, bars_r, bars_h]:
        for bar in bar_group:
            h = bar.get_height()
            if h > 0.01:
                ax.text(bar.get_x() + bar.get_width()/2., h + 0.01,
                       f'{h:.3f}', ha='center', va='bottom', fontsize=6, rotation=90)
    
    ax.set_title('Fidelidad de Hellinger ($\\mathcal{F}_H$)', fontsize=13, fontweight='bold')
    ax.set_ylabel('$\\mathcal{F}_H$')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylim(0, 1.15)
    ax.legend(fontsize=9)
    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
    
    # ─── GRÁFICA 3: Degradación acumulada ───────────────────────────────
    degrad_ir = [f.get("degrad_ideal_ruidoso", 0) or 0 for f in datos_validos]
    degrad_ih = [f.get("degrad_ideal_hw", 0) or 0 for f in datos_validos]
    
    ax = axes[2]
    ax.bar(x - 0.15, degrad_ir, 0.3, label='Ideal → FakeKyiv', 
           color=COLORS['ruidoso'], edgecolor='white', linewidth=0.5)
    ax.bar(x + 0.15, degrad_ih, 0.3, label='Ideal → IBM Torino', 
           color=COLORS['hardware'], edgecolor='white', linewidth=0.5)
    
    ax.set_title('Degradación de PST (pp)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Pérdida de PST (puntos porcentuales)')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.legend(fontsize=9)
    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
    
    plt.suptitle(f'Comparación Cruzada — Shor N={N}: Ideal vs FakeKyiv vs IBM Torino',
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    img_path = os.path.join(IMG_DIR, "comparacion_cruzada_N15.png")
    plt.savefig(img_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  Gráfica guardada en -> {img_path}")
    
    # ─── GRÁFICA 4: Depth 2Q vs PST scatter ────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 7))
    
    for fila in datos_validos:
        d2q = fila.get("depth_2q", 0) or 0
        if d2q == 0:
            continue
        ax.scatter(d2q, fila["pst_ideal"], c=COLORS['ideal'], marker='o', s=120, 
                   zorder=3, edgecolors='white', linewidth=1)
        ax.scatter(d2q, fila["pst_ruidoso"], c=COLORS['ruidoso'], marker='s', s=120, 
                   zorder=3, edgecolors='white', linewidth=1)
        ax.scatter(d2q, fila["pst_hw"], c=COLORS['hardware'], marker='^', s=120, 
                   zorder=3, edgecolors='white', linewidth=1)
        # Línea conectando los 3 puntos
        ax.plot([d2q]*3, [fila["pst_ideal"], fila["pst_ruidoso"], fila["pst_hw"]],
                color='gray', linewidth=0.8, alpha=0.4, linestyle='--')
        # Anotar base
        ax.annotate(f'a={fila["a"]}', (d2q, fila["pst_hw"]), 
                    textcoords="offset points", xytext=(8, -5), fontsize=7)
    
    # Leyenda manual
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS['ideal'], 
               markersize=10, label='Ideal'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor=COLORS['ruidoso'], 
               markersize=10, label='FakeKyiv (ruido)'),
        Line2D([0], [0], marker='^', color='w', markerfacecolor=COLORS['hardware'], 
               markersize=10, label='IBM Torino (HW)'),
    ]
    ax.legend(handles=legend_elements, fontsize=10)
    
    ax.set_title(f'Profundidad 2Q vs PST — Comparación de 3 Entornos (N={N})',
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Profundidad 2Q (after transpilación)', fontsize=12)
    ax.set_ylabel('PST (%)', fontsize=12)
    ax.set_ylim(-5, 110)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    img_path2 = os.path.join(IMG_DIR, "depth2q_vs_pst_cruzado_N15.png")
    plt.savefig(img_path2, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  Gráfica guardada en -> {img_path2}")


# ─── REPORTE ─────────────────────────────────────────────────────────────────

def generar_reporte(tabla):
    """Genera el reporte Markdown de comparación cruzada."""
    md_path = os.path.join(REP_DIR, "comparacion_cruzada.md")
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Comparación Cruzada — Shor N=15: Ideal vs FakeKyiv vs IBM Torino\n\n")
        f.write("> **OE4 de la propuesta:** Cuantificar la degradación de la señal cuántica\n")
        f.write("> comparando los resultados experimentales frente a las simulaciones ideales,\n")
        f.write("> utilizando métricas de Fidelidad ($\\mathcal{F}_H$) y Probabilidad de Éxito (PST).\n\n")
        
        f.write("## Configuración del Experimento\n\n")
        f.write("| Entorno | Backend | Tipo | Shots |\n")
        f.write("|---------|---------|------|:-----:|\n")
        f.write("| **Ideal** | AerSimulator (sin ruido) | Simulación | 4096 |\n")
        f.write("| **Ruidoso** | FakeKyiv (Eagle r3, 127 qubits) | Simulación con modelo de ruido | 1024 |\n")
        f.write("| **Hardware** | IBM Torino (Heron r1, 133 qubits) | Ejecución en QPU real | 4096 |\n\n")
        
        f.write("> [!NOTE]\n")
        f.write("> El entorno ruidoso utiliza **FakeKyiv** (Eagle r3) y no FakeTorino (Heron r1)\n")
        f.write("> porque los datos con `approx_degree=0.7` ya estaban disponibles para FakeKyiv.\n")
        f.write("> Ambos backends tienen modelos de ruido realistas calibrados con hardware real.\n\n")
        
        # ── Tabla principal ──────────────────────────────────────────────
        datos_validos = [fila for fila in tabla if all([
            fila["pst_ideal"] is not None,
            fila["pst_ruidoso"] is not None,
            fila["pst_hw"] is not None
        ])]
        
        f.write("## Tabla de Degradación\n\n")
        f.write("| Estudio | Config | Depth 2Q | PST Ideal | PST Ruidoso | PST HW | "
                "$\\mathcal{F}_H$ Ideal | $\\mathcal{F}_H$ Ruidoso | $\\mathcal{F}_H$ HW | "
                "Δ Ideal→HW | Factores HW |\n")
        f.write("|---------|--------|:--------:|:---------:|:-----------:|:------:|"
                ":---:|:---:|:---:|:---:|:---:|\n")
        
        for fila in datos_validos:
            fac_str = ", ".join(map(str, fila["factors_hw"])) if fila["factors_hw"] else "—"
            f_ideal = f"{fila['f_ideal']:.4f}" if fila['f_ideal'] else "—"
            f_ruidoso = f"{fila['f_ruidoso']:.4f}" if fila['f_ruidoso'] else "—"
            f_hw = f"{fila['f_hw']:.4f}" if fila['f_hw'] else "—"
            degrad = f"-{fila['degrad_ideal_hw']:.1f}pp" if fila['degrad_ideal_hw'] is not None else "—"
            
            f.write(f"| {fila['estudio']} | {fila['label']} | {fila.get('depth_2q', '—')} | "
                    f"{fila['pst_ideal']:.1f}% | {fila['pst_ruidoso']:.1f}% | "
                    f"{fila['pst_hw']:.1f}% | {f_ideal} | {f_ruidoso} | {f_hw} | "
                    f"{degrad} | {fac_str} |\n")
        
        # ── Gráficas ────────────────────────────────────────────────────
        f.write("\n## Gráficas Comparativas\n\n")
        f.write("### PST, Fidelidad y Degradación por Configuración\n")
        f.write("![Comparación cruzada](../imagenes/comparacion_cruzada_N15.png)\n\n")
        f.write("### Profundidad 2Q vs PST en los 3 Entornos\n")
        f.write("![Depth vs PST](../imagenes/depth2q_vs_pst_cruzado_N15.png)\n\n")
        
        # ── Análisis ────────────────────────────────────────────────────
        f.write("## Análisis de Resultados\n\n")
        
        if datos_validos:
            # Promedios
            avg_pst_ideal = np.mean([f["pst_ideal"] for f in datos_validos])
            avg_pst_ruidoso = np.mean([f["pst_ruidoso"] for f in datos_validos])
            avg_pst_hw = np.mean([f["pst_hw"] for f in datos_validos])
            avg_f_ruidoso = np.mean([f["f_ruidoso"] for f in datos_validos if f["f_ruidoso"]])
            avg_f_hw = np.mean([f["f_hw"] for f in datos_validos if f["f_hw"]])
            
            f.write("### Promedios Globales\n\n")
            f.write("| Métrica | Ideal | Ruidoso (FakeKyiv) | Hardware (IBM Torino) |\n")
            f.write("|---------|:-----:|:------------------:|:---------------------:|\n")
            f.write(f"| **PST promedio** | {avg_pst_ideal:.1f}% | {avg_pst_ruidoso:.1f}% | "
                    f"{avg_pst_hw:.1f}% |\n")
            f.write(f"| **$\\mathcal{{F}}_H$ promedio** | ≈1.0 | {avg_f_ruidoso:.4f} | "
                    f"{avg_f_hw:.4f} |\n")
            f.write(f"| **Degradación PST** | — | -{avg_pst_ideal - avg_pst_ruidoso:.1f}pp | "
                    f"-{avg_pst_ideal - avg_pst_hw:.1f}pp |\n\n")
        
        f.write("### Observaciones Clave\n\n")
        f.write("1. **La señal se degrada progresivamente** al pasar de un entorno ideal a uno\n")
        f.write("   ruidoso y luego a hardware real, confirmando la hipótesis de la propuesta.\n\n")
        f.write("2. **El nivel de optimización es crítico**: `opt=0` produce circuitos tan profundos\n")
        f.write("   que la señal colapsa a <5% en hardware, mientras que `opt=2/3` mantiene\n")
        f.write("   señal >50% al reducir drásticamente la profundidad 2Q.\n\n")
        f.write("3. **FakeKyiv no siempre predice el hardware**: en algunos casos el hardware\n")
        f.write("   real rinde mejor que la simulación ruidosa (ejemplo: `opt=2, a=4`), lo cual\n")
        f.write("   sugiere que el modelo de ruido de FakeKyiv puede ser más pesimista que el\n")
        f.write("   hardware real de IBM Torino.\n\n")
        f.write("4. **Factorización exitosa en hardware**: a pesar de la degradación, el\n")
        f.write("   post-procesamiento clásico de fracciones continuas logra extraer los factores\n")
        f.write("   correctos (3 × 5) en la mayoría de configuraciones con señal >20%.\n\n")
        
        f.write("## Conclusiones\n\n")
        f.write("1. Se demuestra cuantitativamente la degradación **Ideal → Ruidoso → Hardware**\n")
        f.write("   para el algoritmo de Shor (N=15), cumpliendo el OE4 de la propuesta.\n")
        f.write("2. La optimización del transpilador (nivel 2-3) es la variable más impactante\n")
        f.write("   para la viabilidad del algoritmo en hardware NISQ.\n")
        f.write("3. El uso de Fake Backends como paso intermedio de validación (Fase III) es\n")
        f.write("   efectivo: los resultados ruidosos anticipan la tendencia del hardware real.\n")
        f.write("4. La factorización de N=15 es viable en IBM Torino con circuitos optimizados,\n")
        f.write("   logrando señal >70% y fidelidad >0.5 en las mejores configuraciones.\n")
    
    print(f"  Reporte guardado en -> {md_path}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print(f"Comparación Cruzada — Shor N={N}")
    print(f"  Entornos: Ideal | FakeKyiv (ruido) | IBM Torino (hardware)\n")
    
    # 1. Cargar datos
    print("  [1/4] Cargando datos...", flush=True)
    estudio = cargar_estudio_completo()
    hw_data = cargar_hardware()
    
    # 2. Construir tabla
    print("  [2/4] Construyendo tabla de comparación...", flush=True)
    tabla = construir_tabla_comparacion(estudio, hw_data)
    
    datos_con_3 = [f for f in tabla if all([
        f["pst_ideal"] is not None,
        f["pst_ruidoso"] is not None,
        f["pst_hw"] is not None
    ])]
    print(f"         -> {len(tabla)} configuraciones totales, "
          f"{len(datos_con_3)} con datos en los 3 entornos")
    
    for fila in datos_con_3:
        print(f"         {fila['label']}: "
              f"PST = {fila['pst_ideal']:.0f}% → {fila['pst_ruidoso']:.0f}% → {fila['pst_hw']:.0f}%")
    
    # 3. Guardar JSON
    print("\n  [3/4] Generando gráficas y JSON...", flush=True)
    json_path = os.path.join(DATOS_DIR, "comparacion_cruzada_N15.json")
    
    # Convertir a serializable
    tabla_serial = []
    for fila in tabla:
        fila_clean = {}
        for k, v in fila.items():
            if isinstance(v, (np.integer, np.floating)):
                fila_clean[k] = float(v)
            else:
                fila_clean[k] = v
        tabla_serial.append(fila_clean)
    
    with open(json_path, 'w') as f:
        json.dump(tabla_serial, f, indent=2, ensure_ascii=False)
    print(f"         -> JSON guardado en {json_path}")
    
    # 4. Gráficas
    generar_graficas(tabla)
    
    # 5. Reporte
    print("\n  [4/4] Generando reporte Markdown...", flush=True)
    generar_reporte(tabla)
    
    print(f"\n[✔] Comparación cruzada completada exitosamente.")


if __name__ == '__main__':
    main()
