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
    # Nuevos parámetros del motor
    propellant_mass_edit = rocket_settings["engine"].get("propellant_mass", 0.0)
    specific_impulse_edit = rocket_settings["engine"].get("specific_impulse", 0.0)
    mean_thrust_edit = rocket_settings["engine"].get("mean_thrust", 0.0)
    max_thrust_edit = rocket_settings["engine"].get("max_thrust", 0.0)
    mean_chamber_pressure_edit = rocket_settings["engine"].get("mean_chamber_pressure", 0.0)
    max_chamber_pressure_edit = rocket_settings["engine"].get("max_chamber_pressure", 0.0)
    thrust_to_weight_ratio_edit = rocket_settings["engine"].get("thrust_to_weight_ratio", 0.0)
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
    propellant_mass_edit = 0.0
    specific_impulse_edit = 0.0
    mean_thrust_edit = 0.0
    max_thrust_edit = 0.0
    mean_chamber_pressure_edit = 0.0
    max_chamber_pressure_edit = 0.0
    thrust_to_weight_ratio_edit = 0.0
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

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = left_column.tabs(["Properties", "Engine", "Fuselage", "Fins", "Nosecone", "Rear Section", "Others"])
        # Add input fields for rocket properties
rocket_name = tab1.text_input("Rocket Name", value=rocket_name_edit, key="rocket_name")
initial_mass = tab1.number_input("Initial Mass (kg)", min_value=0.0, value=float(initial_mass_edit), step=0.1,key="initial_mass")

reference_area = tab1.number_input("Reference area (Lift & Drag) [mm^2]", min_value=0.0, value=float(reference_area_edit), step=0.01, key="reference_area")

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
nozzle_exit_diameter = tab2.number_input("Nozzle Exit Diameter [mm]", min_value=0.0, value=float(nozzle_exit_diameter_edit), step=0.1, key="nozzle_exit_diameter")
propellant_mass = tab2.number_input("Propellant Mass [kg]", min_value=0.0, value=float(propellant_mass_edit), step=0.1, key="propellant_mass")
specific_impulse = tab2.number_input("Specific Impulse [s]", min_value=0.0, value=float(specific_impulse_edit), step=0.1, key="specific_impulse")
mean_thrust = tab2.number_input("Mean Thrust [N]", min_value=0.0, value=float(mean_thrust_edit), step=0.1, key="mean_thrust")
max_thrust = tab2.number_input("Max Thrust [N]", min_value=0.0, value=float(max_thrust_edit), step=0.1, key="max_thrust")
mean_chamber_pressure = tab2.number_input("Mean Chamber Pressure [Pa]", min_value=0.0, value=float(mean_chamber_pressure_edit), step=0.1, key="mean_chamber_pressure")
max_chamber_pressure = tab2.number_input("Max Chamber Pressure [Pa]", min_value=0.0, value=float(max_chamber_pressure_edit), step=0.1, key="max_chamber_pressure")
thrust_to_weight_ratio = tab2.number_input("Thrust to Weight Ratio [-]", min_value=0.0, value=float(thrust_to_weight_ratio_edit), step=0.01, key="thrust_to_weight_ratio")
# ...campos legacy opcionales...

tab4.subheader("Fins")
# In the Fins tab section, replace the current fin inputs with

# Add fin type selection
fin_type = tab4.selectbox("Fin Type", 
                         options=["Trapezoidal", "Delta", "Tapered Swept", "Elliptical", "Custom"],
                         index=0, 
                         key="fin_type")

N_fins = tab4.number_input('Number of fins [-]', min_value=0, value=N_fins_edit, step=1, key="N_fins")

if fin_type == "Trapezoidal":
    fins_chord_root = tab4.number_input('Root chord [mm]', min_value=0.0, value=float(fins_chord_root_edit), step=0.1, key="fins_chord_root")
    fins_chord_tip = tab4.number_input('Tip chord [mm]', min_value=0.0, value=float(fins_chord_tip_edit), step=0.1, key="fins_chord_tip")
    fins_span = tab4.number_input('Span [mm]', min_value=0.0, value=float(fins_span_edit), step=0.1, key="fins_span")
    # Calculate mid-chord automatically for trapezoidal
    fins_mid_chord = (fins_chord_root + fins_chord_tip) / 2
    
elif fin_type == "Delta":
    fins_root_length = tab4.number_input('Root length [mm]', min_value=0.0, value=float(fins_chord_root_edit), step=0.1, key="fins_root_length")
    fins_span = tab4.number_input('Span [mm]', min_value=0.0, value=float(fins_span_edit), step=0.1, key="fins_span")
    sweep_angle = tab4.number_input('Sweep angle [deg]', min_value=0.0, max_value=80.0, value=45.0, step=1.0, key="sweep_angle")
    # Delta fins have tip chord = 0
    fins_chord_root = fins_root_length
    fins_chord_tip = 0.0
    fins_mid_chord = fins_root_length / 2
    
elif fin_type == "Tapered Swept":
    fins_chord_root = tab4.number_input('Root chord [mm]', min_value=0.0, value=float(fins_chord_root_edit), step=0.1, key="fins_chord_root")
    fins_chord_tip = tab4.number_input('Tip chord [mm]', min_value=0.0, value=float(fins_chord_tip_edit), step=0.1, key="fins_chord_tip")
    fins_span = tab4.number_input('Span [mm]', min_value=0.0, value=float(fins_span_edit), step=0.1, key="fins_span")
    sweep_angle = tab4.number_input('Sweep angle [deg]', min_value=0.0, max_value=80.0, value=30.0, step=1.0, key="sweep_angle")
    fins_mid_chord = (fins_chord_root + fins_chord_tip) / 2
    
elif fin_type == "Elliptical":
    fins_chord_root = tab4.number_input('Root chord [mm]', min_value=0.0, value=float(fins_chord_root_edit), step=0.1, key="fins_chord_root")
    fins_span = tab4.number_input('Span [mm]', min_value=0.0, value=float(fins_span_edit), step=0.1, key="fins_span")
    # Elliptical fins have specific shape
    fins_chord_tip = 0.0
    fins_mid_chord = fins_chord_root * 0.707  # Approximation for elliptical mean chord

elif fin_type == "Custom":
    fins_chord_root = tab4.number_input('Root chord [mm]', min_value=0.0, value=float(fins_chord_root_edit), step=0.1, key="fins_chord_root")
    fins_chord_tip = tab4.number_input('Tip chord [mm]', min_value=0.0, value=float(fins_chord_tip_edit), step=0.1, key="fins_chord_tip")
    fins_mid_chord = tab4.number_input('Mid chord [mm]', min_value=0.0, value=float(fins_mid_chord_edit), step=0.1, key="fins_mid_chord")
    fins_span = tab4.number_input('Span [mm]', min_value=0.0, value=float(fins_span_edit), step=0.1, key="fins_span")

len_nosecone_fins = tab4.number_input('Length between nose cone tip and fin leading edge [mm]', min_value=0.0, value=float(len_nosecone_fins_edit), step=0.1, key="len_nosecone_fins")

tab5.subheader("Nosecone")

nosecone_type = tab5.selectbox("Nosecone Type", 
                              options=["Conical", "Ogival", "Elliptical", "Parabolic", "Power Series", "Von Kármán", "Haack Series"],
                              index=0, 
                              key="nosecone_type")

len_warhead = tab5.number_input('Length of nosecone [mm]', min_value=0.0, value=float(len_warhead_edit), step=0.1, key="len_warhead")
diameter_warhead_base = tab5.number_input('Base diameter [mm]', min_value=0.0, value=float(diameter_warhead_base_edit), step=0.1, key="diameter_warhead_base")

# Type-specific parameters
if nosecone_type == "Conical":
    # No additional parameters needed for conical
    pass
    
elif nosecone_type == "Ogival":
    ogive_radius = tab5.number_input('Ogive radius [mm]', min_value=0.0, 
                                   value=float(diameter_warhead_base_edit * 2), 
                                   step=1.0, key="ogive_radius")
    
elif nosecone_type == "Elliptical":
    # No additional parameters needed
    pass
    
elif nosecone_type == "Parabolic":
    parabolic_parameter = tab5.number_input('Parabolic parameter (0-1)', min_value=0.0, max_value=1.0, 
                                          value=0.5, step=0.1, key="parabolic_parameter")
    
elif nosecone_type == "Power Series":
    power_value = tab5.number_input('Power value (n)', min_value=0.0, max_value=1.0, 
                                  value=0.5, step=0.1, key="power_value")
    
elif nosecone_type == "Von Kármán":
    # No additional parameters needed
    pass
    
elif nosecone_type == "Haack Series":
    haack_type = tab5.selectbox("Haack Type", options=["LV-Haack", "LD-Haack"], index=0, key="haack_type")

tab3.subheader("Fuselage")
len_bodytube_wo_rear = tab3.number_input('Length of body tube (not considering rear) [mm]', min_value=0.0, value=float(len_bodytube_wo_rear_edit), step=0.1, key="len_bodytube_wo_rear")
diameter_bodytube = tab3.number_input('Diameter of body tube [mm]', min_value=0.0, value=float(diameter_bodytube_edit), step=0.1, key="diameter_bodytube")


tab6.subheader("Rear Section")
len_rear = tab6.number_input('Length of rear [mm]', min_value=0.0, value=float(len_rear_edit), step=0.1, key="len_rear")
end_diam_rear =  tab6.number_input('End diameter rear [mm]', min_value=0.0, value=float(end_diam_rear_edit), step=0.1, key="end_diam_rear")


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
    
    # Create nosecone based on type
    nosecone_length = len_warhead_edit
    nosecone_radius = diameter_warhead_base_edit / 2

    if nosecone_type == "Conical":
        nosecone = pv.Cone(
            center=(0, len_bodytube_wo_rear_edit/2 + nosecone_length/2, 0),
            direction=(0, 1, 0),
            radius=nosecone_radius,
            height=nosecone_length,
            resolution=30,
            capping=True
        )
        
    elif nosecone_type == "Ogival":
        # Ogive nosecone - create by revolving a circular arc
        ogive_radius_val = ogive_radius if 'ogive_radius' in locals() else nosecone_radius * 3
        theta = np.linspace(0, np.pi/2, 20)
        x_points = ogive_radius_val * np.sin(theta) - ogive_radius_val + nosecone_length
        y_points = ogive_radius_val * np.cos(theta)
        # Filter points to only include those within length
        mask = x_points >= 0
        x_points = x_points[mask]
        y_points = y_points[mask]
        # Create revolution
        nosecone = pv.Line((0, 0, 0), (0, nosecone_length, 0)).revolve(
            resolution=30,
            point=(0, 0, 0),
            direction=(1, 0, 0)
        )
        # Scale to correct dimensions (simplified approach)
        nosecone = pv.Cone(
            center=(0, len_bodytube_wo_rear_edit/2 + nosecone_length/2, 0),
            direction=(0, 1, 0),
            radius=nosecone_radius,
            height=nosecone_length,
            resolution=30
        )
        
    elif nosecone_type == "Elliptical":
        # Elliptical nosecone
        nosecone = pv.ParametricEllipsoid(
            nosecone_radius, nosecone_radius, nosecone_length/2
        ).translate((0, len_bodytube_wo_rear_edit/2 + nosecone_length/2, 0))
        
    elif nosecone_type == "Parabolic":
        # Parabolic nosecone - create from parametric surface
        u = np.linspace(0, nosecone_length, 20)
        v = np.linspace(0, 2*np.pi, 30)
        U, V = np.meshgrid(u, v)
        parabolic_param = parabolic_parameter if 'parabolic_parameter' in locals() else 0.5
        R = nosecone_radius * (U / nosecone_length)
        Z = U
        # Parabolic profile: r = R * (1 - (z/L)^k)
        k = parabolic_param
        radius_profile = R * (1 - (Z/nosecone_length)**k)
        X = radius_profile * np.cos(V)
        Y = len_bodytube_wo_rear_edit/2 + Z
        Z_coord = radius_profile * np.sin(V)
        nosecone = pv.StructuredGrid(X, Y, Z_coord)
        
    else:  # Default to conical for other types
        nosecone = pv.Cone(
            center=(0, len_bodytube_wo_rear_edit/2 + nosecone_length/2, 0),
            direction=(0, 1, 0),
            radius=nosecone_radius,
            height=nosecone_length,
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
    # Create fins based on type
    fins_array = []
    if fin_type == "Trapezoidal":
        fins_points = np.array([
            [0.0, diameter_bodytube_edit/2, 0.0],
            [0.0, fins_chord_root + diameter_bodytube_edit/2, 0.0],
            [fins_span, fins_chord_tip + diameter_bodytube_edit/2, 0.0],
            [fins_span, diameter_bodytube_edit/2, 0.0],
        ])
        
    elif fin_type == "Delta":
        fins_points = np.array([
            [0.0, diameter_bodytube_edit/2, 0.0],
            [0.0, fins_chord_root + diameter_bodytube_edit/2, 0.0],
            [fins_span, diameter_bodytube_edit/2, 0.0],
        ])
        
    elif fin_type == "Tapered Swept":
        sweep_offset = fins_span * np.tan(np.radians(sweep_angle))
        fins_points = np.array([
            [0.0, diameter_bodytube_edit/2, 0.0],
            [0.0, fins_chord_root + diameter_bodytube_edit/2, 0.0],
            [fins_span, fins_chord_tip + diameter_bodytube_edit/2 + sweep_offset, 0.0],
            [fins_span, diameter_bodytube_edit/2 + sweep_offset, 0.0],
        ])
        
    elif fin_type == "Elliptical":
        # Create elliptical shape using multiple points
        theta = np.linspace(0, np.pi, 8)
        x_points = fins_span * np.sin(theta)
        y_points = diameter_bodytube_edit/2 + fins_chord_root * np.cos(theta)
        fins_points = np.column_stack([x_points, y_points, np.zeros_like(x_points)])
        
    else:  # Custom or fallback to trapezoidal
        fins_points = np.array([
            [0.0, diameter_bodytube_edit/2, 0.0],
            [0.0, fins_chord_root + diameter_bodytube_edit/2, 0.0],
            [fins_span/2, fins_mid_chord + diameter_bodytube_edit/2, 0.0],
            [fins_span, fins_chord_tip + diameter_bodytube_edit/2, 0.0],
            [fins_span, diameter_bodytube_edit/2, 0.0],
        ])

    cell_type = np.array([pv.CellType.POLYGON], dtype=np.uint8)
    for i in range(N_fins_edit):
        angle = i * (360 / N_fins_edit)
        if fin_type == "Elliptical":
            grid = pv.PolyData(fins_points)
            grid = grid.triangulate()  # Convert to triangles for elliptical shape
        else:
            grid = pv.UnstructuredGrid(
                np.array([len(fins_points)] + list(range(len(fins_points)))), 
                cell_type, 
                fins_points
            )
    fins_array.append(grid.translate((diameter_bodytube_edit/2, len_bodytube_wo_rear_edit/2 + len_warhead_edit - fins_span*1.33 - len_nosecone_fins_edit, 0)).rotate_y(angle, inplace=False))
    # Combine all parts into a single mesh
    rocket_mesh = sphere + nosecone + rear + fins_array
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
                "propellant_mass": propellant_mass,
                "specific_impulse": specific_impulse,
                "mean_thrust": mean_thrust,
                "max_thrust": max_thrust,
                "mean_chamber_pressure": mean_chamber_pressure,
                "max_chamber_pressure": max_chamber_pressure,
                "thrust_to_weight_ratio": thrust_to_weight_ratio,
            },
            "geometry": {
                "length nosecone fins": len_nosecone_fins,
                "len_nosecone_rear": len_warhead + len_bodytube_wo_rear + len_rear,
            },
            "fins": {
                "fin_type": fin_type,
                "span": fins_span,
                "chord_root": fins_chord_root,
                "chord_tip": fins_chord_tip,
                "mid_chord": fins_mid_chord,
                "N_fins": N_fins,
                "sweep_angle": sweep_angle if fin_type in ["Delta", "Tapered Swept"] else 0.0
            },
            "nosecone": {
                "type": nosecone_type,
                "length": len_warhead,
                "diameter": diameter_warhead_base,
                "ogive_radius": ogive_radius if nosecone_type == "Ogival" else 0.0,
                "parabolic_parameter": parabolic_parameter if nosecone_type == "Parabolic" else 0.5,
                "power_value": power_value if nosecone_type == "Power Series" else 0.5,
                "haack_type": haack_type if nosecone_type == "Haack Series" else "LV-Haack"
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
