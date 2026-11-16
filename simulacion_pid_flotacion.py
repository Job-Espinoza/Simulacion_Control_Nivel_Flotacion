"""Ejecución local por consola de la simulación de control de nivel de flotación.

Ejecutar:
    python simulacion_pid_flotacion.py

Genera CSV y gráficos PNG en la carpeta resultados/.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from simulacion import CELL_PARAMETERS, CELL_NAMES, calculate_metrics, simulate


def main() -> None:
    output_dir = Path("resultados")
    output_dir.mkdir(exist_ok=True)

    common = dict(
        duration_s=600,
        dt_s=1.0,
        setpoint_cm=32.0,
        disturbance_scale=1.0,
        tuning_scale=1.0,
        setpoint_step=True,
    )
    pi = simulate(strategy="PI", **common)
    ff = simulate(strategy="PI + Feedforward", **common)

    metrics_pi = calculate_metrics(pi)
    metrics_ff = calculate_metrics(ff)
    comparison = metrics_pi[["Celda", "IAE (cm·s)"]].merge(
        metrics_ff[["Celda", "IAE (cm·s)"]], on="Celda", suffixes=(" PI", " PI + FF")
    )
    comparison["Mejora (%)"] = (
        (comparison["IAE (cm·s) PI"] - comparison["IAE (cm·s) PI + FF"])
        / comparison["IAE (cm·s) PI"] * 100.0
    )

    # Exporta señales completas y resumen de indicadores.
    export = pd.DataFrame({"Tiempo (s)": pi["Tiempo (s)"]})
    for i in range(1, 4):
        export[f"Celda {i} - Nivel PI (cm)"] = pi[f"C{i} - Nivel (cm)"]
        export[f"Celda {i} - Nivel PI+FF (cm)"] = ff[f"C{i} - Nivel (cm)"]
        export[f"Celda {i} - Setpoint (cm)"] = ff[f"C{i} - Setpoint (cm)"]
        export[f"Celda {i} - Perturbación (L/min)"] = ff[f"C{i} - Perturbación entrada (L/min)"]
        export[f"Celda {i} - Bomba PI+FF (L/min)"] = ff[f"C{i} - Caudal bomba (L/min)"]
    export.to_csv(output_dir / "datos_simulacion.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(output_dir / "comparacion_IAE.csv", index=False, encoding="utf-8-sig")

    # Gráfico de niveles.
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for i, ax in enumerate(axes, start=1):
        ax.plot(pi["Tiempo (s)"], pi[f"C{i} - Nivel (cm)"], label="PI", linestyle="--")
        ax.plot(ff["Tiempo (s)"], ff[f"C{i} - Nivel (cm)"], label="PI + Feedforward")
        ax.plot(ff["Tiempo (s)"], ff[f"C{i} - Setpoint (cm)"], label="Setpoint", linestyle=":")
        ax.set_title(CELL_NAMES[i - 1])
        ax.set_ylabel("Nivel (cm)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
    axes[-1].set_xlabel("Tiempo (s)")
    fig.suptitle("Control de nivel de una batería de flotación")
    fig.tight_layout()
    fig.savefig(output_dir / "respuesta_niveles.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Gráfico comparativo IAE.
    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(3)
    width = 0.36
    ax.bar([v - width / 2 for v in x], comparison["IAE (cm·s) PI"], width, label="PI")
    ax.bar([v + width / 2 for v in x], comparison["IAE (cm·s) PI + FF"], width, label="PI + Feedforward")
    ax.set_xticks(list(x), CELL_NAMES)
    ax.set_ylabel("IAE (cm·s)")
    ax.set_title("Comparación del error integral absoluto")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "comparacion_IAE.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    print("\nPARÁMETROS DE CONTROL (artículo de referencia)")
    for name, p in zip(CELL_NAMES, CELL_PARAMETERS):
        print(f"{name}: Kc={p.kc:.1f}, Ti={p.ti:.1f} s, theta={p.theta} s, Kff={p.kff:.1f}")
    print("\nCOMPARACIÓN DEL IAE")
    print(comparison.to_string(index=False, formatters={
        "IAE (cm·s) PI": "{:,.2f}".format,
        "IAE (cm·s) PI + FF": "{:,.2f}".format,
        "Mejora (%)": "{:+.2f}%".format,
    }))
    print(f"\nArchivos generados en: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
