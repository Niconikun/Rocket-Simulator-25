import streamlit as st
import json
import os
import pandas as pd
from src.models.engine import Engine, EngineConfig

st.set_page_config(page_title="Engine Designer", layout="wide")
st.title("🚀 Solid Rocket Motor (SRM) Design and Configuration")

# Create engine configurations directory
engine_configs_path = 'data/rockets/engines'
os.makedirs(engine_configs_path, exist_ok=True)

def load_engine_configs():
    """Load all engine configurations from the engines directory."""
    engines = {}
    try:
        for filename in os.listdir(engine_configs_path):
            if filename.endswith('.json'):
                file_path = os.path.join(engine_configs_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    engine_data = json.load(f)
                    engine_name = filename[:-5]  # Remove .json extension
                    engines[engine_name] = engine_data
        return engines
    except FileNotFoundError:
        return {}
    except Exception as e:
        st.error(f"Error loading engine configurations: {str(e)}")
        return {}

def save_engine_config(engine_name, config_data):
    """Save engine configuration to file."""
    try:
        safe_name = engine_name.lower().replace(" ", "_")
        file_path = os.path.join(engine_configs_path, f"{safe_name}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True, f"Engine saved as {safe_name}.json"
    except Exception as e:
        return False, f"Error saving engine: {str(e)}"

def delete_engine_config(engine_name):
    """Delete engine configuration."""
    try:
        safe_name = engine_name.lower().replace(" ", "_")
        file_path = os.path.join(engine_configs_path, f"{safe_name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True, f"Engine {engine_name} deleted"
        return False, "File not found"
    except Exception as e:
        return False, f"Error deleting engine: {str(e)}"

def show_engine_performance(engine, time_range):
    """Show engine performance data in a table format."""
    performance_data = []
    
    for t in time_range:
        engine.update(time=t)
        performance_data.append({
            'Time (s)': t,
            'Thrust (N)': round(engine.thrust, 2),
            'Mass Flux (kg/s)': round(engine.mass_flux, 3),
            'Specific Impulse (s)': round(engine.specific_impulse, 1)
        })
    
    df = pd.DataFrame(performance_data)
    return df

# Load existing engine configurations
engines = load_engine_configs()

# Sidebar for engine selection and management
with st.sidebar:
    st.header("Engine Management")
    
    # Engine selection
    engine_options = list(engines.keys()) + ["New Engine"]
    selected_engine = st.selectbox("Select Engine", engine_options, index=len(engine_options)-1)
    
    if selected_engine != "New Engine":
        if st.button("Delete Selected Engine"):
            success, message = delete_engine_config(selected_engine)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# Main configuration area
col1, col2 = st.columns([2, 1])

with col1:
    with st.form("engine_config_form"):
        st.header("Engine Configuration")
        
        # Load existing engine data if selected
        if selected_engine != "New Engine" and selected_engine in engines:
            engine_data = engines[selected_engine]
        else:
            engine_data = {
                "burn_time": 10.0,
                "nozzle_exit_diameter": 0.1,
                "mass_flux_max": 1.0,
                "gas_speed": 2000.0,
                "exit_pressure": 101325.0,
                "mode": "simple",
                "srm_parameters": {
                    "length_chamber": 1.0,
                    "diameter_chamber": 0.1,
                    "grain_outer_diameter": 0.08,
                    "grain_length": 0.5,
                    "grain_inner_diameter": 0.02,
                    "N_grains": 1,
                    "rho_grain": 1800,
                    "rho_percentage": 0.85
                }
            }
        
        # Engine name
        engine_name = st.text_input("Engine Name", 
                                  value=selected_engine if selected_engine != "New Engine" else "New_Engine")
        
        # Engine mode
        mode = st.selectbox("Engine Mode", 
                          ["simple", "srm"], 
                          index=0 if engine_data.get("mode", "simple") == "simple" else 1)
        
        # Basic engine parameters
        st.subheader("Basic Engine Parameters")
        col_basic1, col_basic2 = st.columns(2)
        
        with col_basic1:
            burn_time = st.number_input("Burn Time (s)", 
                                      min_value=0.1, 
                                      value=float(engine_data.get("burn_time", 10.0)), 
                                      step=0.1)
            mass_flux_max = st.number_input("Maximum Mass Flux (kg/s)", 
                                          min_value=0.01, 
                                          value=float(engine_data.get("mass_flux_max", 1.0)), 
                                          step=0.01)
            gas_speed = st.number_input("Gas Exit Velocity (m/s)", 
                                      min_value=100.0, 
                                      value=float(engine_data.get("gas_speed", 2000.0)), 
                                      step=10.0)
        
        with col_basic2:
            nozzle_exit_diameter = st.number_input("Nozzle Exit Diameter (m)", 
                                                 min_value=0.001, 
                                                 value=float(engine_data.get("nozzle_exit_diameter", 0.1)), 
                                                 step=0.001, 
                                                 format="%.3f")
            exit_pressure = st.number_input("Exit Pressure (Pa)", 
                                          min_value=1000.0, 
                                          value=float(engine_data.get("exit_pressure", 101325.0)), 
                                          step=1000.0)
        
        # SRM-specific parameters (shown if SRM mode is selected)
        if mode == "srm":
            st.subheader("SRM-Specific Parameters")
            srm_params = engine_data.get("srm_parameters", {})
            
            col_srm1, col_srm2 = st.columns(2)
            
            with col_srm1:
                st.write("**Chamber Geometry**")
                length_chamber = st.number_input("Chamber Length (m)", 
                                               min_value=0.1, 
                                               value=float(srm_params.get("length_chamber", 1.0)), 
                                               step=0.1)
                diameter_chamber = st.number_input("Chamber Diameter (m)", 
                                                 min_value=0.01, 
                                                 value=float(srm_params.get("diameter_chamber", 0.1)), 
                                                 step=0.01)
                
                st.write("**Grain Geometry**")
                grain_outer_diameter = st.number_input("Grain Outer Diameter (m)", 
                                                     min_value=0.01, 
                                                     value=float(srm_params.get("grain_outer_diameter", 0.08)), 
                                                     step=0.001, 
                                                     format="%.3f")
                grain_inner_diameter = st.number_input("Grain Inner Diameter (m)", 
                                                     min_value=0.001, 
                                                     value=float(srm_params.get("grain_inner_diameter", 0.02)), 
                                                     step=0.001, 
                                                     format="%.3f")
            
            with col_srm2:
                st.write("**Grain Properties**")
                grain_length = st.number_input("Grain Length (m)", 
                                             min_value=0.01, 
                                             value=float(srm_params.get("grain_length", 0.5)), 
                                             step=0.01)
                N_grains = st.number_input("Number of Grains", 
                                         min_value=1, 
                                         value=int(srm_params.get("N_grains", 1)), 
                                         step=1)
                rho_grain = st.number_input("Grain Density (kg/m³)", 
                                          min_value=100.0, 
                                          value=float(srm_params.get("rho_grain", 1800)), 
                                          step=10.0)
                rho_percentage = st.slider("Grain Density Percentage", 
                                         min_value=0.1, 
                                         max_value=1.0, 
                                         value=float(srm_params.get("rho_percentage", 0.85)), 
                                         step=0.01)
        else:
            # Default SRM parameters for simple mode
            length_chamber = 1.0
            diameter_chamber = 0.1
            grain_outer_diameter = 0.08
            grain_length = 0.5
            grain_inner_diameter = 0.02
            N_grains = 1
            rho_grain = 1800
            rho_percentage = 0.85
        
        # Form submission
        submitted = st.form_submit_button("Save Engine Configuration")
        
        if submitted:
            # Create engine configuration
            config_data = {
                "burn_time": burn_time,
                "nozzle_exit_diameter": nozzle_exit_diameter,
                "mass_flux_max": mass_flux_max,
                "gas_speed": gas_speed,
                "exit_pressure": exit_pressure,
                "mode": mode,
                "srm_parameters": {
                    "length_chamber": length_chamber,
                    "diameter_chamber": diameter_chamber,
                    "grain_outer_diameter": grain_outer_diameter,
                    "grain_length": grain_length,
                    "grain_inner_diameter": grain_inner_diameter,
                    "N_grains": N_grains,
                    "rho_grain": rho_grain,
                    "rho_percentage": rho_percentage
                }
            }
            
            # Save configuration
            success, message = save_engine_config(engine_name, config_data)
            if success:
                st.success(f"Engine '{engine_name}' saved successfully!")
                st.rerun()
            else:
                st.error(message)

with col2:
    st.header("Engine Performance")
    
    # Performance analysis section
    if st.button("Analyze Performance"):
        try:
            # Create engine instance for analysis
            if selected_engine != "New Engine" and selected_engine in engines:
                engine_data = engines[selected_engine]
            else:
                # Use current form values
                engine_data = {
                    "burn_time": 10.0,
                    "nozzle_exit_diameter": 0.1,
                    "mass_flux_max": 1.0,
                    "gas_speed": 2000.0,
                    "exit_pressure": 101325.0,
                    "mode": "simple"
                }
            
            srm_params = engine_data.get("srm_parameters", {})
            
            engine = Engine(
                time=0.0,
                ambient_pressure=101325.0,
                burn_time=engine_data["burn_time"],
                nozzle_exit_diameter=engine_data["nozzle_exit_diameter"],
                mass_flux_max=engine_data["mass_flux_max"],
                gas_speed=engine_data["gas_speed"],
                exit_pressure=engine_data["exit_pressure"],
                mode=engine_data.get("mode", "simple"),
                **srm_params
            )
            
            # Generate performance data
            time_range = list(range(0, int(engine.burn_time * 1.2), 1))
            if time_range:
                df = show_engine_performance(engine, time_range)
                st.subheader("Performance Over Time")
                st.dataframe(df, use_container_width=True)
                
                # Show line chart
                st.line_chart(df.set_index('Time (s)'))
            
            # Display performance metrics
            st.subheader("Performance Metrics")
            engine.update(time=engine.burn_time / 2)  # Mid-burn performance
            
            col_metric1, col_metric2 = st.columns(2)
            
            with col_metric1:
                st.metric("Max Thrust", f"{engine.thrust:.1f} N")
                st.metric("Max Mass Flux", f"{engine.mass_flux:.2f} kg/s")
                st.metric("Specific Impulse", f"{engine.specific_impulse:.1f} s")
            
            with col_metric2:
                st.metric("Vacuum Isp", f"{engine.vacuum_specific_impulse:.1f} s")
                st.metric("Total Impulse", f"{engine.thrust * engine.burn_time:.1f} N⋅s")
                st.metric("Propellant Mass", f"{engine.mass_flux * engine.burn_time:.2f} kg")
            
        except Exception as e:
            st.error(f"Error analyzing performance: {str(e)}")
    
    # Display saved engines
    st.subheader("Saved Engines")
    if engines:
        for engine_name in engines.keys():
            with st.expander(f"🔧 {engine_name}"):
                engine_data = engines[engine_name]
                st.write(f"**Mode:** {engine_data.get('mode', 'simple')}")
                st.write(f"**Burn Time:** {engine_data.get('burn_time', 0):.1f} s")
                st.write(f"**Max Mass Flux:** {engine_data.get('mass_flux_max', 0):.2f} kg/s")
                st.write(f"**Gas Velocity:** {engine_data.get('gas_speed', 0):.0f} m/s")
    else:
        st.info("No engines saved yet. Create your first engine configuration above!")

# Footer
st.markdown("---")
st.markdown("**Note:** This engine designer supports both simple engine models (for basic simulations) and advanced SRM models (for detailed solid rocket motor analysis).")
