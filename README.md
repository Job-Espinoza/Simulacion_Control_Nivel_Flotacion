# Simulación del control de nivel en una batería de flotación

Proyecto académico en Python basado en Quintanilla et al. (2023), *A methodology to implement a closed-loop feedback-feedforward level control in a laboratory-scale flotation bank using peristaltic pumps*.

## Funcionalidades

- `app.py`: interfaz Streamlit con dos modalidades:
  - **Simulación convencional:** compara PI frente a PI + Feedforward, presenta niveles, caudales, IAE y permite descargar resultados CSV.
  - **Tiempo real (datos pseudoaleatorios):** genera aproximadamente una muestra por segundo de caudal de alimentación, mediciones con ruido de sensor, niveles de las tres celdas y caudales de bombas. Permite iniciar, pausar, reiniciar con otra semilla aleatoria y descargar el historial CSV.
- `simulacion.py`: modelo dinámico convencional y funciones de evaluación.
- `simulacion_tiempo_real.py`: generador de señales pseudoaleatorias y simulador incremental en tiempo real.
- `simulacion_pid_flotacion.py`: ejecución local por consola y generación de gráficas/CSV.
- `requirements.txt`: dependencias.

## Importante sobre los datos aleatorios

Los datos de la modalidad en tiempo real son **pseudoaleatorios y sintéticos**. Se generan dentro de la aplicación para representar señales que podrían entregar sensores industriales. No son datos de una planta real y no se transmiten a un PLC, sensor físico, MQTT ni servidor externo. La actualización ocurre aproximadamente cada segundo mientras la aplicación está abierta y la simulación está iniciada.

El caudal de alimentación incluye variación correlacionada y perturbaciones ocasionales. Las mediciones de nivel y caudal incluyen ruido configurable. El modelo conserva el banco de tres celdas conectadas en serie, las ganancias y retardos del artículo y el controlador PI o PI + Feedforward seleccionado.

## Modelo y alcance

El documento de referencia describe tres celdas conectadas en serie y una estrategia **PI con feedforward**. El término derivativo del PID general no se utiliza (`Td = 0`), por lo que el controlador implementado es PI + feedforward.

Parámetros finales de sintonización tomados de la Tabla 2 del artículo:

| Parámetro | Celda 1 | Celda 2 | Celda 3 |
|---|---:|---:|---:|
| Kc | -62 | -76 | -85 |
| Ti (s) | 56 | 30 | 44 |
| Retardo θ (s) | 7 | 6 | 3 |
| Kff | 0.8 | 0.8 | 1.0 |
| k' | -0.001018 | -0.001018 | -0.001018 |

La simulación utiliza un balance incremental simplificado y límites de nivel/caudal. El término feedforward del modelo representa la desviación medida de caudal respecto del valor nominal. Es una representación didáctica; no constituye una reproducción exacta de la instalación experimental ni una validación industrial.

## 1. Ejecutar en Windows

Se recomienda Python 3.10 o superior.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Se abrirá la aplicación en `http://localhost:8501`.

## 2. Publicar o actualizar en GitHub y Streamlit Community Cloud

Para actualizar la aplicación existente:

1. Descomprime el ZIP.
2. En tu repositorio de GitHub, reemplaza los archivos anteriores por los archivos de esta versión.
3. Verifica que `app.py`, `simulacion.py`, `simulacion_tiempo_real.py` y `requirements.txt` estén en la raíz del repositorio.
4. Confirma el commit/push a la rama configurada en Streamlit Community Cloud.
5. Streamlit detectará el cambio y reconstruirá la aplicación. Si no lo hace, abre **Manage app** y reinicia la aplicación.
6. Abre la URL pública, selecciona **Tiempo real (datos pseudoaleatorios)** y presiona **Iniciar**.

No necesitas claves API ni secretos para esta aplicación.

## 3. Entregables sugeridos

1. Enlace público de Streamlit Community Cloud.
2. Código fuente Python (`app.py`, `simulacion.py`, `simulacion_tiempo_real.py` y `simulacion_pid_flotacion.py`).
3. CSV y gráficas de la simulación convencional.
4. CSV descargado de la modalidad en tiempo real, si se desea demostrar la generación de datos.

## Referencia

Quintanilla, P., Navia, D., Moreno, F., Neethling, S. J., & Brito-Parada, P. R. (2023). A methodology to implement a closed-loop feedback-feedforward level control in a laboratory-scale flotation bank using peristaltic pumps. *MethodsX, 10*, 102081. https://doi.org/10.1016/j.mex.2023.102081
