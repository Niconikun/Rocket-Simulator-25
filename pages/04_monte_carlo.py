import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go  # type: ignore
import plotly.express as px  # type: ignore
from plotly.subplots import make_subplots  # type: ignore
from src.models.markov_models import (
    AtmosphericMarkovModel, 
    FailureMarkovModel,
    ParachuteMarkovModel
)
from src.models.monte_carlo import MonteCarloSimulation
from src.models.wind_rose import WindRose, Season, AltitudeWindProfile, WindRoseIntegrator
from src.models.rocket import Rocket
import json
from datetime import datetime

st.title("Análisis de Monte Carlo con Rosa de Vientos")

st.markdown("""
### Simulación Mejorada con Modelo de Viento Realista

Esta simulación utiliza un modelo de rosa de vientos que incluye:
- **Patrones direccionales**: 16 sectores de viento con probabilidades estacionales
- **Variación con altitud**: Perfiles de viento que cambian con la altura
- **Efectos estacionales**: Diferentes patrones para primavera, verano, otoño e invierno
- **Turbulencia realista**: Modelos de ráfagas y turbulencia
- **Análisis estadístico**: Zonas de aterrizaje y confiabilidad mejorados
""")

# Configuración de la simulación en la barra lateral
st.sidebar.header("Configuración de Simulación")

# Parámetros básicos
n_sims = st.sidebar.slider("Número de simulaciones", 50, 500, 200)
max_altitude = st.sidebar.number_input("Altitud máxima (m)", 500, 5000, 2000)

# Configuración de viento
st.sidebar.subheader("Configuración de Viento")
location_name = st.sidebar.text_input("Nombre de ubicación", "Concepción")

# Selección de estación
season_options = {
    "Primavera": Season.SPRING,
    "Verano": Season.SUMMER,
    "Otoño": Season.AUTUMN,
    "Invierno": Season.WINTER,
    "Automático (actual)": None
}
season_selection = st.sidebar.selectbox("Estación del año", list(season_options.keys()))
selected_season = season_options[season_selection]

# Mostrar información de la rosa de vientos
st.sidebar.subheader("Información de Rosa de Vientos")
temp_wind_rose = WindRose(location_name)

if selected_season:
    display_season = selected_season
else:
    # Determinar estación actual
    month = datetime.now().month
    if month in [3, 4, 5]:
        display_season = Season.SPRING
    elif month in [6, 7, 8]:
        display_season = Season.SUMMER
    elif month in [9, 10, 11]:
        display_season = Season.AUTUMN
    else:
        display_season = Season.WINTER

wind_stats = temp_wind_rose.get_seasonal_statistics(display_season)
st.sidebar.info(f"""
**Estación:** {display_season.value.title()}
**Dirección dominante:** {wind_stats['dominant_direction']}
**Probabilidad de calma:** {wind_stats['calm_probability']:.1%}
""")

# Crear cohete dummy para la simulación
# En una implementación real, esto se cargaría de la configuración del usuario
dummy_rocket_state = {
    'r_enu': np.array([0.0, 0.0, 0.0]),
    'v_enu': np.array([0.0, 0.0, 0.0]),
    'q_enu2b': np.array([0.0, 0.0, 0.0, 1.0]),
    'w_enu': np.array([0.0, 0.0, 0.0]),
    'mass': 10.0
}

class DummyRocket:
    """Cohete dummy para demostración del Monte Carlo"""
    def __init__(self):
        self.r_enu = np.array([0.0, 0.0, 0.0])
        self.v_enu = np.array([0.0, 0.0, 0.0])
        self.mass = 10.0
        
    def reset(self):
        self.r_enu = np.array([0.0, 0.0, 0.0])
        self.v_enu = np.array([0.0, 0.0, 0.0])

# Botones de control
col1, col2, col3 = st.columns(3)

with col1:
    run_simulation = st.button("🚀 Ejecutar Simulación Monte Carlo", type="primary")

with col2:
    show_wind_rose = st.button("🌪️ Mostrar Rosa de Vientos")

with col3:
    export_results = st.button("💾 Exportar Resultados")

# Mostrar rosa de vientos
if show_wind_rose:
    st.subheader("Rosa de Vientos - " + display_season.value.title())
    
    # Crear gráfico de rosa de vientos
    directions = temp_wind_rose.direction_names
    frequencies = wind_stats['direction_frequencies']
    mean_speeds = wind_stats['mean_speeds']
    
    # Gráfico polar de rosa de vientos
    fig_wind_rose = go.Figure()
    
    # Añadir barras radiales para frecuencias
    fig_wind_rose.add_trace(go.Barpolar(
        r=frequencies,
        theta=temp_wind_rose.directions,
        name='Frecuencia',
        marker_color=px.colors.sequential.Viridis,
        opacity=0.7
    ))
    
    fig_wind_rose.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(frequencies)]),
            angularaxis=dict(
                tickvals=temp_wind_rose.directions,
                ticktext=directions,
                direction="clockwise",
                rotation=90
            )
        ),
        title=f"Rosa de Vientos - {location_name} ({display_season.value.title()})",
        showlegend=True
    )
    
    st.plotly_chart(fig_wind_rose, use_container_width=True)
    
    # Tabla de estadísticas direccionales
    wind_table = pd.DataFrame({
        'Dirección': directions,
        'Frecuencia (%)': (frequencies * 100).round(1),
        'Velocidad Media (m/s)': mean_speeds.round(1)
    })
    st.dataframe(wind_table, use_container_width=True)

# Ejecutar simulación
if run_simulation:
    dummy_rocket = DummyRocket()
    
    # Crear simulación Monte Carlo
    mc_simulation = MonteCarloSimulation(
        rocket=dummy_rocket,
        n_sims=n_sims,
        max_altitude=max_altitude,
        location_name=location_name,
        season=selected_season
    )
    
    # Barra de progreso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(progress):
        progress_bar.progress(progress)
        status_text.text(f"Completado: {int(progress * 100)}% ({int(progress * n_sims)}/{n_sims} simulaciones)")
    
    # Ejecutar simulaciones
    status_text.text("Iniciando simulaciones Monte Carlo...")
    mc_simulation.run_simulations(progress_callback=update_progress)
    
    # Analizar resultados
    results = mc_simulation.analyze_results()
    
    if 'error' in results:
        st.error(results['error'])
    else:
        # Mostrar resultados
        st.success(f"✅ Simulación completada: {n_sims} simulaciones ejecutadas")
        
        # Estadísticas básicas
        st.subheader("📊 Estadísticas de Aterrizaje")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Distancia Media", f"{results['basic_statistics']['mean_distance']:.1f} m")
        with col2:
            st.metric("Distancia Máxima", f"{results['basic_statistics']['max_distance']:.1f} m")
        with col3:
            st.metric("Desviación Estándar", f"{results['basic_statistics']['std_distance']:.1f} m")
        with col4:
            st.metric("Confiabilidad", f"{results['basic_statistics']['reliability']:.1%}")
        
        # Gráfico de puntos de aterrizaje
        st.subheader("🎯 Puntos de Aterrizaje")
        
        landing_df = results['landing_points']
        
        # Gráfico de dispersión con elipse de confianza
        fig_landing = px.scatter(
            landing_df, x='X', y='Y',
            title='Distribución de Puntos de Aterrizaje',
            labels={'X': 'Distancia Este (m)', 'Y': 'Distancia Norte (m)'}
        )
        
        # Añadir elipse de confianza si hay datos de zona de aterrizaje
        if 'landing_zone' in results and results['landing_zone']:
            lz = results['landing_zone']
            
            # Calcular puntos de la elipse
            theta = np.linspace(0, 2*np.pi, 100)
            angle_rad = np.radians(lz['ellipse_orientation_deg'])
            
            ellipse_x = (lz['ellipse_semi_major'] * np.cos(theta) * np.cos(angle_rad) - 
                        lz['ellipse_semi_minor'] * np.sin(theta) * np.sin(angle_rad) + 
                        lz['center_x'])
            ellipse_y = (lz['ellipse_semi_major'] * np.cos(theta) * np.sin(angle_rad) + 
                        lz['ellipse_semi_minor'] * np.sin(theta) * np.cos(angle_rad) + 
                        lz['center_y'])
            
            fig_landing.add_trace(go.Scatter(
                x=ellipse_x, y=ellipse_y,
                mode='lines',
                name='Elipse 95% Confianza',
                line=dict(color='red', width=2)
            ))
        
        fig_landing.update_layout(
            xaxis_title="Distancia Este (m)",
            yaxis_title="Distancia Norte (m)",
            showlegend=True
        )
        
        st.plotly_chart(fig_landing, use_container_width=True)
        
        # Análisis de viento
        if 'wind_analysis' in results and results['wind_analysis']:
            st.subheader("🌬️ Análisis de Viento")
            
            wind_analysis = results['wind_analysis']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Viento Superficie Promedio", 
                         f"{wind_analysis.get('mean_surface_wind_speed', 0):.1f} m/s")
            with col2:
                st.metric("Viento Max Altitud Promedio", 
                         f"{wind_analysis.get('mean_max_altitude_wind_speed', 0):.1f} m/s")
            with col3:
                st.metric("Dirección Dominante", 
                         f"{wind_analysis.get('dominant_direction_deg', 0):.0f}°")
        
        # Estadísticas de fallo
        st.subheader("⚠️ Análisis de Confiabilidad")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Estados del Cohete**")
            failure_df = pd.DataFrame({
                'Estado': results['failure_stats'].index,
                'Cantidad': results['failure_stats'].values,
                'Porcentaje': (results['failure_stats'].values / n_sims * 100).round(1)
            })
            st.dataframe(failure_df, use_container_width=True)
        
        with col2:
            st.write("**Estados del Paracaídas**")
            chute_df = pd.DataFrame({
                'Estado': results['chute_stats'].index,
                'Cantidad': results['chute_stats'].values,
                'Porcentaje': (results['chute_stats'].values / n_sims * 100).round(1)
            })
            st.dataframe(chute_df, use_container_width=True)
        
        # Almacenar resultados en session state para exportación
        st.session_state['mc_results'] = results
        st.session_state['mc_simulation'] = mc_simulation

# Exportar resultados
if export_results and 'mc_results' in st.session_state:
    try:
        filename = f"monte_carlo_results_{location_name}_{display_season.value}_{n_sims}sims.json"
        st.session_state['mc_simulation'].export_results(filename)
        st.success(f"✅ Resultados exportados a: {filename}")
        
        # Mostrar resumen para descarga
        with open(filename, 'r') as f:
            results_json = f.read()
        
        st.download_button(
            label="📥 Descargar Resultados JSON",
            data=results_json,
            file_name=filename,
            mime="application/json"
        )
        
    except Exception as e:
        st.error(f"Error al exportar resultados: {str(e)}")

# Información adicional
with st.expander("ℹ️ Información sobre el Modelo de Monte Carlo"):
    st.markdown("""
    ### Características del Modelo Mejorado
    
    **Rosa de Vientos:**
    - 16 sectores direccionales (22.5° cada uno)
    - Patrones estacionales realistas
    - Variación con altitud usando ley de potencias
    - Efectos diurnos opcionales
    
    **Efectos de Viento:**
    - Velocidad variable con altura
    - Ráfagas y turbulencia
    - Deriva direccional con altitud
    - Componentes Este-Norte-Arriba
    
    **Análisis Estadístico:**
    - Elipse de confianza del 95%
    - Centro de masa de la zona de aterrizaje  
    - Análisis de confiabilidad del sistema
    - Exportación de datos completos
    
    **Limitaciones Actuales:**
    - Modelo de cohete simplificado para demostración
    - Integración completa con dinámica de vuelo pendiente
    - Validación con datos meteorológicos reales pendiente
    """)
    
    st.markdown("""
    ### Referencias
    - World Meteorological Organization - Guide to Meteorological Practices
    - NASA Technical Memorandum - Atmospheric Wind Models  
    - Barrowman (1967) - Aerodynamic Characteristics of Slender Finned Vehicles
    """)