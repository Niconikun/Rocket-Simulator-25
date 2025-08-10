# Rocket-Simulator-UdeC

![Versión](https://img.shields.io/badge/versión-3.2.0-blue.svg)

Simulador de cohetes con interfaz gráfica para análisis de trayectorias y rendimiento.

## Historia

Proyecto iniciado por Jorge Orozco en 2022 para la predicción de trayectorias del Cohete Rayo usando cuaterniones. En 2025 se agregó:

- Interfaz gráfica para simplificar su uso
- Capacidad de agregar nuevos cohetes
- Configuración de ubicaciones de lanzamiento
- Análisis detallado de proyectiles

## Características Pendientes

- Módulos más precisos para cálculos de trayectoria:
  - Mejor modelado aerodinámico
  - Condiciones de viento
- Descomposición física del cohete en subsistemas
- Implementación de simulaciones Monte Carlo

## Uso Básico

El simulador se inicia automáticamente con parámetros predefinidos.

## Funcionalidades Principales

- **Dinámica de Vuelo**
  - Simulación 6-DOF completa
  - Integración numérica RK4
  - Cuaterniones para rotación
  - Conservación de masa y energía

- **Aerodinámica**
  - Coeficientes basados en método Barrowman
  - Efectos de compresibilidad
  - Cálculo de centro de presión
  - Estabilidad aerodinámica

- **Motor Cohete**
  - Empuje variable con la altura
  - Compensación de presión ambiente
  - Flujo másico variable
  - Eficiencia de tobera

## Instalación

- Clonar el repositorio:

```bash
git clone https://github.com/username/Rocket-Simulator---GUI.git
```

- Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Uso

- Ejecutar la interfaz gráfica:

```bash
streamlit run streamlit_app.py
```

- Cargar configuración del cohete desde `data/rockets/`

- Configurar parámetros de simulación:
  - Condiciones iniciales
  - Parámetros atmosféricos
  - Configuración del motor

- Ejecutar simulación y visualizar resultados

## Estructura del Proyecto

```bash
Rocket-Simulator---GUI/
├── src/
│   ├── models/
│   │   ├── rocket.py             # Clase principal del cohete
│   │   ├── engine.py             # Modelo del motor
│   │   ├── aerodynamics.py       # Cálculos aerodinámicos
│   │   ├── atmosphere.py         # Modelo atmosférico
│   │   ├── clock.py              # Reloj y gestión de husos horarios
│   │   ├── gravitational.py      # Modelo gravitacional
│   │   ├── markov_models.py      # Modelos de cadenas de markov para simulación monte carlo
│   │   ├── parachute.py          # Modulo de paracaídas (en proceso)
│   │   └── planet.py             # Modelo del planeta
│   ├── utils/
│   │   ├── mattools.py           # Herramientas matemáticas
│   │   └── geotools.py           # Conversiones geográficas
│   └── app.py                    # Interfaz gráfica
├── tests/
│   └── models/                   # Tests unitarios de los modelos
│   └── utils/                    # Tests unitarios de las clases de utilidades
├── data/
│   └── locations/                # Ubicación de datos de locaciones guardadas
│   └── rockets/                  # Ubicación de datos de cohetes guardados
│   └── schemas/                  # Ubicacion de schemas guardados
│   └── simulation                # Ubicación de datos guardados en formato parquet
├── scripts/
│   └── validate_data.py          # Validacion de datos ingresados en rocket settings y location settings
├── pages/
│   ├── 01_simulation.py          # configuración de la simulación
│   ├── 02_rocket_settings.py     # Agregar y configurar nuevos cohetes para simular
│   ├── 03_location_settings.py   # Agregar y configurar nuevas ubicaciones de lanzamiento
│   ├── 04_monte_carlo.py         # Uso de simulaciones de monte carlo (en proceso)
│   └── 05_dashboard.py           # mostrar panel gráfico de análisis de la simulación de trayectoria realizada
├── static/                       # Fuentes, imágenes
├── README.md
├── LICENSE
└── streamlit_app.py
```

## Tests

Ejecutar tests unitarios:

```bash
python -m unittest discover tests
```

## Referencias

- Sutton, G. P., & Biblarz, O. (2016). Rocket propulsion elements
- Barrowman, J. (1967). The practical calculation of the aerodynamic characteristics of slender finned vehicles
- Yang, (2019). Spacecraft Modeling, Attitude Determination, and Control

## Contribuir

1. Fork el repositorio
2. Crear rama para features (`git checkout -b feature/NuevaFeature`)
3. Commit cambios (`git commit -am 'Agregar nueva feature'`)
4. Push a la rama (`git push origin feature/NuevaFeature`)
5. Crear Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo LICENSE para detalles.
