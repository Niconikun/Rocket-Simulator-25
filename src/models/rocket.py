# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl


"""
Módulo principal para la simulación de cohetes.

Este módulo contiene la clase Rocket que maneja todos los cálculos
relacionados con la dinámica, aerodinámica y control del cohete durante
la simulación.

Clases:
    Rocket: Clase principal que simula el comportamiento del cohete.

Referencias:
    [Regan93] Regan/Anandakrishnan (1993) - Dynamics of Atmospheric Re-Entry
    [Valle22] Vallejos (2022) - Mejora del alcance de un cohete chaff
    [Oroz22] Orozco (2022) - Estimación de trayectoria y actitud para un cohete chaff
    [Barro67] Barrowman (1967) - The Practical Calculation of the Aerodynamic Characteristic of Slender Finned Vehicles
    [Yang19] Yang (2019) - Spacecraft Modeling, Attitude Determination, and Control

Ecuaciones Principales:
    1. Dinámica Traslacional:
       F = ma -> m(dv/dt) = F_total + mg
    
    2. Dinámica Rotacional:
       dω/dt = J⁻¹(M - ω × (Jω))
    
    3. Cinemática del Cuaternión:
       dq/dt = 1/2 Ω(ω)q

    4. Fuerzas Aerodinámicas:
       F_d = 1/2 ρv²C_d A
       F_l = 1/2 ρv²C_l A
"""

# Imports
import numpy as np
import navpy as nav
from cmath import pi
import json
import streamlit as st
import logging
from src.models.engine import Engine
from src.models.aerodynamics import Aerodynamics
from src.utils.mattools import MatTools as Mat
from src.utils.geotools import GeoTools as Geo

class Rocket(object):
    """
    Clase principal para la simulación de cohetes.

    Esta clase maneja todos los aspectos de la simulación, incluyendo:
    - Dinámica traslacional y rotacional
    - Fuerzas aerodinámicas
    - Propulsión
    - Integración numérica
    - Almacenamiento de datos históricos

    Atributos:
        r_enu (np.ndarray): Posición en coordenadas ENU [m]
        v_enu (np.ndarray): Velocidad en coordenadas ENU [m/s]
        q_enu2b (np.ndarray): Cuaternión de rotación ENU a body [-]
        w_enu (np.ndarray): Velocidad angular en ENU [rad/s]
        mass (float): Masa actual del cohete [kg]
    """
    def __init__(self,r_enu_0,v_enu_0,q_enu2b_0,w_enu_0, initial_mass):
        
        #______Initial data_______#
        self.r_enu=r_enu_0        # [m]       # East-North-Up location from launching platform
        self.v_enu=v_enu_0        # [m/s]     # East-North-Up velocity from launching platform
        self.q_enu2b=q_enu2b_0    # [-]       # Quaternion that rotates from launching platform in East-North-Up to bodyframe
        self.w_enu=w_enu_0        # [rad/s]   # East-North-Up rotational velocity from launching platform

        self.mass= initial_mass           # [kg]      # Initial total mass

        self.time=0               # [s]       # Initial time of simulation

        #_______Historical_________#
        #*Note: All measure units in these lists are the same as used during calculation and indicated properly in every method
        self.hist_r_enu=[]       # East-North-Up location from platform
        self.hist_v_enu=[]       # East-North-Up velocity from platform
        self.hist_q_enu2b=[]     # Quaternion that rotates from East-North-Up to bodyframe (q=qi + qj + qk + q0... or q=[q1,q2,q3,q4])
        self.hist_q_enu2b_1=[]   # Quaternion first element (qi or q1)
        self.hist_q_enu2b_2=[]   # Quaternion second element (qj or q2)
        self.hist_q_enu2b_3=[]   # Quaternion third element (qk or q3)
        self.hist_q_enu2b_4=[]   # Quaternion fourth element or scalar part (q0 or q4)
        self.hist_w_enu=[]       # East-North-Up rotational velocity from platform

        self.hist_gmst=[]        # Greenwich Mean Sidereal Time
        self.hist_time=[]        # Time of simulation

        self.hist_mass=[]        # Mass
        self.hist_inertia_b=[]   # Inertia
        self.hist_cm_b=[]        # Centre of mass 

        self.hist_yaw=[]         # Yaw from East
        self.hist_pitch=[]       # Pitch from ground
        self.hist_roll=[]        # Roll (assumed to be always equal to zero)

        self.hist_v_b=[]         # Velocity in bodyframe
        self.hist_v_bx=[]        # Velocity in bodyframe (X or axial component)
        self.hist_v_by=[]        # Velocity in bodyframe (Y or cross component...if Rocket point to East at the beginning, this would be pointing towards North)
        self.hist_v_bz=[]        # Velocity in bodyframe (Z of cross component...if X and Y are parallel to East and North, respectively, this would point Up)
        self.hist_alpha=[]       # Angle of attack

        self.hist_density=[]     # Density
        self.hist_press_amb=[]   # Pressure
        self.hist_v_sonic=[]     # Speed of sound

        self.hist_mach=[]        # Mach number
        self.hist_drag_coeff=[]  # Drag coefficient
        self.hist_lift_coeff=[]  # Lift coefficient
        self.hist_cp_b=[]        # Centre of pressure

        self.hist_mass_flux=[]   # Mass flux
        self.hist_thrust=[]      # Thrust

        self.hist_drag=[]               # Drag
        self.hist_lift=[]               # Lift
        self.hist_cm2cp_b=[]            # Centre of pressure's distance from centre of mass
        self.hist_forces_aero_b = []     # Aerodynamic forces in bodyframe
        self.hist_torques_aero_b=[]     # Aerodynamic torques in bodyframe
        self.hist_accel_b = []

        self.hist_forces_engine_b=[]    # Forces produced by engine in bodyframe
        self.hist_torques_engine_b=[]   # Torques produced by engine in bodyframe

        self.hist_range=[]              # Horizontal range norm from platform
        self.hist_east=[]               # Distance towards East from platform
        self.hist_north=[]              # Distance towards North from platform
        self.hist_up=[]                 # Distance towards Up from platform (can be treated as altitude)

        self.hist_v_norm=[]

        self.hist_coord=[]
        self.hist_lat=[]
        self.hist_long=[]
        self.hist_alt=[]

        self.forces_aero_b = np.array([0.0, 0.0, 0.0])
        self.torques_aero_b = np.array([0.0, 0.0, 0.0])
        self.cm2cp_b = np.array([0.0, 0.0, 0.0])
        self.accel_b = np.zeros(3)   # Inicializar forces_aero_b

        self.parachute = None
        self.has_parachute = False
        
        # Historial para paracaídas
        self.hist_parachute_state = []
        self.hist_parachute_force = []

        # Preallocate historical arrays
        self._initialize_history_arrays()
    
    def _initialize_history_arrays(self):
        """Inicializa los arrays históricos como listas Python"""
        # Inicializar como listas vacías en lugar de numpy arrays
        self.hist_r_enu = []
        self.hist_v_enu = []
        self.hist_q_enu2b = []
        self.hist_q_enu2b_1 = []
        self.hist_q_enu2b_2 = []
        self.hist_q_enu2b_3 = []
        self.hist_q_enu2b_4 = []
        self.hist_w_enu = []
        self.hist_gmst = []
        self.hist_time = []
        self.hist_mass = []
        self.hist_inertia_b = []
        self.hist_cm_b = []
        self.hist_yaw = []
        self.hist_pitch = []
        self.hist_roll = []
        self.hist_v_b = []
        self.hist_v_bx = []
        self.hist_v_by = []
        self.hist_v_bz = []
        self.hist_alpha = []
        self.hist_density = []
        self.hist_press_amb = []
        self.hist_v_sonic = []
        self.hist_mach = []
        self.hist_drag_coeff = []
        self.hist_lift_coeff = []
        self.hist_cp_b = []
        self.hist_mass_flux = []
        self.hist_thrust = []
        self.hist_drag = []
        self.hist_lift = []
        self.hist_cm2cp_b = []
        self.hist_forces_aero_b = []
        self.hist_torques_aero_b = []
        self.hist_forces_engine_b = []
        self.hist_torques_engine_b = []
        self.hist_range = []
        self.hist_east = []
        self.hist_north = []
        self.hist_up = []
        self.hist_v_norm = []
        self.hist_coord = []
        self.hist_lat = []
        self.hist_long = []
        self.hist_alt = []



    def update_gmst(self,gmst):
        """
        Actualiza el tiempo sideral medio de Greenwich.

        Args:
            gmst (float): Tiempo sideral medio de Greenwich [rad]

        Notas:
            GMST es necesario para la rotación entre sistemas ECEF y ECI.
        """
        self.gmst=gmst  # [rad]    # Greenwich Mean Sidereal Time (rotation of Earth Centered-Earth Fixed from Earth Centered Inertial systems)

    def update_mass_related(self, burn_time, cm_before_x, cm_before_y, cm_before_z, I_before_x, I_before_y, I_before_z, cm_after_x, cm_after_y, cm_after_z, I_after_x, I_after_y, I_after_z):
        """
        Actualiza propiedades relacionadas con la masa del cohete.

        Args:
            burn_time (float): Tiempo total de quemado [s]
            cm_before_x/y/z (float): Posición del centro de masa antes del quemado [m]
            I_before_x/y/z (float): Momentos de inercia antes del quemado [kg·m²]
            cm_after_x/y/z (float): Posición del centro de masa después del quemado [m]
            I_after_x/y/z (float): Momentos de inercia después del quemado [kg·m²]

        Notas:
            Los valores se obtienen de Autodesk Inventor.
        """
        self.burn_time=burn_time    # [s]    # Propellant total burning time                                                  
        if self.time<=self.burn_time:
            self.cm_b=np.array([cm_before_x,cm_before_y,cm_before_z])                                 # [m]        # Centre of Mass before burning obtained via Autodesk Inventor
            self.inertia_b=np.array([I_before_x, I_before_y, I_before_z])   # [kg m2]    # Inertia before burning obtained via Autodesk Inventor
        else: 
            self.cm_b=np.array([cm_after_x, cm_after_y, cm_after_z])                                # [m]        # Centre of Mass after burning obtained via Autodesk Inventor
            self.inertia_b=np.array([I_after_x, I_after_y, I_after_z])     # [kg m2]    # Inertia after burning obtained via Autodesk Inventor 

    def update_pos_vel(self,coordinates):
        """
        Actualiza todas las variables relacionadas con posición y velocidad.

        Args:
            coordinates (np.ndarray): Coordenadas de la plataforma [lat, lon, alt]

        Cálculos:
            1. Actitud (ángulos de Euler desde cuaternión)
            2. Velocidades en marco del cuerpo
            3. Ángulo de ataque
            4. Posiciones en diferentes marcos de referencia
            5. Velocidades angulares

        Referencias:
            [Oroz22] Para convenciones de ángulos
        """
        
        #_____Attitude calculation______#
        q0=self.q_enu2b[3]       # Quaternion first three elements (vectorial or imaginary part)
        qvec=self.q_enu2b[0:3]   # Quaternion last element (scalar or real part)
        angles=nav.quat2angle(q0,qvec,output_unit='deg',rotation_sequence='ZYX') 
        self.yaw=angles[0]       # Rotación respecto a East [deg] 
        self.pitch=-angles[1]    # Negativo cuando apunta arriba en plano XZ [deg]
        self.roll=angles[2]      # Rotación sobre eje longitudinal [deg]

        #_______Velocity related calculation_____#
        self.v_b=Mat.q_rot(self.v_enu,self.q_enu2b,0)    # [m/s]   # Rotation of velocity from East-North-Up system to bodyframe
        self.v_norm=np.linalg.norm(self.v_enu)           # [m/s]   # Norm or magnitude of velocity from a East-North-Up system

        #_______Angle of attack___________#
        self.alpha=Mat.angle_vector_z(self.v_b)          # [deg]    # Angle of attack in a XZ plane (see [Oroz22])       

        #______Location related calculations_____#
        self.r_platform_ecef=Geo.geo2ecef(coordinates)              # [m]     # Platform's Earth Centered-Earth Fixed location  
        self.r_relative_ecef=Geo.enu2ecef(coordinates,self.r_enu)   # [m]     # Rocket's location from platform in Earth Centered-Earth Fixed system
        self.r_ecef= self.r_platform_ecef + self.r_relative_ecef    # [m]     # Rocket's absolute location in Earth Centered-Earth Fixed
        range_h=self.r_enu - np.array([0,0,self.r_enu[2]])          # [m]     # Rocket's horizontal range vector from platform
        self.range=np.linalg.norm(range_h)                          # [m]     # Rocket's horizontal range norm from platform

        self.coord=Geo.ecef2geo(self.r_ecef)

        #_____Rotational velocity related calculations____#
        self.w_b=Mat.q_rot(self.w_enu,self.q_enu2b,0)               # [rad/s] # Rocket's rotational velocity in bodyframe   

    def update_atmosphere(self,density,press_amb,v_sonic):
        
        """
        Actualiza las propiedades atmosféricas.

        Args:
            density (float): Densidad del aire [kg/m³]
            press_amb (float): Presión atmosférica [Pa]
            v_sonic (float): Velocidad del sonido [m/s]

        Referencias:
            - Atmósfera Estándar Internacional (ISA)
        """
        self.density = density      
        self.press_amb = press_amb  
        self.v_sonic = v_sonic 
        self.density=density      # [kg m3]   # Atmospheric air density
        self.press_amb=press_amb  # [Pa]      # Atmospheric pressure
        self.v_sonic=v_sonic      # [m/s]     # Speed of sound 

    def update_aerodynamics(self, rocket_name):
        """
        Actualiza las características aerodinámicas del cohete.

        Args:
            rocket_name (str): Nombre del cohete para cargar su configuración

        Cálculos:
            1. Número Mach
            2. Coeficientes aerodinámicos (CD, CL)
            3. Centro de presión

        Referencias:
            [Barro67] Método de Barrowman para coeficientes
        """
        # Calcular número Mach
        self.mach = 0 if self.v_norm == 0 else self.v_norm/self.v_sonic

        try:
            # Cargar configuración del cohete
            with open('data/rockets/configs/' + rocket_name + '.json', 'r') as file:
                rocket_settings = json.load(file)

            # Crear diccionario de geometría
            geometry = {
                'len_warhead': rocket_settings['nosecone']['length'],
                'diameter_warhead_base': rocket_settings['nosecone']['diameter'],
                'len_nosecone_fins': rocket_settings['geometry']['length nosecone fins'],
                'len_nosecone_rear': rocket_settings['geometry']['total length'],
                'len_bodytube_wo_rear': rocket_settings['fuselage']['length'],
                'diameter_bodytube': rocket_settings['fuselage']['diameter'],
                'len_rear': rocket_settings['rear_section']['length'],
                'end_diam_rear': rocket_settings['rear_section']['diameter'],
                'diameter_rear_bodytube': rocket_settings['rear_section']['diameter'],
                'diameter_bodytube_fins': rocket_settings['fuselage']['diameter'],
                'fins_chord_root': rocket_settings['fins']['chord_root'],
                'fins_chord_tip': rocket_settings['fins']['chord_tip'],
                'fins_mid_chord': rocket_settings['fins']['mid_chord'],
                'fins_span': rocket_settings['fins']['span'],
                'N_fins': rocket_settings['fins']['N_fins']
            }

            # Crear instancia de Aerodynamics con validación
            try:
                aero = Aerodynamics(self.mach, self.alpha, geometry)
                self.drag_coeff = aero.cd
                self.lift_coeff = aero.cl
                self.cp_b = aero.xcp
            except ValueError as e:
                logging.error(f"Error en cálculo aerodinámico: {str(e)}")
                st.error(f"Error en cálculos aerodinámicos: {str(e)}")
                # Usar valores por defecto seguros
                self.drag_coeff = 0.5
                self.lift_coeff = 0.0
                self.cp_b = np.array([0.5, 0, 0])

        except FileNotFoundError:
            logging.error(f"No se encontró el archivo de configuración para {rocket_name}")
            st.error(f"No se encontró la configuración del cohete {rocket_name}")
        except Exception as e:
            logging.error(f"Error cargando configuración: {str(e)}")
            st.error(f"Error en la configuración aerodinámica: {str(e)}")

    def update_engine(self, rocket_name):
        """
        Actualiza las características del motor.

        Args:
            rocket_name (str): Nombre del cohete para cargar configuración del motor

        Cálculos:
            1. Flujo másico
            2. Empuje total considerando presión ambiente
        
        Referencias:
            - Sutton, G. P., & Biblarz, O. (2016). Rocket propulsion elements
        """
        
        with open('data/rockets/configs/'+ rocket_name +'.json', 'r') as file:
            rocket_settings = json.load(file)

        # Check if the rocket references a saved engine configuration
        engine_config_name = rocket_settings['engine'].get('config_name')
        
        if engine_config_name:
            # Load from saved engine configuration
            try:
                engine_config_path = f'data/rockets/engines/{engine_config_name}.json'
                with open(engine_config_path, 'r') as f:
                    engine_config = json.load(f)
                
                # Use enhanced engine with full configuration
                Eng = Engine(
                    time=self.time,
                    ambient_pressure=self.press_amb,
                    burn_time=engine_config['burn_time'],
                    nozzle_exit_diameter=engine_config['nozzle_exit_diameter'],
                    mass_flux_max=engine_config['mass_flux_max'],
                    gas_speed=engine_config['gas_speed'],
                    exit_pressure=engine_config['exit_pressure'],
                    mode=engine_config.get('mode', 'simple'),
                    **engine_config.get('srm_parameters', {})
                )
                
            except FileNotFoundError:
                # Fall back to rocket engine configuration if saved config not found
                st.warning(f"Engine configuration '{engine_config_name}' not found. Using rocket engine settings.")
                Eng = self._create_engine_from_rocket_config(rocket_settings)
        else:
            # Use legacy rocket engine configuration
            Eng = self._create_engine_from_rocket_config(rocket_settings)

        self.mass_flux = Eng.mass_flux              # [kg/s] # Engine mass flux
        self.thrust = Eng.thrust                    # [N]    # Engine thrust

    def _create_engine_from_rocket_config(self, rocket_settings):
        """Helper method to create engine from rocket configuration (backward compatibility)."""
        burn_time = rocket_settings['engine']["burn_time"]
        nozzle_exit_diameter = rocket_settings['engine']["nozzle_exit_diameter"]
        mass_flux = rocket_settings['engine']["mass_flux"]
        gas_speed = rocket_settings['engine']["gas_speed"]
        exit_pressure = rocket_settings['engine']["exit_pressure"]

        return Engine(
            time=self.time,
            ambient_pressure=self.press_amb,
            burn_time=burn_time,
            nozzle_exit_diameter=nozzle_exit_diameter,
            mass_flux_max=mass_flux,
            gas_speed=gas_speed,
            exit_pressure=exit_pressure
        )


    def update_forces_aero(self, reference_area):
        """
        Calcula las fuerzas y momentos aerodinámicos.

        Args:
            reference_area (float): Área de referencia [m²]

        Cálculos:
            1. Presión dinámica: q = 1/2 ρV²
            2. Fuerzas: F = qSC
            3. Momentos: M = r × F

        Validaciones:
            - Ángulo de ataque entre -180° y 180°
            - Velocidad mínima para cálculos
            - Límites de fuerzas máximas
        """
        try:
            # Validar valores críticos
            if not (-180 <= self.alpha <= 180):
                raise ValueError(f"Ángulo de ataque inválido: {self.alpha}°")
                
            if self.v_norm < 1e-6:  # Velocidad casi cero
                self.drag = 0
                self.lift = 0
                return
                
            # Cálculo de fuerzas con validación
            dynamic_pressure = 0.5 * self.density * (self.v_norm**2)
            
            self.drag = dynamic_pressure * self.drag_coeff * reference_area
            self.lift = dynamic_pressure * self.lift_coeff * reference_area

            # Verificar valores razonables
            max_force = 10000  # 10kN como límite razonable
            if abs(self.drag) > max_force or abs(self.lift) > max_force:
                raise ValueError(f"Fuerzas excesivas: Drag={self.drag:.2f}N, Lift={self.lift:.2f}N")
                
            self.forces_drag_b = np.array([-self.drag, 0, 0])
            self.forces_lift_b = np.array([0, 0, self.lift])
            self.cm2cp_b=self.cm_b-self.cp_b                              # [m]   # Distance of centre of pressure from centre of mass
            self.forces_aero_b=self.forces_drag_b  + self.forces_lift_b   # [N]   # Lift can be neglected if necessary for evaluation
            self.torques_aero_b=np.cross(self.cm2cp_b,self.forces_aero_b) # [N m] # Torques produced by aerodynamic forces (lift mainly)
            
        except Exception as e:
            logging.error(f"Error en cálculo aerodinámico: {str(e)}")
            st.error(f"Error en fuerzas aerodinámicas: {str(e)}")

    def update_forces_engine(self):
        """
        Calcula las fuerzas y torques producidos por el motor.

        Cálculos:
            1. Vector de empuje en el marco del cuerpo
            2. Torques del motor (asumidos como cero por diseño)

        Notas:
            Se asume que el empuje está alineado con el eje longitudinal del cohete.
        """
        self.forces_engine_b=np.array([self.thrust,0,0])    # [N]    # Thrust vector in bodyframe
        self.torques_engine_b=np.zeros(3)                   # [N m]  # Torques produced by engine in bodyframe (assumed to be zero )

    def update_forces_torques(self):
        """
        Calcula todas las fuerzas y torques en diferentes sistemas de referencia.

        Cálculos:
            1. Suma de fuerzas en marco del cuerpo (bodyframe)
            2. Transformación de fuerzas a marco ENU
            3. Suma de torques en marco del cuerpo
            4. Transformación de torques a marco ENU

        Referencias:
            [Yang19] Para transformaciones entre marcos de referencia
        """

        self.forces_b=self.forces_aero_b + self.forces_engine_b     # [N]   # Sum of all forces in bodyframe
        self.forces_enu=Mat.q_rot(self.forces_b,self.q_enu2b,1)     # [N]   # Sum of all forces in East-North-Up system

        self.torques_b=self.torques_aero_b                          # [N m] # Sum of all torques in bodyframe
        self.torques_enu=Mat.q_rot(self.torques_b,self.q_enu2b,1)   # [N m] # Sum of all torques in East-North-Up system 
    
    def update_g_accel(self,coordinates):
        """
        Calcula la aceleración gravitacional en todos los sistemas de referencia.

        Args:
            coordinates (np.ndarray): Coordenadas de la plataforma [lat, lon, alt]

        Cálculos:
            1. Vector unitario en ECEF
            2. Transformación a ENU
            3. Cálculo de aceleración gravitacional
            4. Transformación a marco del cuerpo

        Referencias:
            [Regan93] Para modelo gravitacional
        """
        self.g_vector_ecef=Mat.normalise(self.r_ecef)                  # [-]     # Rocket's location unit vector in Earth Centered-Earth Fixed system
        self.g_vector_enu=Geo.ecef2enu(coordinates,self.g_vector_ecef) # [-]     # Rocket's location unit vector in East-North-Up system
        self.g_enu=-9.81*self.g_vector_enu                             # [m/s2]  # Rocket's gravitational acceleration in East-North-Up system
        #self.g_enu=np.array([0,0,-9.81])   # [m/s2] # Gravitational acceleration assuming it parallel to Up direction
        self.g_b=Mat.q_rot(self.g_enu,self.q_enu2b,0)                  # [m/s2]  # Rocket's gravitational acceleration in bodyframe (used later for conditional only)
 

    def dynamics(self, x):
        """
        Calcula las ecuaciones de movimiento del cohete.

        Args:
            x (np.ndarray): Vector de estado [r_enu, v_enu, q_enu2b, w_b, mass]

        Returns:
            np.ndarray: Derivadas temporales del vector de estado

        Ecuaciones:
            1. Traslación: 
                dr/dt = v
                dv/dt = F/m + g

            2. Rotación:
                dq/dt = 1/2 Ω(ω)q
                dω/dt = J⁻¹(M - ω × (Jω))

            3. Masa:
                dm/dt = -ṁ
        """
        r_enu = x[0:3]
        v_enu = x[3:6]
        q_enu2b = x[6:10]
        w_b = x[10:13]
        mass = x[13]

        # Modificar la condición de parada
        total_force = np.linalg.norm(self.forces_b)
        total_grav = np.linalg.norm(self.g_b)

        # Solo detener si la velocidad es muy baja y las fuerzas son menores que la gravedad
        if total_force <= total_grav and np.linalg.norm(v_enu) < 1.0:
            r_dot_enu = np.zeros(3)
            v_dot_enu = np.zeros(3)
        else:
            r_dot_enu = v_enu
            v_dot_enu = (1/mass)*self.forces_enu + self.g_enu

        # Calcular aceleración en bodyframe
        forces_total_b = self.forces_b + Mat.q_rot(self.g_enu, self.q_enu2b, 0) * mass
        self.accel_b = forces_total_b / mass  # [m/s²]

        #________Attitude_________#
        
        j=Mat.vec2mat(self.inertia_b)    # [kg m2]     # Rocket's inertia as a 3x3 matrix
        j_invs=np.linalg.inv(j)          # [1/(kg m2)] # Rocket's inertia inverse
 
        w_enu=Mat.q_rot(w_b,q_enu2b,1)   # [rad/s]     # Rotational velocity in East-North-Up system
        w_enu_skew4=Mat.skew4(w_enu)     # [rad/s]     # Rotational velocity as a 4x4 skew matrix

        # Conditionals to avoid problems with negative values of velocity and setting and end when landing (same for consistency)
        if total_force <= total_grav and np.linalg.norm(v_enu) < 1.0:
            q_dot_enu2b=np.zeros(4)
            w_dot_b=np.zeros(3) 
        else:
            q_dot_enu2b=0.5*w_enu_skew4.dot(q_enu2b)                                 # Time derivative of quaternion [Yang19]
            w_dot_b=np.dot(j_invs,(np.cross(-w_b,(np.dot(j,w_b))) + self.torques_b)) # [rad/s2] Time derivative of rotational velocity in bodyframe (for simplicity of calculation) [Yang19]
        
        #______Mass_____________#
        
        mass_dot=-self.mass_flux   # [kg/s]    # Time derivative of mass

        # Concatenation of variables
        f_traj=np.concatenate((r_dot_enu,v_dot_enu))
        f_att=np.concatenate((q_dot_enu2b,w_dot_b))
        f_mov=np.concatenate((f_traj,f_att))
        m_dot_aux=np.array([mass_dot]) # Auxiliary array of mass_dot for concatenation
        fx=np.concatenate((f_mov,m_dot_aux))
        return fx

    def RK4_update(self,dt):
        
        """
        Propaga las variables de estado usando el método Runge-Kutta de 4to orden.

        Args:
            dt (float): Paso de tiempo [s]

        Cálculos:
            1. Concatenación de variables de estado
            2. Cálculo de coeficientes k1, k2, k3, k4
            3. Actualización del vector de estado
            4. Normalización del cuaternión

        Referencias:
            - Butcher, J.C. (2016). Numerical Methods for Ordinary Differential Equations
        """

        # Consecutive concatenation of all required variables
        traj=np.concatenate((self.r_enu,self.v_enu))
        att=np.concatenate((self.q_enu2b,self.w_b))
        mov=np.concatenate((traj,att))
        mass=np.array([self.mass])     # Auxiliary mass_dot to avoid float error in Numpy
        x=np.concatenate((mov,mass))

        #_________Runge-Kutta 4 sequence________#
        k1=self.dynamics(x)
        xk2=x + 0.5*dt*k1

        k2=self.dynamics(xk2)
        xk3=x+ 0.5*dt*k2

        k3=self.dynamics(xk3)
        xk4=x+ dt*k3

        k4=self.dynamics(xk4)

        new_x= x + (dt/6)*(k1 + 2*k2 + 2*k3 + k4)

        #_______Obtaining data from concatenated results_____#
        self.r_enu=new_x[0:3]
        self.v_enu=new_x[3:6]
        
        q_enu2b=new_x[6:10]
        q_norm = np.linalg.norm(q_enu2b)
        if q_norm > 0:
            self.q_enu2b = q_enu2b / q_norm
        else:
            st.error("Error: Quaternion normalization failed")
            raise RuntimeError("Quaternion became zero")
        
        w_b=new_x[10:13]
        self.w_enu=Mat.q_rot(w_b,q_enu2b,1)

        self.mass=new_x[13]

    def save_data(self):
        """Saves all obtained data before propagation"""
        try:
            # Datos básicos
            self.hist_time.append(self.time)
            self.hist_gmst.append(self.gmst)
            
            # Posición y velocidad
            self.hist_r_enu.append(list(self.r_enu))
            self.hist_v_enu.append(list(self.v_enu))
            self.hist_range.append(float(self.range))
            self.hist_east.append(float(self.r_enu[0]))
            self.hist_north.append(float(self.r_enu[1]))
            self.hist_up.append(float(self.r_enu[2]))
            self.hist_v_norm.append(float(self.v_norm))
            
            # Actitud y rotación
            self.hist_q_enu2b.append(list(self.q_enu2b))
            self.hist_q_enu2b_1.append(float(self.q_enu2b[0]))
            self.hist_q_enu2b_2.append(float(self.q_enu2b[1]))
            self.hist_q_enu2b_3.append(float(self.q_enu2b[2]))
            self.hist_q_enu2b_4.append(float(self.q_enu2b[3]))
            self.hist_w_enu.append(list(self.w_enu))
            
            # Ángulos
            self.hist_yaw.append(float(self.yaw))
            self.hist_pitch.append(float(self.pitch))
            self.hist_roll.append(float(self.roll))
            self.hist_alpha.append(float(self.alpha))
            
            # Velocidades en bodyframe
            self.hist_v_b.append(list(self.v_b))
            self.hist_v_bx.append(float(self.v_b[0]))
            self.hist_v_by.append(float(self.v_b[1]))
            self.hist_v_bz.append(float(self.v_b[2]))
            
            # Datos atmosféricos
            self.hist_density.append(float(self.density))
            self.hist_press_amb.append(float(self.press_amb))
            self.hist_v_sonic.append(float(self.v_sonic))
            self.hist_mach.append(float(self.mach))
            
            # Coeficientes aerodinámicos
            self.hist_drag_coeff.append(float(self.drag_coeff))
            self.hist_lift_coeff.append(float(self.lift_coeff))
            
            # Masa e inercia
            self.hist_mass.append(float(self.mass))
            self.hist_inertia_b.append(list(self.inertia_b))
            self.hist_cm_b.append(list(self.cm_b))
            self.hist_cp_b.append(list(self.cp_b))
            
            # Fuerzas y torques
            self.hist_drag.append(float(self.drag))
            self.hist_lift.append(float(self.lift))
            self.hist_thrust.append(float(self.thrust))
            self.hist_mass_flux.append(float(self.mass_flux))
            self.hist_accel_b.append(list(self.accel_b))
            
            # Vectores de fuerza y torque
            self.hist_cm2cp_b.append(list(self.cm2cp_b))
            self.hist_forces_aero_b.append(list(self.forces_aero_b))
            self.hist_torques_aero_b.append(list(self.torques_aero_b))
            self.hist_forces_engine_b.append(list(self.forces_engine_b))
            self.hist_torques_engine_b.append(list(self.torques_engine_b))
            
            # Coordenadas geográficas
            self.hist_coord.append(list(self.coord))
            self.hist_lat.append(float(self.coord[0]))
            self.hist_long.append(float(self.coord[1]))
            self.hist_alt.append(float(self.coord[2]))

        except Exception as e:
            logging.error(f"Error en save_data: {str(e)}")
            st.error(f"Error guardando datos históricos: {str(e)}")

    def update_time(self,dt):
        """
        Actualiza el tiempo de simulación.

        Args:
            dt (float): Incremento de tiempo [s]

        Notas:
            Método simple pero necesario para mantener consistencia en la simulación
        """
        self.time+=dt   # [s]