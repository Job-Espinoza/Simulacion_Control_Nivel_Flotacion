from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from simulacion import CELL_NAMES, CELL_PARAMETERS, calculate_metrics, compare_strategies

st.set_page_config(
    page_title="Simulación de control de nivel – Flotación",
    page_icon="⚙️",
    layout="wide",
)

st.title("Simulación del control de nivel en una batería de flotación")
st.caption("Modelo de tres celdas en serie · Control PI con compensación feedforward · Sintonización SIMC")

with st.sidebar:
    st.header("Parámetros de simulación")
    duration = st.slider("Duración de la simulación (s)", 300, 900, 600, 60)
    setpoint = st.slider("Nivel de referencia (cm)", 25.0, 40.0, 32.0, 0.5)
    disturbance_scale = st.slider("Intensidad de perturbaciones", 0.0, 1.5, 1.0, 0.1)
    tuning_scale = st.slider("Factor de ajuste de Kc", 0.5, 1.5, 1.0, 0.05)
    setpoint_step = st.checkbox("Aplicar cambio de setpoint durante la simulación", value=True)
    st.divider()
    st.caption("El factor de ajuste modifica Kc para explorar la respuesta. El valor 1.00 conserva la sintonización final del artículo.")

simulation_args = dict(
    duration_s=duration,
    dt_s=1.0,
    setpoint_cm=setpoint,
    disturbance_scale=disturbance_scale,
    tuning_scale=tuning_scale,
    setpoint_step=setpoint_step,
)
pi_df, ff_df, comparison = compare_strategies(**simulation_args)

st.markdown(
    """El sistema representa tres celdas de flotación conectadas en serie. El nivel de pulpa es la variable controlada y el caudal de la bomba peristáltica de descarga es la variable manipulada. Se comparan dos configuraciones: **PI (feedback)** y **PI + feedforward**, que incorpora la medición de la perturbación de caudal de entrada."""
)

# Indicadores principales
m1, m2, m3 = st.columns(3)
mean_pi = comparison["IAE (cm·s) PI"].mean()
mean_ff = comparison["IAE (cm·s) PI + FF"].mean()
reduction = ((mean_pi - mean_ff) / mean_pi * 100.0) if mean_pi else 0.0
m1.metric("IAE promedio – PI", f"{mean_pi:,.1f} cm·s")
m2.metric("IAE promedio – PI + FF", f"{mean_ff:,.1f} cm·s")
m3.metric("Variación del IAE promedio", f"{reduction:+.1f}%", help="Un porcentaje positivo indica una reducción del error integral con feedforward.")

st.subheader("1. Respuesta del nivel de pulpa")
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                    subplot_titles=CELL_NAMES)
for i in range(1, 4):
    fig.add_trace(go.Scatter(x=pi_df["Tiempo (s)"], y=pi_df[f"C{i} - Nivel (cm)"],
                             name="PI", legendgroup="PI", showlegend=(i == 1),
                             line=dict(dash="dash")), row=i, col=1)
    fig.add_trace(go.Scatter(x=ff_df["Tiempo (s)"], y=ff_df[f"C{i} - Nivel (cm)"],
                             name="PI + Feedforward", legendgroup="FF", showlegend=(i == 1)), row=i, col=1)
    fig.add_trace(go.Scatter(x=ff_df["Tiempo (s)"], y=ff_df[f"C{i} - Setpoint (cm)"],
                             name="Setpoint", legendgroup="SP", showlegend=(i == 1),
                             line=dict(dash="dot", color="gray")), row=i, col=1)
    fig.update_yaxes(title_text="Nivel (cm)", row=i, col=1)
fig.update_xaxes(title_text="Tiempo (s)", row=3, col=1)
fig.update_layout(height=750, hovermode="x unified", legend=dict(orientation="h", y=1.04, x=0))
st.plotly_chart(fig, use_container_width=True)

st.subheader("2. Comparación del desempeño")
show_comparison = comparison.copy()
for col in ["IAE (cm·s) PI", "IAE (cm·s) PI + FF"]:
    show_comparison[col] = show_comparison[col].map(lambda x: f"{x:,.2f}")
show_comparison["Mejora (%)"] = show_comparison["Mejora (%)"].map(lambda x: f"{x:+.2f}%")
st.dataframe(show_comparison, hide_index=True, use_container_width=True)

bar = go.Figure()
bar.add_bar(name="PI", x=comparison["Celda"], y=comparison["IAE (cm·s) PI"])
bar.add_bar(name="PI + Feedforward", x=comparison["Celda"], y=comparison["IAE (cm·s) PI + FF"])
bar.update_layout(barmode="group", height=370, yaxis_title="IAE (cm·s)", xaxis_title="Celda", legend=dict(orientation="h", y=1.12))
st.plotly_chart(bar, use_container_width=True)

st.subheader("3. Caudal manipulado por las bombas")
flow_fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                         subplot_titles=CELL_NAMES)
for i in range(1, 4):
    flow_fig.add_trace(go.Scatter(x=ff_df["Tiempo (s)"], y=ff_df[f"C{i} - Caudal bomba (L/min)"],
                                  name=f"Bomba {i}", showlegend=False), row=i, col=1)
    flow_fig.update_yaxes(title_text="L/min", row=i, col=1)
flow_fig.update_xaxes(title_text="Tiempo (s)", row=3, col=1)
flow_fig.update_layout(height=650, hovermode="x unified")
st.plotly_chart(flow_fig, use_container_width=True)

st.subheader("4. Parámetros de control utilizados")
parameter_rows = []
for i, p in enumerate(CELL_PARAMETERS, start=1):
    parameter_rows.append({
        "Celda": f"Celda {i}",
        "Kc (L/min·cm⁻¹)": p.kc,
        "Ti (s)": p.ti,
        "Retardo θ (s)": p.theta,
        "Kff": p.kff,
        "k' (cm·s⁻¹·(L/min)⁻¹)": p.kp_rate,
    })
st.dataframe(pd.DataFrame(parameter_rows), hide_index=True, use_container_width=True)

with st.expander("5. Fundamento matemático y supuestos del modelo"):
    st.latex(r"e_i(t)=h_{sp,i}(t)-h_i(t)")
    st.latex(r"u_{PI,i}(t)=K_{c,i}\left[e_i(t)+\frac{1}{T_{i,i}}\int_0^t e_i(\tau)\,d\tau\right]")
    st.latex(r"u_i(t)=u_{PI,i}(t)+K_{ff,i}\,\Delta Q_{in,i}(t)")
    st.latex(r"\frac{dh_i}{dt}=|k_i'|\left[\Delta Q_{in,i}(t)-\Delta Q_{out,i}(t-\theta_i)\right]")
    st.write(
        "La simulación utiliza el balance incremental de caudales, incorpora el retardo de la bomba y limita el caudal manipulado entre 0 y 100 L/min. "
        "La perturbación externa se aplica a la alimentación de la celda 1; la descarga de la celda 1 alimenta la celda 2 y la descarga de la celda 2 alimenta la celda 3. "
        "Para hacer explícita la acción anticipada, ΔQin se representa como la desviación medida del caudal de entrada respecto del valor nominal. "
        "El escalón de alimentación es un escenario didáctico generado en el código; no es una medición experimental del artículo."
    )
    st.warning("El artículo reporta control PI (τd = 0), no un PID con acción derivativa activa. Por eso esta reproducción implementa PI + feedforward.")

with st.expander("6. Referencia y validación respecto del artículo"):
    st.write("Quintanilla, P., Navia, D., Moreno, F., Neethling, S. J., & Brito-Parada, P. R. (2023). A methodology to implement a closed-loop feedback-feedforward level control in a laboratory-scale flotation bank using peristaltic pumps. MethodsX, 10, 102081.")
    st.write("El artículo comunica que el IAE disminuye al añadir feedforward en las tres celdas. La figura de resultados (página 13) muestra aproximadamente 196→164, 325→187 y 260→221 cm·s. Los resultados de esta aplicación son simulados y dependen de los escenarios y supuestos seleccionados aquí.")
    st.markdown("[Abrir artículo original](https://doi.org/10.1016/j.mex.2023.102081)")

# Descarga de los datos que alimentan los gráficos
export_df = pd.DataFrame({"Tiempo (s)": pi_df["Tiempo (s)"]})
for i in range(1, 4):
    export_df[f"Celda {i} - Nivel PI (cm)"] = pi_df[f"C{i} - Nivel (cm)"]
    export_df[f"Celda {i} - Nivel PI+FF (cm)"] = ff_df[f"C{i} - Nivel (cm)"]
    export_df[f"Celda {i} - Setpoint (cm)"] = ff_df[f"C{i} - Setpoint (cm)"]
    export_df[f"Celda {i} - Perturbación (L/min)"] = ff_df[f"C{i} - Perturbación entrada (L/min)"]
    export_df[f"Celda {i} - Caudal bomba PI+FF (L/min)"] = ff_df[f"C{i} - Caudal bomba (L/min)"]

st.download_button(
    "Descargar resultados en CSV",
    data=export_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="resultados_simulacion_flotacion.csv",
    mime="text/csv",
)

st.info("Para obtener un enlace público, sube esta carpeta a un repositorio de GitHub y despliega app.py en Streamlit Community Cloud. La guía README.md incluida explica el procedimiento.")
