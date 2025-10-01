import streamlit as st
import pandas as pd
import numpy as np
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl
import matplotlib.pyplot as plt
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import io
import base64
from math import cos, pi

# Configuración de la página
st.set_page_config(page_title="Rocket Simulator Dashboard", page_icon=":rocket:", layout="wide")
st.title("Rocket Simulator Dashboard")

# Funciones auxiliares
@st.cache_data
def load_simulation_data():
    """Carga y valida los datos de la simulación"""
    try:
        data = pd.read_parquet("data/simulation/sim_data.parquet")
        return data
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def compress_data(data, compression_factor=50):
    """Comprime los datos para visualización"""
    return data.iloc[::compression_factor].copy()

@st.cache_data
def calculate_metrics(data):
    """Calcula métricas principales de la simulación"""
    try:
        accel_magnitudes = [np.linalg.norm(np.array(acc)) if isinstance(acc, (list, np.ndarray)) else 0 for acc in data["Acceleration in bodyframe"]]
        max_accel_gs = max(accel_magnitudes) / 9.81 if accel_magnitudes else 0  # Convertir a G's
        
        # Calculate propellant used
        initial_mass = data["Mass of the rocket"].iloc[0]
        final_mass = data["Mass of the rocket"].iloc[-1]
        propellant_used = initial_mass - final_mass
        
        return {
            "total_time": round(data["Simulation time"].iloc[-1], 2),
            "max_range": round(data["Range"].iloc[-1] / 1000, 2),
            "max_alt": round(data["Up coordinate"].max() / 1000, 3),
            "max_speed": round(data["Velocity norm"].max(), 2),
            "max_mach": round(data["Mach number"].max(), 2),
            "initial_mass": round(initial_mass, 3),
            "final_mass": round(final_mass, 3),
            "propellant_used": round(propellant_used, 3),
            "max_accel_g": round(max_accel_gs, 2)
        }
    except Exception as e:
        st.error(f"Error calculating metrics: {e}")
        return {}

def generate_pdf_report(chart_data, metrics, stability_df, title, include_plots=True, include_analysis=True):
    """Generate a comprehensive PDF report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1
    )
    story.append(Paragraph(title, title_style))
    
    # Simulation Overview
    story.append(Paragraph("Simulation Overview", styles['Heading2']))
    
    # Key metrics table
    overview_data = [
        ['Parameter', 'Value', 'Parameter', 'Value'],
        ['Rocket', chart_data['Rocket name'].iloc[0], 'Location', chart_data['Location name'].iloc[0]],
        ['Total Time', f"{metrics['total_time']} s", 'Max Altitude', f"{metrics['max_alt']} km"],
        ['Max Range', f"{metrics['max_range']} km", 'Max Speed', f"{metrics['max_speed']} m/s"],
        ['Max Mach', f"{metrics['max_mach']}", 'Max G-Force', f"{metrics['max_accel_g']} G"],
        ['Initial Mass', f"{metrics['initial_mass']} kg", 'Final Mass', f"{metrics['final_mass']} kg"],
        ['Propellant Used', f"{metrics['propellant_used']} kg", 'Launch Site', f"{chart_data['Location Latitude'].iloc[0]:.3f}°S, {chart_data['Location Longitude'].iloc[0]:.3f}°W"],
    ]
    
    overview_table = Table(overview_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 0.3*inch))
    
    if include_analysis:
        # Stability Analysis Section
        story.append(Paragraph("Stability Analysis", styles['Heading2']))
        
        stability_data = [
            ['Stability Metric', 'Value', 'Status'],
            ['Minimum Stability', f"{stability_df['stability_calibers'].min():.2f} calibers", 
             stability_df.loc[stability_df['stability_calibers'].idxmin(), 'status']],
            ['Maximum Stability', f"{stability_df['stability_calibers'].max():.2f} calibers", 
             stability_df.loc[stability_df['stability_calibers'].idxmax(), 'status']],
            ['Average Stability', f"{stability_df['stability_calibers'].mean():.2f} calibers", 
             'N/A'],
            ['Final Stability', f"{stability_df['stability_calibers'].iloc[-1]:.2f} calibers", 
             stability_df['status'].iloc[-1]],
        ]
        
        stability_table = Table(stability_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        stability_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(stability_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Stability guidelines
        guidelines = """
        <b>Stability Guidelines:</b><br/>
        • 2.0+ calibers: Very Stable<br/>
        • 1.5-2.0 calibers: Stable<br/>
        • 1.0-1.5 calibers: Marginal Stability<br/>
        • <1.0 calibers: Unstable<br/>
        <br/>
        <i>Target 1.5-2.0 calibers for optimal performance and safety.</i>
        """
        story.append(Paragraph(guidelines, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
    
    # Risk Assessment
    story.append(Paragraph("Risk Assessment", styles['Heading2']))
    
    max_range_km = metrics['max_range']
    max_alt_km = metrics['max_alt']
    
    risk_assessment = []
    if max_range_km > 5:
        risk_assessment.append("⚠️ High range - ensure adequate safety zone")
    if max_alt_km > 2:
        risk_assessment.append("⚠️ High altitude - consider airspace regulations")
    if stability_df['stability_calibers'].min() < 1.0:
        risk_assessment.append("🚨 Stability margin below safe minimum")
    if metrics['max_accel_g'] > 15:
        risk_assessment.append("⚠️ High acceleration - verify structural integrity")
    
    if not risk_assessment:
        risk_assessment.append("✅ All parameters within safe limits")
    
    for risk in risk_assessment:
        story.append(Paragraph(f"• {risk}", styles['Normal']))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Paragraph(f"Report generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                          styles['Italic']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_csv_export(chart_data, stability_df):
    """Generate CSV export of simulation data"""
    # Combine main data with stability metrics
    export_data = chart_data.copy()
    
    # Add stability columns
    export_data['stability_calibers'] = stability_df['stability_calibers']
    export_data['stability_status'] = stability_df['status']
    export_data['cm_cp_distance'] = stability_df['cm_cp_distance']
    
    return export_data.to_csv(index=False)

def generate_json_summary(metrics, stability_df):
    """Generate JSON summary of key results"""
    summary = {
        'simulation_metrics': metrics,
        'stability_analysis': {
            'min_stability': float(stability_df['stability_calibers'].min()),
            'max_stability': float(stability_df['stability_calibers'].max()),
            'avg_stability': float(stability_df['stability_calibers'].mean()),
            'final_stability': float(stability_df['stability_calibers'].iloc[-1]),
            'min_stability_status': stability_df.loc[stability_df['stability_calibers'].idxmin(), 'status'],
            'stability_timeline': stability_df[['time', 'stability_calibers']].to_dict('records')
        },
        'export_info': {
            'timestamp': pd.Timestamp.now().isoformat(),
            'version': '1.0'
        }
    }
    
    return json.dumps(summary, indent=2)

# Cargar y preparar datos
try:
    chart_data = load_simulation_data()
    if chart_data.empty:
        st.error("No simulation data found. Please run a simulation first.")
        st.stop()
        
    chart_data_compressed = compress_data(chart_data)
    metrics = calculate_metrics(chart_data)

    st.subheader("Simulation Parameters")
    
    # Crear tres columnas para los parámetros
    param_col1, param_col2, param_col3 = st.columns(3)

    with param_col1:
        st.write("📌 Launch Configuration")
        st.info(f"""
        **Rocket**: {chart_data['Rocket name'].iloc[0]}
        **Location**: {chart_data['Location name'].iloc[0]}
        **Coordinates**: {chart_data['Location Latitude'].iloc[0]:.3f}°S, {chart_data['Location Longitude'].iloc[0]:.3f}°W
        """)

    with param_col2:
        st.write("🎯 Initial Conditions")
        # Crear un DataFrame con los datos iniciales
        initial_data = pd.DataFrame({
            "Parameter": ["Launch Elevation", "Initial Mass", "Initial Velocity"],
            "Value": [
                f"{chart_data['Pitch Angle'].iloc[0]:.1f}°",
                f"{chart_data['Mass of the rocket'].iloc[0]:.2f} kg",
                f"{chart_data['Velocity norm'].iloc[0]:.1f} m/s"
            ]
        })
        st.dataframe(initial_data, hide_index=True)

    with param_col3:
        st.write("🌡️ Environmental Conditions")
        env_data = pd.DataFrame({
            "Parameter": ["Density", "Pressure", "Speed of Sound"],
            "Value": [
                f"{chart_data['Density of the atmosphere'].iloc[0]:.3f} kg/m³",
                f"{chart_data['Ambient pressure'].iloc[0]/1000:.1f} kPa",
                f"{chart_data['Speed of sound'].iloc[0]:.1f} m/s"
            ]
        })
        st.dataframe(env_data, hide_index=True)

    # Línea divisoria
    st.markdown("---")

    # Layout de métricas
    st.subheader("Rocket Performance Metrics")
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)
    col7, col8, col9 = st.columns(3)
    col_landing = st.columns(1)

    # Primera fila de métricas
    col1.metric("Total Flight Time", f"{metrics['total_time']}s")
    col2.metric("Max Range", f"{metrics['max_range']}km")
    col3.metric("Max Altitude", f"{metrics['max_alt']}km")

    # Segunda fila de métricas
    col4.metric("Initial Mass", f"{metrics['initial_mass']}kg")
    col5.metric("Final Mass", f"{metrics['final_mass']}kg")
    col6.metric("Propellant Used", f"{metrics['propellant_used']}kg")

    # Tercera fila de métricas
    col7.metric("Max Speed", f"{metrics['max_speed']}m/s")
    col8.metric("Max Mach", f"{metrics['max_mach']}")
    col9.metric("Max G-Force", f"{metrics['max_accel_g']}G")

    # Coordenadas de aterrizaje
    col_landing[0].metric("Landing Coordinates", 
                         f"{abs(round(chart_data['Latitude'].iloc[-1], 1))}° S, {abs(round(chart_data['Longitude'].iloc[-1], 1))}° W")

    # Mapa de trayectoria
    st.subheader("Trajectory Overview")
    trajectory_data = pd.DataFrame({
        'Latitude': chart_data_compressed["Latitude"],
        'Longitude': chart_data_compressed["Longitude"],
        'Altitude': chart_data_compressed["Altitude"]
    })

    map_config = {
        "version": "v1",
        "config": {
            "mapState": {
                "bearing": 0,
                "latitude": float(chart_data["Location Latitude"].iloc[0]),
                "longitude": float(chart_data["Location Longitude"].iloc[0]),
                "pitch": 60,
                "zoom": 9,
            }
        }
    }

    map_1 = KeplerGl(data={"trajectory": trajectory_data})
    map_1.config = map_config
    keplergl_static(map_1, height=800, width=1400, center_map=True)

    # Gráficos de rendimiento
    st.subheader("Performance Charts")
    chart_col1, chart_col2, chart_col3 = st.columns(3)
    chart_col4, chart_col5, chart_col6 = st.columns(3)
    chart_col7, chart_col8, chart_col9 = st.columns(3)

    # Primera fila de gráficos
    with chart_col1:
        st.write('Altitude [m] & Speed [m/s] vs Time [s]')
        st.line_chart(chart_data_compressed, 
                     x="Simulation time", 
                     y=["Up coordinate", "Velocity norm"])

    with chart_col2:
        st.write('Flight Path - Altitude [m] vs Range [m]')
        st.line_chart(chart_data_compressed,
                     x="Range",
                     y="Up coordinate")

    with chart_col3:
        st.write('Aerodynamic Parameters - Mach [-] & AoA [°] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Mach number", "Angle of attack"])

    # Segunda fila de gráficos
    with chart_col4:
        st.write('Forces Analysis [N] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Thrust", "Lift force in bodyframe", "Drag force in bodyframe"])

    with chart_col5:
        st.write('Mass [kg] & Altitude [m] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Mass of the rocket", "Up coordinate"])

    with chart_col6:
        st.write('Attitude Analysis - Euler Angles [°] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Pitch Angle", "Roll Angle", "Yaw Angle"])
    
    # Tercera fila de gráficos
    with chart_col7:
        st.write('Velocity Components [m/s] vs Time [s]')
        st.line_chart(chart_data_compressed,
                    x="Simulation time",
                    y=["v_bx", "v_by", "v_bz"])

    with chart_col8:
        st.write('Atmospheric Conditions vs Altitude [m]')
        # Crear un DataFrame temporal normalizado para mejor visualización
        atm_data = chart_data_compressed.copy()
        atm_data['Normalized Density'] = atm_data['Density of the atmosphere'] / atm_data['Density of the atmosphere'].max()
        atm_data['Normalized Pressure'] = atm_data['Ambient pressure'] / atm_data['Ambient pressure'].max()
        st.line_chart(atm_data,
                    x="Up coordinate",
                    y=["Normalized Density", "Normalized Pressure"])

    with chart_col9:
        st.write('Aerodynamic Coefficients [-] vs Time [s]')
        st.line_chart(chart_data_compressed,
                     x="Simulation time",
                     y=["Drag coefficient", "Lift coefficient"])

    # Enhanced Stability Analysis
    st.subheader("🚀 Advanced Stability Analysis")

    # Calculate stability metrics
    stability_metrics = []

    for i in range(len(chart_data)):
        try:
            cm = np.array(chart_data['Center of mass in bodyframe'].iloc[i])
            cp = np.array(chart_data['Center of pressure in bodyframe'].iloc[i])
            time = chart_data['Simulation time'].iloc[i]
            
            # Calculate distance between CM and CP
            cm_cp_distance = np.linalg.norm(cp - cm)
            
            # Calculate stability margin in calibers (rocket diameters)
            rocket_diameter = 0.103  # meters from your rocket config
            stability_calibers = cm_cp_distance / rocket_diameter
            
            # Determine stability status
            if stability_calibers > 2.0:
                status = "Very Stable"
                color = "green"
            elif stability_calibers > 1.5:
                status = "Stable"
                color = "blue"
            elif stability_calibers > 1.0:
                status = "Marginally Stable"
                color = "orange"
            else:
                status = "Unstable"
                color = "red"
            
            stability_metrics.append({
                'time': time,
                'cm_cp_distance': cm_cp_distance,
                'stability_calibers': stability_calibers,
                'status': status,
                'color': color,
                'cm_x': cm[0],
                'cp_x': cp[0]
            })
        except Exception as e:
            # Skip this data point if there's an error
            continue

    if not stability_metrics:
        st.error("No stability data available. Please check your simulation data.")
        st.stop()
        
    stability_df = pd.DataFrame(stability_metrics)
    stability_compressed = compress_data(stability_df)

    # Create columns for stability display
    stab_col1, stab_col2, stab_col3 = st.columns([2, 1, 1])

    with stab_col1:
        st.write("**Stability Margin Evolution**")
        
        # Create a more informative stability chart
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Plot stability margin
        color = 'tab:blue'
        ax1.set_xlabel('Time [s]')
        ax1.set_ylabel('Stability Margin [calibers]', color=color)
        line1 = ax1.plot(stability_compressed['time'], stability_compressed['stability_calibers'], 
                         color=color, label='Stability Margin', linewidth=2)
        ax1.tick_params(axis='y', labelcolor=color)
        
        # Add stability regions
        ax1.axhspan(2.0, 4.0, alpha=0.2, color='green', label='Very Stable')
        ax1.axhspan(1.5, 2.0, alpha=0.2, color='blue', label='Stable')
        ax1.axhspan(1.0, 1.5, alpha=0.2, color='orange', label='Marginal')
        ax1.axhspan(0.0, 1.0, alpha=0.2, color='red', label='Unstable')
        
        ax1.set_ylim(0, max(4, stability_df['stability_calibers'].max() * 1.1))
        ax1.legend(loc='upper left')
        
        # Second y-axis for CM-CP positions
        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('Position [m]', color=color)
        line2 = ax2.plot(stability_compressed['time'], stability_compressed['cm_x'], 
                         color='purple', label='CM Position', linestyle='--', linewidth=2)
        line3 = ax2.plot(stability_compressed['time'], stability_compressed['cp_x'], 
                         color='brown', label='CP Position', linestyle='--', linewidth=2)
        ax2.tick_params(axis='y', labelcolor=color)
        
        # Combine legends
        lines = line1 + line2 + line3
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper right')
        
        plt.title('Rocket Stability Analysis')
        plt.tight_layout()
        st.pyplot(fig)

    with stab_col2:
        st.write("**Stability Summary**")
        
        # Calculate key stability metrics
        min_stability = stability_df['stability_calibers'].min()
        max_stability = stability_df['stability_calibers'].max()
        avg_stability = stability_df['stability_calibers'].mean()
        final_stability = stability_df['stability_calibers'].iloc[-1]
        
        # Determine overall stability rating
        if min_stability > 1.5:
            overall_rating = "Excellent"
            rating_color = "🟢"  # Using emoji instead of color parameter
        elif min_stability > 1.0:
            overall_rating = "Good"
            rating_color = "🔵"
        elif min_stability > 0.5:
            overall_rating = "Marginal"
            rating_color = "🟠"
        else:
            overall_rating = "Poor"
            rating_color = "🔴"
        
        # Display overall rating with emoji
        st.write(f"**Overall Rating:** {rating_color} {overall_rating}")
        st.metric("Min Stability", f"{min_stability:.2f} cal")
        st.metric("Max Stability", f"{max_stability:.2f} cal")
        st.metric("Final Stability", f"{final_stability:.2f} cal")

    with stab_col3:
        st.write("**Stability Guidelines**")
        
        stability_info = """
        **Stability Margins:**
        - 🟢 2.0+ cal: Very Stable
        - 🔵 1.5-2.0 cal: Stable  
        - 🟠 1.0-1.5 cal: Marginal
        - 🔴 <1.0 cal: Unstable
        
        **Recommendations:**
        - Target 1.5-2.0 cal for safety
        - <1.0 cal risks instability
        - >2.5 cal may be overstable
        """
        
        st.info(stability_info)

    # Add CM/CP position analysis
    st.write("**Center of Mass & Pressure Analysis**")
    cm_cp_col1, cm_cp_col2 = st.columns(2)

    with cm_cp_col1:
        st.write("CM and CP Position vs Time")
        position_data = pd.DataFrame({
            'Time': stability_compressed['time'],
            'CM Position': stability_compressed['cm_x'],
            'CP Position': stability_compressed['cp_x'],
            'Separation': stability_compressed['cm_cp_distance']
        })
        st.line_chart(position_data, x='Time', y=['CM Position', 'CP Position', 'Separation'])

    with cm_cp_col2:
        st.write("Stability Statistics")
        
        stats_data = {
            'Metric': ['Minimum Separation', 'Maximum Separation', 'Average Separation', 
                      'Initial Separation', 'Final Separation', 'Separation Change'],
            'Value': [
                f"{stability_df['cm_cp_distance'].min():.3f} m",
                f"{stability_df['cm_cp_distance'].max():.3f} m", 
                f"{stability_df['cm_cp_distance'].mean():.3f} m",
                f"{stability_df['cm_cp_distance'].iloc[0]:.3f} m",
                f"{stability_df['cm_cp_distance'].iloc[-1]:.3f} m",
                f"{(stability_df['cm_cp_distance'].iloc[-1] - stability_df['cm_cp_distance'].iloc[0]):.3f} m"
            ]
        }
        st.dataframe(pd.DataFrame(stats_data), use_container_width=True)

    # Línea divisoria
    st.markdown("---")

    # Análisis de riesgo
    st.subheader("Risk Analysis")
    
    # Calcular el área de seguridad
    max_range = metrics['max_range']  # km
    safety_factor = 1.15  # 15% extra
    safe_range = max_range * safety_factor
    
    # Definir límites de seguridad
    safety_box = {
        'width': 4.5,  # km
        'length': 4.5,  # km
        'height': 1.8   # km
    }

    # Verificar si la trayectoria está dentro de los límites
    trajectory_in_bounds = (
        chart_data['Range'].max() / 1000 <= safety_box['length'] and  # Convertir m a km
        abs(chart_data['East coordinate']).max() / 1000 <= safety_box['width'] / 2 and
        abs(chart_data['North coordinate']).max() / 1000 <= safety_box['width'] / 2 and
        chart_data['Up coordinate'].max() / 1000 <= safety_box['height']
    )

    # Crear área de seguridad para el mapa
    center_lat = chart_data['Location Latitude'].iloc[0]
    center_lon = chart_data['Location Longitude'].iloc[0]
    
    def create_safety_box(center_lat, center_lon, width_km, length_km):
        """Crea un polígono rectangular para el área segura"""
        lat_delta = (width_km / 2) / 111.32  # 1 grado ≈ 111.32 km
        lon_delta = (length_km / 2) / (111.32 * cos(center_lat * pi / 180))
        
        return [
            [center_lon - lon_delta, center_lat - lat_delta],
            [center_lon + lon_delta, center_lat - lat_delta],
            [center_lon + lon_delta, center_lat + lat_delta],
            [center_lon - lon_delta, center_lat + lat_delta],
            [center_lon - lon_delta, center_lat - lat_delta]
        ]

    # Crear GeoJSON con área de seguridad
    safety_area = create_safety_box(center_lat, center_lon, 
                                  safety_box['width'], 
                                  safety_box['length'])

    geojson_dict = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": list(zip(chart_data_compressed['Longitude'], 
                                         chart_data_compressed['Latitude']))
                },
                "properties": {
                    "name": "Flight Path",
                    "color": [255, 0, 0]
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [safety_area]
                },
                "properties": {
                    "name": "Safety Area",
                    "color": [0, 255, 0, 80]
                }
            }
        ]
    }

    # Mostrar resultados del análisis
    risk_col1, risk_col2 = st.columns([2, 1])

    with risk_col2:
        st.write("Safety Analysis")
        st.info(f"""
        **Safety Box Dimensions**:
        - Width: {safety_box['width']} km
        - Length: {safety_box['length']} km
        - Height: {safety_box['height']} km
        
        **Flight Analysis**:
        - Max Range: {max_range:.2f} km
        - Range + Safety Factor: {safe_range:.2f} km
        - Max Height: {metrics['max_alt']:.2f} km
        
        **Safety Status**: {'✅ Within Limits' if trajectory_in_bounds else '❌ Exceeds Limits'}
        """)

    with risk_col1:
        risk_map = KeplerGl(height=600, data={"risk_layer": geojson_dict})
        risk_map.config = {
            "version": "v1",
            "config": {
                "mapState": {
                    "bearing": 0,
                    "latitude": center_lat,
                    "longitude": center_lon,
                    "pitch": 45,
                    "zoom": 12,
                },
                "visState": {
                    "layers": [
                        {
                            "type": "geojson",
                            "config": {
                                "dataId": "risk_layer",
                                "visible": True,
                                "opacity": 0.8
                            }
                        }
                    ]
                }
            }
        }
        keplergl_static(risk_map, height=600, width=1000, center_map=True)

    # PDF Export Section
    st.markdown("---")
    st.subheader("📊 Export Report")

    # Create export columns
    export_col1, export_col2, export_col3 = st.columns([1, 1, 1])

    with export_col1:
        st.write("**Export Options**")
        export_format = st.selectbox(
            "Select Export Format",
            ["PDF Report", "CSV Data", "Summary JSON"]
        )

    with export_col2:
        st.write("**Report Content**")
        include_plots = st.checkbox("Include Plots", value=True)
        include_raw_data = st.checkbox("Include Raw Data", value=False)
        include_analysis = st.checkbox("Include Analysis", value=True)

    with export_col3:
        st.write("**Generate Report**")
        report_title = st.text_input("Report Title", "Rocket Simulation Report")
        
        if st.button("📥 Generate Export", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    if export_format == "PDF Report":
                        pdf_buffer = generate_pdf_report(
                            chart_data, 
                            metrics, 
                            stability_df,
                            report_title,
                            include_plots,
                            include_analysis
                        )
                        
                        st.success("PDF report generated successfully!")
                        
                        st.download_button(
                            label="📄 Download PDF Report",
                            data=pdf_buffer,
                            file_name=f"rocket_simulation_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        
                    elif export_format == "CSV Data":
                        csv_data = generate_csv_export(chart_data, stability_df)
                        
                        st.download_button(
                            label="📊 Download CSV Data",
                            data=csv_data,
                            file_name=f"rocket_simulation_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                    elif export_format == "Summary JSON":
                        json_data = generate_json_summary(metrics, stability_df)
                        
                        st.download_button(
                            label="📋 Download JSON Summary",
                            data=json_data,
                            file_name=f"rocket_simulation_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                        
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")

except KeyError as e:
    st.error(f"Error: Columna no encontrada - {e}")
    if 'chart_data' in locals():
        st.write("Columnas disponibles:", list(chart_data.columns))
except Exception as e:
    st.error(f"Error inesperado: {e}")