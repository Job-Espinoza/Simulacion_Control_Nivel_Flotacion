# Simulación del control de nivel en una batería de flotación

Proyecto académico en Python basado en el artículo de Quintanilla et al. (2023), *A methodology to implement a closed-loop feedback-feedforward level control in a laboratory-scale flotation bank using peristaltic pumps*.

## ¿Qué contiene?

- `app.py`: aplicación interactiva en Streamlit. Presenta los tres niveles, setpoints, caudales de bomba, comparación de IAE y descarga de resultados CSV.
- `simulacion.py`: modelo dinámico de las tres celdas y funciones de simulación y evaluación.
- `simulacion_pid_flotacion.py`: versión ejecutable desde consola que genera gráficos PNG y archivos CSV.
- `requirements.txt`: librerías necesarias.

## Modelo y alcance

El documento de referencia describe tres celdas de flotación conectadas en serie y una estrategia **PI con feedforward**. El término derivativo del PID general no se utiliza (`Td = 0`), por lo que el controlador implementado en este proyecto es PI + feedforward.

Parámetros finales tomados de la Tabla 2 del artículo:

| Parámetro | Celda 1 | Celda 2 | Celda 3 |
|---|---:|---:|---:|
| Kc | -62 | -76 | -85 |
| Ti (s) | 56 | 30 | 44 |
| Retardo θ (s) | 7 | 6 | 3 |
| Kff | 0.8 | 0.8 | 1.0 |
| k' | -0.001018 | -0.001018 | -0.001018 |

La simulación usa un balance incremental simplificado:

`dh/dt = |k'| * (ΔQentrada - ΔQsalida_retardada)`

La bomba se limita entre 0 y 100 L/min y se incorpora el retardo individual de cada celda. Las perturbaciones escalonadas del programa son **escenarios sintéticos para fines didácticos**, no datos experimentales del artículo. El término feedforward utiliza la desviación medida del caudal de entrada respecto al punto nominal para representar la compensación anticipada.

Por ello, los resultados de la aplicación son resultados de simulación reproducibles con los supuestos declarados, no una reproducción exacta de la instalación experimental ni una validación industrial.

## 1. Ejecutar en una computadora

Se recomienda Python 3.10 o superior.

### Windows (PowerShell)

```powershell
cd simulacion_flotacion
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Se abrirá la aplicación en el navegador, normalmente en `http://localhost:8501`.

### Ejecutar solo el programa Python

Con el entorno virtual activado:

```powershell
python simulacion_pid_flotacion.py
```

El programa creará la carpeta `resultados/` con:

- `datos_simulacion.csv`
- `comparacion_IAE.csv`
- `respuesta_niveles.png`
- `comparacion_IAE.png`

## 2. Obtener un enlace público para entregar al profesor

El enlace público se obtiene desplegando la aplicación en Streamlit Community Cloud. El proyecto queda preparado para ese despliegue, pero el enlace no se puede crear desde este archivo: se debe publicar desde una cuenta de GitHub y autorizar el despliegue.

1. Crea una cuenta o inicia sesión en GitHub.
2. Crea un repositorio nuevo, por ejemplo `simulacion-control-flotacion`.
3. Sube al repositorio `app.py`, `simulacion.py` y `requirements.txt`. Puedes subir también este README y el script de consola.
4. Entra a [Streamlit Community Cloud](https://share.streamlit.io/) e inicia sesión con GitHub.
5. Selecciona **Create app** y elige tu repositorio, la rama principal y como archivo principal `app.py`.
6. Selecciona **Deploy**. Cuando finalice, Streamlit mostrará una URL pública similar a `https://nombre-del-proyecto.streamlit.app`.
7. Abre el enlace en una ventana privada para comprobar que cualquier persona puede ver la simulación y copia esa URL para entregarla al profesor.

No compartas contraseñas ni tokens en el repositorio. Para este proyecto no se necesitan secretos ni claves API.

## 3. Entregables sugeridos

1. **Enlace público:** URL que proporciona Streamlit Community Cloud después del despliegue.
2. **Código fuente Python:** carpeta del proyecto o repositorio GitHub con `app.py`, `simulacion.py` y `simulacion_pid_flotacion.py`.
3. **Resultados:** CSV y gráficas que genera la aplicación o el script local.

## Referencia bibliográfica

Quintanilla, P., Navia, D., Moreno, F., Neethling, S. J., & Brito-Parada, P. R. (2023). A methodology to implement a closed-loop feedback-feedforward level control in a laboratory-scale flotation bank using peristaltic pumps. *MethodsX, 10*, 102081. https://doi.org/10.1016/j.mex.2023.102081
