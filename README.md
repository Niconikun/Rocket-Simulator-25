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
python main.py
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
├── main.py                      # Punto de entrada de la aplicación PyQt6
├── build_exe.py                 # Script de construcción con PyInstaller
├── build_exe.spec               # Especificación de PyInstaller
├── src/
│   ├── models/                  # Modelos de simulación física y aeroespacial
│   ├── utils/                   # Utilidades matemáticas, geográficas y de simulación
├── ui/                          # Componentes de la interfaz gráfica PyQt6
│   ├── widgets/                 # Widgets principales de configuración y visualización
├── workers/                     # Hilos y tareas de simulación en segundo plano
├── data/                        # Datos de cohetes, locaciones, simulaciones y configuraciones
├── scripts/                     # Herramientas auxiliares como validación de datos
├── tests/                       # Pruebas unitarias y de integración
├── requirements.txt             # Dependencias de Python
├── environment.yml              # Entorno Conda para desarrollo
├── README.md
└── LICENSE
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
