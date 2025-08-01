# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** GeoTools.py ***

Contains:
Functions for reference frames and coordinates conversion.

External dependencies:
numpy       -Numpy Python extension. http://numpy.org/
             Version: Numpy 1.22.3
MatTools    -Self-written python module containing mathematical functions

Internal dependencies:
cmath       -cMath Python extension. https://docs.python.org/3/library/cmath.html

Changelog:
Date          Name              Change
__ _          __ _              ____ _
15/08/2022    Jorge Orozco      Initial release

References:
Short       Author(s),Year                  Title
___ _       ____________ _                  ___ _
[Kuna20]    Kuna/Santhosh/Perumalla,2020    Preliminary Analysis of Standalone Galileo and NavIC in the 
                                            context of Positioning Performance for Low Latitude Region
[Regan93]   Regan/Anandakrishnan,1993       Dynamics of Atmospheric Re-Entry
[Done12]    Donelly, 2012                   Session 1.3: Worked examples of Terrestrial Reference Frame Realisations 
                                            Determining Coordinates in a Local Reference Frame from Absolute ITRF Positions:
                                            A New Zealand Case Study
[Curt20]    Curtis,2020                     Orbital Mechanics for Engineering Students
[Seem02]    Seemkooei,2002                  Comparison of different algorithms to transform geocentric to geodetic coordinates
[Beau05]    Beaulne/Sikaneta,2005           A Simple and Precise Approach to Position and Velocity Estimation of Low Earth Orbit Satellites
[Zhao16]    Zhao,2016                       Time Derivative of Rotation Matrices: A Tutorial

"""
# Imports
import numpy as np
from src.utils.mattools import MatTools as Mat
from cmath import pi

class GeoTools:
    """Clase de utilidades para conversiones geométricas y transformaciones de coordenadas."""
    
    # Constantes de clase
    deg2rad = pi/180
    rad2deg = 180/pi
    
    # Earth angular velocity as 3x3 skew matrix, [Regan93]
    w_earth_skew3 = Mat.skew3([0, 0, 7.2119e-5])  # [rad/s]
    
    # Ellipsoid WGS84 parameters [Kuna20]
    a = 6378137                    # Equatorial radius [m]
    b = 6356752.314245179         # Polar Radius [m]
    f = 1/298.257223563           # Flattening [-]
    e = np.sqrt(f*(2-f))          # Eccentricity [-]
    e2 = 2*f - (f**2)             # First eccentricity [-]
    eps2 = (a*a - b*b)/(b*b)      # Second eccentricity [-]

    @staticmethod
    def enu2ecef(coord, r_enu):
        """Convierte coordenadas ENU a ECEF"""
        lat = coord[0] * GeoTools.deg2rad
        long = coord[1] * GeoTools.deg2rad
        
        sin_lat, cos_lat = np.sin(lat), np.cos(lat)
        sin_long, cos_long = np.sin(long), np.cos(long)
        
        DCM_enu2ecef = np.array([
            [-sin_long, -sin_lat*cos_long, cos_lat*cos_long],
            [cos_long, -sin_lat*sin_long, cos_lat*sin_long],
            [0, cos_lat, sin_lat]
        ])
        
        return DCM_enu2ecef.dot(r_enu)

    @staticmethod
    def ecef2enu(coord, r_ecef):
        """Convierte coordenadas ECEF a ENU"""
        lat = coord[0] * GeoTools.deg2rad
        long = coord[1] * GeoTools.deg2rad
        
        sin_lat, cos_lat = np.sin(lat), np.cos(lat)
        sin_long, cos_long = np.sin(long), np.cos(long)
        
        DCM_ecef2enu = np.array([
            [-sin_long, cos_long, 0],
            [-sin_lat*cos_long, -sin_lat*sin_long, cos_lat],
            [cos_lat*cos_long, cos_lat*sin_long, sin_lat]
        ])
        
        return DCM_ecef2enu.dot(r_ecef)

    @staticmethod
    def ecef2geo(r_ecef):
        """Convierte coordenadas ECEF a geodéticas usando método iterativo"""
        x, y, z = r_ecef
        
        p = np.sqrt(x**2 + y**2)
        long = np.arctan2(y, x)
        
        # Método iterativo de Bowring
        lat = np.arctan2(z, p * (1 - GeoTools.e2))
        
        for _ in range(5):  # 5 iteraciones suelen ser suficientes
            N = GeoTools.a / np.sqrt(1 - GeoTools.e2 * np.sin(lat)**2)
            h = p / np.cos(lat) - N
            lat = np.arctan2(z, p * (1 - GeoTools.e2 * N/(N + h)))
        
        return np.array([lat * GeoTools.rad2deg, 
                        long * GeoTools.rad2deg, 
                        h])

    @staticmethod
    def geo2ecef(coord):
        """Convierte coordenadas geodéticas a ECEF"""
        lat = coord[0] * GeoTools.deg2rad
        long = coord[1] * GeoTools.deg2rad
        alt = coord[2]
        
        sin_lat, cos_lat = np.sin(lat), np.cos(lat)
        sin_long, cos_long = np.sin(long), np.cos(long)
        
        N = GeoTools.a / np.sqrt(1 - GeoTools.e2 * sin_lat**2)
        
        x = (N + alt) * cos_lat * cos_long
        y = (N + alt) * cos_lat * sin_long
        z = (N * (1 - GeoTools.e2) + alt) * sin_lat
        
        return np.array([x, y, z])
                             
    @staticmethod
    def ecef2eci(gmst,r_ecef):
        """
        Position and forces from Earth Centered-Earth Fixed to Earth Centered Inertial...[Beau05]
        gmst in [rad] and r_ecef in [m]
        """
        
        cos_gmst=np.cos(gmst); sin_gmst=np.sin(gmst)
        
        # Builds rotation matrix
        DCM_ecef2eci=np.array([[cos_gmst,-sin_gmst,0],[sin_gmst,cos_gmst,0],[0,0,1]])
        
        r_eci=np.dot(DCM_ecef2eci,r_ecef) # [m]
        return r_eci
                                                      
    @staticmethod
    def ecef2eci_v(gmst,r_ecef,v_ecef):
        """
        Converts velocity in Earth Centered-Earth Fixed system into Earth Centered Inertial system... [Beau05] and [Zhao16]
        gmst in [rad], r_ecef in [m] and v_ecef in [m/s]
        """
        cos_gmst=np.cos(gmst); sin_gmst=np.sin(gmst)

        # Builds rotation matrix
        DCM_ecef2eci=np.array([[cos_gmst,-sin_gmst,0],[sin_gmst,cos_gmst,0],[0,0,1]])
        
        # Derivative of rotation matrix, [Zhao16]
        DCM_ecef2eci_dot=DCM_ecef2eci.dot(GeoTools.w_earth_skew3)
        
        elem1=DCM_ecef2eci.dot(v_ecef)
        elem2=np.dot(DCM_ecef2eci_dot,r_ecef)
        v_eci_from_ecef=elem1 + elem2         # [m/s]
           
        return v_eci_from_ecef
                                                
    @staticmethod
    def eci2ecef(gmst,r_eci):
        """
        Converts Earth Centered Inertial coordinates to Earth Centered-Earth Fixed coordinates...[Beau05]   
        gmst in [rad] and r_eci in [m]
        """

        cos_gmst=np.cos(gmst); sin_gmst=np.sin(gmst)
        
        # Builds rotation matrix
        DCM_eci2ecef=np.array([[cos_gmst,sin_gmst,0],[-sin_gmst,cos_gmst,0],[0,0,1]])
        
        r_eci=DCM_eci2ecef.dot(r_eci) # [m]
        return r_eci
                                                      
    @staticmethod
    def eci2ecef_v(gmst,r_eci,v_eci):
        """
        Converts Earth Centered Inertial velocity into Earth Centered-Earth Fixed system...[Beau05] and [Zhao16] 
        gmst in [rad], r_ecef in [m] and v_ecef in [m/s]
        """
        cos_gmst=np.cos(gmst); sin_gmst=np.sin(gmst)
        
        # Builds rotation matrix
        DCM_eci2ecef=np.array([[cos_gmst,sin_gmst,0],[-sin_gmst,cos_gmst,0],[0,0,1]])   
        
        # Derivative of rotation matrix, [Zhao16]
        DCM_eci2ecef_dot=(DCM_eci2ecef.dot(GeoTools.w_earth_skew3))    
        
        elem1=np.dot(DCM_eci2ecef,v_eci)
        elem2=-np.dot(DCM_eci2ecef_dot,r_eci)
        v_ecef_from_eci=elem1 + elem2           # [m/s]
            
        return v_ecef_from_eci

    @staticmethod
    def yawpitchroll(rot_vector):
        """
        Builds Director Cosine Matrix from angles of rotation in 312 sequence or yaw pitch roll...[Curt20]
        Receives angles in [deg]
        """
        phi=rot_vector[0]*GeoTools.deg2rad ; sin_phi=np.sin(phi) ; cos_phi=np.cos(phi)
        theta=rot_vector[1]*GeoTools.deg2rad ; sin_theta=np.sin(theta) ; cos_theta=np.cos(theta)
        psy=rot_vector[2]*GeoTools.deg2rad ; sin_psy=np.sin(psy) ; cos_psy=np.cos(psy)

        matrix_phi=np.array([[cos_phi,sin_phi,0],[-sin_phi,cos_phi,0],[0,0,1]])            # Yaw
        matrix_theta=np.array([[cos_theta,0,-sin_theta],[0,1,0],[sin_theta,0,cos_theta]])  # Pitch
        matrix_psy=np.array([[1,0,0],[0,cos_psy,sin_psy],[0,-sin_psy,cos_psy]])            # Roll

        mult1=np.dot(matrix_theta,matrix_phi)
        mult2=np.dot(matrix_psy,mult1)
        
        return mult2
    
    @staticmethod
    def calculate_rotation_matrix(lat, long):
        """Calcula matriz de rotación basada en latitud y longitud"""
        lat_rad = lat * GeoTools.deg2rad
        long_rad = long * GeoTools.deg2rad
        
        sin_lat, cos_lat = np.sin(lat_rad), np.cos(lat_rad)
        sin_long, cos_long = np.sin(long_rad), np.cos(long_rad)
        
        R = np.array([
            [-sin_long, -sin_lat*cos_long, cos_lat*cos_long],
            [cos_long, -sin_lat*sin_long, cos_lat*sin_long],
            [0, cos_lat, sin_lat]
        ])
        
        return R

    @staticmethod
    def calculate_geodetic_radius(lat):
        """Calcula el radio geodético en una latitud dada"""
        lat_rad = lat * GeoTools.deg2rad
        sin_lat = np.sin(lat_rad)
        
        N = GeoTools.a / np.sqrt(1 - GeoTools.e2 * sin_lat**2)
        return N