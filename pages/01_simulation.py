import streamlit as st
from math import pi
import numpy as np
import datetime
import json
import pandas as pd
import pytz
import logging
import time
from src.models.rocket import Rocket
from src.models.atmosphere import Atmosphere
from src.models.clock import Clock
from src.models.planet import Planet
from src.utils.mattools import MatTools as Mat
from src.utils.thrust_processor import ThrustCurveProcessor
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Rocket Simulator Settings", layout="wide")

# Initialize session state for simulation control
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'simulation_progress' not in st.session_state:
    st.session_state.simulation_progress = 0.0
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None
if 'simulation_error' not in st.session_state:
    st.session_state.simulation_error = None
if 'simulation_data' not in st.session_state:
    st.session_state.simulation_data = None

def load_json_file(filename):
    try:
        # Actualizar rutas
        if 'rockets.json' in filename:
            rockets = {}
            configs_path = 'data/rockets/configs/'
            for file in os.listdir(configs_path):
                if file.endswith('.json'):
                    with open(os.path.join(configs_path, file), 'r') as f:
                        rocket_data = json.load(f)
                        rockets[rocket_data["name"]] = rocket_data
            return rockets
        elif 'locations.json' in filename:
            with open('data/locations/launch_sites.json', 'r') as file:
                return json.load(file)
    except FileNotFoundError:
        st.error(f"Error: {filename} no encontrado")
        return {}
    except json.JSONDecodeError:
        st.error(f"Error: {filename} tiene un formato inválido")
        return {}

def validate_simulation_inputs(rocket, location, time_step, runtime, temperature, pressure, elevation, initial_velocity):
    """Validate simulation inputs before running"""
    errors = []
    
    if time_step <= 0:
        errors.append("❌ Time step must be positive")
    if runtime <= 0:
        errors.append("❌ Runtime must be positive")
    if time_step > runtime:
        errors.append("❌ Time step cannot be larger than runtime")
    if rocket not in rocket_settings:
        errors.append("❌ Selected rocket configuration not found")
    if location not in location_settings:
        errors.append("❌ Selected location not found")
    if not (-50 <= temperature <= 50):
        errors.append("❌ Temperature must be between -50°C and 50°C")
    if not (80000 <= pressure <= 110000):
        errors.append("❌ Pressure must be between 80,000 Pa and 110,000 Pa")
    if not (0 <= elevation <= 180):
        errors.append("❌ Launch elevation must be between 0° and 180°")
    if initial_velocity < 0:
        errors.append("❌ Initial velocity cannot be negative")
    if initial_velocity > 1000:
        errors.append("❌ Initial velocity cannot exceed 1000 m/s")
    
    return errors

def load_thrust_curve(rocket_name):
    """Load thrust curve data for specified rocket"""
    try:
        with open(f'data/rockets/configs/{rocket_name}.json', 'r') as f:
            rocket_config = json.load(f)
        
        engine_data = rocket_config.get('engine', {})
        if engine_data.get('thrust_curve_mode') == 'experimental':
            thrust_file = engine_data.get('thrust_curve_file')
            if thrust_file and os.path.exists(thrust_file):
                processor = ThrustCurveProcessor()
                return processor.process_csv_file(thrust_file)
        
        return None
    except Exception as e:
        logging.error(f"Error loading thrust curve: {e}")
        return None

def prepare_data_for_storage(data):
    """Convert data to storage-friendly format"""
    if isinstance(data, (list, np.ndarray)):
        # Convert numpy arrays to lists for JSON serialization
        return data.tolist() if hasattr(data, 'tolist') else list(data)
    elif isinstance(data, (int, float, str, bool)):
        return data
    else:
        # Convert other types to string representation
        return str(data)

def save_simulation_data(sim_params, Sistema, min_length):
    """Save simulation data to parquet file for dashboard"""
    try:
        sim_rocket = sim_params['rocket']
        sim_location = sim_params['location']
        Latitude = location_settings[sim_location]['latitude']
        Longitude = location_settings[sim_location]['longitude']
        
        # Create data dictionary in the exact format expected by dashboard
        df_data = {
            "Rocket name": [sim_rocket] * min_length,
            "Location name": [sim_location] * min_length,
            "Location Latitude": [float(Latitude)] * min_length,
            "Location Longitude": [float(Longitude)] * min_length,
            # Simulation data, coordinates and velocity
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
            
            # Atmosphere
            "Density of the atmosphere": prepare_data_for_storage(np.array(Sistema.hist_density[:min_length])),
            "Ambient pressure": prepare_data_for_storage(np.array(Sistema.hist_press_amb[:min_length])),
            "Speed of sound": prepare_data_for_storage(np.array(Sistema.hist_v_sonic[:min_length])),
            "Mach number": prepare_data_for_storage(np.array(Sistema.hist_mach[:min_length])),

            # Forces and torques
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
            
            # Separate quaternion components into individual columns
            "Quaternion_1": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_1[:min_length])),
            "Quaternion_2": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_2[:min_length])),
            "Quaternion_3": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_3[:min_length])),
            "Quaternion_4": prepare_data_for_storage(np.array(Sistema.hist_q_enu2b_4[:min_length])),
        }
        
        # Create DataFrame
        simulation_df = pd.DataFrame(df_data)
        
        # Ensure directory exists
        os.makedirs('data/simulation', exist_ok=True)
        
        # Save to parquet
        simulation_df.to_parquet('data/simulation/sim_data.parquet', index=False)
        
        logger.info(f"Simulation data saved to parquet file with {min_length} data points")
        return True
        
    except Exception as e:
        logger.error(f"Error saving simulation data: {e}")
        return False

def run_simulation_direct(sim_params):
    """Run simulation directly in the main thread with progress updates"""
    try:
        # Extract parameters
        sim_rocket = sim_params['rocket']
        sim_location = sim_params['location']
        sim_runtime = sim_params['runtime']
        sim_time_step = sim_params['time_step']
        sim_date = sim_params['date']
        sim_time = sim_params['time']
        sim_timezone = sim_params['timezone']
        average_temperature = sim_params['temperature']
        launch_elevation = sim_params['elevation']
        launch_site_orientation = sim_params['orientation']
        vel_initial = sim_params['initial_velocity']
        average_pressure = sim_params['pressure']
        conditions = sim_params.get('conditions', [])
        
        # Load settings
        rocket_settings = load_json_file('data/rockets.json')
        location_settings = load_json_file('data/locations.json')
        
        # Extract initial data
        initial_mass = rocket_settings[sim_rocket]['initial_mass']
        Latitude = location_settings[sim_location]['latitude']
        Longitude = location_settings[sim_location]['longitude']
        Altitude = location_settings[sim_location]['altitude']

        thrust_curve_data = load_thrust_curve(sim_rocket)
        if thrust_curve_data:
            logger.info(f"Using experimental thrust curve: {thrust_curve_data['duration']:.2f}s duration, {thrust_curve_data['max_thrust']:.0f}N peak thrust")
        
        # Auxiliary functions
        deg2rad = pi / 180
        rad2deg = 180 / pi

        # Convert the simulation date and time to a timezone-aware datetime object
        sim_datetime = datetime.datetime.combine(sim_date, sim_time)
        sim_datetime = sim_datetime.replace(tzinfo=pytz.timezone(timezone_dict[sim_timezone]))

        # Configuration of time simulation related data
        Start = 0
        Steps_num = int(sim_runtime / sim_time_step)
        Steps = np.linspace(Start, sim_runtime, Steps_num)

        # Initial data
        East = 0
        North = 0
        Up = 1.0

        Vel_east = vel_initial * np.sin(launch_elevation * deg2rad) * np.cos(launch_site_orientation * deg2rad)
        Vel_north = vel_initial * np.sin(launch_elevation * deg2rad) * np.sin(launch_site_orientation * deg2rad)
        Vel_up = vel_initial * np.cos(launch_elevation * deg2rad)

        Roll = 0
        W_yaw = 0
        W_pitch = 0
        W_roll = 0

        Max_altitude = 1000000
        Max_range = 1250000
        Detonate_altitude = 900
        
        Detonate = "Detonation" in conditions if conditions else False

        # Enhanced simulation parameters
        max_safe_altitude = 200000  # 200 km safety limit
        max_safe_velocity = 5000    # 5 km/s safety limit
        stability_check_interval = 100

        # Initialization
        date = [sim_datetime.year, sim_datetime.month, sim_datetime.day, 
                sim_datetime.hour, sim_datetime.minute, sim_datetime.second]
        julian_date = Clock().julian_day(date)
        gmst_0 = Clock().gmst(julian_date, 1)

        r_enu_0 = np.array([East, North, Up])
        v_enu_0 = np.array([Vel_east, Vel_north, Vel_up])

        # Quaternion initialization
        q_roll = np.array([
            np.sin(Roll * 0.5 * deg2rad),
            0,
            0,
            np.cos(Roll * 0.5 * deg2rad)
        ])

        q_pitch = np.array([
            0,
            np.sin(-launch_elevation * 0.5 * deg2rad),
            0,
            np.cos(-launch_elevation * 0.5 * deg2rad)
        ])

        q_yaw = np.array([
            0,
            0,
            np.sin(launch_site_orientation * 0.5 * deg2rad),
            np.cos(launch_site_orientation * 0.5 * deg2rad)
        ])

        q_temp = Mat.hamilton(q_pitch, q_roll)
        q_enu2b_0 = Mat.hamilton(q_yaw, q_temp)

        w_enu_0 = np.array([W_yaw, W_pitch, W_roll])
        coordinates = np.array([Latitude, Longitude, Altitude])

        # Object creation
        Earth = Planet(gmst_0)
        Environment = Atmosphere(average_temperature)
        Sistema = Rocket(r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, initial_mass)

        # Create progress placeholder
        progress_placeholder = st.empty()
        progress_bar = progress_placeholder.progress(0)
        status_placeholder = st.empty()

        # Simulation loop
        Time = []
        t = Start
        
        for i in range(len(Steps)):
            # Update progress
            progress = min(1.0, i / len(Steps))
            st.session_state.simulation_progress = progress
            progress_bar.progress(progress)
            status_placeholder.info(f"🔄 Simulation running... Progress: {progress:.1%}")
            
            try:
                # Enhanced stability checks
                if i % stability_check_interval == 0:
                    # Check for numerical instability
                    if (np.any(np.isnan(Sistema.r_enu)) or 
                        np.any(np.isnan(Sistema.v_enu)) or
                        np.any(np.abs(Sistema.r_enu) > 1e10) or
                        np.any(np.abs(Sistema.v_enu) > max_safe_velocity)):
                        raise RuntimeError("Numerical instability detected - values out of bounds")
                    
                    # Check physical limits
                    if (Sistema.r_enu[2] > max_safe_altitude or
                        Sistema.r_enu[2] < -1000 or
                        np.linalg.norm(Sistema.v_enu) > max_safe_velocity):
                        logger.warning("Simulation approaching physical limits")
                        break
                
                # Simulation steps
                Earth.update(sim_time_step)
                Sistema.update_gmst(Earth.gmst)
                Sistema.update_mass_related(
                    rocket_settings[sim_rocket]['engine']['burn_time'],
                    rocket_settings[sim_rocket]["CoM_before_burn"]["x"],
                    rocket_settings[sim_rocket]["CoM_before_burn"]["y"], 
                    rocket_settings[sim_rocket]["CoM_before_burn"]["z"],
                    rocket_settings[sim_rocket]["I_before_burn"]["x"],
                    rocket_settings[sim_rocket]["I_before_burn"]["y"],
                    rocket_settings[sim_rocket]["I_before_burn"]["z"],
                    rocket_settings[sim_rocket]["CoM_after_burn"]["x"],
                    rocket_settings[sim_rocket]["CoM_after_burn"]["y"],
                    rocket_settings[sim_rocket]["CoM_after_burn"]["z"],
                    rocket_settings[sim_rocket]["I_after_burn"]["x"],
                    rocket_settings[sim_rocket]["I_after_burn"]["y"],
                    rocket_settings[sim_rocket]["I_after_burn"]["z"]
                )
                Sistema.update_pos_vel(coordinates)
                Sistema.update_atmosphere(
                    Environment.give_dens(Sistema.r_enu[2]),
                    Environment.give_press(Sistema.r_enu[2]),
                    Environment.give_v_sonic(Sistema.r_enu[2])
                )
                Sistema.update_aerodynamics(sim_rocket)
                Sistema.update_forces_aero(reference_area=rocket_settings[sim_rocket]['reference_area'])
                Sistema.update_engine(sim_rocket)
                Sistema.update_forces_engine()
                Sistema.update_forces_torques()
                Sistema.update_g_accel(coordinates)
                Sistema.RK4_update(sim_time_step)
                Sistema.save_data()

                # Enhanced termination conditions
                if Sistema.time >= 1:
                    if (Sistema.r_enu[2] < Sistema.hist_up[-2] and 
                        Sistema.r_enu[2] < Detonate_altitude and 
                        Detonate):
                        logger.info(f"Detonation triggered at {Sistema.time:.2f}s")
                        break
                
                termination_conditions = [
                    Sistema.r_enu[2] <= 0,
                    Sistema.r_enu[2] >= Max_altitude,
                    Sistema.range >= Max_range,
                    np.any(np.isnan(Sistema.r_enu)),
                    abs(Sistema.v_enu[2]) > max_safe_velocity,
                ]
                
                if any(termination_conditions):
                    termination_reasons = [
                        "Rocket hit the ground",
                        "Maximum altitude exceeded",
                        "Maximum range exceeded", 
                        "Numerical instability detected",
                        "Velocity exceeded safe limits",
                    ]
                    reason_idx = termination_conditions.index(True)
                    if reason_idx < len(termination_reasons):
                        logger.info(f"Simulation stopped: {termination_reasons[reason_idx]}")
                    break
                    
                Time.append(t)
                t += sim_time_step
                Sistema.update_time(sim_time_step)
                
            except Exception as step_error:
                logger.error(f"Step error at t={t:.3f}s: {step_error}")
                # Try to continue but log the error
                continue

        # Clear progress indicators
        progress_placeholder.empty()
        status_placeholder.empty()
        
        # Final progress update
        st.session_state.simulation_progress = 1.0
        
        # Determine minimum length of history arrays
        hist_arrays = [
            Sistema.hist_time, Sistema.hist_gmst, Sistema.hist_range, Sistema.hist_east,
            Sistema.hist_north, Sistema.hist_up, Sistema.hist_v_norm, Sistema.hist_lat,
            Sistema.hist_long, Sistema.hist_alt, Sistema.hist_r_enu, Sistema.hist_v_enu,
            Sistema.hist_pitch, Sistema.hist_yaw, Sistema.hist_roll, Sistema.hist_alpha,
            Sistema.hist_v_bx, Sistema.hist_v_by, Sistema.hist_v_bz, Sistema.hist_w_enu,
            Sistema.hist_density, Sistema.hist_press_amb, Sistema.hist_v_sonic, Sistema.hist_mach,
            Sistema.hist_mass, Sistema.hist_drag_coeff, Sistema.hist_lift_coeff, Sistema.hist_thrust,
            Sistema.hist_inertia_b, Sistema.hist_cm_b, Sistema.hist_cp_b, Sistema.hist_mass_flux,
            Sistema.hist_drag, Sistema.hist_lift, Sistema.hist_cm2cp_b, Sistema.hist_forces_aero_b,
            Sistema.hist_torques_aero_b, Sistema.hist_forces_engine_b, Sistema.hist_torques_engine_b,
            Sistema.hist_accel_b, Sistema.hist_q_enu2b_1, Sistema.hist_q_enu2b_2, 
            Sistema.hist_q_enu2b_3, Sistema.hist_q_enu2b_4
        ]
        
        min_length = min(len(arr) for arr in hist_arrays if hasattr(arr, '__len__'))
        
        # Save simulation data to parquet file
        save_success = save_simulation_data(sim_params, Sistema, min_length)
        
        # Store results in session state
        if hasattr(Sistema, 'hist_up') and Sistema.hist_up:
            max_alt = max(Sistema.hist_up)
        else:
            max_alt = 0
            
        if hasattr(Sistema, 'hist_v_norm') and Sistema.hist_v_norm:
            max_vel = max(Sistema.hist_v_norm)
        else:
            max_vel = 0

        st.session_state.simulation_results = {
            'rocket_data': Sistema,
            'simulation_time': Sistema.time,
            'max_altitude': max_alt,
            'max_velocity': max_vel,
            'final_altitude': Sistema.r_enu[2] if hasattr(Sistema, 'r_enu') else 0,
            'data_saved': save_success
        }
        
        # Store simulation data for plotting
        st.session_state.simulation_data = {
            'time': Time,
            'altitude': Sistema.hist_up if hasattr(Sistema, 'hist_up') else [],
            'velocity': Sistema.hist_v_norm if hasattr(Sistema, 'hist_v_norm') else [],
            'position_east': Sistema.hist_east if hasattr(Sistema, 'hist_east') else [],
            'position_north': Sistema.hist_north if hasattr(Sistema, 'hist_north') else [],
        }
        
        logger.info("Simulation completed successfully")
        
    except Exception as e:
        error_msg = f"Simulation failed: {str(e)}"
        st.session_state.simulation_error = error_msg
        logger.exception(error_msg)
    finally:
        st.session_state.simulation_running = False


rocket_settings = load_json_file('data/rockets.json')
location_settings = load_json_file('data/locations.json')

timezone_dict = {
    "United States": "America/New_York",
    "Canada": "America/Toronto",
    "Mexico": "America/Mexico_City",
    "Chile": "America/Santiago",
    "United Kingdom": "Europe/London",
    "Germany": "Europe/Berlin",
    "France": "Europe/Paris",
    "Japan": "Asia/Tokyo",
    "Australia": "Australia/Sydney"
}

options = list(timezone_dict.keys())
default_index = options.index("Chile") if "Chile" in options else 0

# Main header
st.header('UdeC Rocket Simulation Software')
st.write("Configure the simulation settings for your rocket launch. You can select the rocket, location, and various simulation parameters."
         " Once you have set the parameters, click 'Run Simulation' to start the simulation."
         " The simulation will run based on the provided settings and will display the results in a table format.")
st.write("Code written by Orozco 2022. GUI done by Sepúlveda 2025.")

# Simulation Status Dashboard
st.markdown("---")
st.subheader("📊 Simulation Status")

# Create status columns
status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    if st.session_state.simulation_running:
        st.metric("Status", "🟢 Running", delta="Active")
    elif st.session_state.simulation_results:
        st.metric("Status", "✅ Completed", delta="Ready")
    else:
        st.metric("Status", "⚪ Ready", delta="Waiting")

with status_col2:
    if st.session_state.simulation_results:
        results = st.session_state.simulation_results
        st.metric("Max Altitude", f"{results['max_altitude']:.1f} m")
    else:
        st.metric("Max Altitude", "N/A")

with status_col3:
    if st.session_state.simulation_results:
        results = st.session_state.simulation_results
        st.metric("Duration", f"{results['simulation_time']:.1f} s")
    else:
        st.metric("Duration", "N/A")

# Error display
if st.session_state.simulation_error:
    st.error(f"❌ {st.session_state.simulation_error}")
    if st.button("Clear Error"):
        st.session_state.simulation_error = None
        st.rerun()

# Quick actions
st.markdown("#### Quick Actions")
action_col1, action_col2, action_col3 = st.columns(3)

with action_col1:
    if st.button("📊 View Results", disabled=not st.session_state.simulation_results):
        if st.session_state.simulation_results:
            results = st.session_state.simulation_results
            st.subheader("Simulation Summary")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Final Time", f"{results['simulation_time']:.2f} s")
            with col2:
                st.metric("Max Altitude", f"{results['max_altitude']:.1f} m")
            with col3:
                st.metric("Max Velocity", f"{results['max_velocity']:.1f} m/s")
            with col4:
                st.metric("Final Altitude", f"{results['final_altitude']:.1f} m")
            
            # Add data saving status
            if results.get('data_saved'):
                st.success("✅ Simulation data saved successfully! You can now view the dashboard.")
            else:
                st.warning("⚠️ Simulation data may not have been saved properly.")
            
            # Add simple plot if data is available
            if st.session_state.simulation_data:
                st.subheader("Altitude vs Time")
                if st.session_state.simulation_data['time'] and st.session_state.simulation_data['altitude']:
                    chart_data = pd.DataFrame({
                        'Time (s)': st.session_state.simulation_data['time'],
                        'Altitude (m)': st.session_state.simulation_data['altitude']
                    })
                    st.line_chart(chart_data.set_index('Time (s)'))

with action_col2:
    if st.button("🔄 Restart Simulation"):
        st.session_state.simulation_running = False
        st.session_state.simulation_results = None
        st.session_state.simulation_error = None
        st.session_state.simulation_data = None
        st.rerun()

with action_col3:
    if st.button("🗑️ Clear Results"):
        st.session_state.simulation_results = None
        st.session_state.simulation_error = None
        st.session_state.simulation_data = None
        st.rerun()

st.markdown("---")

# Main simulation form
with st.form("Simulation Settings"):
    left_column, right_column = st.columns(2)
    
    sim_runtime = st.slider('Simulation runtime [s]', min_value=0, max_value=1000, value=600, step=10, key="sim_runtime")
    
    with left_column:
        st.subheader("Simulation Properties")
        sim_time_step = st.number_input('Simulation time step [s]', min_value=0.000, max_value=10.000, value=0.001, step=0.001, key="sim_time_step")
        sim_date = st.date_input('Simulation date', min_value=None, max_value=None, key="sim_date")
        sim_time = st.time_input('Simulation time', key="sim_time")
        sim_timezone = st.selectbox('Simulation timezone', options=options, index=default_index, key="sim_timezone")
        conditions = st.segmented_control(label="Conditions for simulation", options=[
            "Detonation", 
            "Parachute [Coming Soon]", 
            "Second Stage [Coming Soon]", 
            "Wind Conditions [Coming Soon]", 
            "Telemetry [Coming Soon]", 
            "ACS [Coming Soon]",
            "Thermal Model [coming Soon]",
            "Structural Model [Coming Soon]",
            "Inertial Navigation System [Coming Soon]"], default=None)

    with right_column:
        st.subheader("Simulation Settings")
        sim_rocket = st.selectbox('Rocket Selection', options=list(rocket_settings.keys()), index=0, key="sim_rocket")
        sim_location = st.selectbox('Location Selection', options=list(location_settings.keys()), index=0, key="sim_location")
        average_temperature = st.number_input('Average temperature [°C]', min_value=-50.0, max_value=50.0, value=20.0, step=1.0, key="average_temperature")
        launch_elevation = st.number_input('Launch elevation [°]', min_value=0.0, max_value=180.0, value=60.0, step=1.0, key="launch_elevation")
        launch_site_orientation = st.number_input('Launch site orientation (from the East) [°]', min_value=-180.0, max_value=180.0, value=20.0, step=1.0, key="launch_site_orientation")
        vel_initial = st.number_input('Initial velocity [m/s]', min_value=0.0, max_value=1000.0, value=0.0, step=1.0, key="vel_initial")
        average_pressure = st.number_input('Average pressure [Pa]', min_value=0.0, max_value=1000000.0, value=101325.0, step=1.0, key="average_pressure")
    
    # Simulation control buttons
    col1, col2 = st.columns([1, 1])
    
    with col1:
        run = st.form_submit_button("🚀 Run Simulation", type="primary", disabled=st.session_state.simulation_running)
    
    with col2:
        clear = st.form_submit_button("🗑️ Clear All", type="secondary")

    if run:
        # Validate inputs first
        validation_errors = validate_simulation_inputs(
            sim_rocket, sim_location, sim_time_step, sim_runtime,
            average_temperature, average_pressure, launch_elevation, vel_initial
        )
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        else:
            # Reset flags and start simulation
            st.session_state.simulation_error = None
            st.session_state.simulation_running = True
            
            # Store simulation parameters
            sim_params = {
                'rocket': sim_rocket,
                'location': sim_location,
                'runtime': sim_runtime,
                'time_step': sim_time_step,
                'date': sim_date,
                'time': sim_time,
                'timezone': sim_timezone,
                'temperature': average_temperature,
                'elevation': launch_elevation,
                'orientation': launch_site_orientation,
                'initial_velocity': vel_initial,
                'pressure': average_pressure,
                'conditions': conditions
            }
            
            # Run simulation directly in main thread
            run_simulation_direct(sim_params)
            st.rerun()
        
    if clear:
        # Clear all simulation state
        st.session_state.simulation_running = False
        st.session_state.simulation_results = None
        st.session_state.simulation_error = None
        st.session_state.simulation_progress = 0.0
        st.session_state.simulation_data = None
        st.info("🧹 All simulation data cleared!")
        st.rerun()