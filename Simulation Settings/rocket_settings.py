#create and edit rockets properties for the simulator
import streamlit as st


with st.form("Rocket Settings"):
    st.write("Rocket Settings")
    
    left_column, right_column = st.columns(2)

    with left_column:
        st.subheader("Rocket Properties")
        # Add input fields for rocket properties
        st.text_input("Rocket Name", "My Rocket")
        st.number_input("Initial Mass (kg)", min_value=0.0, value=100.0)
        st.number_input("Burn Time [s]", min_value=0.0, value=500.0)
        st.number_input("Reference area (Lift & Drag)", min_value=0.0, value=0.1)
        st.number_input("Inertia before burning", min_value=0.0, value=0.1)
        st.number_input("Centre of Mass (CoM) before burning", min_value=0.0, value=0.1)
        st.number_input("Inertia after burning", min_value=0.0, value=0.1)
        st.number_input("Centre of Mass (CoM) after burning", min_value=0.0, value=0.1)

    with right_column:
        st.subheader("Rocket Geometry")
        # Add input fields for rocket performance metrics
        len_warhead = st.number_input('Length of warhead or distance from tip of nose to base of nose', min_value=0.0, value=500.0)
        len_nosecone_fins = st.number_input('Length between nose cone tip and the point where the fin leading edge meets the body tube', min_value=0.0, value=500.0)
        len_nosecone_rear = st.number_input('Length between nose tip to rear', min_value=0.0, value=500.0)              
        len_bodytube_wo_rear = st.number_input('Length of body tube (not considering rear)', min_value=0.0, value=500.0)
        fins_chord_root = st.number_input('Fins aerodynamic chord at root', min_value=0.0, value=500.0)
        fins_mid_chord = st.number_input('Fins aerodynamic mid-chord', min_value=0.0, value=500.0)
        len_rear = st.number_input('Length of rear', min_value=0.0, value=500.0)
        fins_span = st.number_input('Fins span', min_value=0.0, value=500.0)
        diameter_warhead_base = st.number_input('Diameter of base of warhead', min_value=0.0, value=500.0)
        diameter_bodytube = st.number_input('Diameter of body tube', min_value=0.0, value=500.0)
        diameter_bodytube_fins = st.number_input('Diameter of body tube where fins are met', min_value=0.0, value=500.0)
        diameter_rear_bodytube = st.number_input('Diameter of rear where it meets body tube', min_value=0.0, value=500.0)
        end_diam_rear =  st.number_input('End diameter rear', min_value=0.0, value=500.0)
        normal_f_coef_warhead = st.number_input('Normal force coefficient gradient for warhead', min_value=0.0, value=500.0)
        N_fins = st.number_input('Number of fins', min_value=0.0, value=500.0)
   
    
    # Add a submit button
    submitted = st.form_submit_button("Save Settings")
    if submitted:
        st.success("Rocket settings saved!")
