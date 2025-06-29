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
        st.text_input("Rocket Name", "My Rocket")
        st.number_input("Mass (kg)", min_value=0.0, value=100.0)
        st.number_input("Thrust (N)", min_value=0.0, value=500.0)
        st.number_input("Drag Coefficient", min_value=0.0, value=0.1)
        st.text_input("Rocket Name", "My Rocket")
        st.number_input("Mass (kg)", min_value=0.0, value=100.0)
        st.number_input("Thrust (N)", min_value=0.0, value=500.0)
        st.number_input("Drag Coefficient", min_value=0.0, value=0.1)
        st.text_input("Rocket Name", "My Rocket")
        st.number_input("Mass (kg)", min_value=0.0, value=100.0)
        st.number_input("Thrust (N)", min_value=0.0, value=500.0)
        st.number_input("Drag Coefficient", min_value=0.0, value=0.1)
        st.text_input("Rocket Name", "My Rocket")
        st.number_input("Mass (kg)", min_value=0.0, value=100.0)
        st.number_input("Thrust (N)", min_value=0.0, value=500.0)
        st.number_input("Drag Coefficient", min_value=0.0, value=0.1)
        st.text_input("Rocket Name", "My Rocket")
        st.number_input("Mass (kg)", min_value=0.0, value=100.0)
        st.number_input("Thrust (N)", min_value=0.0, value=500.0)
        st.number_input("Drag Coefficient", min_value=0.0, value=0.1)

   
    
    # Add a submit button
    submitted = st.form_submit_button("Save Settings")
    if submitted:
        st.success("Rocket settings saved!")


# You can use a column just like st.sidebar:
# Or even better, call Streamlit functions inside a "with" block:
with right_column:
    chosen = st.radio(
        'Sorting hat',
        ("Gryffindor", "Ravenclaw", "Hufflepuff", "Slytherin"))
    st.write(f"You are in {chosen} house!")