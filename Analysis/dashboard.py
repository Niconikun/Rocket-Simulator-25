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
        data = pd.read_parquet("sim_data.parquet")
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
    return {
        "total_time": round(data["Simulation time"].iloc[-1], 2),
        "max_range": round(data["Range"].iloc[-1] / 1000, 2),
        "max_alt": round(data["Up coordinate"].max() / 1000, 3),
        "max_speed": round(data["Velocity norm"].max(), 2),
        "max_mach": round(data["Mach number"].max(), 2),
        "initial_mass": round(data["Mass of the rocket"].iloc[0], 3),
        "final_mass": round(data["Mass of the rocket"].iloc[-1], 3)
    }

# Cargar y preparar datos
try:
    chart_data = load_simulation_data()
    chart_data_compressed = compress_data(chart_data)
    metrics = calculate_metrics(chart_data)

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
    col6.metric("Mass Delta", f"{metrics['initial_mass'] - metrics['final_mass']}kg", border=True)

    # Tercera fila de métricas
    col7.metric("Max Speed", f"{metrics['max_speed']}m/s", border=True)
    col8.metric("Max Mach", f"{metrics['max_mach']}", border=True)
    col9.metric("Max G-Force", "N/A", border=True)

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

    map_1 = KeplerGl(height=600, data={"trajectory": trajectory_data})
    map_1.config = map_config
    keplergl_static(map_1, height=600, width=1000, center_map=True)

    # Gráficos de rendimiento
    st.subheader("Performance Charts")
    chart_col1, chart_col2, chart_col3 = st.columns(3)
    chart_col4, chart_col5, chart_col6 = st.columns(3)

    with chart_col1:
        st.write('Velocities vs Time')
        st.line_chart(chart_data_compressed, 
                     x="Simulation time", 
                     y=["v_bx", "v_by", "v_bz"])

    with chart_col2:
        st.write('Altitude vs Range')
        st.line_chart(chart_data_compressed,
                     x="Range",
                     y="Up coordinate")

    with chart_col3:
        st.write('Lift vs Time')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y="Lift force in bodyframe")
        
    with chart_col4:
        st.write('Pitch, Altitude vs Time')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Pitch Angle", "Up coordinate"])

    with chart_col5:
        st.write('Pitch vs Time')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y= "Pitch Angle")

    with chart_col6:
        st.write('Angle of attack vs Time')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y= "Angle of attack")

except KeyError as e:
    st.error(f"Error: Columna no encontrada - {e}")
    st.write("Columnas disponibles:", list(chart_data.columns))
except Exception as e:
    st.error(f"Error inesperado: {e}")

st.subheader("Risk Analysis")

geojson_dict = {
       "type": "FeatureCollection",
       "features": [{
           "type": "Feature",
           "geometry": {
               "type": "Point",
               "coordinates": [102.0, 0.5]
           },
           "properties": {
               "prop0": "value0"
           }
       }, {
           "type": "Feature",
           "geometry": {
               "type": "LineString",
               "coordinates": [
                   [102.0, 0.0],
                   [103.0, 1.0],
               ]
           },
           "properties": {
               "prop0": "value0",
               "prop1": 0.0
           }
       }, {
           "type": "Feature",
           "geometry": {
               "type": "Polygon",
               "coordinates": [
                   [
                       [100.0, 0.0],
                       [101.0, 0.0],
                       [101.0, 1.0],
                       [100.0, 1.0],
                       [100.0, 0.0]
                   ]
               ]
           },
           "properties": {
               "prop0": "value0",
               "prop1": {
                   "this": "that"
               }
           }
       }]
   }

risk_map = KeplerGl(height=600, data={"risk_layer": geojson_dict})
risk_map.config = {
    "version": "v1",
    "config": {
        "mapState": {
            "bearing": 0,
            "latitude": chart_data.iloc[0]["Location Latitude"],
            "longitude": chart_data.iloc[0]["Location Longitude"],
            "pitch": 60,
            "zoom": 2,
        }
    },
}
keplergl_static(risk_map, height=600, width=1000, center_map=True)