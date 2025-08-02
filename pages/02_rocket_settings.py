#create and edit rockets properties for the simulator
import streamlit as st
import json
import numpy as np
import pyvista as pv # type: ignore
from stpyvista import stpyvista # type: ignore
import os

# Cargar configuraciones de cohetes
try:
    rockets = {}
    configs_path = 'data/rockets/configs/'
    for file in os.listdir(configs_path):
        if file.endswith('.json'):
            with open(os.path.join(configs_path, file), 'r') as f:
                rocket_data = json.load(f)
                rockets[rocket_data["name"]] = rocket_data
except FileNotFoundError:
    rockets = {}

sim_rocket = st.selectbox('Rocket Selection', options=list(rockets.keys()) + ["Manual"], index=0, key="sim_rocket")

if sim_rocket != "Manual":
    rocket_settings = rockets[sim_rocket]
    rocket_name_edit = rocket_settings["name"]
    initial_mass_edit = rocket_settings["initial_mass"]
    burn_time_edit = rocket_settings["engine"]["burn_time"]
    reference_area_edit = rocket_settings["reference_area"]
    I_before_burn_x_edit = rocket_settings["I_before_burn"]["x"]
    I_before_burn_y_edit = rocket_settings["I_before_burn"]["y"]
    I_before_burn_z_edit = rocket_settings["I_before_burn"]["z"]
    CoM_before_burn_x_edit = rocket_settings["CoM_before_burn"]["x"]
    CoM_before_burn_y_edit = rocket_settings["CoM_before_burn"]["y"]
    CoM_before_burn_z_edit = rocket_settings["CoM_before_burn"]["z"]
    I_after_burn_x_edit = rocket_settings["I_after_burn"]["x"]
    I_after_burn_y_edit = rocket_settings["I_after_burn"]["y"]
    I_after_burn_z_edit = rocket_settings["I_after_burn"]["z"]
    CoM_after_burn_x_edit = rocket_settings["CoM_after_burn"]["x"]
    CoM_after_burn_y_edit = rocket_settings["CoM_after_burn"]["y"]
    CoM_after_burn_z_edit = rocket_settings["CoM_after_burn"]["z"]
    nozzle_exit_diameter_edit = rocket_settings["engine"]["nozzle_exit_diameter"]
    mass_flux_edit = rocket_settings["engine"]["mass_flux"]
    gas_speed_edit = rocket_settings["engine"]["gas_speed"]
    exit_pressure_edit = rocket_settings["engine"]["exit_pressure"]
    len_warhead_edit = rocket_settings["geometry"]["len_warhead"]
    len_nosecone_fins_edit = rocket_settings["geometry"]["len_nosecone_fins"]
    len_nosecone_rear_edit = rocket_settings["geometry"]["len_nosecone_rear"]
    len_bodytube_wo_rear_edit = rocket_settings["geometry"]["len_bodytube_wo_rear"]
    fins_chord_root_edit = rocket_settings["geometry"]["fins_chord_root"]
    fins_mid_chord_edit = rocket_settings["geometry"]["fins_mid_chord"]
    fins_chord_tip_edit = rocket_settings["geometry"]["fins_chord_tip"]
    len_rear_edit = rocket_settings["geometry"]["len_rear"]
    fins_span_edit = rocket_settings["geometry"]["fins_span"]
    diameter_warhead_base_edit = rocket_settings["geometry"]["diameter_warhead_base"]
    diameter_bodytube_edit = rocket_settings["geometry"]["diameter_bodytube"]
    diameter_bodytube_fins_edit = rocket_settings["geometry"]["diameter_bodytube_fins"]
    diameter_rear_bodytube_edit = rocket_settings["geometry"]["diameter_rear_bodytube"]
    end_diam_rear_edit =  rocket_settings["geometry"]["end_diam_rear"]
    normal_f_coef_warhead_edit = rocket_settings["geometry"]["normal_f_coef_warhead"]
    N_fins_edit =rocket_settings["geometry"]["N_fins"]
else:

    rocket_name_edit = "New Rocket"
    initial_mass_edit = 0
    burn_time_edit = 0
    reference_area_edit = 0
    I_before_burn_x_edit = 0.0
    I_before_burn_y_edit = 0.0
    I_before_burn_z_edit = 0.0
    CoM_before_burn_x_edit = 0.0
    CoM_before_burn_y_edit = 0.0
    CoM_before_burn_z_edit = 0.0
    I_after_burn_x_edit = 0.0
    I_after_burn_y_edit = 0.0
    I_after_burn_z_edit = 0.0
    CoM_after_burn_x_edit = 0.0
    CoM_after_burn_y_edit = 0.0
    CoM_after_burn_z_edit = 0.0
    nozzle_exit_diameter_edit = 0.0
    mass_flux_edit = 0.0
    gas_speed_edit = 0.0
    exit_pressure_edit = 0.0
    len_warhead_edit = 0.0
    len_nosecone_fins_edit = 0.0
    len_nosecone_rear_edit = 0.0
    len_bodytube_wo_rear_edit = 0.0
    fins_chord_root_edit = 0.0
    fins_mid_chord_edit = 0.0
    fins_chord_tip_edit = 0.0
    len_rear_edit = 0.0
    fins_span_edit = 0.0
    diameter_warhead_base_edit = 0.0
    diameter_bodytube_edit = 0.0
    diameter_bodytube_fins_edit = 0.0
    diameter_rear_bodytube_edit = 0.0
    end_diam_rear_edit =  0.0
    normal_f_coef_warhead_edit = 0.0
    N_fins_edit = 0

bodytube = {
     "x": np.array([0,0,len_bodytube_wo_rear_edit,len_bodytube_wo_rear_edit,0]),
     "y": np.array([0,diameter_bodytube_edit,diameter_bodytube_edit,0,0]),

}
    
st.set_page_config(page_title="Rocket Settings", page_icon=":material/rocket:", layout="wide")
rock_set = st.form("Rocket Settings")
rock_set.title("Rocket Settings")
    
left_column, middle_column, right_column = rock_set.columns([2, 2, 4])
    


        
left_column.subheader("Rocket Properties")
        # Add input fields for rocket properties
rocket_name = left_column.text_input("Rocket Name", value=rocket_name_edit, key="rocket_name")
initial_mass = left_column.number_input("Initial Mass (kg)", min_value=0.0, value=float(initial_mass_edit), step=0.1,key="initial_mass")
burn_time = left_column.number_input("Burn Time [s]", min_value=0.0, value=float(burn_time_edit), step=0.1, key="burn_time")
reference_area = left_column.number_input("Reference area (Lift & Drag) [mm]", min_value=0.0, value=float(reference_area_edit), step=0.01, key="reference_area")

left_column.subheader("Inertia and Centre of Mass (CoM) Settings")
left_column.write("Inertia Before burning")
a, b, c = left_column.columns(3)

I_before_burn_x = a.number_input("X", min_value=0.0, value=float(I_after_burn_x_edit), step=0.01, key="I_before_burn_x")
I_before_burn_y = b.number_input("Y", min_value=0.0, value=float(I_before_burn_y_edit), step=0.01, key="I_before_burn_y")
I_before_burn_z = c.number_input("Z", min_value=0.0, value=float(I_before_burn_z_edit), step=0.01, key="I_before_burn_z")

left_column.write("Centre of Mass (CoM) Before burning")
d, e, f = left_column.columns(3)
CoM_before_burn_x = d.number_input("X", min_value=0.0, value=float(CoM_before_burn_x_edit), step=0.01, key="CoM_before_burn_x")
CoM_before_burn_y = e.number_input("Y", min_value=0.0, value=float(CoM_before_burn_y_edit), step=0.01, key="CoM_before_burn_y")
CoM_before_burn_z = f.number_input("Z", min_value=0.0, value=float(CoM_before_burn_z_edit), step=0.01, key="CoM_before_burn_z")

left_column.write("Inertia After burning")
g, h, i = left_column.columns(3)
I_after_burn_x = g.number_input("X", min_value=0.0, value=float(I_after_burn_x_edit), step=0.01, key="I_after_burn_x")
I_after_burn_y = h.number_input("Y", min_value=0.0, value=float(I_after_burn_y_edit), step=0.01, key="I_after_burn_y")
I_after_burn_z = i.number_input("Z", min_value=0.0, value=float(I_after_burn_z_edit), step=0.01, key="I_after_burn_z")

left_column.write("Centre of Mass (CoM) After burning")
j, k, l = left_column.columns(3)
CoM_after_burn_x = j.number_input("X", min_value=0.0, value=float(CoM_after_burn_x_edit), step=0.01, key="CoM_after_burn_x")
CoM_after_burn_y = k.number_input("Y", min_value=0.0, value=float(CoM_after_burn_y_edit), step=0.01, key="CoM_after_burn_y")
CoM_after_burn_z = l.number_input("Z", min_value=0.0, value=float(CoM_after_burn_z_edit), step=0.01, key="CoM_after_burn_z")

left_column.subheader("Engine Properties")
nozzle_exit_diameter= left_column.number_input("Nozzle Exit Diameter [mm]", min_value=0.0, value=float(nozzle_exit_diameter_edit), step=0.1, key="nozzle_exit_diameter")
mass_flux = left_column.number_input("Mass Flux ", min_value=0.0, value=float(mass_flux_edit), step=0.1, key="mass_flux")
gas_speed = left_column.number_input("Gas Speed", min_value=0.0, value=float(gas_speed_edit), step=0.1, key="gas_speed")
exit_pressure = left_column.number_input("Exit Pressure", min_value=0.0, value=float(exit_pressure_edit), step=0.1, key="exit_pressure")

middle_column.subheader("Rocket Geometry")
        # Add input fields for rocket performance metrics
len_warhead = middle_column.number_input('Length of warhead or distance from tip of nose to base of nose [mm]', min_value=0.0, value=float(len_warhead_edit), step=0.1, key="len_warhead")
len_nosecone_fins = middle_column.number_input('Length between nose cone tip and the point where the fin leading edge meets the body tube [mm]', min_value=0.0, value=float(len_nosecone_fins_edit), step=0.1, key="len_nosecone_fins")
len_nosecone_rear = middle_column.number_input('Length between nose tip to rear [mm]', min_value=0.0, value=float(len_nosecone_rear_edit), step=0.1, key="len_nosecone_rear")              
len_bodytube_wo_rear = middle_column.number_input('Length of body tube (not considering rear) [mm]', min_value=0.0, value=float(len_bodytube_wo_rear_edit), step=0.1, key="len_bodytube_wo_rear")
fins_chord_root = middle_column.number_input('Fins aerodynamic chord at root [mm]', min_value=0.0, value=float(fins_chord_root_edit), step=0.1, key="fins_chord_root")
fins_mid_chord = middle_column.number_input('Fins aerodynamic mid-chord [mm]', min_value=0.0, value=float(fins_mid_chord_edit), step=0.1, key="fins_mid_chord")
fins_chord_tip = middle_column.number_input('Fins aerodynamic chord at tip [mm]', min_value=0.0, value=float(fins_chord_tip_edit), step=0.1, key="fins_chord_tip")
len_rear = middle_column.number_input('Length of rear [mm]', min_value=0.0, value=float(len_rear_edit), step=0.1, key="len_rear")
fins_span = middle_column.number_input('Fins span [mm]', min_value=0.0, value=float(fins_span_edit), step=0.1, key="fins_span")
diameter_warhead_base = middle_column.number_input('Diameter of base of warhead [mm]', min_value=0.0, value=float(diameter_warhead_base_edit), step=0.1, key="diameter_warhead_base")
diameter_bodytube = middle_column.number_input('Diameter of body tube [mm]', min_value=0.0, value=float(diameter_bodytube_edit), step=0.1, key="diameter_bodytube")
diameter_bodytube_fins = middle_column.number_input('Diameter of body tube where fins are met [mm]', min_value=0.0, value=float(diameter_bodytube_fins_edit), step=0.1, key="diameter_bodytube_fins")
diameter_rear_bodytube = middle_column.number_input('Diameter of rear where it meets body tube [mm]', min_value=0.0, value=float(diameter_rear_bodytube_edit), step=0.1, key="diameter_rear_bodytube")
end_diam_rear =  middle_column.number_input('End diameter rear [mm]', min_value=0.0, value=float(end_diam_rear_edit), step=0.1, key="end_diam_rear")
N_fins = middle_column.number_input('Number of fins [-]', min_value=0, value=N_fins_edit, step=1, key="N_fins")
   
with right_column:
    right_column.subheader("Rocket Graphics")
    
    p = pv.Plotter(window_size=[300,500])
    #pv.set_plot_theme("#111111ff")  
    
    sphere = pv.Cylinder(
        center=(0, 0, 0),
        direction=(0, 1, 0),
        radius=diameter_bodytube_edit/2,
        height=len_bodytube_wo_rear_edit,
        resolution=30,
        capping=True
    )
    nosecone = pv.Cone(
        center=(0, len_bodytube_wo_rear_edit/2 + len_warhead_edit/2, 0),
        direction=(0, 1, 0),
        radius=diameter_warhead_base_edit/2,
        height=len_warhead_edit,
        resolution=30,
        capping=True
    )
    rear = pv.Cylinder(
        center=(0, -len_bodytube_wo_rear_edit/2 - len_rear_edit/2, 0),
        direction=(0, 1, 0),
        radius=end_diam_rear_edit/2,
        height=len_rear_edit,
        resolution=30,
        capping=True
    )
    # Create fins
    fins_points = np.array([
    [0.0, diameter_bodytube_edit/2, 0.0],  # 0
    [0.0, fins_chord_root_edit + diameter_bodytube_edit/2, 0.0],  # 1
    [fins_span_edit/2, fins_mid_chord_edit+ diameter_bodytube_edit/2, 0.0],  # 2
    [fins_span_edit, fins_chord_tip_edit+ diameter_bodytube_edit/2, 0.0],  # 2
    [fins_span_edit, diameter_bodytube_edit/2, 0.0],  # 3
    ])
    fins_array = []
    cell_type = np.array([pv.CellType.POLYGON], dtype=np.uint8)
    for i in range(N_fins_edit):
        angle = i * (360 / N_fins_edit)
        grid = pv.UnstructuredGrid(np.array([5, 0, 1, 2, 3, 4], dtype=np.int64), cell_type, fins_points)
        fins_array.append(grid.translate((diameter_bodytube_edit/2, len_bodytube_wo_rear_edit/2 + len_warhead_edit - 2* fins_span_edit - len_nosecone_fins_edit, 0)).rotate_y(angle, inplace=False))
    fins = pv.merge(fins_array)
    # Combine all parts into a single mesh
    rocket_mesh = sphere + nosecone + rear + fins
    # Add the rocket mesh to the plotter
    p.add_mesh(rocket_mesh, name='rocket', style='wireframe', color='white')
    p.set_background('#111111ff')
    p.view_isometric()
    stpyvista(p)

#right_column.line_chart(bodytube, x="x",y="y", use_container_width=True)

    # Add a submit button
submitted = rock_set.form_submit_button("Save Settings")
if submitted:
        st.success("Rocket settings saved!")
        new_rocket = {
            "name": rocket_name,
            "initial_mass": initial_mass,
            "reference_area": reference_area,
            "I_before_burn": {
                "x": I_before_burn_x,
                "y": I_before_burn_y,
                "z": I_before_burn_z
            },
            "CoM_before_burn": {
                "x": CoM_before_burn_x,
                "y": CoM_before_burn_y,
                "z": CoM_before_burn_z
            },
            "I_after_burn": {
                "x": I_after_burn_x,
                "y": I_after_burn_y,
                "z": I_after_burn_z
            },
            "CoM_after_burn": {
                "x": CoM_after_burn_x,
                "y": CoM_after_burn_y,
                "z": CoM_after_burn_z
            },
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
                "N_fins": N_fins
            }
        }
        # Save the new rocket settings to a JSON file
        #replace the existing rocket settings if the name already exists
        if rocket_name in rockets:
            st.warning(f"Rocket '{rocket_name}' already exists. It will be overwritten.")
            

        rockets[new_rocket["name"]] = new_rocket
        with open("rockets.json", "w") as file: 
            json.dump(rockets, file, indent=4)
        st.success(f"Rocket '{new_rocket['name']}' settings saved successfully!")
        # Optionally, you can clear the form fields after submission
        st.session_state.clear()
        
        #aca poner que se guarden los datos en un nested dictionary
