import streamlit as st
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl
import json
import pandas as pd

st.set_page_config(page_title="Location Settings", page_icon=":material/rocket:", layout="wide")
st.title("Location Settings")


st.subheader("Location Properties")
        # Add input fields for location properties
left_column, right_column = st.columns(2)

with left_column:
    launch_site_name = st.text_input("Location Name", "My Location")
    launch_site_lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=0.0, step=0.1)
    launch_site_lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=0.0, step=0.1)
    launch_site_alt = st.number_input("Altitude (m)", min_value=0.0, value=0.0)

with right_column:
    # Add input fields for geographical information
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

# Add a submit button
submitted = st.button("Save Location Settings")
# Al guardar una nueva ubicación
if submitted:
    st.success("Location settings saved!")
    new_location = {
        "name": launch_site_name,
        "latitude": launch_site_lat,
        "longitude": launch_site_lon,
        "altitude": launch_site_alt,
    }
    
    try:
        with open("data/locations/launch_sites.json", "r") as file:
            locations = json.load(file)
    except FileNotFoundError:
        locations = {}
    
    locations[new_location["name"]] = new_location
    with open("data/locations/launch_sites.json", "w") as f:
        json.dump(locations, f, indent=4)
