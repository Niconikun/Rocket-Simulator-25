import streamlit as st
from Clock import Clock
from Planet import Planet
from Atmosphere import Atmosphere
from Rocket import Rocket
from cmath import pi
from pickle import FALSE, TRUE
import numpy as np
import datetime
import MatTools as Mat
import json
import pandas as pd

with open('rockets.json', 'r') as file:
    rocket_settings = json.load(file)
with open('locations.json', 'r') as file:
    location_settings = json.load(file)

# Create and edit rockets properties for the simulator
with st.form("Simulation Settings"):

    left_column, right_column = st.columns(2)
    sim_runtime = st.slider('Simulation runtime [s]', min_value=0, max_value=1000, value=200, step=10, key="sim_runtime")
    with left_column:
        #info
        st.subheader("Simulation Properties")
        sim_time_step = st.number_input('Simulation time step [s]', min_value=0.0, max_value=10.0, value=0.001, step=0.001, key="sim_time_step")
        sim_date = st.date_input('Simulation date', value=None, min_value=None, max_value=None, key="sim_date")
        sim_time = st.time_input('Simulation time', value=None, key="sim_time")
        sim_timezone = st.selectbox('Simulation timezone', options=['UTC', 'Local'], index=0, key="sim_timezone")
        

    with right_column:
        #info
        st.subheader("Simulation Settings")
        sim_rocket = st.selectbox('Rocket Selection', options=list(rocket_settings.keys()), index=0, key="sim_rocket")
        sim_location = st.selectbox('Location Selection', options=list(location_settings.keys()), index=0, key="sim_location")
        average_temperature = st.number_input('Average temperature [C]', min_value=-50.0, max_value=50.0, value=20.0, step=1.0, key="average_temperature")
        launch_elevation = st.number_input('Launch elevation [m]', min_value=0.0, max_value=10000.0, value=60.0, step=1.0, key="launch_elevation")
        launch_site_orientation = st.number_input('Launch site orientation (from the East)', min_value=-180.0, max_value=180.0, value=20.0, step=1.0, key="launch_site_orientation")
        average_pressure = st.number_input('Average pressure [Pa]', min_value=0.0, max_value=1000000.0, value=101325.0, step=1.0, key="average_pressure")
        average_humidity = st.number_input('Average humidity [%]', min_value=0.0, max_value=100.0, value=50.0, step=1.0, key="average_humidity")
    # Add a submit button
    
    
    run = st.form_submit_button("Run Simulation")
    if run:

        st.info("Running!")
        open("sim_data.pkl", "w").close() # Clear previous simulation data
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

        # ------ Configuration of time simulation related data ------ #
        Start=0                     # [s]  # Starting time of simulation
        Steps_num=int(sim_runtime/sim_time_step)                 
        Steps=np.linspace(Start,sim_runtime,Steps_num)
        #st.write(f"Simulation steps: {Steps_num} with time step: {sim_time_step:.3f} s. {Steps}")

        # ___________________ Initial data to be INPUT ________________ #  # (All of this should to be obtained from external file!!!)
        East=0        # [m]   # X axis initial location of rocket from platform
        North=0       # [m]   # Y axis initial location of rocket from platform
        Up=0.1        # [m]   # Z axis initial location of rocket from platform  (do not set at 0...this is in order to used a conditional later on for max. alt and range)

        Vel_east=0    # [m/s]   # X axis initial velocity of rocket from platform
        Vel_north=0   # [m/s]   # Y axis initial velocity of rocket from platform
        Vel_up=0      # [m/s]   # Z axis initial velocity of rocket from platform

        Roll=0        # [deg]   # From initial position (between -180 and 180). Assumed to be always zero

        W_yaw=0       # [rad/s]   # X axis initial rotational velocity of rocket from platform
        W_pitch=0     # [rad/s]   # Y axis initial rotational velocity of rocket from platform
        W_roll=0      # [rad/s]   # Z axis initial rotational velocity of rocket from platform

        Max_altitude=1000000     # [m] # Max. altitude
        Max_range=1250000        # [m] # Max. range

        Detonate=FALSE          # Statement for detonation or not
        Detonate_altitude=900  # [m] # Altitude for detonation

        # ___________________ Initialization of data ________________ #
        date=[sim_date.year, sim_date.month, sim_date.day, sim_time.hour, sim_time.minute, sim_time.second]                # List containing date
        julian_date=Clock().julian_day(date)                         # Obtaining Julian Date
        gmst_0=Clock().gmst(julian_date,1)                           # Initial Greenwich Mean Sidereal Time [rad]

        r_enu_0=np.array([East,North,Up])                            # [m]   # Initial East-North-Up location from platform
        v_enu_0=np.array([Vel_east,Vel_north,Vel_up])                # [m/s] # Initial East-North-Up velocity from platform

        q_yaw=np.array([0,0,np.sin(launch_site_orientation*0.5*deg2rad),np.cos(launch_site_orientation*0.5*deg2rad)])         # Quaternion single yaw rotation
        q_pitch=np.array([0,np.sin(-launch_elevation*0.5*deg2rad),0,np.cos(-launch_elevation*0.5*deg2rad)]) # Quaternion single pitch rotation
        q_roll=np.array([np.sin(Roll*0.5*deg2rad),0,0,np.cos(Roll*0.5*deg2rad)])      # Quaternion single roll rotation
        q_enu2b_0=Mat.hamilton(q_pitch,q_yaw)                                         # Initial quaternion from East-North-Up to bodyframe

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
            Sistema.update_mass_related(rocket_settings[sim_rocket]['engine']['burn_time'])  # [s]    # Propellant total burning time
            Sistema.update_pos_vel(coordinates)
            Sistema.update_atmosphere(Environment.give_dens(Sistema.r_enu[2]),Environment.give_press(Sistema.r_enu[2]),Environment.give_v_sonic(Sistema.r_enu[2]))    
            Sistema.update_aerodynamics(sim_rocket)
            Sistema.update_engine(sim_rocket)
            Sistema.update_forces_aero(reference_area=rocket_settings[sim_rocket]['reference_area'])
            Sistema.update_forces_engine()
            Sistema.update_forces_torques()
            Sistema.update_g_accel(coordinates)
            Sistema.RK4_update(sim_time_step)
            Sistema.save_data()

            if Sistema.time>=1:
                if Sistema.r_enu[2]<Sistema.hist_up[-2] and Sistema.r_enu[2]<Detonate_altitude and Detonate==TRUE:
                    st.warning(f"Rocket has reached the detonation altitude of {Detonate_altitude} m at time {Sistema.time:.2f} s. Simulation will stop.")
                    break
    
            # Conditional to stop when reached
            if Sistema.r_enu[2]<=0 or Sistema.r_enu[2]>=Max_altitude or Sistema.range>= Max_range:
                st.warning(f"Rocket has reached the maximum altitude of {Max_altitude} m or maximum range of {Max_range} m at time {Sistema.time:.2f} s. Simulation will stop.")
                break

            Time.append(t)
            t+=sim_time_step

            # Rocket's updating of simulation time
            Sistema.update_time(sim_time_step)

        st.success("Finished!")
        df = pd.DataFrame({
                    "Rocket name": sim_rocket,
                    "Location name": sim_location,
                    "Location Latitude": Latitude,
                    "Location Longitude": Longitude,
                    "East-North-Up location from platform": Sistema.hist_r_enu,
                    "East-North-Up velocity from platform": Sistema.hist_v_enu,
                    "Quaternion that rotates from East-North-Up to bodyframe": Sistema.hist_q_enu2b,
                    "q_enu2b_1": Sistema.hist_q_enu2b_1,
                    "q_enu2b_2": Sistema.hist_q_enu2b_2,
                    "q_enu2b_3": Sistema.hist_q_enu2b_3,
                    "q_enu2b_4": Sistema.hist_q_enu2b_4,
                    "Rotational velocity in East-North-Up": Sistema.hist_w_enu,
                    "Greenwich Mean Sidereal Time": Sistema.hist_gmst,
                    "Simulation time": Sistema.hist_time,
                    "Inertia matrix in bodyframe": Sistema.hist_inertia_b,
                    "Mass of the rocket": Sistema.hist_mass,
                    "Center of mass in bodyframe": Sistema.hist_cm_b,
                    "Yaw angle": Sistema.hist_yaw,
                    "Pitch angle": Sistema.hist_pitch,
                    "Roll angle": Sistema.hist_roll,
                    "Velocity in bodyframe": Sistema.hist_v_b,
                    "v_bx": Sistema.hist_v_bx,
                    "v_by": Sistema.hist_v_by,
                    "v_bz": Sistema.hist_v_bz,
                    "Angle of attack": Sistema.hist_alpha,
                    "Density of the atmosphere": Sistema.hist_density,
                    "Ambient pressure": Sistema.hist_press_amb,
                    "Speed of sound": Sistema.hist_v_sonic,
                    "Mach number": Sistema.hist_mach,
                    "Drag coefficient": Sistema.hist_drag_coeff,
                    "Lift coefficient": Sistema.hist_lift_coeff,
                    "Center of pressure in bodyframe": Sistema.hist_cp_b,
                    "Mass flux": Sistema.hist_mass_flux,
                    "Thrust": Sistema.hist_thrust,
                    "Drag force in bodyframe": Sistema.hist_drag,
                    "Lift force in bodyframe": Sistema.hist_lift,
                    "Center of mass to center of pressure in bodyframe": Sistema.hist_cm2cp_b,
                    "Aerodynamic forces in bodyframe": Sistema.hist_forces_aero_b,
                    "Aerodynamic torques in bodyframe": Sistema.hist_torques_aero_b,
                    "Engine forces in bodyframe": Sistema.hist_forces_engine_b,
                    "Engine torques in bodyframe": Sistema.hist_torques_engine_b,
                    "Range": Sistema.hist_range,
                    "East coordinate": Sistema.hist_east,
                    "North coordinate": Sistema.hist_north,
                    "Up coordinate": Sistema.hist_up,
                    "Velocity norm": Sistema.hist_v_norm,
                    "Geographic coordinates": Sistema.hist_coord,
                    "Latitude": Sistema.hist_lat,
                    "Longitude": Sistema.hist_long,
                    "Altitude": Sistema.hist_alt
                    })
        
        st.write(df)
        df.to_pickle("sim_data.pkl")

        #add save button
        #if st.button("Save Simulation Data"):
          #  df.to_csv("simulation_data.csv", index=False)
           # st.success("Simulation data saved successfully!")





