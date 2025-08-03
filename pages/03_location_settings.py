import streamlit as st
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl
import json
import pandas as pd
from jsonschema import validate
import os

def load_launch_sites():
    """Carga los sitios de lanzamiento desde el archivo JSON"""
    try:
        with open("data/locations/launch_sites.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def load_schema():
    """Carga el esquema de validación"""
    try:
        with open("data/schemas/launch_sites.schema.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Esquema de validación no encontrado")
        return None

def save_launch_site(site_data):
    """Guarda un sitio de lanzamiento validando contra el esquema"""
    schema = load_schema()
    if not schema:
        return False, "Error: Esquema no disponible"

    try:
        # Validar contra el esquema
        locations = load_launch_sites()
        locations[site_data["name"]] = site_data
        validate(instance=locations, schema=schema)
        
        # Guardar si la validación es exitosa
        os.makedirs("data/locations", exist_ok=True)
        with open("data/locations/launch_sites.json", "w", encoding='utf-8') as f:
            json.dump(locations, f, indent=4, ensure_ascii=False)
        return True, "Sitio de lanzamiento guardado exitosamente"
    
    except Exception as e:
        return False, f"Error guardando sitio: {str(e)}"

def delete_launch_site(site_name):
    """Elimina un sitio de lanzamiento"""
    try:
        locations = load_launch_sites()
        if site_name in locations:
            del locations[site_name]
            with open("data/locations/launch_sites.json", "w", encoding='utf-8') as f:
                json.dump(locations, f, indent=4, ensure_ascii=False)
            return True, f"Sitio {site_name} eliminado"
        return False, "Sitio no encontrado"
    except Exception as e:
        return False, f"Error eliminando sitio: {str(e)}"

# Configuración de la página
st.set_page_config(page_title="Location Settings", page_icon=":material/rocket:", layout="wide")
st.title("Location Settings")

# Cargar sitios existentes
locations = load_launch_sites()

# Selector de sitio existente
existing_site = st.selectbox(
    "Seleccionar sitio existente",
    ["Nuevo sitio"] + list(locations.keys())
)

# Formulario principal
with st.form("location_settings"):
    st.subheader("Location Properties")
    left_column, right_column = st.columns(2)

    with left_column:
        # Cargar valores existentes si se selecciona un sitio
        default_values = locations.get(existing_site, {}) if existing_site != "Nuevo sitio" else {}
        
        launch_site_name = st.text_input(
            "Location Name", 
            value=default_values.get("name", "")
        )
        launch_site_lat = st.number_input(
            "Latitude", 
            min_value=-90.0, 
            max_value=90.0, 
            value=float(default_values.get("latitude", -36.8))
        )
        launch_site_lon = st.number_input(
            "Longitude", 
            min_value=-180.0, 
            max_value=180.0, 
            value=float(default_values.get("longitude", -73.0))
        )
        launch_site_alt = st.number_input(
            "Altitude (m)", 
            min_value=0.0, 
            value=float(default_values.get("altitude", 0.0))
        )

    with right_column:
        # Mapa
        config = {
            "version": "v1",
            "config": {
                "mapState": {
                    "bearing": 0,
                    "latitude": launch_site_lat,
                    "longitude": launch_site_lon,
                    "pitch": 0,
                    "zoom": 11,
                }
            },
        }

        position_data = pd.DataFrame({
            'Latitude': [launch_site_lat],
            'Longitude': [launch_site_lon]
        })

        map_1 = KeplerGl()
        map_1.config = config
        map_1.add_data(data=position_data, name="position")
        keplergl_static(map_1, center_map=True)

    # Botones de acción
    col1, col2 = st.columns(2)
    with col1:
        submitted = st.form_submit_button("Guardar")
    with col2:
        delete = st.form_submit_button("Eliminar") if existing_site != "Nuevo sitio" else None

# Procesar acciones
if submitted:
    new_location = {
        "name": launch_site_name,
        "latitude": launch_site_lat,
        "longitude": launch_site_lon,
        "altitude": launch_site_alt
    }
    
    success, message = save_launch_site(new_location)
    if success:
        st.success(message)
        st.rerun()
    else:
        st.error(message)

if delete:
    success, message = delete_launch_site(existing_site)
    if success:
        st.success(message)
        st.rerun()
    else:
        st.error(message)
