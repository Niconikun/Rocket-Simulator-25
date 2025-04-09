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
                
        Delta_UT1=-0.11  # Delta UT1 from [Schl17]
       
        # Obtains current date and time from library datetime using Delta_UT1                                        
        self.current_time_utc=datetime.now(timezone.utc)    
        self.current_year_ut1=self.current_time_utc.year                  # Year
        self.current_month_ut1=self.current_time_utc.month                # Month
        self.current_day_ut1=self.current_time_utc.day                    # Day
        self.current_hour_ut1=self.current_time_utc.hour                  # Hour
        self.current_minute_ut1=self.current_time_utc.minute              # Minute
        self.current_second_ut1=self.current_time_utc.second + Delta_UT1  # Second
        
        # Arranges date as an array (could be a list as well)
        self.time_vector=np.array([self.current_year_ut1,self.current_month_ut1,
                                  self.current_day_ut1, self.current_hour_ut1,
                                  self.current_minute_ut1,self.current_second_ut1])
      
        # Julian day calculation, [Vall13]
        self.j_day=(367*self.time_vector[0] - 
            int((7*(self.time_vector[0]+int((self.time_vector[1]+9)/(12))))/(4)) + 
            int((275*self.time_vector[1])/9) + self.time_vector[2] + 1721013.5 + 
            ((((self.time_vector[5]/60)+self.time_vector[4])/60)+self.time_vector[3])/24)
    
    # List of date and time
    def time_utc(self):                        
        'Obtain current ut1 time in Greenwich in a vector automatically'

        return self.time_vector
    
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