#create and edit rockets properties for the simulator
import streamlit as st
import json
import numpy as np
import pyvista as pv # type: ignore
from stpyvista import stpyvista # type: ignore
import os

def load_rocket_configs():
    """Carga todas las configuraciones de cohetes desde la nueva estructura"""
    rockets = {}
    configs_path = 'data/rockets/configs'
    
    try:
        for filename in os.listdir(configs_path):
            if filename.endswith('.json'):
                file_path = os.path.join(configs_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    rocket_data = json.load(f)
                    rockets[rocket_data["name"]] = rocket_data
        return rockets
    except FileNotFoundError:
        st.error(f"No se encontró el directorio {configs_path}")
        return {}
    except Exception as e:
        st.error(f"Error cargando configuraciones: {str(e)}")
        return {}

def save_rocket_config(rocket_data):
    """Guarda la configuración de un cohete en un archivo individual"""
    configs_path = 'data/rockets/configs'
    
    try:
        # Crear directorio si no existe
        os.makedirs(configs_path, exist_ok=True)
        
        # Generar nombre de archivo seguro
        safe_name = rocket_data["name"].lower().replace(" ", "_")
        file_path = os.path.join(configs_path, f"{safe_name}.json")
        
        # Guardar archivo
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(rocket_data, f, indent=4, ensure_ascii=False)
            
        return True, f"Cohete guardado en {file_path}"
    except Exception as e:
        return False, f"Error guardando cohete: {str(e)}"

def delete_rocket_config(rocket_name):
    """Elimina la configuración de un cohete"""
    configs_path = 'data/rockets/configs'
    safe_name = rocket_name.lower().replace(" ", "_")
    file_path = os.path.join(configs_path, f"{safe_name}.json")
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True, f"Cohete {rocket_name} eliminado"
        return False, "Archivo no encontrado"
    except Exception as e:
        return False, f"Error eliminando cohete: {str(e)}"

# Cargar configuraciones de cohetes
rockets = load_rocket_configs()

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
    len_warhead_edit = rocket_settings["nosecone"]["length"]
    nosecone_shape = rocket_settings["nosecone"]["shape"]
    len_nosecone_fins_edit = rocket_settings["geometry"]["length nosecone fins"]
    len_bodytube_wo_rear_edit = rocket_settings["fuselage"]["length"]
    fins_chord_root_edit = rocket_settings["fins"]["chord_root"]
    fins_mid_chord_edit = rocket_settings["fins"]["mid_chord"]
    fins_chord_tip_edit = rocket_settings["fins"]["chord_tip"]
    len_rear_edit = rocket_settings["rear_section"]["length"]
    fins_span_edit = rocket_settings["fins"]["span"]
    diameter_warhead_base_edit = rocket_settings["nosecone"]["diameter"]
    diameter_bodytube_edit = rocket_settings["fuselage"]["diameter"]
    end_diam_rear_edit =  rocket_settings["rear_section"]["diameter"]
    N_fins_edit =rocket_settings["fins"]["N_fins"]
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
    N_fins_edit = 0

bodytube = {
     "x": np.array([0,0,len_bodytube_wo_rear_edit,len_bodytube_wo_rear_edit,0]),
     "y": np.array([0,diameter_bodytube_edit,diameter_bodytube_edit,0,0]),

}
    
st.set_page_config(page_title="Rocket Settings", page_icon=":material/rocket:", layout="wide")
rock_set = st.form("Rocket Settings")
rock_set.title("Rocket Settings")
    
left_column, right_column = rock_set.columns([4, 2])

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = left_column.tabs(["Properties", "Engine", "Fuselage", "Fins", "Nosecone", "Rear Section", "Aerodynamics [soon]", "Others"])
        # Add input fields for rocket properties
rocket_name = tab1.text_input("Rocket Name", value=rocket_name_edit, key="rocket_name")
initial_mass = tab1.number_input("Initial Mass (kg)", min_value=0.0, value=float(initial_mass_edit), step=0.1,key="initial_mass")

reference_area = tab1.number_input("Reference area (Lift & Drag) [mm]", min_value=0.0, value=float(reference_area_edit), step=0.01, key="reference_area")

tab1.subheader("Inertia and Centre of Mass (CoM) Settings")
tab1.write("Inertia Before burning")
a, b, c = tab1.columns(3)

I_before_burn_x = a.number_input("X", min_value=0.0, value=float(I_after_burn_x_edit), step=0.01, key="I_before_burn_x")
I_before_burn_y = b.number_input("Y", min_value=0.0, value=float(I_before_burn_y_edit), step=0.01, key="I_before_burn_y")
I_before_burn_z = c.number_input("Z", min_value=0.0, value=float(I_before_burn_z_edit), step=0.01, key="I_before_burn_z")

tab1.write("Centre of Mass (CoM) Before burning")
d, e, f = tab1.columns(3)
CoM_before_burn_x = d.number_input("X", min_value=0.0, value=float(CoM_before_burn_x_edit), step=0.01, key="CoM_before_burn_x")
CoM_before_burn_y = e.number_input("Y", min_value=0.0, value=float(CoM_before_burn_y_edit), step=0.01, key="CoM_before_burn_y")
CoM_before_burn_z = f.number_input("Z", min_value=0.0, value=float(CoM_before_burn_z_edit), step=0.01, key="CoM_before_burn_z")

tab1.write("Inertia After burning")
g, h, i = tab1.columns(3)
I_after_burn_x = g.number_input("X", min_value=0.0, value=float(I_after_burn_x_edit), step=0.01, key="I_after_burn_x")
I_after_burn_y = h.number_input("Y", min_value=0.0, value=float(I_after_burn_y_edit), step=0.01, key="I_after_burn_y")
I_after_burn_z = i.number_input("Z", min_value=0.0, value=float(I_after_burn_z_edit), step=0.01, key="I_after_burn_z")

tab1.write("Centre of Mass (CoM) After burning")
j, k, l = tab1.columns(3)
CoM_after_burn_x = j.number_input("X", min_value=0.0, value=float(CoM_after_burn_x_edit), step=0.01, key="CoM_after_burn_x")
CoM_after_burn_y = k.number_input("Y", min_value=0.0, value=float(CoM_after_burn_y_edit), step=0.01, key="CoM_after_burn_y")
CoM_after_burn_z = l.number_input("Z", min_value=0.0, value=float(CoM_after_burn_z_edit), step=0.01, key="CoM_after_burn_z")

tab2.subheader("Engine Properties")
burn_time = tab2.number_input("Burn Time [s]", min_value=0.0, value=float(burn_time_edit), step=0.1, key="burn_time")
nozzle_exit_diameter= tab2.number_input("Nozzle Exit Diameter [mm]", min_value=0.0, value=float(nozzle_exit_diameter_edit), step=0.1, key="nozzle_exit_diameter")
mass_flux = tab2.number_input("Mass Flux ", min_value=0.0, value=float(mass_flux_edit), step=0.1, key="mass_flux")
gas_speed = tab2.number_input("Gas Speed", min_value=0.0, value=float(gas_speed_edit), step=0.1, key="gas_speed")
exit_pressure = tab2.number_input("Exit Pressure", min_value=0.0, value=float(exit_pressure_edit), step=0.1, key="exit_pressure")

tab4.subheader("Fins")
N_fins = tab4.number_input('Number of fins [-]', min_value=0, value=N_fins_edit, step=1, key="N_fins")
fins_chord_root = tab4.number_input('Fins aerodynamic chord at root [mm]', min_value=0.0, value=float(fins_chord_root_edit), step=0.1, key="fins_chord_root")
fins_mid_chord = tab4.number_input('Fins aerodynamic mid-chord [mm]', min_value=0.0, value=float(fins_mid_chord_edit), step=0.1, key="fins_mid_chord")
fins_chord_tip = tab4.number_input('Fins aerodynamic chord at tip [mm]', min_value=0.0, value=float(fins_chord_tip_edit), step=0.1, key="fins_chord_tip")
fins_span = tab4.number_input('Fins span [mm]', min_value=0.0, value=float(fins_span_edit), step=0.1, key="fins_span")
len_nosecone_fins = tab4.number_input('Length between nose cone tip and the point where the fin leading edge meets the body tube [mm]', min_value=0.0, value=float(len_nosecone_fins_edit), step=0.1, key="len_nosecone_fins")

tab5.subheader("Nosecone")
len_warhead = tab5.number_input('Length of warhead or distance from tip of nose to base of nose [mm]', min_value=0.0, value=float(len_warhead_edit), step=0.1, key="len_warhead")
diameter_warhead_base = tab5.number_input('Diameter of base of warhead [mm]', min_value=0.0, value=float(diameter_warhead_base_edit), step=0.1, key="diameter_warhead_base")
nosecone_shape = tab5.selectbox("Nosecone Shape", options=["Conical", "Elliptical", "Parabolic"], index=0, key="nosecone_shape")


tab3.subheader("Fuselage")
len_bodytube_wo_rear = tab3.number_input('Length of body tube (not considering rear) [mm]', min_value=0.0, value=float(len_bodytube_wo_rear_edit), step=0.1, key="len_bodytube_wo_rear")
diameter_bodytube = tab3.number_input('Diameter of body tube [mm]', min_value=0.0, value=float(diameter_bodytube_edit), step=0.1, key="diameter_bodytube")


tab6.subheader("Rear Section")
len_rear = tab6.number_input('Length of rear [mm]', min_value=0.0, value=float(len_rear_edit), step=0.1, key="len_rear")
end_diam_rear =  tab6.number_input('End diameter rear [mm]', min_value=0.0, value=float(end_diam_rear_edit), step=0.1, key="end_diam_rear")

tab8.write("Section in progress!")

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
        fins_array.append(grid.translate((diameter_bodytube_edit/2, len_bodytube_wo_rear_edit/2 + len_warhead_edit - fins_span_edit*1.33 - len_nosecone_fins_edit, 0)).rotate_y(angle, inplace=False))
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
                "length nosecone fins": len_nosecone_fins,
                "len_nosecone_rear": len_warhead + len_bodytube_wo_rear + len_rear,
            },
            "fins": {
                "span": fins_span,
                "chord_root": fins_chord_root,
                "chord_tip": fins_chord_tip,
                "mid_chord": fins_mid_chord,
                "N_fins": N_fins,
            },
            "nosecone": {
                "length": len_warhead,
                "diameter": diameter_warhead_base,
                "shape": nosecone_shape
            },
            "fuselage": {
                "length": len_bodytube_wo_rear,
                "diameter": diameter_bodytube
            },
            "rear_section": {
                "length": len_rear,
                "diameter": end_diam_rear
            }
        }
        # Save the new rocket settings to a JSON file
        #replace the existing rocket settings if the name already exists
        if rocket_name in rockets:
            st.warning(f"Rocket '{rocket_name}' already exists. It will be overwritten.")
            

        rockets[new_rocket["name"]] = new_rocket
        success, message = save_rocket_config(new_rocket)
        if success:
            st.success(f"Cohete '{new_rocket['name']}' guardado exitosamente!")
            st.rerun()  # Recargar la página
        else:
            st.error(message)
        
        # Optionally, you can clear the form fields after submission
        st.session_state.clear()
        
        #aca poner que se guarden los datos en un nested dictionary

# Agregar botón de eliminación
if sim_rocket != "Manual":
    if st.button("Eliminar Cohete"):
        success, message = delete_rocket_config(sim_rocket)
        if success:
            st.success(message)
            st.rerun()  # Recargar la página
        else:
            st.error(message)
