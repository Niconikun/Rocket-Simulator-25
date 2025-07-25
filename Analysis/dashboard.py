import streamlit as st
import pandas as pd
import numpy as np
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl
import json
import geopy as geo

st.set_page_config(page_title="Rocket Simulator Dashboard", page_icon=":rocket:", layout="wide")
st.title("Rocket Simulator Dashboard")

chart_data= pd.read_pickle("sim_data.pkl")

chart_data_compressed = chart_data.iloc[::20, :]

#with open('rockets.json', 'r') as file:
 #   rocket_settings = json.load(file)

#with open('locations.json', 'r') as file:
 #   location_settings = json.load(file)

#Latitude = location_settings[location_name]['latitude']
#Longitude = location_settings[location_name]['longitude']

a, b, c = st.columns(3)
d, e, f = st.columns(3)
g, h, i = st.columns(3)

j = st.columns(1)

st.subheader("Rocket Performance Metrics")

a.metric("Total Flight Time", str(round((chart_data.iloc[-1]["Simulation time"]), 2)) + "s", border=True)
b.metric("Max Range", str(round((chart_data.iloc[-1]["Range"]) / 1000,2)) + 'km', border=True)
c.metric("Max Alt", str(round((max(chart_data.loc[:,"Up coordinate"])) / 1000,3)) + "km", str(round((chart_data.loc[chart_data.loc[:,"Up coordinate"].idxmax(), "Simulation time"]),2))+ "s", border=True)

d.metric("Pitch at Max Alt", str(round((chart_data.loc[chart_data.loc[:,"Up coordinate"].idxmax(),"Pitch angle"]),2)) + '°', border=True)
e.metric("Initial Mass", str(round(chart_data.iloc[0]["Mass of the rocket"],3)) + 'kg', border=True)
f.metric("Final Mass", str(round(chart_data.iloc[-1]["Mass of the rocket"],3)) + ' kg', border=True)

g.metric("Max Speed", str(round((max(chart_data.loc[:,"Velocity norm"])),2)) + 'm/s', str(round((chart_data.loc[chart_data.loc[:,"Velocity norm"].idxmax(),"Simulation time"]),3)) + 's', border=True)
h.metric("Max Mach", str(round((max(chart_data.loc[:,"Mach number"])),2)), str(round((chart_data.loc[chart_data.loc[:,"Mach number"].idxmax(),"Simulation time"]),3)) + 's', border=True)
i.metric("Max Acceleration", "2023-10-01", border=True)

j[0].metric("Landing Coordinates", str(abs(round((chart_data.iloc[-1]["Latitude"]),1)))+ "° S, " + str(abs(round((chart_data.iloc[-1]["Longitude"]),1)))+ "° W", border=True)

st.subheader("Trajectory Overview")

config = {
    "version": "v1",
    "config": {
        "mapState": {
            "bearing": 0,
            "latitude": chart_data.iloc[0]["Location Latitude"],
            "longitude": chart_data.iloc[0]["Location Longitude"],
            "pitch": 60,
            "zoom": 9,
        }
    },
}

trajectory_data = pd.DataFrame({
    'Latitude': chart_data_compressed.loc[:,"Latitude"].to_list(),
    'Longitude': chart_data_compressed.loc[:,"Longitude"].to_list(),
    'Altitude': chart_data_compressed.loc[:,"Altitude"].to_list(),
    })

map_1 = KeplerGl(height=600, data={"trajectory": trajectory_data})
map_1.config = config



#map_1.add_data(data=trajectory_data, name="Rayon's Trajectory")

#st.write(map_1)
keplergl_static(map_1, height=600, width=1000, center_map=True)
#chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["a", "b", "c"])

left_up, middle_up, right_up = st.columns(3)
left_down, middle_down, right_down = st.columns(3)

st.subheader("Rocket Performance Charts")

left_up.write('Bodyframe Velocities vs Time')
left_up.line_chart(chart_data_compressed, x="Simulation time", y=["v_bx","v_by","v_bz"], x_label="Flight time [s]", y_label="Velocidad Bodyframe [m/s]", color=["#ffffff", "#cccccc", "#aaaaaa"])

middle_up.write('Altitude vs Range')
middle_up.line_chart(chart_data_compressed, x="Range", y="Up coordinate", x_label="Distancia [m]", y_label="Altitud [m]", color="#ffffff")

right_up.write('Lift vs Time')
right_up.line_chart(chart_data_compressed, x="Simulation time", y="Lift force in bodyframe", x_label="Tiempo de vuelo [s]", y_label="Fuerza de sustentación [N]", color="#ffffff")

left_down.write('Pitch, Altitude vs Time')
left_down.line_chart(chart_data_compressed, x="Simulation time", y=["Pitch angle", "Up coordinate"], x_label="Tiempo de vuelo [s]", y_label="Ángulo de cabeceo [rad] / Altitud [m]", color=["#ffffff", "#888888"])

middle_down.write('Pitch vs Time')
middle_down.line_chart(chart_data_compressed, x="Simulation time", y="Pitch angle", x_label="Tiempo de vuelo [s]", y_label="Ángulo de cabeceo [rad]", color="#ffffff")

right_down.write('Alpha vs Time')
right_down.line_chart(chart_data_compressed, x="Simulation time", y="Angle of attack", x_label="Tiempo de vuelo [s]", y_label="Ángulo de ataque [rad]", color="#ffffff")

st.subheader("Risk Analysis")

geojson_dict = {
       "type": "FeatureCollection",
       "features": [{
           "type": "Feature",
           "geometry": {
               "type": "Point",
               "coordinates": [102.0, 0.5]
           },
           "properties": {
               "prop0": "value0"
           }
       }, {
           "type": "Feature",
           "geometry": {
               "type": "LineString",
               "coordinates": [
                   [102.0, 0.0],
                   [103.0, 1.0],
               ]
           },
           "properties": {
               "prop0": "value0",
               "prop1": 0.0
           }
       }, {
           "type": "Feature",
           "geometry": {
               "type": "Polygon",
               "coordinates": [
                   [
                       [100.0, 0.0],
                       [101.0, 0.0],
                       [101.0, 1.0],
                       [100.0, 1.0],
                       [100.0, 0.0]
                   ]
               ]
           },
           "properties": {
               "prop0": "value0",
               "prop1": {
                   "this": "that"
               }
           }
       }]
   }

risk_map = KeplerGl(height=600, data={"risk_layer": geojson_dict})
risk_map.config = {
    "version": "v1",
    "config": {
        "mapState": {
            "bearing": 0,
            "latitude": chart_data.iloc[0]["Location Latitude"],
            "longitude": chart_data.iloc[0]["Location Longitude"],
            "pitch": 60,
            "zoom": 2,
        }
    },
}
keplergl_static(risk_map, height=600, width=1000, center_map=True)