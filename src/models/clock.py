# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** Clock.py ***

Contains:
Clock object to calculate date related variables

External dependencies:
numpy       -Numpy Python extension. http://numpy.org/
             Version: Numpy 1.22.3
datetime    -Datetime Library. https://github.com/zopefoundation/DateTime
             Version: Datetime 4.3

Internal dependencies:
cmath       -cMath Python extension. https://docs.python.org/3/library/cmath.html

Changelog:
Date          Name              Change
__ _          __ _              ____ _
15/08/2022    Jorge Orozco      Initial release

References:
Short       Author,Year            Title
___ _       _________ _            ___ _
[Vall13]    Vallado/McClain,2013   Fundamentals of Astrodynamics and Applications
[Schl17]    Schlyter,2017          TIMESCALES. https://stjarnhimlen.se/comp/time.html#deltat72p
"""
# Imports
from datetime import datetime, timezone
from cmath import pi
import numpy as np

# Auxiliary functions
deg2rad=pi/180
rad2deg=180/pi

class Clock(object):
    "julian day, GMST..."
    def __init__(self):
        """Inicialización del reloj"""
        self.Delta_UT1 = 0.0
        self.time_vector = self._get_current_time()
        self.j_day = self.julian_day(self.time_vector)


    # List of date and time
    def time_utc(self):
        """Retorna el vector de tiempo actual considerando Delta_UT1"""
        time = self._get_current_time()
        # Aplicar Delta_UT1 solo a los segundos
        time[5] = time[5] + self.Delta_UT1
        
        # Manejar el wraparound de segundos si es necesario
        if time[5] >= 60:
            time[5] = time[5] % 60
            time[4] += 1  # Incrementar minutos
        
        return time
    
    # Calculation of julian day, [Vall13]
    def julian_day(self,time_vector):                                                 
        'Julian Day from [year, month, day, hour(consider utc), minute, second]'

        j_day=(367*time_vector[0] - int((7*(time_vector[0]+int((time_vector[1]+9)/(12))))/(4)) + 
                   int((275*time_vector[1])/9) + time_vector[2] + 1721013.5 + 
                   ((((time_vector[5]/60)+time_vector[4])/60)+time_vector[3])/24)
        
        return j_day
    

    # Obtains Greenwich Mean Sidereal Time using Vallado's first Method, [Vall13]
    def gmst(self,julian_day,rad_or_deg):
        """
        Greenwich Mean Sidereal Time ...
        rad_or_deg: -.1 for [rads] -.2 for [deg]...
        """

        self.T_ut1=(julian_day-2451545.0)/36525
        self.Theta_GMST=(67310.54841 + ((876600*3600) + 8640184.812866)*self.T_ut1 +    
                        0.093104*(self.T_ut1**2) - 6.2*(1/1000000)*(self.T_ut1**3))
        self.GMST_leap=self.Theta_GMST-(int(self.Theta_GMST/86400)*86400)
        self.GMST_degrees=self.GMST_leap/240
       
        # Corrects angle for interval between 0° to 360°
        if self.GMST_degrees < 0:                        
            self.GMST_degrees=self.GMST_degrees+360
        elif self.GMST_degrees > 360:
            self.GMST_degrees=self.GMST_degrees-360
        else:
            self.GMST_degrees=self.GMST_degrees

        # Gives gmst in [rad] or [deg]
        if rad_or_deg==2:                                   
            self.GMST=self.GMST_degrees
        elif rad_or_deg==1:
            self.GMST=(self.GMST_degrees)*deg2rad
        
        return self.GMST

    def _calculate_julian_day(self):
        # Julian day calculation, [Vall13]
        self.j_day=(367*self.time_vector[0] - 
            int((7*(self.time_vector[0]+int((self.time_vector[1]+9)/(12))))/(4)) + 
            int((275*self.time_vector[1])/9) + self.time_vector[2] + 1721013.5 + 
            ((((self.time_vector[5]/60)+self.time_vector[4])/60)+self.time_vector[3])/24)
    
    def _get_current_time(self):
        """Obtiene el tiempo actual en UTC"""
        current = datetime.now(timezone.utc)
        return np.array([
            current.year,
            current.month,
            current.day,
            current.hour,
            current.minute,
            current.second + current.microsecond/1e6
        ])