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

left_column, right_column = st.columns(2)

# --- Formulario de parámetros básicos ---
with left_column.form("engine_form"):
    st.subheader("Data and Kn")
    engine_name = st.text_input("Nombre del motor", value="Nuevo Motor")
    propellant_type = st.selectbox("Tipo de propelente", ["KN-SB", "KN-Dextrose", "KN-Sorbitol", "AP-HTPB", "Otro"])
    grain_type = st.selectbox("Tipo de grano", ["Bates", "Cilíndrico", "End Burner", "Finocyl", "Star", "Moon Burner", "Otro"])
    diameter = st.number_input("Diámetro externo del motor [mm]", min_value=10.0, value=50.0, step=1.0)
    length = st.number_input("Longitud total del motor [mm]", min_value=10.0, value=200.0, step=1.0)
    st.subheader("Pressure Parameters")
    throat_diameter = st.number_input("Diámetro garganta tobera [mm]", min_value=5.0, value=15.0, step=0.5)
    exit_diameter = st.number_input("Diámetro salida tobera [mm]", min_value=5.0, value=30.0, step=0.5)
    nozzle_expansion = st.number_input("Relación de expansión de la tobera", min_value=1.0, value=3.0, step=0.1)
    grain_count = st.number_input("Cantidad de granos", min_value=1, value=1, step=1)
    st.subheader("Performance Parameters")
    grain_length = st.number_input("Longitud de cada grano [mm]", min_value=5.0, value=100.0, step=1.0)
    grain_od = st.number_input("Diámetro externo del grano [mm]", min_value=5.0, value=48.0, step=1.0)
    grain_id = st.number_input("Diámetro interno del grano [mm]", min_value=0.0, value=10.0, step=1.0)
    web = st.number_input("Espesor web [mm]", min_value=0.0, value=5.0, step=0.5)
    # Puedes agregar más parámetros según los modelos de OpenMotor/Nakka

    submitted = st.form_submit_button("Calcular y Guardar Motor")

# --- Cálculos y guardado ---
if submitted:
    # Ejemplo: calcular propiedades usando los módulos importados
    # (Ajusta según la API real de los módulos)
    try:
        # Propiedades del propelente
        prop = get_propellant(propellant_type)
        # Geometría del grano
        grain_geom = Grain(
            type=grain_type,
            length=grain_length,
            od=grain_od,
            id=grain_id,
            web=web,
            count=grain_count
        )
        # Geometría de la tobera
        noz = Nozzle(
            throat_diameter,
            exit_diameter,
            efficiency,
            divergence_angle,
            convergence_angle,
            throat_length,
            slag_coefficient,
            erosion_coefficient
        )
        # Motor
        mot = Motor(
            name=engine_name,
            diameter=diameter,
            length=length,
            propellant=prop,
            grain=grain_geom,
            nozzle=noz
        )
        # Calcular resultados principales
        results = mot.simulate()
        st.success("Motor simulado correctamente.")
        st.write("Empuje máximo [N]:", results['max_thrust'])
        st.write("Impulso total [Ns]:", results['total_impulse'])
        st.write("Duración de combustión [s]:", results['burn_time'])
        st.write("Masa propelente [kg]:", results['propellant_mass'])
        st.write("ISP [s]:", results['isp'])

        # Guardar configuración en JSON
        engine_config = {
            "name": engine_name,
            "propellant_type": propellant_type,
            "grain_type": grain_type,
            "diameter": diameter,
            "length": length,
            "throat_diameter": throat_diameter,
            "exit_diameter": exit_diameter,
            "nozzle_expansion": nozzle_expansion,
            "grain_count": grain_count,
            "grain_length": grain_length,
            "grain_od": grain_od,
            "grain_id": grain_id,
            "web": web,
            "results": results
        }
        file_path = os.path.join(engine_configs_path, f"{engine_name.lower().replace(' ', '_')}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(engine_config, f, indent=4, ensure_ascii=False)
        st.success(f"Configuración guardada en {file_path}")
    except Exception as e:
        st.error(f"Error en el cálculo o guardado: {e}")

# --- Mostrar motores guardados ---
st.markdown("### Motores guardados")
try:
    engine_files = [f for f in os.listdir(engine_configs_path) if f.endswith('.json')]
    for ef in engine_files:
        with open(os.path.join(engine_configs_path, ef), "r", encoding="utf-8") as f:
            data = json.load(f)
            st.write(f"**{data['name']}**: {data['propellant_type']} - {data['grain_type']} - Impulso: {data['results'].get('total_impulse', 'N/A')} Ns")
except Exception as e:
    st.warning(f"No se pudieron cargar motores guardados: {e}")