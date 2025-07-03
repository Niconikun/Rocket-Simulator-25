# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** Main_simulator.py ***

Contains:
Main simulation for data initialization and simulation sequence.

External dependencies:
numpy        -Numpy Python extension. http://numpy.org/
              Version: Numpy 1.22.3
matplotlib   -Matplotlib Python plotting package. https://matplotlib.org
              Version: Matplotlib 3.4.1
pandas       -Pandas Python for data analysis, time series, and statistics
              Version: Pandas 1.2.4. https://pandas.pydata.org
MatTools     -Self-written python module containing mathematical functions
Aerodynamics -Self-written python module containing aerodynamic coefficients
Engine       -Self-written python module containing engine performance parameters
Rocket       -Self-written python module containing rocket parameters main calculations
Atmosphere   -Self-written python module containing atmospheric model

Internal dependencies:
cmath       -cMath Python extension. https://docs.python.org/3/library/cmath.html

Changelog:
Date          Name              Change
__ _          __ _              ____ _
15/08/2022    Jorge Orozco      Initial release

References:
Short     Author,Year     Title
___ _     _________ _     ___ _

"""
# Imports
from pickle import FALSE, TRUE
import numpy as np
import MatTools as Mat
from cmath import pi
import matplotlib.pyplot as plt
from Clock import Clock
from Planet import Planet
from Atmosphere import Atmosphere
from Rocket import Rocket
import pandas as pd

# Auxiliary functions
deg2rad=pi/180
rad2deg=180/pi

# ------ Configuration of time simulation related data ------ #
Start=0                     # [s]  # Starting time of simulation
End=80                      # [s]  # Ending time of simulation
dt=0.001                    # [s]  # Time step of every cycle of simulation
Steps_num=int(End/dt)                 
Steps=np.linspace(Start,End,Steps_num)

# ___________________ Initial data to be INPUT ________________ #  # (All of this should to be obtained from external file!!!)
Year=2022
Month= 5
Day= 16
Hour= 0
Minute=0
Second=0   

Latitude=0       # [deg]   # Latitude for platform location
Longitude=-70      # [deg]   # Longitude for platform location
Altitude=0         # [m]     # Altitude for platform location (if 0 it will be assumed to be at sea level)

East=0        # [m]   # X axis initial location of rocket from platform
North=0       # [m]   # Y axis initial location of rocket from platform
Up=0.1        # [m]   # Z axis initial location of rocket from platform  (do not set at 0...this is in order to used a conditional later on for max. alt and range)

Vel_east=0    # [m/s]   # X axis initial velocity of rocket from platform
Vel_north=0   # [m/s]   # Y axis initial velocity of rocket from platform
Vel_up=0      # [m/s]   # Z axis initial velocity of rocket from platform

Yaw=0         # [deg]   # From East   (between -180 and 180)
Pitch=45      # [deg]   # From ground (between 10 and 70)
Roll=0        # [deg]   # From initial position (between -180 and 180). Assumed to be always zero

W_yaw=0       # [rad/s]   # X axis initial rotational velocity of rocket from platform
W_pitch=0     # [rad/s]   # Y axis initial rotational velocity of rocket from platform
W_roll=0      # [rad/s]   # Z axis initial rotational velocity of rocket from platform

Temperature=25   # [°C]   # Temperature at platform

Max_altitude=10000     # [m] # Max. altitude
Max_range=12500        # [m] # Max. range

Detonate=TRUE          # Statement for detonation or not
Detonate_altitude=900  # [m] # Altitude for detonation

# ___________________ Initialization of data ________________ # 
date=[Year, Month, Day, Hour, Minute, Second]                # List containing date
julian_date=Clock().julian_day(date)                         # Obtaining Julian Date
gmst_0=Clock().gmst(julian_date,1)                           # Initial Greenwich Mean Sidereal Time [rad]

r_enu_0=np.array([East,North,Up])                            # [m]   # Initial East-North-Up location from platform
v_enu_0=np.array([Vel_east,Vel_north,Vel_up])                # [m/s] # Initial East-North-Up velocity from platform

q_yaw=np.array([0,0,np.sin(Yaw*0.5*deg2rad),np.cos(Yaw*0.5*deg2rad)])         # Quaternion single yaw rotation
q_pitch=np.array([0,np.sin(-Pitch*0.5*deg2rad),0,np.cos(-Pitch*0.5*deg2rad)]) # Quaternion single pitch rotation
q_roll=np.array([np.sin(Roll*0.5*deg2rad),0,0,np.cos(Roll*0.5*deg2rad)])      # Quaternion single roll rotation
q_enu2b_0=Mat.hamilton(q_pitch,q_yaw)                                         # Initial quaternion from East-North-Up to bodyframe

###---Alternative way to get quaternion using navpy library---###
#q_enu2b_0=Mat.hamilton(q_roll,q_enu_0)
# q0,qvec=nav.angle2quat(Yaw,-Pitch,Roll,input_unit='deg',rotation_sequence='ZYX')
# q_enu2b_0=np.array(Mat.check([qvec[0],qvec[1],qvec[2],q0]))

w_enu_0=np.array([W_yaw,W_pitch,W_roll])                     # [rad/s] # Initial rotational velocity in East-North-Up

coordinates=np.array([Latitude, Longitude, Altitude])        # [deg,m] # Geodetic coordinates of platform 

# _________________ Objects creation ___________________ #
Earth=Planet(gmst_0)                                       # Planet module object creation
Environment=Atmosphere(Temperature)                        # Atmosphere module object creation
Sistema=Rocket(r_enu_0,v_enu_0,q_enu2b_0,w_enu_0)          # Rocket module object creation

# Auxiliary timer for conditionals loop break
Time=[]       
t=Start

# ________________ Simulation sequence _________________#
for i in range(len(Steps)):

    # Planet Greenwich Mean Sidereal Time updating
    Earth.update(dt)
    # Rocket's sequence of simulation
    Sistema.update_gmst(Earth.gmst)
    Sistema.update_mass_related()
    Sistema.update_pos_vel(coordinates)
    Sistema.update_atmosphere(Environment.give_dens(Sistema.r_enu[2]),Environment.give_press(Sistema.r_enu[2]),Environment.give_v_sonic(Sistema.r_enu[2]))    
    Sistema.update_aerodynamics()
    Sistema.update_engine()
    Sistema.update_forces_aero()
    Sistema.update_forces_engine()
    Sistema.update_forces_torques()
    Sistema.update_g_accel(coordinates)
    Sistema.RK4_update(dt)
    Sistema.save_data()

    if Sistema.time>=1:
        if Sistema.r_enu[2]<Sistema.hist_up[-2] and Sistema.r_enu[2]<Detonate_altitude and Detonate==TRUE:
            break
    
    # Conditional to stop when reached
    if Sistema.r_enu[2]<=0 or Sistema.r_enu[2]>=Max_altitude or Sistema.range>= Max_range:
        break

    Time.append(t)
    t+=dt

    # Rocket's updating of simulation time
    Sistema.update_time(dt)

# Datos puntuales del vuelo
print()
print('Tiempo de vuelo total: ' + str(round((Sistema.hist_time[-1]),3)) + ' segundos')
print()
print('Alcance horizontal máximo: ' + str(round((max(Sistema.hist_range)),3)) + ' metros')
print()
print('Altitud máxima: ' + str(round((max(Sistema.hist_up)),3)) + ' metros a los ' + str(round((Sistema.hist_time[Sistema.hist_up.index(max(Sistema.hist_up))]),3)) + ' segundos')
print()
print('Pitch (cabeceo) en altitud máxima: ' + str(round((Sistema.hist_pitch[Sistema.hist_up.index(max(Sistema.hist_up))]),3)) + ' grados' )
print()
print('Masa inicial: ' + str(round(Sistema.hist_mass[0],3)) + ' kilogramos')
print()
print('Masa final: ' + str(round(Sistema.hist_mass[-1],3)) + ' kilogramos')
print()
print('Velocidad máxima: ' + str(round((max(Sistema.hist_v_norm)),3)) + ' metros por segundo a los ' + str(round((Sistema.hist_time[Sistema.hist_v_norm.index(max(Sistema.hist_v_norm))]),3)) + ' segundos')
print()
print('Número de Mach máximo: ' + str(round((max(Sistema.hist_mach)),3)) + ' a los ' + str(round((Sistema.hist_time[Sistema.hist_mach.index(max(Sistema.hist_mach))]),3)) + ' segundos')
print()
print('Latitud final: ' + str(round((Sistema.hist_lat[-1]),5)) + ' grados')
print('Longitud final: ' + str(round((Sistema.hist_long[-1]),5)) + ' grados')
print('Altitud final: ' + str(round((Sistema.hist_alt[-1]),5)) +' metros' )
print()

## Velocidades bodyframe vs tiempo 

plt.plot(Sistema.hist_time,Sistema.hist_v_bx,'-b',label="$V_{b,x}$")
plt.plot(Sistema.hist_time,Sistema.hist_v_by,'-g',label="$V_{b,y}$")
plt.plot(Sistema.hist_time,Sistema.hist_v_bz,'-r',label="$V_{b,z}$")
plt.title("Velocidad en bodyframe vs tiempo")
plt.xlabel("Tiempo de vuelo [s]")
plt.ylabel("Velocidad en bodyframe [m/s]")
plt.legend(loc="upper right")
plt.grid()

### Altitud vs Rango 

plt.figure()
plt.plot(Sistema.hist_range,Sistema.hist_up)
plt.title("Altitud vs alcance")
plt.xlabel("Alcance [m]")
plt.ylabel("Altitud [m]")
plt.grid()

### Altitud vs tiempo 

plt.figure()
plt.plot(Sistema.hist_time,Sistema.hist_up)
plt.title("Altitud vs tiempo")
plt.xlabel("Tiempo [s]")
plt.ylabel("Altitud [m]")
plt.grid()

### Fuerza de sustentación vs tiempo 

plt.figure()
plt.plot(Sistema.hist_time,Sistema.hist_lift)
plt.title("Fuerza de sustentación vs tiempo")
plt.xlabel("Tiempo [s]")
plt.ylabel("Fuerza de sustentación [N]")
plt.grid()


### Pitch, Altitud  vs Tiempo

plt.figure()
fig, axs = plt.subplots(2,sharex='col')
fig.suptitle('Pitch y Altitud vs Tiempo')
axs[0].plot(Sistema.hist_time, Sistema.hist_up)
axs[0].set(ylabel='Altitud [m]')
axs[0].grid()
axs[1].plot(Sistema.hist_time, Sistema.hist_pitch)
axs[1].set(xlabel='Tiempo [s]',ylabel='Pitch [deg]')
axs[1].grid()

### Pitch vs tiempo
plt.figure()
plt.plot(Sistema.hist_time, Sistema.hist_pitch)
plt.title("Pitch (\u03C6) vs tiempo")
plt.xlabel("Tiempo de vuelo [s]")
plt.ylabel("Pitch (\u03C6) [°]")
plt.grid()

### ALpha vs tiempo
plt.figure()
plt.plot(Sistema.hist_time, Sistema.hist_alpha)
plt.title("Alpha (\u03B1) vs tiempo")
plt.xlabel("Tiempo de vuelo [s]")
plt.ylabel("Alpha (\u03B1) [°]")
plt.grid()

#### 3D Plotting ####
#### East-North-Up #####
fig = plt.figure()
ay = fig.add_subplot(111, projection='3d')
ay.plot(Sistema.hist_east,Sistema.hist_north,Sistema.hist_up,label='Trayectoria East-North-Up')
ay.legend()
ay.set_xlabel('East [m]')
ay.set_ylabel('North [m]')
ay.set_zlabel('Up [m]')
ay.xaxis.set_rotate_label(False)
ay.yaxis.set_rotate_label(False)
ay.zaxis.set_rotate_label(False)

ay.xaxis.labelpad=15
ay.yaxis.labelpad=15
ay.zaxis.labelpad=15

plt.show()


# case='No Rotation'

# df=pd.DataFrame({
#     'time':Sistema.hist_time,
#     'range': Sistema.hist_range,
#     'pitch': Sistema.hist_pitch,
#     'east':Sistema.hist_east,
#     'north': Sistema.hist_north,
#     'up': Sistema.hist_up,
#     'drag': Sistema.hist_drag,
#     'alpha': Sistema.hist_alpha,
#     'v_b_x': Sistema.hist_v_bx,
#     'v_b_y': Sistema.hist_v_by,
#     'v_b_z': Sistema.hist_v_bz
# })

# df.to_excel('Book1.xlsx',sheet_name=case,index=False)