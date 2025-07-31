import streamlit as st
from Clock import Clock
from Planet import Planet
from Atmosphere import Atmosphere
from Rocket import Rocket
from math import pi
import numpy as np
import datetime
import MatTools as Mat
import json
import pandas as pd
import pytz
import logging



st.set_page_config(page_title="Rocket Simulator Settings", layout="wide")

def load_json_file(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        st.error(f"Error: {filename} no encontrado")
        return {}
    except json.JSONDecodeError:
        st.error(f"Error: {filename} tiene un formato inválido")
        return {}

rocket_settings = load_json_file('rockets.json')
location_settings = load_json_file('locations.json')

timezone_dict = {
        "United States": "America/New_York",
        "Canada": "America/Toronto",
        "Mexico": "America/Mexico_City",
        "Jamaica": "America/Jamaica",
        "Costa Rica": "America/Costa_Rica",
        "Bahamas": "America/Nassau",
        "Honduras": "America/Tegucigalpa",
        "Cuba": "America/Havana",
        "Dominican Republic": "America/Santo_Domingo",
        "Brazil": "America/Sao_Paulo",
        "Argentina": "America/Argentina/Buenos_Aires",
        "Chile": "America/Santiago",
        "Colombia": "America/Bogota",
        "Peru": "America/Lima",
        "Uruguay": "America/Montevideo",
        "Ecuador": "America/Guayaquil",
        "Bolivia": "America/La_Paz",
        "Paraguay": "America/Asuncion",
        "Venezuela": "America/Caracas",
        "United Kingdom": "Europe/London",
        "France": "Europe/Paris",
        "Germany": "Europe/Berlin",
        "Italy": "Europe/Rome",
        "Spain": "Europe/Madrid",
        "Russia": "Europe/Moscow",
        "Turkey": "Europe/Istanbul",
        "Greece": "Europe/Athens",
        "Poland": "Europe/Warsaw",
        "Ukraine": "Europe/Kiev",
        "India": "Asia/Kolkata",
        "Japan": "Asia/Tokyo",
        "China": "Asia/Shanghai",
        "Saudi Arabia": "Asia/Riyadh",
        "South Korea": "Asia/Seoul",
        "Indonesia": "Asia/Jakarta",
        "Malaysia": "Asia/Kuala_Lumpur",
        "Vietnam": "Asia/Ho_Chi_Minh",
        "Philippines": "Asia/Manila",
        "Thailand": "Asia/Bangkok",
        "Australia": "Australia/Sydney",
        "New Zealand": "Pacific/Auckland",
        "Fiji": "Pacific/Fiji",
        "Papua New Guinea": "Pacific/Port_Moresby",
        "Samoa": "Pacific/Apia",
        "Tonga": "Pacific/Tongatapu",
        "Solomon Islands": "Pacific/Guadalcanal",
        "Vanuatu": "Pacific/Efate",
        "Kiribati": "Pacific/Tarawa",
        "New Caledonia": "Pacific/Noumea"
}
options = list(timezone_dict.keys())
default_index = options.index("Chile")

# Main header
st.header('Rocket Simulation Settings')
st.write("Configure the simulation settings for your rocket launch. You can select the rocket, location, and various simulation parameters."
         " Once you have set the parameters, click 'Run Simulation' to start the simulation."
         " The simulation will run based on the provided settings and will display the results in a table format.")
st.write("Code written by Orozco 2022. GUI done by Sepúlveda 2025.")

# Add some blank space
st.markdown("##")

# Create and edit rockets properties for the simulator
with st.form("Simulation Settings"):

    left_column, right_column = st.columns(2)
    sim_runtime = st.slider('Simulation runtime [s]', min_value=0, max_value=1000, value=600, step=10, key="sim_runtime")
    with left_column:
        #info
        st.subheader("Simulation Properties")
        sim_time_step = st.number_input('Simulation time step [s]', min_value=0.000, max_value=10.000, value=0.001, step=0.001, key="sim_time_step")
        sim_date = st.date_input('Simulation date', min_value=None, max_value=None, key="sim_date")
        sim_time = st.time_input('Simulation time', key="sim_time")
        sim_timezone = st.selectbox('Simulation timezone', options=options, index=default_index, key="sim_timezone")
        conditions = st.pills("Conditions for simulation", ["Detonation","Parachute [Coming soon]", "Second Stage [Coming Soon]"], key="conditions")
        

    with right_column:
        #info
        st.subheader("Simulation Settings")
        sim_rocket = st.selectbox('Rocket Selection', options=list(rocket_settings.keys()), index=0, key="sim_rocket")
        sim_location = st.selectbox('Location Selection', options=list(location_settings.keys()), index=1, key="sim_location")
        average_temperature = st.number_input('Average temperature [°C]', min_value=-50.0, max_value=50.0, value=20.0, step=1.0, key="average_temperature")
        launch_elevation = st.number_input('Launch elevation [°]', min_value=0.0, max_value=180.0, value=60.0, step=1.0, key="launch_elevation")
        launch_site_orientation = st.number_input('Launch site orientation (from the East) [°]', min_value=-180.0, max_value=180.0, value=20.0, step=1.0, key="launch_site_orientation")
        average_pressure = st.number_input('Average pressure [Pa]', min_value=0.0, max_value=1000000.0, value=101325.0, step=1.0, key="average_pressure")
        
        #average_humidity = st.number_input('Average humidity [%]', min_value=0.0, max_value=100.0, value=50.0, step=1.0, key="average_humidity")
    # Add a submit button
    
    
    run = st.form_submit_button("Run Simulation")
    if run:

        st.info("Running!")
        # loading json file for location and rocket settings
        # (This part should be replaced with actual loading of the JSON file)

        # Extracting the initial mass from the rocket settings
        initial_mass = rocket_settings[sim_rocket]['initial_mass']
        # Extracting the coordinates from the location settings
        Latitude = location_settings[sim_location]['latitude']
        Longitude = location_settings[sim_location]['longitude']
        Altitude = location_settings[sim_location]['altitude']
        
        # Auxiliary functions
        deg2rad=pi/180
        rad2deg=180/pi

        # Convert the simulation date and time to a timezone-aware datetime object
        sim_datetime = datetime.datetime.combine(sim_date, sim_time)
        sim_datetime = sim_datetime.replace(tzinfo=pytz.timezone(timezone_dict[sim_timezone]))


        # ------ Configuration of time simulation related data ------ #
        Start=0                     # [s]  # Starting time of simulation
        Steps_num=int(sim_runtime/sim_time_step)                 
        Steps=np.linspace(Start,sim_runtime,Steps_num)
        #st.write(f"Simulation steps: {Steps_num} with time step: {sim_time_step:.3f} s. {Steps}")

        # ___________________ Initial data to be INPUT ________________ #  # (All of this should to be obtained from external file!!!)
        East=0        # [m]   # X axis initial location of rocket from platform
        North=0       # [m]   # Y axis initial location of rocket from platform
        Up=1.0        # [m]   # Z axis initial location of rocket from platform  (do not set at 0...this is in order to used a conditional later on for max. alt and range)

        Vel_east=0    # [m/s]   # X axis initial velocity of rocket from platform
        Vel_north=0   # [m/s]   # Y axis initial velocity of rocket from platform
        Vel_up=0      # [m/s]   # Z axis initial velocity of rocket from platform

        Roll=0        # [deg]   # From initial position (between -180 and 180). Assumed to be always zero

        W_yaw=0       # [rad/s]   # X axis initial rotational velocity of rocket from platform
        W_pitch=0     # [rad/s]   # Y axis initial rotational velocity of rocket from platform
        W_roll=0      # [rad/s]   # Z axis initial rotational velocity of rocket from platform

        Max_altitude=1000000     # [m] # Max. altitude
        Max_range=1250000        # [m] # Max. range
        Detonate_altitude=900
        
        if conditions and "Detonation" in conditions:
            Detonate=True
            
        else:           # Statement for detonation or not
            Detonate=False          # Statement for detonation or not
         # [m] # Altitude for detonation

        # ___________________ Initialization of data ________________ #
        date=[sim_datetime.year, sim_datetime.month, sim_datetime.day, sim_datetime.hour, sim_datetime.minute, sim_datetime.second]                # List containing date
        julian_date=Clock().julian_day(date)                         # Obtaining Julian Date
        gmst_0=Clock().gmst(julian_date,1)                           # Initial Greenwich Mean Sidereal Time [rad]

        r_enu_0=np.array([East,North,Up])                            # [m]   # Initial East-North-Up location from platform
        v_enu_0=np.array([Vel_east,Vel_north,Vel_up])                # [m/s] # Initial East-North-Up velocity from platform

        # Primero creamos los cuaterniones individuales para cada rotación
        q_roll = np.array([
            np.sin(Roll*0.5*deg2rad),
            0,
            0,
            np.cos(Roll*0.5*deg2rad)
        ])

        q_pitch = np.array([
            0,
            np.sin(-launch_elevation*0.5*deg2rad),  # Removido el signo negativo
            0,
            np.cos(-launch_elevation*0.5*deg2rad)
        ])

        q_yaw = np.array([
            0,
            0,
            np.sin(launch_site_orientation*0.5*deg2rad),
            np.cos(launch_site_orientation*0.5*deg2rad)
        ])

        # Aplicamos las rotaciones en el orden correcto: roll → pitch → yaw
        q_temp = Mat.hamilton(q_pitch, q_roll)  # Primero roll, luego pitch
        q_enu2b_0 = Mat.hamilton(q_yaw, q_temp)  # Finalmente yaw

        w_enu_0=np.array([W_yaw,W_pitch,W_roll])                     # [rad/s] # Initial rotational velocity in East-North-Up

        coordinates=np.array([Latitude, Longitude, Altitude])  # [rad, rad, m] # Initial coordinates of the platform

        # _________________ Objects creation ___________________ #
        Earth=Planet(gmst_0)                                       # Planet module object creation
        Environment=Atmosphere(average_temperature)                        # Atmosphere module object creation
        Sistema=Rocket(r_enu_0,v_enu_0,q_enu2b_0,w_enu_0, initial_mass)          # Rocket module object creation

        # Auxiliary timer for conditionals loop break
        Time=[]       
        t=Start

        # ________________ Simulation sequence _________________#
        for i in range(len(Steps)):
            #st.write(f"Simulation time: {t:.4f} s")

            # Planet Greenwich Mean Sidereal Time updating
            Earth.update(sim_time_step)
            # Rocket's sequence of simulation
            Sistema.update_gmst(Earth.gmst)
            Sistema.update_mass_related(rocket_settings[sim_rocket]['engine']['burn_time'], rocket_settings[sim_rocket]["CoM_before_burn"]["x"], rocket_settings[sim_rocket]["CoM_before_burn"]["y"], rocket_settings[sim_rocket]["CoM_before_burn"]["z"], rocket_settings[sim_rocket]["I_before_burn"]["x"], rocket_settings[sim_rocket]["I_before_burn"]["y"], rocket_settings[sim_rocket]["I_before_burn"]["z"], rocket_settings[sim_rocket]["CoM_after_burn"]["x"], rocket_settings[sim_rocket]["CoM_after_burn"]["y"], rocket_settings[sim_rocket]["CoM_after_burn"]["z"], rocket_settings[sim_rocket]["I_after_burn"]["x"], rocket_settings[sim_rocket]["I_after_burn"]["y"], rocket_settings[sim_rocket]["I_after_burn"]["z"])  # [s]    # Propellant total burning time
            Sistema.update_pos_vel(coordinates)
            Sistema.update_atmosphere(Environment.give_dens(Sistema.r_enu[2]),Environment.give_press(Sistema.r_enu[2]),Environment.give_v_sonic(Sistema.r_enu[2]))    
            Sistema.update_aerodynamics(sim_rocket)
            Sistema.update_forces_aero(reference_area=rocket_settings[sim_rocket]['reference_area'])
            Sistema.update_engine(sim_rocket)
            Sistema.update_forces_engine()
            Sistema.update_forces_torques()
            Sistema.update_g_accel(coordinates)
            Sistema.RK4_update(sim_time_step)
            Sistema.save_data()

            if Sistema.time>=1:
                if Sistema.r_enu[2]<Sistema.hist_up[-2] and Sistema.r_enu[2]<Detonate_altitude and Detonate==True:
                    st.warning(f"Rocket has reached the detonation altitude of {Detonate_altitude} m at time {Sistema.time:.2f} s. Simulation will stop.")
                    break
    
            # Conditional to stop when reached
            if (Sistema.r_enu[2]<=0 or 
                Sistema.r_enu[2]>=Max_altitude or 
                Sistema.range>= Max_range or
                np.isnan(Sistema.r_enu[2]) or  # Detectar valores NaN
                abs(Sistema.v_enu[2]) > 1e4):  # Detectar velocidades irreales
                st.warning("Simulation stopped due to physical limits or numerical instability")
                break

            Time.append(t)
            t+=sim_time_step

            # Rocket's updating of simulation time
            Sistema.update_time(sim_time_step)

            if i % 100 == 0:  # Log cada 100 pasos
                logging.debug(f"t={t:.3f}s, h={Sistema.r_enu[2]:.2f}m, v={Sistema.v_norm:.2f}m/s")
        
            # Verificar estabilidad numérica
            if np.any(np.isnan(Sistema.r_enu)) or np.any(np.isnan(Sistema.v_enu)):
                raise RuntimeError("Numerical instability detected")
            

        st.success("Finished!")
        
        # Primero, definimos una función auxiliar mejorada para preparar los datos
        def prepare_data_for_storage(data):
            """
            Prepara los datos para almacenamiento, convirtiendo arrays y objetos complejos a formato serializable
            """
            if isinstance(data, np.ndarray):
                if data.ndim == 0:  # Si es un array escalar
                    return float(data)  # Convertir a float
                if data.ndim > 1:
                    return [prepare_data_for_storage(row) for row in data]
                return list(data)
            if isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], np.ndarray):
                    return [prepare_data_for_storage(item) for item in data]
                return data
            return data

        try:
            # Obtener la longitud de los datos de simulación
            sim_length = len(Sistema.hist_time)
            
            # Modificar cómo se manejan los componentes del cuaternión
            df_data = {
                # Replicar valores escalares
                "Rocket name": [sim_rocket] * sim_length,
                "Location name": [sim_location] * sim_length,
                "Location Latitude": [float(Latitude)] * sim_length,
                "Location Longitude": [float(Longitude)] * sim_length,
                
                # Datos de la simulación, coordenadas y velocidad
                "Simulation time": prepare_data_for_storage(np.array(Sistema.hist_time)),
                "Greenwich Mean Sidereal Time": prepare_data_for_storage(np.array(Sistema.hist_gmst)),
                "Range": prepare_data_for_storage(np.array(Sistema.hist_range)),
                "East coordinate": prepare_data_for_storage(np.array(Sistema.hist_east)),
                "North coordinate": prepare_data_for_storage(np.array(Sistema.hist_north)),
                "Up coordinate": prepare_data_for_storage(np.array(Sistema.hist_up)),
                "Velocity norm": prepare_data_for_storage(np.array(Sistema.hist_v_norm)),
                "Latitude": prepare_data_for_storage(np.array(Sistema.hist_lat)),
                "Longitude": prepare_data_for_storage(np.array(Sistema.hist_long)),
                "Altitude": prepare_data_for_storage(np.array(Sistema.hist_alt)),
                "East-North-Up location from platform": prepare_data_for_storage(Sistema.hist_r_enu),
                "East-North-Up velocity from platform": prepare_data_for_storage(Sistema.hist_v_enu),
                "Pitch Angle": prepare_data_for_storage(np.array(Sistema.hist_pitch)),
                "Yaw Angle": prepare_data_for_storage(np.array(Sistema.hist_yaw)),
                "Roll Angle": prepare_data_for_storage(np.array(Sistema.hist_roll)),
                "Angle of attack": prepare_data_for_storage(np.array(Sistema.hist_alpha)),
                "v_bx": prepare_data_for_storage(np.array(Sistema.hist_v_bx)),
                "v_by": prepare_data_for_storage(np.array(Sistema.hist_v_by)),
                "v_bz": prepare_data_for_storage(np.array(Sistema.hist_v_bz)),
                "Rotational velocity in East-North-Up": prepare_data_for_storage(np.array(Sistema.hist_w_enu)),
                
                # Atmosfera
                "Density of the atmosphere": prepare_data_for_storage(np.array(Sistema.hist_density)),
                "Ambient pressure": prepare_data_for_storage(np.array(Sistema.hist_press_amb)),
                "Speed of sound": prepare_data_for_storage(np.array(Sistema.hist_v_sonic)),
                "Mach number": prepare_data_for_storage(np.array(Sistema.hist_mach)),

                # Fuerzas y torques
                "Mass of the rocket": prepare_data_for_storage(np.array(Sistema.hist_mass)),
                "Drag coefficient": prepare_data_for_storage(np.array(Sistema.hist_drag_coeff)),
                "Lift coefficient": prepare_data_for_storage(np.array(Sistema.hist_lift_coeff)),
                "Thrust": prepare_data_for_storage(np.array(Sistema.hist_thrust)),
                "Inertia matrix in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_inertia_b)),
                "Center of mass in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_cm_b)),
                "Center of pressure in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_cp_b)),
                "Mass flux": prepare_data_for_storage(np.array(Sistema.hist_mass_flux)),
                "Drag force in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_drag)),
                "Lift force in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_lift)),
                "Center of mass to center of pressure in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_cm2cp_b)),
                "Aerodynamic forces in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_forces_aero_b)),
                "Aerodynamic torques in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_torques_aero_b)),
                "Engine forces in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_forces_engine_b)),
                "Engine torques in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_torques_engine_b)),
                "Acceleration in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_accel_b)),
                
                
                # Separar los componentes del cuaternión en columnas individuales
                "Quaternion_1": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_1)),
                "Quaternion_2": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_2)),
                "Quaternion_3": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_3)),
                "Quaternion_4": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_4)),
            }

            # Asegurarse de que todas las listas tengan la misma longitud
            min_length = min(len(Sistema.hist_time), len(Sistema.hist_range), len(Sistema.hist_east),
                            len(Sistema.hist_north), len(Sistema.hist_up), len(Sistema.hist_v_norm),
                            len(Sistema.hist_lat), len(Sistema.hist_long), len(Sistema.hist_alt),
                            len(Sistema.hist_cm2cp_b), len(Sistema.hist_forces_aero_b),
                            len(Sistema.hist_torques_aero_b), len(Sistema.hist_forces_engine_b),
                            len(Sistema.hist_torques_engine_b))

            # Truncar todas las listas a la longitud mínima
            df_data = {
                "Rocket name": [sim_rocket] * min_length,
                "Location name": [sim_location] * min_length,
                "Location Latitude": [float(Latitude)] * min_length,
                "Location Longitude": [float(Longitude)] * min_length,
                # Datos de la simulación, coordenadas y velocidad
                "Simulation time": prepare_data_for_storage(np.array(Sistema.hist_time[:min_length])),
                "Greenwich Mean Sidereal Time": prepare_data_for_storage(np.array(Sistema.hist_gmst[:min_length])),
                "Range": prepare_data_for_storage(np.array(Sistema.hist_range[:min_length])),
                "East coordinate": prepare_data_for_storage(np.array(Sistema.hist_east[:min_length])),
                "North coordinate": prepare_data_for_storage(np.array(Sistema.hist_north[:min_length])),
                "Up coordinate": prepare_data_for_storage(np.array(Sistema.hist_up[:min_length])),
                "Velocity norm": prepare_data_for_storage(np.array(Sistema.hist_v_norm[:min_length])),
                "Latitude": prepare_data_for_storage(np.array(Sistema.hist_lat[:min_length])),
                "Longitude": prepare_data_for_storage(np.array(Sistema.hist_long[:min_length])),
                "Altitude": prepare_data_for_storage(np.array(Sistema.hist_alt[:min_length])),
                "East-North-Up location from platform": prepare_data_for_storage(Sistema.hist_r_enu[:min_length]),
                "East-North-Up velocity from platform": prepare_data_for_storage(Sistema.hist_v_enu[:min_length]),
                "Pitch Angle": prepare_data_for_storage(np.array(Sistema.hist_pitch[:min_length])),
                "Yaw Angle": prepare_data_for_storage(np.array(Sistema.hist_yaw[:min_length])),
                "Roll Angle": prepare_data_for_storage(np.array(Sistema.hist_roll[:min_length])),
                "Angle of attack": prepare_data_for_storage(np.array(Sistema.hist_alpha[:min_length])),
                "v_bx": prepare_data_for_storage(np.array(Sistema.hist_v_bx[:min_length])),
                "v_by": prepare_data_for_storage(np.array(Sistema.hist_v_by[:min_length])),
                "v_bz": prepare_data_for_storage(np.array(Sistema.hist_v_bz[:min_length])),
                "Rotational velocity in East-North-Up": prepare_data_for_storage(np.array(Sistema.hist_w_enu[:min_length])),
                
                # Atmosfera
                "Density of the atmosphere": prepare_data_for_storage(np.array(Sistema.hist_density[:min_length])),
                "Ambient pressure": prepare_data_for_storage(np.array(Sistema.hist_press_amb[:min_length])),
                "Speed of sound": prepare_data_for_storage(np.array(Sistema.hist_v_sonic[:min_length])),
                "Mach number": prepare_data_for_storage(np.array(Sistema.hist_mach[:min_length])),

                # Fuerzas y torques
                "Mass of the rocket": prepare_data_for_storage(np.array(Sistema.hist_mass[:min_length])),
                "Drag coefficient": prepare_data_for_storage(np.array(Sistema.hist_drag_coeff[:min_length])),
                "Lift coefficient": prepare_data_for_storage(np.array(Sistema.hist_lift_coeff[:min_length])),
                "Thrust": prepare_data_for_storage(np.array(Sistema.hist_thrust[:min_length])),
                "Inertia matrix in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_inertia_b[:min_length])),
                "Center of mass in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_cm_b[:min_length])),
                "Center of pressure in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_cp_b[:min_length])),
                "Mass flux": prepare_data_for_storage(np.array(Sistema.hist_mass_flux[:min_length])),
                "Drag force in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_drag[:min_length])),
                "Lift force in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_lift[:min_length])),
                "Center of mass to center of pressure in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_cm2cp_b[:min_length])),
                "Aerodynamic forces in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_forces_aero_b[:min_length])),
                "Aerodynamic torques in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_torques_aero_b[:min_length])),
                "Engine forces in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_forces_engine_b[:min_length])),
                "Engine torques in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_torques_engine_b[:min_length])),
                "Acceleration in bodyframe": prepare_data_for_storage(np.array(Sistema.hist_accel_b[:min_length])),
                
                # Separar los componentes del cuaternión en columnas individuales
                "Quaternion_1": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_1[:min_length])),
                "Quaternion_2": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_2[:min_length])),
                "Quaternion_3": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_3[:min_length])),
                "Quaternion_4": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_4[:min_length])),
            }

            # Verificación de longitudes
            for key, value in df_data.items():
                if len(value) != min_length:
                    st.write(f"Advertencia: {key} tiene longitud {len(value)}, esperada {min_length}")
            
            # Crear DataFrame y guardar
            df = pd.DataFrame(df_data)
            df.to_parquet("sim_data.parquet", engine='pyarrow')
            st.success("Datos guardados exitosamente!")

        except Exception as e:
            st.error(f"Error al guardar los datos: {str(e)}")
            if df_data:
                st.write("Debugging info:")
                for key, value in df_data.items():
                    try:
                        if isinstance(value, (list, np.ndarray)):
                            shape = np.array(value).shape if isinstance(value, np.ndarray) else len(value)
                            st.write(f"{key}: tipo {type(value)}, forma {shape}")
                            if len(value) > 0:
                                st.write(f"Primer elemento: {type(value[0])}")
                    except Exception as debug_e:
                        st.write(f"{key}: Error al analizar - {str(debug_e)}")
            # Dentro del bucle de simulación
            if abs(t - 11.3) < 0.1:  # Cerca del tiempo crítico
                st.write(f"""
                    Estado del cohete en t={t:.2f}s:
                    Altura: {Sistema.r_enu[2]:.2f}m
                    Pitch: {Sistema.pitch:.2f}°
                    Velocidad: {Sistema.v_norm:.2f}m/s
                    Lift: {Sistema.lift:.2f}N
                    Ángulo de ataque: {Sistema.alpha:.2f}°
                    Coef. sustentación: {Sistema.lift_coeff:.4f}
                    Densidad: {Sistema.density:.4f}kg/m³
                """)





