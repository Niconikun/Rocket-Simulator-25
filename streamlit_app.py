import json
from pathlib import Path
import streamlit as st

# Carga de datos
@st.cache_data
def load_config():
    """Carga la configuración desde archivos JSON"""
    rockets_path = Path("data/rockets.json")
    locations_path = Path("data/launch_sites.json")
    
    with open(rockets_path) as f:
        rockets = json.load(f)
    with open(locations_path) as f:
        locations = json.load(f)
    
    return rockets, locations

def main():
    rocket_page = st.Page("pages/02_rocket_settings.py", title="Rocket", icon=":material/rocket:")
    sim_page = st.Page("pages/01_simulation.py", title="Simulation", icon=":material/nest_heat_link_e:",default=True)
    location_page = st.Page("pages/03_location_settings.py", title="Location", icon=":material/location_on:")
    dashboard_page = st.Page("pages/05_dashboard.py", title="Dashboard", icon=":material/dashboard:")
    monte_carlo_page = st.Page("pages/04_monte_carlo.py", title="Monte Carlo", icon=":material/graph_3:")
    units_page = st.Page("pages/06_units_conversion.py", title="Units Conversion", icon=":material/scale:")
    engine_page = st.Page("pages/07_engine_settings.py", title="Engine", icon=":material/explosion:")

    pg = st.navigation(
        [engine_page, rocket_page, location_page, sim_page, dashboard_page, monte_carlo_page, units_page],
        position="top")

    st.set_page_config(page_title="Data manager", page_icon=":material/hub:")

    pg.run()

if __name__ == "__main__":
    main()