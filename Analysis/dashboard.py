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

#chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["a", "b", "c"])

left_up, middle_up, right_up = st.columns(3)
left_down, middle_down, right_down = st.columns(3)

chart_data= pd.read_pickle("my_data.pkl")

left_up.write('Bodyframe Velocities vs Time')
left_up.line_chart(chart_data, x="Simulation time", y=["v_bx","v_by","v_bz"], x_label="Tiempo de vuelo [s]", y_label="Velocidad Bodyframe [m/s]")

middle_up.write('Altitude vs Range')
middle_up.line_chart(chart_data, x="Range", y="Up coordinate", x_label="Distancia [m]", y_label="Altitud [m]")

right_up.write('Lift vs Time')
right_up.line_chart(chart_data, x="Simulation time", y="Lift force in bodyframe", x_label="Tiempo de vuelo [s]", y_label="Fuerza de sustentación [N]")

left_down.write('Pitch, Altitude vs Time')
left_down.line_chart(chart_data, x="Simulation time", y=["Pitch angle", "Up coordinate"], x_label="Tiempo de vuelo [s]", y_label="Ángulo de cabeceo [rad] / Altitud [m]")

middle_down.write('Pitch vs Time')
middle_down.line_chart(chart_data, x="Simulation time", y="Pitch angle", x_label="Tiempo de vuelo [s]", y_label="Ángulo de cabeceo [rad]")

right_down.write('Alpha vs Time')
right_down.line_chart(chart_data, x="Simulation time", y="Angle of attack", x_label="Tiempo de vuelo [s]", y_label="Ángulo de ataque [rad]")
