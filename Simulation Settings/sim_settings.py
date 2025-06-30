import streamlit as st

# Create and edit rockets properties for the simulator
with st.form("Simulation Settings"):
    st.write("Rocket Settings")

    left_column, right_column = st.columns(2)
    sim_runtime = st.slider('Simulation runtime [s]', min_value=0.0, max_value=10000.0, value=500.0, step=1.0)
    with left_column:
        #info
        st.subheader("Simulation Properties")
        sim_time_step = st.number_input('Simulation time step [s]', min_value=0.0, max_value=10.0, value=0.1, step=0.01)
        sim_date = st.date_input('Simulation date', value=None, min_value=None, max_value=None, key=None)
        sim_time = st.time_input('Simulation time', value=None, key=None)
        sim_timezone = st.selectbox('Simulation timezone', options=['UTC', 'Local'], index=0)   

    with right_column:
        #info
        st.subheader("Simulation Settings")
        sim_rocket = st.selectbox('Rocket Selection', options=['UTC', 'Local'], index=0)
        sim_location = st.selectbox('Location Selection', options=['UTC', 'Local'], index=0)
        average_temperature = st.number_input('Average temperature [C]', min_value=-50.0, max_value=50.0, value=20.0, step=1.0)
        launch_elevation = st.number_input('Launch elevation [m]', min_value=0.0, max_value=10000.0, value=0.0, step=1.0)
        launch_site_orientation = st.number_input('Launch site orientation', min_value=-50.0, max_value=50.0, value=20.0, step=1.0)
        average_pressure = st.number_input('Average pressure [Pa]', min_value=0.0, max_value=100000.0, value=101325.0, step=1.0)
        average_humidity = st.number_input('Average humidity [%]', min_value=0.0, max_value=100.0, value=50.0, step=1.0)
    # Add a submit button
    run = st.form_submit_button("Run Simulation")
    if run:
        st.success("Running!")