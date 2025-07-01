import streamlit as st
from streamlit_globe import streamlit_globe
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl

st.subheader("Globe")
pointsData=[{'lat': 49.19788311472706, 'lng': 8.114625722364316, 'size': 0.3, 'color': 'red'}]
labelsData=[{'lat': 49.19788311472706, 'lng': 8.114625722364316, 'size': 0.3, 'color': 'red', 'text': 'Landau'}]
streamlit_globe(pointsData=pointsData, labelsData=labelsData, daytime='day', width=800, height=600)


st.write("This is a kepler.gl map with specified configuration in streamlit")

config = {
    "version": "v1",
    "config": {
        "mapState": {
            "bearing": 0,
            "latitude": 52.52,
            "longitude": 13.4,
            "pitch": 60,
            "zoom": 11,
        }
    },
}
map_1 = KeplerGl()
map_1.config = config

keplergl_static(map_1)