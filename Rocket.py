# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** Rocket.py ***

Contains:
Module that calculates all data to be obtained by a single rocket

External dependencies:
numpy           -Numpy Python extension. http://numpy.org/
                 Version: Numpy 1.22.3
navpy           -Numpy-based library for attitude determination. https://github.com/NavPy/NavPy/
                 Version: 1.0
MatTools        -Self-written python module containing mathematical functions
Aerodynamics    -Self-written python module containing aerodynamics data 
Engine          -Self-written python module containing engine performance data
GeoTools        -Self-written python module containing functions for reference systems conversion

Internal dependencies:
cmath       -cMath Python extension. https://docs.python.org/3/library/cmath.html

Changelog:
Date          Name              Change
__ _          __ _              ____ _
15/08/2022    Jorge Orozco      Initial release

References:
Short       Author,Year                 Title
___ _       _________ _                 ___ _
[Regan93]   Regan/Anandakrishnan,1993   Dynamics of Atmospheric Re-Entry
[Valle22]   Vallejos,2022               Mejora del alcance de un cohete chaff
[Oroz22]    Orozco,2022                 Estimación de trayectoria y actitud para un cohete chaff
[Barro67]   Barrowman,1967              The Practical Calculation of the Aerodynamic Characteristic of Slender Finned Vehicles
[Yang19]    Yang,2019                   Spacecraft Modeling, Attitude Determination, and Control. Quaternion-based Approach


"""
# Imports
import numpy as np
import navpy as nav
import MatTools as Mat
from Aerodynamics import Aerodynamics
from Engine import Engine
from cmath import pi
import GeoTools as Geo
import json
import streamlit as st
import logging

class Rocket(object):
    "Calculates all data during simulation. It's the main module of simulation"
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
        "Updates Greenwich Mean Sidereal Time from Planet Module"
        self.gmst=gmst  # [rad]    # Greenwich Mean Sidereal Time (rotation of Earth Centered-Earth Fixed from Earth Centered Inertial systems)

    def update_mass_related(self, burn_time, cm_before_x, cm_before_y, cm_before_z, I_before_x, I_before_y, I_before_z, cm_after_x, cm_after_y, cm_after_z, I_after_x, I_after_y, I_after_z):
        "Updates mass related data: Centre of Mass and Inertia"
        self.burn_time=burn_time    # [s]    # Propellant total burning time                                                  
        if self.time<=self.burn_time:
            self.cm_b=np.array([cm_before_x,cm_before_y,cm_before_z])                                 # [m]        # Centre of Mass before burning obtained via Autodesk Inventor
            self.inertia_b=np.array([I_before_x, I_before_y, I_before_z])   # [kg m2]    # Inertia before burning obtained via Autodesk Inventor
        else: 
            self.cm_b=np.array([cm_after_x, cm_after_y, cm_after_z])                                # [m]        # Centre of Mass after burning obtained via Autodesk Inventor
            self.inertia_b=np.array([I_after_x, I_after_y, I_after_z])     # [kg m2]    # Inertia after burning obtained via Autodesk Inventor 

    def update_pos_vel(self,coordinates):
        "Updates all data related to location and velocity"
        
        #_____Attitude calculation______#
        q0=self.q_enu2b[3]       # Quaternion first three elements (vectorial or imaginary part)
        qvec=self.q_enu2b[0:3]   # Quaternion last element (scalar or real part)
        angles=nav.quat2angle(q0,qvec,output_unit='deg',rotation_sequence='ZYX') 
        self.yaw=angles[0]       # [deg]   # Yaw 
        self.pitch=-angles[1]    # [deg]   # Pitch  (it is negative when pointing up in a XZ plane...see [Oroz22])
        self.roll=angles[2]      # [deg]   # Roll

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
        "Updates environment atmospheric properties from Atmosphere Module"
        self.density=density      # [kg m3]   # Atmospheric air density
        self.press_amb=press_amb  # [Pa]      # Atmospheric pressure
        self.v_sonic=v_sonic      # [m/s]     # Speed of sound 

    def update_aerodynamics(self,rocket_name):
        "Updates aerodynamic characteristics from Aerodynamics Module"
        # Conditional to avoid Runtime Warning for division by zero
       
        if self.v_norm==0:
            self.mach=0                           # [-]    # Mach number
        else:
            self.mach=self.v_norm/self.v_sonic    # [-]    # Mach number
        
        with open('rockets.json', 'r') as file:
            rocket_settings = json.load(file)

        len_warhead = rocket_settings[rocket_name]['geometry']["len_warhead"] 
        len_nosecone_fins = rocket_settings[rocket_name]['geometry']["len_nosecone_fins"]
        len_nosecone_rear = rocket_settings[rocket_name]['geometry']["len_nosecone_rear"]
        len_bodytube_wo_rear = rocket_settings[rocket_name]['geometry']["len_bodytube_wo_rear"]
        fins_chord_root = rocket_settings[rocket_name]['geometry']["fins_chord_root"]
        fins_chord_tip = rocket_settings[rocket_name]['geometry']["fins_chord_tip"]
        fins_mid_chord = rocket_settings[rocket_name]['geometry']["fins_mid_chord"]
        len_rear = rocket_settings[rocket_name]['geometry']["len_rear"]
        fins_span = rocket_settings[rocket_name]['geometry']["fins_span"]
        diameter_warhead_base = rocket_settings[rocket_name]['geometry']["diameter_warhead_base"]
        diameter_bodytube = rocket_settings[rocket_name]['geometry']["diameter_bodytube"]
        diameter_bodytube_fins = rocket_settings[rocket_name]['geometry']["diameter_bodytube_fins"]
        diameter_rear_bodytube = rocket_settings[rocket_name]['geometry']["diameter_rear_bodytube"]
        end_diam_rear = rocket_settings[rocket_name]['geometry']["end_diam_rear"]
        normal_f_coef_warhead = rocket_settings[rocket_name]['geometry']["normal_f_coef_warhead"]
        N_fins = rocket_settings[rocket_name]['geometry']["N_fins"]
        

        Aero=Aerodynamics(self.mach,self.alpha, len_warhead, len_nosecone_fins, len_nosecone_rear, len_bodytube_wo_rear, fins_chord_root, fins_chord_tip, fins_mid_chord, len_rear, fins_span, diameter_warhead_base, diameter_bodytube, diameter_bodytube_fins, diameter_rear_bodytube, end_diam_rear, normal_f_coef_warhead, N_fins)   # Aerodynamics instance 
        self.drag_coeff=Aero.cd                   # [-]    # Drag coefficient
        self.lift_coeff=Aero.cl                   # [-]    # Lift coefficient
        self.cp_b=Aero.xcp                        # [m]    # Location of centre of pressure from nose (ogive) tip

    def update_engine(self, rocket_name):
        
        with open('rockets.json', 'r') as file:
            rocket_settings = json.load(file)

        burn_time = rocket_settings[rocket_name]['engine']["burn_time"]
        nozzle_exit_diameter = rocket_settings[rocket_name]['engine']["nozzle_exit_diameter"]
        mass_flux = rocket_settings[rocket_name]['engine']["mass_flux"]
        gas_speed = rocket_settings[rocket_name]['engine']["gas_speed"]
        exit_pressure = rocket_settings[rocket_name]['engine']["exit_pressure"]

        "Updates engine performance characteristics from Engine Module"
        Eng=Engine(self.time,self.press_amb, burn_time, nozzle_exit_diameter, mass_flux, gas_speed, exit_pressure)      # Engine instance
        self.mass_flux=Eng.mass_flux              # [kg/s] # Engine mass flux
        self.thrust=Eng.thrust                    # [N]    # Engine thrust

    def update_forces_aero(self, reference_area):
        "Calculates all aerodynamics related data"
        
        ref_area= reference_area  # [m2]     # Reference area for drag and lift calculation [Valle22]
        raise RuntimeError(f"Mass became too low: {self.mass}kg")

    def update_forces_aero(self, reference_area):
        """Calcula las fuerzas aerodinámicas con mejores validaciones"""
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
        "Obtains forces and torques produced by the engine"
        self.forces_engine_b=np.array([self.thrust,0,0])    # [N]    # Thrust vector in bodyframe
        self.torques_engine_b=np.zeros(3)                   # [N m]  # Torques produced by engine in bodyframe (assumed to be zero )

    def update_forces_torques(self):
        "Calculates all forces and torques for different reference systems"
        self.forces_b=self.forces_aero_b + self.forces_engine_b     # [N]   # Sum of all forces in bodyframe
        self.forces_enu=Mat.q_rot(self.forces_b,self.q_enu2b,1)     # [N]   # Sum of all forces in East-North-Up system

        self.torques_b=self.torques_aero_b                          # [N m] # Sum of all torques in bodyframe
        self.torques_enu=Mat.q_rot(self.torques_b,self.q_enu2b,1)   # [N m] # Sum of all torques in East-North-Up system 
    
    def update_g_accel(self,coordinates):
        "Calculates gravitational acceleration in all reference systems"
        self.g_vector_ecef=Mat.normalise(self.r_ecef)                  # [-]     # Rocket's location unit vector in Earth Centered-Earth Fixed system
        self.g_vector_enu=Geo.ecef2enu(coordinates,self.g_vector_ecef) # [-]     # Rocket's location unit vector in East-North-Up system
        self.g_enu=-9.81*self.g_vector_enu                             # [m/s2]  # Rocket's gravitational acceleration in East-North-Up system
        #self.g_enu=np.array([0,0,-9.81])   # [m/s2] # Gravitational acceleration assuming it parallel to Up direction
        self.g_b=Mat.q_rot(self.g_enu,self.q_enu2b,0)                  # [m/s2]  # Rocket's gravitational acceleration in bodyframe (used later for conditional only)

    def dynamics(self,x):
        "Calculates motion equations according to Newton's Second Law of motion"
        r_enu=x[0:3]
        v_enu=x[3:6]
        q_enu2b=x[6:10]
        w_b=x[10:13]
        mass=x[13]

        #________Trajectory_______#

        ### Auxiliary values for conditional at the beginning of simulation
        abs_force=np.abs(self.forces_b[0])
        abs_grav=np.abs(self.g_b[0])
        
        # Conditionals to avoid problems with negative values of velocity and setting and end when landing
        if abs_force<=abs_grav:
            r_dot_enu=np.zeros(3)
            v_dot_enu=np.zeros(3)
    def dynamics(self, x):
        """Calcula las ecuaciones de movimiento"""
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
        "Propagation of variables previously obtained in dynamics and updates all obtained variables"
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
        "Updates time of simulation after each cycle"
        self.time+=dt   # [s]