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

class Rocket(object):
    "Calculates all data during simulation. It's the main module of simulation"
    def __init__(self,r_enu_0,v_enu_0,q_enu2b_0,w_enu_0):
        
        #______Initial data_______#
        self.r_enu=r_enu_0        # [m]       # East-North-Up location from launching platform
        self.v_enu=v_enu_0        # [m/s]     # East-North-Up velocity from launching platform
        self.q_enu2b=q_enu2b_0    # [-]       # Quaternion that rotates from launching platform in East-North-Up to bodyframe
        self.w_enu=w_enu_0        # [rad/s]   # East-North-Up rotational velocity from launching platform

        self.mass=9.48            # [kg]      # Initial total mass

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
        self.hist_forces_aero_b=[]      # Aerodynamic forces in bodyframe
        self.hist_torques_aero_b=[]     # Aerodynamic torques in bodyframe

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

    def update_gmst(self,gmst):
        "Updates Greenwich Mean Sidereal Time from Planet Module"
        self.gmst=gmst  # [rad]    # Greenwich Mean Sidereal Time (rotation of Earth Centered-Earth Fixed from Earth Centered Inertial systems)

    def update_mass_related(self):
        "Updates mass related data: Centre of Mass and Inertia"
        self.burn_time=3.15    # [s]    # Propellant total burning time                                                  
        if self.time<=self.burn_time:
            self.cm_b=np.array([0.5109,0,0])                                 # [m]        # Centre of Mass before burning obtained via Autodesk Inventor
            self.inertia_b=np.array([0.009057381,0.784037556,0.784037556])   # [kg m2]    # Inertia before burning obtained via Autodesk Inventor
        else: 
            self.cm_b=np.array([0.40215,0,0])                                # [m]        # Centre of Mass after burning obtained via Autodesk Inventor
            self.inertia_b=np.array([0.0062581,0.522648762,0.522648762])     # [kg m2]    # Inertia after burning obtained via Autodesk Inventor 

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

    def update_aerodynamics(self):
        "Updates aerodynamic characteristics from Aerodynamics Module"
        # Conditional to avoid Runtime Warning for division by zero
       
        if self.v_norm==0:
            self.mach=0                           # [-]    # Mach number
        else:
            self.mach=self.v_norm/self.v_sonic    # [-]    # Mach number
        
        Aero=Aerodynamics(self.mach,self.alpha)   # Aerodynamics instance 
        self.drag_coeff=Aero.cd                   # [-]    # Drag coefficient
        self.lift_coeff=Aero.cl                   # [-]    # Lift coefficient
        self.cp_b=Aero.xcp                        # [m]    # Location of centre of pressure from nose (ogive) tip

    def update_engine(self):
        "Updates engine performance characteristics from Engine Module"
        Eng=Engine(self.time,self.press_amb)      # Engine instance
        self.mass_flux=Eng.mass_flux              # [kg/s] # Engine mass flux
        self.thrust=Eng.thrust                    # [N]    # Engine thrust

    def update_forces_aero(self):
        "Calculates all aerodynamics related data"
        
        ref_area=(0.0889**2)*pi*0.25  # [m2]     # Reference area for drag and lift calculation [Valle22]

        # Conditional to avoid Runtime Warning for double zero multiplication
        if self.drag_coeff==0:                          
            self.drag=0             
        else: 
            self.drag=0.5*self.density*self.drag_coeff*ref_area*(self.v_norm**2)  # [N]   # Drag force  [Barro67]

        # Conditional to avoid Runtime Warning for double zero multiplication
        if self.lift_coeff==0:                          
            self.lift=0                                       
        else: 
            self.lift=0.5*self.density*self.lift_coeff*ref_area*(self.v_norm**2)  # [N]   # Lift force  [Barro67]

        self.forces_drag_b=np.array([-self.drag,0,0])                 # [N]   # Drag force on bodyframe
        self.forces_lift_b=np.array([0,0,self.lift])                  # [N]   # Lift force on bodyframe ## Assumes that roll will always be 0 [rad/s]   
        
        self.cm2cp_b=self.cm_b-self.cp_b                              # [m]   # Distance of centre of pressure from centre of mass
        self.forces_aero_b=self.forces_drag_b  + self.forces_lift_b   # [N]   # Lift can be neglected if necessary for evaluation
        self.torques_aero_b=np.cross(self.cm2cp_b,self.forces_aero_b) # [N m] # Torques produced by aerodynamic forces (lift mainly)

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
        else:
            r_dot_enu=v_enu                                  # [m/s]  # Time derivative of location in East-North-Up system
            v_dot_enu=(1/mass)*self.forces_enu + self.g_enu  # [m/s2] # Time derivative of velocity in East-North-Up system

        #________Attitude_________#
        
        j=Mat.vec2mat(self.inertia_b)    # [kg m2]     # Rocket's inertia as a 3x3 matrix
        j_invs=np.linalg.inv(j)          # [1/(kg m2)] # Rocket's inertia inverse
 
        w_enu=Mat.q_rot(w_b,q_enu2b,1)   # [rad/s]     # Rotational velocity in East-North-Up system
        w_enu_skew4=Mat.skew4(w_enu)     # [rad/s]     # Rotational velocity as a 4x4 skew matrix

        # Conditionals to avoid problems with negative values of velocity and setting and end when landing (same for consistency)
        if abs_force<=abs_grav:
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
        self.q_enu2b=Mat.normalise(q_enu2b)  # Quaternion needs to be normalized after propagation
        
        w_b=new_x[10:13]
        self.w_enu=Mat.q_rot(w_b,q_enu2b,1)

        self.mass=new_x[13]

    def save_data(self):
        "Saves all obtained data before propagation"
        self.hist_r_enu.append(self.r_enu)
        self.hist_v_enu.append(self.v_enu)
        self.hist_q_enu2b.append(self.q_enu2b)
        self.hist_q_enu2b_1.append(self.q_enu2b[0])
        self.hist_q_enu2b_2.append(self.q_enu2b[1])
        self.hist_q_enu2b_3.append(self.q_enu2b[2])
        self.hist_q_enu2b_4.append(self.q_enu2b[3])
        
        self.hist_w_enu.append(self.w_enu)

        self.hist_gmst.append(self.gmst)
        self.hist_time.append(self.time)
    
        self.hist_inertia_b.append(self.inertia_b)
        self.hist_mass.append(self.mass)
        self.hist_cm_b.append(self.cm_b)

        self.hist_yaw.append(self.yaw)
        self.hist_pitch.append(self.pitch)
        self.hist_roll.append(self.roll)

        self.hist_v_b.append(self.v_b)
        self.hist_v_bx.append(self.v_b[0])
        self.hist_v_by.append(self.v_b[1])
        self.hist_v_bz.append(self.v_b[2])
        self.hist_alpha.append(self.alpha)

        self.hist_density.append(self.density)
        self.hist_press_amb.append(self.press_amb)
        self.hist_v_sonic.append(self.v_sonic)
    
        self.hist_mach.append(self.mach)
        self.hist_drag_coeff.append(self.drag_coeff)
        self.hist_lift_coeff.append(self.lift_coeff)
        self.hist_cp_b.append(self.cp_b)

        self.hist_mass_flux.append(self.mass_flux)
        self.hist_thrust.append(self.thrust)

        self.hist_drag.append(self.drag)
        self.hist_lift.append(self.lift)
        self.hist_cm2cp_b.append(self.cm2cp_b)
        self.hist_forces_aero_b.append(self.forces_aero_b)
        self.hist_torques_aero_b.append(self.torques_aero_b)

        self.hist_forces_engine_b.append(self.forces_engine_b)
        self.hist_torques_engine_b.append(self.torques_engine_b)

        self.hist_range.append(self.range)
        self.hist_east.append(self.r_enu[0])
        self.hist_north.append(self.r_enu[1])
        self.hist_up.append(self.r_enu[2])

        self.hist_v_norm.append(self.v_norm)
        self.hist_coord.append(self.coord)
        self.hist_lat.append(self.coord[0])
        self.hist_long.append(self.coord[1])
        self.hist_alt.append(self.coord[2])


    def update_time(self,dt):
        "Updates time of simulation after each cycle"
        self.time+=dt   # [s]