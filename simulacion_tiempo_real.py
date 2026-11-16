"""Generador pseudoaleatorio y simulador incremental en tiempo real.

Los datos son sintéticos: representan señales de caudal y nivel como si provinieran
 de instrumentación industrial, pero no proceden de sensores ni de un PLC real.
"""
from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np
import pandas as pd

from simulacion import CELL_NAMES, CELL_PARAMETERS


class LiveFlotationSimulator:
    """Simula un banco de tres celdas, avanzando un segundo por llamada a step()."""

    def __init__(
        self,
        seed: int,
        setpoint_cm: float = 32.0,
        nominal_flow_lpm: float = 45.0,
        feed_noise_std_lpm: float = 1.2,
        sensor_noise_std_cm: float = 0.12,
        flow_sensor_noise_std_lpm: float = 0.25,
        history_limit: int = 600,
    ) -> None:
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.setpoint_cm = float(setpoint_cm)
        self.nominal_flow = float(nominal_flow_lpm)
        self.feed_noise_std = float(feed_noise_std_lpm)
        self.sensor_noise_std = float(sensor_noise_std_cm)
        self.flow_sensor_noise_std = float(flow_sensor_noise_std_lpm)
        self.history_limit = int(history_limit)

        self.time_s = 0
        self.levels = np.full(3, self.setpoint_cm, dtype=float)
        self.integrals = np.zeros(3, dtype=float)
        self.pump_flows = np.full(3, self.nominal_flow, dtype=float)
        self.pump_deviations = np.zeros(3, dtype=float)
        self.delay_queues = [
            deque([0.0] * max(1, int(p.theta)), maxlen=max(1, int(p.theta)))
            for p in CELL_PARAMETERS
        ]
        self.feed_deviation = 0.0
        self.iae = np.zeros(3, dtype=float)
        self.records: list[dict[str, Any]] = []

    def set_conditions(
        self,
        setpoint_cm: float,
        feed_noise_std_lpm: float,
        sensor_noise_std_cm: float,
    ) -> None:
        """Actualiza consignas y amplitudes de ruido sin reiniciar la simulación."""
        self.setpoint_cm = float(setpoint_cm)
        self.feed_noise_std = float(feed_noise_std_lpm)
        self.sensor_noise_std = float(sensor_noise_std_cm)

    def step(self, strategy: str = "PI + Feedforward") -> dict[str, Any]:
        """Genera una muestra nueva y avanza un segundo el modelo dinámico."""
        if strategy not in {"PI", "PI + Feedforward"}:
            raise ValueError("strategy debe ser 'PI' o 'PI + Feedforward'.")

        dt = 1.0
        # Ruido de caudal correlacionado: evita saltos completamente independientes.
        innovation = self.rng.normal(0.0, self.feed_noise_std * np.sqrt(1.0 - 0.78**2))
        self.feed_deviation = 0.78 * self.feed_deviation + innovation

        # Perturbaciones ocasionales, como cambios de alimentación del proceso.
        spike = 0.0
        if self.rng.random() < 0.018:
            spike = float(self.rng.choice([-1.0, 1.0]) * self.rng.uniform(2.0, 4.5))
        feed_actual = float(np.clip(self.nominal_flow + self.feed_deviation + spike, 32.0, 58.0))
        feed_deviation_actual = feed_actual - self.nominal_flow
        feed_measured = feed_actual + self.rng.normal(0.0, self.flow_sensor_noise_std)

        inlet_deviations = np.zeros(3, dtype=float)
        inlet_flows = np.zeros(3, dtype=float)
        inlet_measured = np.zeros(3, dtype=float)
        sensor_levels = self.levels + self.rng.normal(0.0, self.sensor_noise_std, size=3)
        ff_outputs = np.zeros(3, dtype=float)
        delayed_outputs = np.zeros(3, dtype=float)

        for i, p in enumerate(CELL_PARAMETERS):
            # La descarga de cada celda alimenta a la siguiente.
            inlet_deviation = (
                feed_deviation_actual if i == 0 else self.pump_deviations[i - 1]
            )
            inlet_deviations[i] = inlet_deviation
            inlet_flows[i] = self.nominal_flow + inlet_deviation
            measured_inlet = inlet_flows[i] + self.rng.normal(
                0.0, self.flow_sensor_noise_std
            )
            inlet_measured[i] = measured_inlet
            measured_deviation = measured_inlet - self.nominal_flow

            error = self.setpoint_cm - sensor_levels[i]
            candidate_integral = self.integrals[i] + error * dt
            u_pi_candidate = p.kc * (error + candidate_integral / p.ti)
            u_ff_candidate = p.kff * measured_deviation if strategy == "PI + Feedforward" else 0.0
            candidate_flow = self.nominal_flow + u_pi_candidate + u_ff_candidate
            saturated_high = candidate_flow > 100.0
            saturated_low = candidate_flow < 0.0
            pushes_further = (saturated_high and error < 0.0) or (saturated_low and error > 0.0)
            if not pushes_further:
                self.integrals[i] = candidate_integral

            u_pi = p.kc * (error + self.integrals[i] / p.ti)
            u_ff = p.kff * measured_deviation if strategy == "PI + Feedforward" else 0.0
            pump_flow = float(np.clip(self.nominal_flow + u_pi + u_ff, 0.0, 100.0))
            pump_deviation = pump_flow - self.nominal_flow
            self.pump_flows[i] = pump_flow
            self.pump_deviations[i] = pump_deviation
            ff_outputs[i] = u_ff

            # Aplicación del retardo de transporte/accionamiento de cada celda.
            delayed_deviation = self.delay_queues[i][0]
            self.delay_queues[i].append(pump_deviation)
            delayed_outputs[i] = delayed_deviation

            # Balance incremental simplificado del artículo.
            dh_dt = abs(p.kp_rate) * (inlet_deviation - delayed_deviation)
            self.levels[i] = float(np.clip(self.levels[i] + dh_dt * dt, 0.0, 45.0))

        # El IAE en línea se calcula con el nivel de proceso (sin ruido de sensor).
        self.iae += np.abs(self.setpoint_cm - self.levels) * dt

        record: dict[str, Any] = {
            "Tiempo (s)": self.time_s,
            "Caudal alimentación real (L/min)": feed_actual,
            "Caudal alimentación medido (L/min)": float(feed_measured),
            "Estrategia": strategy,
        }
        for i, name in enumerate(CELL_NAMES, start=1):
            record[f"{name} - Nivel real (cm)"] = float(self.levels[i - 1])
            record[f"{name} - Nivel sensor (cm)"] = float(sensor_levels[i - 1])
            record[f"{name} - Setpoint (cm)"] = self.setpoint_cm
            record[f"{name} - Caudal entrada real (L/min)"] = float(inlet_flows[i - 1])
            record[f"{name} - Caudal entrada medido (L/min)"] = float(inlet_measured[i - 1])
            record[f"{name} - Caudal bomba (L/min)"] = float(self.pump_flows[i - 1])
            record[f"{name} - Feedforward (L/min)"] = float(ff_outputs[i - 1])
            record[f"{name} - IAE acumulado (cm·s)"] = float(self.iae[i - 1])
            record[f"{name} - Retardo aplicado (L/min)"] = float(delayed_outputs[i - 1])

        self.records.append(record)
        if len(self.records) > self.history_limit:
            self.records = self.records[-self.history_limit :]
        self.time_s += 1
        return record

    def dataframe(self) -> pd.DataFrame:
        """Devuelve el historial visible en la interfaz."""
        return pd.DataFrame(self.records)
