import streamlit as st
import json
import os
from src.models.engine.motor import Motor
from src.models.engine.nozzle import Nozzle
from src.models.engine.grain import Grain
from src.models.engine.propellant import Propellant  # o Propellant, según tu API
# ...otros imports según necesites

st.set_page_config(page_title="Engine Designer", layout="wide")
st.title("Solid Rocket Motor (SRM) Design and Configuration")

# Carpeta donde se guardarán los motores
engine_configs_path = 'data/rockets/engines'
os.makedirs(engine_configs_path, exist_ok=True)

left_nozzle, right_grain = st.columns(2)

with left_nozzle:
    st.header("Nozzle Configuration")
    throat = st.number_input("Throat Diameter (m)", min_value=0.0, value=0.1)
    exit_diameter = st.number_input("Exit Diameter (m)", min_value=0.0, value=0.3)
    efficiency = st.slider("Nozzle Efficiency", min_value=0.0, max_value=1.0, value=0.95)
    divAngle = st.number_input("Divergence Half Angle (deg)", min_value=0.0, max_value=45.0, value=15.0)
    convAngle = st.number_input("Convergence Half Angle (deg)", min_value=0.0, max_value=45.0, value=30.0)
    throatLength = st.number_input("Throat Length (m)", min_value=0.0, value=0.05)
    slagCoeff = st.number_input("Slag Buildup Coefficient ((m*Pa)/s)", min_value=0.0, value=0.0)
    erosionCoeff = st.number_input("Throat Erosion Coefficient (m/(s*Pa))", min_value=0.0, value=0.0)
    nozzle = Nozzle(throat, exit_diameter, efficiency, divAngle, convAngle, throatLength, slagCoeff, erosionCoeff)
    # Aquí puedes agregar los controles para la configuración de la tobera

with right_grain:
    st.header("Grain Configuration")
    diameter = st.number_input("Chamber Diameter (m)", min_value=0.0, value=0.5)
    length = st.number_input("Chamber Length (m)", min_value=0.0, value=1.0)
    grain = Grain(diameter, length)
    

# --- Formulario de parámetros básicos ---
