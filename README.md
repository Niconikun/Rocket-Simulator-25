# Rocket Simulator GUI

![version](https://img.shields.io/badge/version-3.5.0-blue.svg)

## Descripción

Simulador de trayectoria de cohetes con interfaz gráfica, visualización 3D y análisis de rendimiento.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso rápido

```bash
streamlit run streamlit_app.py
```

## Estructura del Proyecto

- `Rocket.py`: Lógica principal de simulación.
- `Analysis/dashboard.py`: Dashboard de resultados.
- `Simulation Settings/rocket_settings.py`: Configuración de cohetes.
- `rockets.json`: Base de datos de cohetes.

## Ecuaciones Físicas Utilizadas

- **Fuerza de arrastre**  
  $$
  F_d = \frac{1}{2} \rho v^2 C_d A
  $$
  Donde:
  - $F_d$: Fuerza de arrastre [N]
  - $\rho$: Densidad del aire [kg/m³]
  - $v$: Velocidad relativa [m/s]
  - $C_d$: Coeficiente de arrastre [-]
  - $A$: Área de referencia [m²]

- **Fuerza de sustentación**  
  $$
  F_l = \frac{1}{2} \rho v^2 C_l A
  $$
  Donde $C_l$ es el coeficiente de sustentación.

- **Ecuación de movimiento**  
  $$
  m \frac{d\vec{v}}{dt} = \vec{F}_{\text{total}}
  $$

- **Pérdida de masa por propulsión**  
  $$
  \dot{m} = -\frac{T}{v_e}
  $$
  Donde $T$ es el empuje y $v_e$ la velocidad de escape.

## Contribuir

1. Haz un fork del repositorio.
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Haz commit de tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Haz push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request.

## Licencia

MIT
