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
        with open("data/locations/launch_sites.json", "r", encoding='utf-8') as f:  # Ensure UTF-8
            return json.load(f)
    except FileNotFoundError:
        return {}
    except UnicodeDecodeError as e:
        st.error(f"Error de codificación al cargar sitios de lanzamiento: {e}")
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
        with open("data/locations/launch_sites.json", "w", encoding='utf-8') as f:  # Added encoding
            json.dump(locations, f, indent=4, ensure_ascii=False)  # ensure_ascii=False to preserve special chars
        return True, "Sitio de lanzamiento guardado exitosamente"
    
    except Exception as e:
        return False, f"Error guardando sitio: {str(e)}"

def delete_launch_site(site_name):
    """Elimina un sitio de lanzamiento"""
    try:
        locations = load_launch_sites()
        if site_name in locations:
            del locations[site_name]
            with open("data/locations/launch_sites.json", "w", encoding='utf-8') as f:  # Added encoding
                json.dump(locations, f, indent=4, ensure_ascii=False)  # ensure_ascii=False to preserve special chars
            return True, f"Sitio {site_name} eliminado"
        return False, "Sitio no encontrado"
    except Exception as e:
        return False, f"Error eliminando sitio: {str(e)}"

# Configuración de la página
st.set_page_config(page_title="Location Settings", page_icon=":material/rocket:", layout="wide")
st.title("🚀 Location Settings")

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
            value=default_values.get("name", ""),
            help="Unique name for this launch site"
        )
        
        # Coordinates
        col1, col2, col3 = st.columns(3)
        with col1:
            launch_site_lat = st.number_input(
                "Latitude °", 
                min_value=-90.0, 
                max_value=90.0, 
                value=float(default_values.get("latitude", -36.8)),
                format="%.6f",
                help="Latitude in decimal degrees"
            )
        with col2:
            launch_site_lon = st.number_input(
                "Longitude °", 
                min_value=-180.0, 
                max_value=180.0, 
                value=float(default_values.get("longitude", -73.0)),
                format="%.6f",
                help="Longitude in decimal degrees"
            )
        with col3:
            launch_site_alt = st.number_input(
                "Altitude (m)", 
                min_value=-1000.0,
                max_value=10000.0,
                value=float(default_values.get("altitude", 0.0)),
                help="Altitude above sea level in meters"
            )
        
        # NEW: Rocket-specific parameters
        st.subheader("Launch Parameters")
        
        # Launch azimuth options
        azimuth_options = {
            "Polar": 0,
            "Equatorial": 90,
            "Retrograde": 180,
            "Custom": "custom"
        }
        
        azimuth_choice = st.selectbox(
            "Preferred Launch Azimuth",
            list(azimuth_options.keys()),
            help="Default launch direction for this site"
        )
        
        if azimuth_choice == "Custom":
            launch_azimuth = st.number_input(
                "Custom Azimuth °",
                min_value=0.0,
                max_value=360.0,
                value=float(default_values.get("azimuth", 90.0)),
                help="Launch azimuth in degrees from North"
            )
        else:
            launch_azimuth = azimuth_options[azimuth_choice]
        
        # NEW: Safety parameters
        st.subheader("Safety Parameters")
        
        col1, col2 = st.columns(2)
        with col1:
            max_launch_angle = st.number_input(
                "Max Launch Angle °",
                min_value=0.0,
                max_value=90.0,
                value=float(default_values.get("max_launch_angle", 80.0)),
                help="Maximum allowed launch angle"
            )
            
            exclusion_radius = st.number_input(
                "Exclusion Radius (km)",
                min_value=1.0,
                max_value=100.0,
                value=float(default_values.get("exclusion_radius", 5.0)),
                help="Safety exclusion radius around launch site"
            )
        
        with col2:
            min_altitude = st.number_input(
                "Minimum Altitude (m)",
                min_value=0.0,
                max_value=50000.0,
                value=float(default_values.get("min_altitude", 10000.0)),
                help="Minimum safe altitude for maneuvers"
            )
            
            # NEW: Atmospheric conditions
            surface_pressure = st.number_input(
                "Surface Pressure (kPa)",
                min_value=50.0,
                max_value=110.0,
                value=float(default_values.get("surface_pressure", 101.3)),
                help="Average atmospheric pressure at launch site"
            )

    with right_column:
        # Enhanced map with more context
        st.subheader("Location Map")
        
        # Create data for all launch sites
        all_sites_data = []
        for site_name, site_data in locations.items():
            all_sites_data.append({
                'Latitude': site_data.get('latitude', 0),
                'Longitude': site_data.get('longitude', 0),
                'Name': site_name,
                'Type': 'Existing'
            })
        
        # Add current site (even if new)
        if launch_site_name:
            all_sites_data.append({
                'Latitude': launch_site_lat,
                'Longitude': launch_site_lon,
                'Name': launch_site_name if launch_site_name != default_values.get("name", "") else f"{launch_site_name} (editing)",
                'Type': 'Current'
            })
        
        if all_sites_data:
            sites_df = pd.DataFrame(all_sites_data)
            
            config = {
                "version": "v1",
                "config": {
                    "mapState": {
                        "bearing": 0,
                        "latitude": launch_site_lat,
                        "longitude": launch_site_lon,
                        "pitch": 0,
                        "zoom": 8 if len(all_sites_data) > 1 else 11,
                    },
                    "visState": {
                        "layers": [
                            {
                                "id": "launch-sites",
                                "type": "point",
                                "config": {
                                    "dataId": "sites",
                                    "label": "Launch Sites",
                                    "color": [255, 0, 0],
                                    "columns": {
                                        "lat": "Latitude",
                                        "lng": "Longitude"
                                    },
                                    "isVisible": True
                                }
                            }
                        ]
                    }
                },
            }

            map_1 = KeplerGl()
            map_1.config = config
            map_1.add_data(data=sites_df, name="sites")
            keplergl_static(map_1, center_map=True, read_only=True)
            
            st.caption(f"Showing {len(all_sites_data)} launch site(s)")
        else:
            st.info("No launch sites to display")

    # NEW: Site description
    site_description = st.text_area(
        "Site Description",
        value=default_values.get("description", ""),
        help="Optional description of the launch site",
        placeholder="Describe the site characteristics, facilities, etc."
    )

    # Botones de acción
    col1, col2, col3 = st.columns(3)
    with col1:
        submitted = st.form_submit_button("💾 Save", use_container_width=True)
    with col2:
        if existing_site != "Nuevo sitio":
            delete = st.form_submit_button("🗑️ Delete", use_container_width=True)
        else:
            delete = None
    with col3:
        test_site = st.form_submit_button("🚀 Test Site", use_container_width=True)

# Procesar acciones
if submitted:
    new_location = {
        "name": launch_site_name,
        "latitude": launch_site_lat,
        "longitude": launch_site_lon,
        "altitude": launch_site_alt,
        "azimuth": launch_azimuth,
        "max_launch_angle": max_launch_angle,
        "exclusion_radius": exclusion_radius,
        "min_altitude": min_altitude,
        "surface_pressure": surface_pressure,
        "description": site_description
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

if test_site:
    st.session_state.test_location = {
        "name": launch_site_name,
        "latitude": launch_site_lat,
        "longitude": launch_site_lon,
        "altitude": launch_site_alt
    }
    st.success(f"Site '{launch_site_name}' configured to testing. Go to the simulation tab.")
