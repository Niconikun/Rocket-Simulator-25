import streamlit as st
import pandas as pd
import numpy as np
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl

# Configuración de la página
st.set_page_config(page_title="Rocket Simulator Dashboard", page_icon=":rocket:", layout="wide")
st.title("Rocket Simulator Dashboard")

# Funciones auxiliares
@st.cache_data
def load_simulation_data():
    """Carga y valida los datos de la simulación"""
    try:
        data = pd.read_parquet("data/simulation/sim_data.parquet")
        return data
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def compress_data(data, compression_factor=50):
    """Comprime los datos para visualización"""
    return data.iloc[::compression_factor].copy()

@st.cache_data
def calculate_metrics(data):
    """Calcula métricas principales de la simulación"""
    accel_magnitudes = [np.linalg.norm(np.array(acc)) for acc in data["Acceleration in bodyframe"]]
    max_accel_gs = max(accel_magnitudes) / 9.81  # Convertir a G's
    return {
        "total_time": round(data["Simulation time"].iloc[-1], 2),
        "max_range": round(data["Range"].iloc[-1] / 1000, 2),
        "max_alt": round(data["Up coordinate"].max() / 1000, 3),
        "max_speed": round(data["Velocity norm"].max(), 2),
        "max_mach": round(data["Mach number"].max(), 2),
        "initial_mass": round(data["Mass of the rocket"].iloc[0], 3),
        "final_mass": round(data["Mass of the rocket"].iloc[-1], 3),
        "max_accel_g": round(max_accel_gs, 2)
        
    }

# Cargar y preparar datos
try:
    chart_data = load_simulation_data()
    chart_data_compressed = compress_data(chart_data)
    metrics = calculate_metrics(chart_data)

    st.subheader("Simulation Parameters")
    
    # Crear tres columnas para los parámetros
    param_col1, param_col2, param_col3 = st.columns(3)

    with param_col1:
        st.write("📌 Launch Configuration")
        st.info(f"""
        **Rocket**: {chart_data['Rocket name'].iloc[0]}
        **Location**: {chart_data['Location name'].iloc[0]}
        **Coordinates**: {chart_data['Location Latitude'].iloc[0]:.3f}°S, {chart_data['Location Longitude'].iloc[0]:.3f}°W
        """)

    with param_col2:
        st.write("🎯 Initial Conditions")
        # Crear un DataFrame con los datos iniciales
        initial_data = pd.DataFrame({
            "Parameter": ["Launch Elevation", "Initial Mass", "Initial Velocity"],
            "Value": [
                f"{chart_data['Pitch Angle'].iloc[0]:.1f}°",
                f"{chart_data['Mass of the rocket'].iloc[0]:.2f} kg",
                f"{chart_data['Velocity norm'].iloc[0]:.1f} m/s"
            ]
        })
        st.dataframe(initial_data, hide_index=True)

    with param_col3:
        st.write("🌡️ Environmental Conditions")
        env_data = pd.DataFrame({
            "Parameter": ["Density", "Pressure", "Speed of Sound"],
            "Value": [
                f"{chart_data['Density of the atmosphere'].iloc[0]:.3f} kg/m³",
                f"{chart_data['Ambient pressure'].iloc[0]/1000:.1f} kPa",
                f"{chart_data['Speed of sound'].iloc[0]:.1f} m/s"
            ]
        })
        st.dataframe(env_data, hide_index=True)

    # Línea divisoria
    st.markdown("---")

    # Layout de métricas
    st.subheader("Rocket Performance Metrics")
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)
    col7, col8, col9 = st.columns(3)
    col_landing = st.columns(1)

    # Primera fila de métricas
    col1.metric("Total Flight Time", f"{metrics['total_time']}s", border=True)
    col2.metric("Max Range", f"{metrics['max_range']}km", border=True)
    col3.metric("Max Altitude", f"{metrics['max_alt']}km", border=True)

    # Segunda fila de métricas
    col4.metric("Initial Mass", f"{metrics['initial_mass']}kg", border=True)
    col5.metric("Final Mass", f"{metrics['final_mass']}kg", border=True)
    col6.metric("Mass Delta", f"{round(metrics['initial_mass'] - metrics['final_mass'],3)}kg", border=True)

    # Tercera fila de métricas
    col7.metric("Max Speed", f"{metrics['max_speed']}m/s", border=True)
    col8.metric("Max Mach", f"{metrics['max_mach']}", border=True)
    col9.metric("Max G-Force", f"{metrics['max_accel_g']}G", border=True)

    # Coordenadas de aterrizaje
    col_landing[0].metric("Landing Coordinates", 
                         f"{abs(round(chart_data['Latitude'].iloc[-1], 1))}° S, {abs(round(chart_data['Longitude'].iloc[-1], 1))}° W",
                         border=True)

    # Mapa de trayectoria
    st.subheader("Trajectory Overview")
    trajectory_data = pd.DataFrame({
        'Latitude': chart_data_compressed["Latitude"],
        'Longitude': chart_data_compressed["Longitude"],
        'Altitude': chart_data_compressed["Altitude"]
    })

    map_config = {
        "version": "v1",
        "config": {
            "mapState": {
                "bearing": 0,
                "latitude": float(chart_data["Location Latitude"].iloc[0]),
                "longitude": float(chart_data["Location Longitude"].iloc[0]),
                "pitch": 60,
                "zoom": 9,
            }
        }
    }

    map_1 = KeplerGl(data={"trajectory": trajectory_data})
    map_1.config = map_config
    keplergl_static(map_1, height=800, width=1400, center_map=True)

    # Gráficos de rendimiento
    st.subheader("Performance Charts")
    chart_col1, chart_col2, chart_col3 = st.columns(3)
    chart_col4, chart_col5, chart_col6 = st.columns(3)
    chart_col7, chart_col8, chart_col9 = st.columns(3)

    # Primera fila de gráficos
    with chart_col1:
        st.write('Altitude [m] & Speed [m/s] vs Time [s]')
        st.line_chart(chart_data_compressed, 
                     x="Simulation time", 
                     y=["Up coordinate", "Velocity norm"])

    with chart_col2:
        st.write('Flight Path - Altitude [m] vs Range [m]')
        st.line_chart(chart_data_compressed,
                     x="Range",
                     y="Up coordinate")

    with chart_col3:
        st.write('Aerodynamic Parameters - Mach [-] & AoA [°] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Mach number", "Angle of attack"])

    # Segunda fila de gráficos
    with chart_col4:
        st.write('Forces Analysis [N] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Thrust", "Lift force in bodyframe", "Drag force in bodyframe"])

    with chart_col5:
        st.write('Mass [kg] & Altitude [m] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Mass of the rocket", "Up coordinate"])

    with chart_col6:
        st.write('Attitude Analysis - Euler Angles [°] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Pitch Angle", "Roll Angle", "Yaw Angle"])
    
    # Tercera fila de gráficos
    with chart_col7:
        st.write('Velocity Components [m/s] vs Time [s]')
        st.line_chart(chart_data_compressed,
                    x="Simulation time",
                    y=["v_bx", "v_by", "v_bz"])

    with chart_col8:
        st.write('Atmospheric Conditions vs Altitude [m]')
        # Crear un DataFrame temporal normalizado para mejor visualización
        atm_data = chart_data_compressed.copy()
        atm_data['Normalized Density'] = atm_data['Density of the atmosphere'] / atm_data['Density of the atmosphere'].max()
        atm_data['Normalized Pressure'] = atm_data['Ambient pressure'] / atm_data['Ambient pressure'].max()
        st.line_chart(atm_data,
                    x="Up coordinate",
                    y=["Normalized Density", "Normalized Pressure"])

    with chart_col9:
        st.write('Aerodynamic Coefficients [-] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Drag coefficient", "Lift coefficient"])


    # Análisis de estabilidad
    st.subheader("Stability Analysis")

    # Preparar datos para el gráfico de barras
    stability_data = {
        'Parameter': ['CM X', 'CM Y', 'CM Z',
                     'CP X', 'CP Y', 'CP Z'],
        'Initial [m]': [
            chart_data['Center of mass in bodyframe'].iloc[0][0],
            chart_data['Center of mass in bodyframe'].iloc[0][1],
            chart_data['Center of mass in bodyframe'].iloc[0][2],
            chart_data['Center of pressure in bodyframe'].iloc[0][0],
            chart_data['Center of pressure in bodyframe'].iloc[0][1],
            chart_data['Center of pressure in bodyframe'].iloc[0][2]
        ],
        'Final [m]': [
            chart_data['Center of mass in bodyframe'].iloc[-1][0],
            chart_data['Center of mass in bodyframe'].iloc[-1][1],
            chart_data['Center of mass in bodyframe'].iloc[-1][2],
            chart_data['Center of pressure in bodyframe'].iloc[-1][0],
            chart_data['Center of pressure in bodyframe'].iloc[-1][1],
            chart_data['Center of pressure in bodyframe'].iloc[-1][2]
        ]
    }

    # Crear DataFrame para el gráfico
    stability_df = pd.DataFrame(stability_data)

    # Calcular la distancia total entre CM y CP
    initial_distance = np.linalg.norm(
        np.array(stability_data['Initial [m]'][:3]) - 
        np.array(stability_data['Initial [m]'][3:])
    )
    final_distance = np.linalg.norm(
        np.array(stability_data['Final [m]'][:3]) - 
        np.array(stability_data['Final [m]'][3:])
    )

    # Crear dos columnas
    stab_col1, stab_col2 = st.columns([2, 1])

    with stab_col1:
        # Crear gráfico de barras
        st.bar_chart(
            stability_df,
            x='Parameter',
            y=['Initial [m]', 'Final [m]'],
            height=400,
            stack=False
        )

    with stab_col2:
        st.write("Stability Metrics")
        st.info(f"**Initial CM-CP Distance**: {initial_distance:.3f} m")
        st.info(f"**Final CM-CP Distance**: {final_distance:.3f} m")
        st.info(f"**Distance Change**: {(final_distance - initial_distance):.3f} m")
        st.info("A positive CM-CP distance indicates static stability.Greater distance means more stability.")
        st.info("A negative distance indicates instability, which can lead to loss of control during flight.")

    # Línea divisoria
    st.markdown("---")

    # Análisis de riesgo
    st.subheader("Risk Analysis")
    
    # Calcular el área de seguridad
    max_range = metrics['max_range']  # km
    safety_factor = 1.15  # 15% extra
    safe_range = max_range * safety_factor
    
    # Definir límites de seguridad
    safety_box = {
        'width': 4.5,  # km
        'length': 4.5,  # km
        'height': 1.8   # km
    }

    # Verificar si la trayectoria está dentro de los límites
    trajectory_in_bounds = (
        chart_data['Range'].max() / 1000 <= safety_box['length'] and  # Convertir m a km
        abs(chart_data['East coordinate']).max() / 1000 <= safety_box['width'] / 2 and
        abs(chart_data['North coordinate']).max() / 1000 <= safety_box['width'] / 2 and
        chart_data['Up coordinate'].max() / 1000 <= safety_box['height']
    )

    # Crear área de seguridad para el mapa
    center_lat = chart_data['Location Latitude'].iloc[0]
    center_lon = chart_data['Location Longitude'].iloc[0]
    
    # Crear polígono de área segura
    from math import cos, pi
    
    def create_safety_box(center_lat, center_lon, width_km, length_km):
        """Crea un polígono rectangular para el área segura"""
        lat_delta = (width_km / 2) / 111.32  # 1 grado ≈ 111.32 km
        lon_delta = (length_km / 2) / (111.32 * cos(center_lat * pi / 180))
        
        return [
            [center_lon - lon_delta, center_lat - lat_delta],
            [center_lon + lon_delta, center_lat - lat_delta],
            [center_lon + lon_delta, center_lat + lat_delta],
            [center_lon - lon_delta, center_lat + lat_delta],
            [center_lon - lon_delta, center_lat - lat_delta]
        ]

    # Crear GeoJSON con área de seguridad
    safety_area = create_safety_box(center_lat, center_lon, 
                                  safety_box['width'], 
                                  safety_box['length'])

    geojson_dict = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": list(zip(chart_data_compressed['Longitude'], 
                                         chart_data_compressed['Latitude']))
                },
                "properties": {
                    "name": "Flight Path",
                    "color": [255, 0, 0]
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [safety_area]
                },
                "properties": {
                    "name": "Safety Area",
                    "color": [0, 255, 0, 80]
                }
            }
        ]
    }

    # Mostrar resultados del análisis
    risk_col1, risk_col2 = st.columns([2, 1])

    with risk_col2:
        st.write("Safety Analysis")
        st.info(f"""
        **Safety Box Dimensions**:
        - Width: {safety_box['width']} km
        - Length: {safety_box['length']} km
        - Height: {safety_box['height']} km
        
        **Flight Analysis**:
        - Max Range: {max_range:.2f} km
        - Range + Safety Factor: {safe_range:.2f} km
        - Max Height: {metrics['max_alt']:.2f} km
        
        **Safety Status**: {'✅ Within Limits' if trajectory_in_bounds else '❌ Exceeds Limits'}
        """)

    with risk_col1:
        risk_map = KeplerGl(height=600, data={"risk_layer": geojson_dict})
        risk_map.config = {
            "version": "v1",
            "config": {
                "mapState": {
                    "bearing": 0,
                    "latitude": center_lat,
                    "longitude": center_lon,
                    "pitch": 45,
                    "zoom": 12,
                },
                "visState": {
                    "layers": [
                        {
                            "type": "geojson",
                            "config": {
                                "dataId": "risk_layer",
                                "visible": True,
                                "opacity": 0.8
                            }
                        }
                    ]
                }
            }
        }
        keplergl_static(risk_map, height=600, width=1000, center_map=True)

except KeyError as e:
    st.error(f"Error: Columna no encontrada - {e}")
    st.write("Columnas disponibles:", list(chart_data.columns))
except Exception as e:
    st.error(f"Error inesperado: {e}")