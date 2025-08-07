import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go # type: ignore
from src.models.markov_models import (
    AtmosphericMarkovModel, 
    FailureMarkovModel,
    ParachuteMarkovModel
)

st.title("Análisis de Monte Carlo [En Proceso]")

# Configuración de la simulación
n_sims = st.sidebar.slider("Número de simulaciones", 100, 1000, 500)
max_altitude = st.sidebar.number_input("Altitud máxima (m)", 1000, 5000, 2000)
wind_initial = st.sidebar.selectbox("Condición inicial del viento", 
                                  ["calm", "moderate", "strong", "turbulent"])

# Inicializar modelos
atm_model = AtmosphericMarkovModel()
fail_model = FailureMarkovModel()
chute_model = ParachuteMarkovModel()

if st.button("Ejecutar simulaciones"):
    # Inicializar estadísticas usando los estados de los modelos
    failure_stats = {state: 0 for state in fail_model.states}
    chute_stats = {state: 0 for state in chute_model.states}
    
    landing_points = []
    max_altitudes = []
    
    progress_bar = st.progress(0)
    
    # Ejecutar simulaciones
    for i in range(n_sims):
        # Estado inicial
        wind_state = wind_initial
        rocket_state = "nominal"
        chute_state = "packed"
        
        # Simular trayectoria
        altitude = 0
        x, y = 0, 0
        
        while altitude >= 0:
            # Actualizar estados
            wind_state = atm_model.get_next_state(wind_state)
            wind_cond = atm_model.get_wind_conditions(wind_state)
            
            rocket_state = fail_model.get_next_state(
                rocket_state, altitude, velocity=100, acceleration=20)
                
            if altitude > 100 and altitude < max_altitude:
                chute_state = chute_model.get_next_state(
                    chute_state, velocity=50, altitude=altitude)
            
            # Actualizar posición (simplificado)
            x += wind_cond["base_speed"] * np.cos(wind_cond["direction"])
            y += wind_cond["base_speed"] * np.sin(wind_cond["direction"])
            
            # Actualizar altitud
            if altitude < max_altitude and rocket_state == "nominal":
                altitude += 10
            else:
                altitude -= 5
        
        # Guardar resultados (convertir a str normal)
        landing_points.append((x, y))
        failure_stats[str(rocket_state)] += 1
        chute_stats[str(chute_state)] += 1
        
        progress_bar.progress((i + 1) / n_sims)
    
    # Visualización de resultados
    landing_df = pd.DataFrame(landing_points, columns=["X", "Y"])
    
    fig = go.Figure(data=go.Scatter(
        x=landing_df["X"],
        y=landing_df["Y"],
        mode="markers",
        marker=dict(
            size=8,
            color="red",
            opacity=0.6
        )
    ))
    
    fig.update_layout(
        title="Puntos de aterrizaje",
        xaxis_title="Distancia X (m)",
        yaxis_title="Distancia Y (m)"
    )
    
    st.plotly_chart(fig)
    
    # Estadísticas
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Estados del cohete")
        st.write(pd.Series(failure_stats))
    with col2:
        st.subheader("Estados del paracaídas")
        st.write(pd.Series(chute_stats))