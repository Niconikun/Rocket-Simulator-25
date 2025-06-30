import streamlit as st
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl

st.write("Location Settings")


st.subheader("Location Properties")
        # Add input fields for location properties
st.text_input("Location Name", "My Location")
launch_site_lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=0.0, step=0.1)
launch_site_lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=0.0, step=0.1)
st.number_input("Altitude (m)", min_value=0.0, value=0.0)
st.text_input("Country", "Country Name")
st.text_input("City", "City Name")


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
        
map_1 = KeplerGl()
map_1.config = config

keplergl_static(map_1)
