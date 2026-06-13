# Rocket Simulator Pro

![Versión](https://img.shields.io/badge/versión-0.5.5-blue.svg)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.10-green.svg)
![Licencia](https://img.shields.io/badge/licencia-MIT-lightgrey.svg)

Simulador de cohetes 6-DOF con interfaz gráfica PyQt6 para análisis de trayectorias, rendimiento y dispersión estadística.

## Historia

Proyecto iniciado por Jorge Orozco (Universidad de Concepción, 2022) para la predicción de trayectorias del Cohete Rayo usando cuaterniones. Expandido en 2025–2026 con:

- Interfaz gráfica completa (PyQt6) con editor de cohetes por pestañas
- Simulaciones Monte Carlo con muestreo estadístico de parámetros
- Importación desde OpenRocket (`.ork`) y mallas STL
- Análisis de margen de estabilidad mediante el método de Barrowman

## Funcionalidades Principales

### Dinámica de Vuelo
- Simulación **6-DOF** completa (traslación + rotación)
- Integración numérica **RK4**
- Cuaterniones para representación de rotación
- Conservación de masa y energía; flujo másico variable

### Aerodinámica
- Coeficientes de arrastre por componentes (fricción, presión, base, onda)
- Cálculo de centro de presión (método **Barrowman**)
- Correcciones de compresibilidad (Prandtl-Glauert, Karman-Tsien)
- Análisis de margen de estabilidad estática en calibres

### Motor
- Curvas de empuje desde CSV
- Compensación de presión ambiente en tobera
- Parámetros: Isp, flujo másico, velocidad de gases, presión de salida

### Simulaciones Monte Carlo
- Muestreo de parámetros con distribuciones `normal`, `truncated_normal` y `uniform`
- Ejecución en `QThread` con señales de progreso
- Estadísticas: media, desviación, percentiles (P5/P50/P95), máximo
- CEP (Circular Error Probable) y elipse de dispersión
- Visualizaciones: histograma de apogeo, scatter de impacto, boxplot

### Editor de Cohetes
- Pestañas: Propiedades, Inercia & CoM, Motor, Geometría, Nariz, Aletas, Curvas de Empuje
- Importar desde **OpenRocket** (`.ork`) sin dependencias adicionales
- Importar propiedades físicas desde **STL** (`pip install trimesh`)
- Botón **"⚖️ Check Stability"**: margen de Barrowman antes y después del burn
- Validación de configuración con errores y advertencias

## Instalación

```bash
git clone https://github.com/Niconikun/Rocket-Simulator-25.git
cd Rocket-Simulator-25
pip install -r requirements.txt
```

> Para importación STL (opcional):
> ```bash
> pip install trimesh
> ```

## Uso

```bash
python main.py
```

1. Seleccionar o importar un cohete desde la pestaña **Rocket Settings**
2. Configurar el sitio de lanzamiento en **Launch Settings**
3. Ejecutar la simulación desde **Simulation**
4. Analizar resultados en **Results** o ejecutar Monte Carlo en **Monte Carlo**

## Estructura del Proyecto

```
Rocket-Simulator---GUI/
├── main.py                          # Punto de entrada PyQt6
├── version.py                       # Versión semántica
├── src/
│   ├── models/                      # Modelos físicos (aerodinámica, atmósfera, motor, paracaídas...)
│   └── utils/
│       ├── monte_carlo_sampler.py   # Distribuciones y muestreo MC
│       ├── monte_carlo_aggregator.py# Estadísticas y figuras post-MC
│       ├── ork_importer.py          # Importador OpenRocket .ork
│       ├── stl_importer.py          # Importador STL con trimesh
│       ├── stability_calculator.py  # Método de Barrowman (CP + margen)
│       └── simulation_manager.py   # Gestión de resultados
├── ui/
│   └── widgets/
│       ├── rocket_settings_widget.py# Editor completo de cohetes
│       └── monte_carlo_widget.py    # UI de simulaciones Monte Carlo
├── workers/
│   ├── simulation_worker.py         # Worker 6-DOF (RK4) con run_with_params()
│   └── monte_carlo_runner.py        # Orquestador de N corridas MC en QThread
├── data/
│   ├── rockets/configs/             # Configuraciones JSON de cohetes
│   ├── schemas/                     # Esquemas de validación JSON
│   ├── thrust_curves/               # Curvas de empuje CSV
│   └── simulations/                 # Resultados guardados
├── tests/                           # Pruebas unitarias e integración
├── requirements.txt
├── environment.yml
└── LICENSE
```

## Validar Configuraciones de Cohetes

```bash
python validate_rockets.py
```

## Tests

```bash
python -m pytest tests/ -v
# o con unittest:
python -m unittest discover tests
```

## Referencias

- Sutton, G. P., & Biblarz, O. (2016). *Rocket Propulsion Elements*
- Barrowman, J. S. (1967). *The Practical Calculation of the Aerodynamic Characteristics of Slender Finned Vehicles*. Catholic University of America
- Yang, (2019). *Spacecraft Modeling, Attitude Determination, and Control*

## Contribuir

1. Fork el repositorio
2. Crear rama para features (`git checkout -b feature/NuevaFeature`)
3. Commit cambios (`git commit -am 'Agregar nueva feature'`)
4. Push a la rama (`git push origin feature/NuevaFeature`)
5. Crear Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT — ver el archivo [LICENSE](LICENSE) para detalles.
