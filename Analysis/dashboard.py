import streamlit as st
import pandas as pd
import numpy as np
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl

st.set_page_config(page_title="Rocket Simulator Dashboard", page_icon=":rocket:", layout="wide")
st.title("Rocket Simulator Dashboard")

a, b = st.columns(2)
c, d = st.columns(2)

a.metric("Temperature", "30°F", "-9°F", border=True)
b.metric("Wind", "4 mph", "2 mph", border=True)

c.metric("Humidity", "77%", "5%", border=True)
d.metric("Pressure", "30.34 inHg", "-2 inHg", border=True)

st.subheader("Rocket Performance Metrics")
st.write("Here you can display various performance metrics of the rocket, such as altitude, speed, and acceleration.")  

st.write("Trajectory Overview")

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

chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["a", "b", "c"])

st.write('Bodyframe Velocities vs Time')
st.line_chart(chart_data)

st.write('Altitude vs Range')
st.line_chart(chart_data)

st.write('Lift vs Time')
st.line_chart(chart_data)

st.write('Pitch, Altitude vs Time')
st.line_chart(chart_data)

st.write('Pitch vs Time')
st.line_chart(chart_data)

st.write('Alpha vs Time')
st.line_chart(chart_data)
