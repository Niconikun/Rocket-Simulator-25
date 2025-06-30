import streamlit as st
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl

st.set_page_config(page_title="Rocket Simulator Dashboard", page_icon=":rocket:", layout="wide")
st.title("Rocket Simulator Dashboard")
st.write("This dashboard provides an overview of the rocket simulation results.")
# Placeholder for rocket simulation data
