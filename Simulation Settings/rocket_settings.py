#create and edit rockets properties for the simulator
import streamlit as st
import json


with st.form("Rocket Settings"):
    st.write("Rocket Settings")
    
    left_column, right_column = st.columns(2)

    with left_column:
        st.subheader("Rocket Properties")
        # Add input fields for rocket properties
        rocket_name = st.text_input("Rocket Name", "My Rocket", key="rocket_name")
        initial_mass = st.number_input("Initial Mass (kg)", min_value=0.0, value=100.0, step=0.1,key="initial_mass")
        burn_time = st.number_input("Burn Time [s]", min_value=0.0, value=500.0, step=0.1, key="burn_time")
        reference_area = st.number_input("Reference area (Lift & Drag)", min_value=0.0, value=0.1, step=0.01, key="reference_area")
        I_before_burn = st.number_input("Inertia before burning", min_value=0.0, value=0.1, step=0.01, key="I_before_burn")
        CoM_before_burn = st.number_input("Centre of Mass (CoM) before burning", min_value=0.0, value=0.1, step=0.01, key="CoM_before_burn")
        I_after_burn = st.number_input("Inertia after burning", min_value=0.0, value=0.1, step=0.01, key="I_after_burn")
        CoM_after_burn = st.number_input("Centre of Mass (CoM) after burning", min_value=0.0, value=0.1, step=0.01, key="CoM_after_burn")

        st.subheader("Engine Properties")
        nozzle_exit_diameter= st.number_input("Nozzle Exit Diameter", min_value=0.0, value=100.0, step=0.1, key="nozzle_exit_diameter")
        mass_flux = st.number_input("Mass Flux", min_value=0.0, value=100.0, step=0.1, key="mass_flux")
        gas_speed = st.number_input("Gas Speed", min_value=0.0, value=100.0, step=0.1, key="gas_speed")
        exit_pressure = st.number_input("Exit Pressure", min_value=0.0, value=100.0, step=0.1, key="exit_pressure")


    with right_column:
        st.subheader("Rocket Geometry")
        # Add input fields for rocket performance metrics
        len_warhead = st.number_input('Length of warhead or distance from tip of nose to base of nose', min_value=0.0, value=500.0, step=0.1, key="len_warhead")
        len_nosecone_fins = st.number_input('Length between nose cone tip and the point where the fin leading edge meets the body tube', min_value=0.0, value=500.0, step=0.1, key="len_nosecone_fins")
        len_nosecone_rear = st.number_input('Length between nose tip to rear', min_value=0.0, value=500.0, step=0.1, key="len_nosecone_rear")              
        len_bodytube_wo_rear = st.number_input('Length of body tube (not considering rear)', min_value=0.0, value=500.0, step=0.1, key="len_bodytube_wo_rear")
        fins_chord_root = st.number_input('Fins aerodynamic chord at root', min_value=0.0, value=500.0, step=0.1, key="fins_chord_root")
        fins_mid_chord = st.number_input('Fins aerodynamic mid-chord', min_value=0.0, value=500.0, step=0.1, key="fins_mid_chord")
        fins_chord_tip = st.number_input('Fins aerodynamic mid-chord', min_value=0.0, value=500.0, step=0.1, key="fins_chord_tip")
        len_rear = st.number_input('Length of rear', min_value=0.0, value=500.0, step=0.1, key="len_rear")
        fins_span = st.number_input('Fins span', min_value=0.0, value=500.0, step=0.1, key="fins_span")
        diameter_warhead_base = st.number_input('Diameter of base of warhead', min_value=0.0, value=500.0, step=0.1, key="diameter_warhead_base")
        diameter_bodytube = st.number_input('Diameter of body tube', min_value=0.0, value=500.0, step=0.1, key="diameter_bodytube")
        diameter_bodytube_fins = st.number_input('Diameter of body tube where fins are met', min_value=0.0, value=500.0, step=0.1, key="diameter_bodytube_fins")
        diameter_rear_bodytube = st.number_input('Diameter of rear where it meets body tube', min_value=0.0, value=500.0, step=0.1, key="diameter_rear_bodytube")
        end_diam_rear =  st.number_input('End diameter rear', min_value=0.0, value=500.0, step=0.1, key="end_diam_rear")
        normal_f_coef_warhead = st.number_input('Normal force coefficient gradient for warhead', min_value=0.0, value=500.0, step=0.1, key="normal_f_coef_warhead")
        N_fins = st.number_input('Number of fins', min_value=0.0, value=500.0, step=1, key="N_fins")
   
    
    # Add a submit button
    submitted = st.form_submit_button("Save Settings")
    if submitted:
        st.success("Rocket settings saved!")
        new_rocket = {
            "name": rocket_name,
            "initial_mass": initial_mass,
            "reference_area": reference_area,
            "inertia_before_burning": I_before_burn,
            "com_before_burning": CoM_before_burn,
            "inertia_after_burning": I_after_burn,
            "com_after_burning": CoM_after_burn,
            'engine': {
                "burn_time": burn_time,
                "nozzle_exit_diameter": nozzle_exit_diameter,
                "mass_flux": mass_flux,
                "gas_speed": gas_speed,
                "exit_pressure": exit_pressure
            },
            "geometry": {
                "len_warhead": len_warhead,
                "len_nosecone_fins": len_nosecone_fins,
                "len_nosecone_rear": len_nosecone_rear,
                "len_bodytube_wo_rear": len_bodytube_wo_rear,
                "fins_chord_root": fins_chord_root,
                "fins_chord_tip": fins_chord_tip,
                "fins_mid_chord": fins_mid_chord,
                "len_rear": len_rear,
                "fins_span": fins_span,
                "diameter_warhead_base": diameter_warhead_base,
                "diameter_bodytube": diameter_bodytube,
                "diameter_bodytube_fins": diameter_bodytube_fins,
                "diameter_rear_bodytube": diameter_rear_bodytube,
                "end_diam_rear": end_diam_rear,
                "normal_f_coef_warhead": normal_f_coef_warhead,
                "N_fins": N_fins
            }
        }
        # Save the new rocket settings to a JSON file
        try:
            with open("rockets.json", "r") as file:
                rockets = json.load(file)
        except FileNotFoundError:
            rockets = {}
        rockets[new_rocket["name"]] = new_rocket
        with open("rockets.json", "w") as file: 
            json.dump(rockets, file, indent=4)
        st.success(f"Rocket '{new_rocket['name']}' settings saved successfully!")
        # Optionally, you can clear the form fields after submission
        st.session_state.clear()
        
        #aca poner que se guarden los datos en un nested dictionary
