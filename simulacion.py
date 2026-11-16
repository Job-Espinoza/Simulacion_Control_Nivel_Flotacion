"""Modelo dinámico y control PI + feedforward para un banco de flotación de 3 celdas.

La implementación es una simulación didáctica basada en los parámetros publicados por
Quintanilla et al. (2023). No sustituye la identificación ni la validación experimental.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CellParameters:
    """Parámetros finales de sintonización reportados en el artículo."""
    kc: float       # L/min por cm (ganancia negativa por la acción de extracción)
    ti: float       # s
    theta: int      # s, retardo del proceso
    kff: float      # constante feedforward
    kp_rate: float  # cm/s por (L/min), pendiente de integración


CELL_PARAMETERS: Tuple[CellParameters, ...] = (
    CellParameters(kc=-62.0, ti=56.0, theta=7, kff=0.8, kp_rate=-0.001018),
    CellParameters(kc=-76.0, ti=30.0, theta=6, kff=0.8, kp_rate=-0.001018),
    CellParameters(kc=-85.0, ti=44.0, theta=3, kff=1.0, kp_rate=-0.001018),
)

CELL_NAMES = ("Celda 1", "Celda 2", "Celda 3")


def disturbance_profile(time_s: np.ndarray, magnitude: float = 1.0) -> np.ndarray:
    """Perturbación externa sintética del caudal de alimentación a la celda 1.

    Las perturbaciones que reciben las celdas 2 y 3 se calculan durante la simulación
    a partir de las descargas de las celdas anteriores, para representar el arreglo en serie.
    El escalón de alimentación es un escenario didáctico, no un dato experimental.
    """
    disturbance = np.zeros(len(time_s), dtype=float)
    disturbance[(time_s >= 160) & (time_s < 320)] = 8.0 * magnitude
    return disturbance


def simulate(
    strategy: str = "PI + Feedforward",
    duration_s: int = 600,
    dt_s: float = 1.0,
    setpoint_cm: float = 32.0,
    disturbance_scale: float = 1.0,
    tuning_scale: float = 1.0,
    setpoint_step: bool = True,
) -> pd.DataFrame:
    """Simula las tres celdas mediante balance de caudal y PI discreto con retardo.

    strategy: "PI" o "PI + Feedforward".
    El término feedforward compensa la desviación medida del caudal de entrada.
    El retardo theta se aplica a la acción de la bomba.
    """
    if strategy not in {"PI", "PI + Feedforward"}:
        raise ValueError("strategy debe ser 'PI' o 'PI + Feedforward'.")
    if duration_s < 60 or dt_s <= 0:
        raise ValueError("La duración debe ser >= 60 s y dt_s debe ser positivo.")

    n = int(round(duration_s / dt_s)) + 1
    time_s = np.linspace(0.0, duration_s, n)
    dt = float(time_s[1] - time_s[0]) if n > 1 else dt_s
    external_feed_disturbance = disturbance_profile(time_s, disturbance_scale)
    disturbances = np.zeros((n, 3), dtype=float)

    # Nivel inicial y referencia coinciden para aislar la respuesta a perturbaciones.
    levels = np.full((n, 3), float(setpoint_cm), dtype=float)
    setpoints = np.full((n, 3), float(setpoint_cm), dtype=float)
    if setpoint_step:
        step_time = min(420.0, duration_s * 0.70)
        setpoints[time_s >= step_time, :] += 0.8

    # Las bombas operan alrededor de un caudal nominal de 45 L/min.
    nominal_flow = 45.0
    min_flow, max_flow = 0.0, 100.0
    integral = np.zeros(3, dtype=float)
    pump_deviation = np.zeros((n, 3), dtype=float)
    pump_flow = np.full((n, 3), nominal_flow, dtype=float)
    feedback_output = np.zeros((n, 3), dtype=float)
    feedforward_output = np.zeros((n, 3), dtype=float)

    for k in range(n - 1):
        for i, p in enumerate(CELL_PARAMETERS):
            # En el banco en serie, la descarga de una celda alimenta la siguiente.
            # C1 recibe la perturbación externa; C2 y C3 reciben el caudal manipulado
            # de la celda inmediatamente anterior.
            disturbances[k, i] = (
                external_feed_disturbance[k] if i == 0 else pump_deviation[k, i - 1]
            )
            error = setpoints[k, i] - levels[k, i]
            kc = p.kc * tuning_scale

            # PI en forma ideal: u_PI = Kc * (e + integral(e)/Ti).
            # La acción derivativa es cero, tal como en el artículo.
            candidate_integral = integral[i] + error * dt
            u_pi_candidate = kc * (error + candidate_integral / p.ti)

            # Anti-windup condicional simple al alcanzar límites físicos de la bomba.
            d_input = disturbances[k, i]
            u_ff = p.kff * d_input if strategy == "PI + Feedforward" else 0.0
            raw_candidate = u_pi_candidate + u_ff
            candidate_flow = nominal_flow + raw_candidate
            saturated_high = candidate_flow > max_flow
            saturated_low = candidate_flow < min_flow
            pushes_further = (saturated_high and error < 0) or (saturated_low and error > 0)
            if not pushes_further:
                integral[i] = candidate_integral

            u_pi = kc * (error + integral[i] / p.ti)
            u_ff = p.kff * d_input if strategy == "PI + Feedforward" else 0.0
            raw_output = u_pi + u_ff
            actual_flow = float(np.clip(nominal_flow + raw_output, min_flow, max_flow))
            actual_deviation = actual_flow - nominal_flow

            feedback_output[k, i] = u_pi
            feedforward_output[k, i] = u_ff
            pump_flow[k, i] = actual_flow
            pump_deviation[k, i] = actual_deviation

            # Retardo de la bomba: u(t-theta). Para dt=1 s, theta es número de muestras.
            delay_samples = max(0, int(round(p.theta / dt)))
            delayed_index = k - delay_samples
            delayed_pump_deviation = (
                pump_deviation[delayed_index, i] if delayed_index >= 0 else 0.0
            )

            # Balance incremental: dh/dt = g * (ΔQentrada - ΔQsalida).
            # g = |k'|; la extracción por bomba disminuye el nivel.
            gain = abs(p.kp_rate)
            dh_dt = gain * (disturbances[k, i] - delayed_pump_deviation)
            levels[k + 1, i] = levels[k, i] + dh_dt * dt

            # Límite geométrico aproximado de las celdas (altura útil 0–45 cm).
            levels[k + 1, i] = np.clip(levels[k + 1, i], 0.0, 45.0)

    # Completa último punto para facilitar exportación y gráficas.
    disturbances[-1, 0] = external_feed_disturbance[-1]
    for i in range(1, 3):
        disturbances[-1, i] = pump_deviation[-2, i - 1]
    pump_flow[-1, :] = pump_flow[-2, :]
    pump_deviation[-1, :] = pump_deviation[-2, :]
    feedback_output[-1, :] = feedback_output[-2, :]
    feedforward_output[-1, :] = feedforward_output[-2, :]

    data: Dict[str, np.ndarray] = {"Tiempo (s)": time_s}
    for i, name in enumerate(CELL_NAMES):
        short = f"C{i + 1}"
        data[f"{short} - Nivel (cm)"] = levels[:, i]
        data[f"{short} - Setpoint (cm)"] = setpoints[:, i]
        data[f"{short} - Perturbación entrada (L/min)"] = disturbances[:, i]
        data[f"{short} - Caudal bomba (L/min)"] = pump_flow[:, i]
        data[f"{short} - Salida PI (L/min)"] = feedback_output[:, i]
        data[f"{short} - Feedforward (L/min)"] = feedforward_output[:, i]
    return pd.DataFrame(data)


def calculate_metrics(df: pd.DataFrame, dt_s: float | None = None) -> pd.DataFrame:
    """Calcula IAE de cada celda (cm·s) y error absoluto medio (cm)."""
    if dt_s is None:
        time_values = df["Tiempo (s)"].to_numpy()
        dt_s = float(np.mean(np.diff(time_values))) if len(time_values) > 1 else 1.0
    rows = []
    for i, name in enumerate(CELL_NAMES, start=1):
        level = df[f"C{i} - Nivel (cm)"].to_numpy()
        sp = df[f"C{i} - Setpoint (cm)"].to_numpy()
        abs_error = np.abs(sp - level)
        rows.append({
            "Celda": name,
            "IAE (cm·s)": float(np.sum(abs_error) * dt_s),
            "Error absoluto medio (cm)": float(np.mean(abs_error)),
            "Desviación máxima (cm)": float(np.max(abs_error)),
        })
    return pd.DataFrame(rows)


def compare_strategies(**kwargs) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Devuelve resultados PI, PI+FF y tabla comparativa de IAE."""
    pi = simulate(strategy="PI", **kwargs)
    ff = simulate(strategy="PI + Feedforward", **kwargs)
    metrics_pi = calculate_metrics(pi)
    metrics_ff = calculate_metrics(ff)
    comparison = metrics_pi[["Celda", "IAE (cm·s)"]].merge(
        metrics_ff[["Celda", "IAE (cm·s)"]], on="Celda", suffixes=(" PI", " PI + FF")
    )
    comparison["Mejora (%)"] = np.where(
        comparison["IAE (cm·s) PI"] > 0,
        (comparison["IAE (cm·s) PI"] - comparison["IAE (cm·s) PI + FF"])
        / comparison["IAE (cm·s) PI"] * 100.0,
        0.0,
    )
    return pi, ff, comparison
