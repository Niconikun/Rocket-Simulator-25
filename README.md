# Rocket-Simulator-GUI

Simulador de cohetes con interfaz gráfica para análisis de trayectorias y rendimiento.

## Descripción

Este proyecto implementa un simulador de cohetes completo con las siguientes características:

- Modelado físico completo (6 grados de libertad)
- Cálculo de fuerzas aerodinámicas
- Simulación del motor cohete
- Interfaz gráfica para visualización de resultados
- Almacenamiento y análisis de datos de vuelo

## Características Principales

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

1. Clonar el repositorio:

```bash
git clone https://github.com/username/Rocket-Simulator---GUI.git
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Uso

1. Ejecutar la interfaz gráfica:

```bash
streamlit run streamlit_app.py
```

2. Cargar configuración del cohete desde `data/rockets.json`

3. Configurar parámetros de simulación:
   - Condiciones iniciales
   - Parámetros atmosféricos
   - Configuración del motor

4. Ejecutar simulación y visualizar resultados

## Estructura del Proyecto

```
Rocket-Simulator---GUI/
├── src/
│   ├── models/
│   │   ├── rocket.py       # Clase principal del cohete
│   │   ├── engine.py       # Modelo del motor
│   │   ├── aerodynamics.py # Cálculos aerodinámicos
│   │   └── atmosphere.py   # Modelo atmosférico
│   ├── utils/
│   │   ├── mattools.py     # Herramientas matemáticas
│   │   └── geotools.py     # Conversiones geográficas
│   └── app.py             # Interfaz gráfica
├── tests/
│   └── models/            # Tests unitarios
├── data/
│   └── rockets.json      # Configuraciones de cohetes
└── README.md
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
