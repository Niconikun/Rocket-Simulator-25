import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from dataclasses import dataclass
import ephem  # Para cálculos astronómicos
from src.models.atmosphere import Atmosphere

@dataclass
class AtmosphericConditions:
    """Condiciones atmosféricas detalladas"""
    temperature: float      # Temperatura [K]
    pressure: float        # Presión [Pa]
    density: float         # Densidad [kg/m³]
    wind_speed: float      # Velocidad del viento [m/s]
    wind_direction: float  # Dirección del viento [rad]
    ion_density: float    # Densidad de iones [e/m³]
    electron_temp: float  # Temperatura de electrones [K]

class AdvancedAtmosphere:
    """
    Modelo atmosférico avanzado que considera:
    - Variación diurna
    - Efectos estacionales
    - Perturbaciones ionosféricas
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Configuración del modelo {
                'latitude': float,      # Latitud [deg]
                'longitude': float,     # Longitud [deg]
                'date': datetime,       # Fecha y hora
                'f10.7': float,        # Flujo solar F10.7 [sfu]
                'ap': float,           # Índice geomagnético Ap
            }
        """
        self.config = config
        self.base_atmosphere = Atmosphere(config.get('base_temp', 15))
        self._init_astronomical_parameters()
        
        # Capas atmosféricas
        self.layers = {
            "troposphere": (0, 12000),
            "stratosphere": (12000, 50000),
            "mesosphere": (50000, 80000),
            "thermosphere": (80000, 700000),
            "exosphere": (700000, float('inf'))
        }
        
    def _init_astronomical_parameters(self):
        """Inicializa parámetros astronómicos"""
        self.observer = ephem.Observer()
        self.observer.lat = str(self.config['latitude'])
        self.observer.lon = str(self.config['longitude'])
        self.observer.date = self.config['date']
        self.sun = ephem.Sun()
        
    def get_solar_position(self) -> Tuple[float, float]:
        """Calcula posición solar"""
        self.sun.compute(self.observer)
        return float(self.sun.alt), float(self.sun.az)
        
    def calculate_diurnal_variation(self, altitude: float, 
                                  local_time: datetime) -> Dict[str, float]:
        """
        Calcula variación diurna de parámetros atmosféricos.
        
        Args:
            altitude: Altitud [m]
            local_time: Hora local
            
        Returns:
            Dict con factores de corrección
        """
        hour = local_time.hour + local_time.minute/60
        
        # Factor diurno (máximo al mediodía)
        diurnal_factor = np.sin(np.pi * (hour - 6) / 12)
        
        # Amplitud de variación según altitud
        amplitude = np.exp(-altitude/50000)  # Decrece con la altura
        
        return {
            'temperature': 1.0 + 0.1 * amplitude * diurnal_factor,
            'density': 1.0 - 0.05 * amplitude * diurnal_factor,
            'pressure': 1.0 - 0.02 * amplitude * diurnal_factor
        }
        
    def calculate_seasonal_effects(self, day_of_year: int, 
                                 latitude: float) -> Dict[str, float]:
        """
        Calcula efectos estacionales.
        
        Args:
            day_of_year: Día del año [1-366]
            latitude: Latitud [deg]
            
        Returns:
            Dict con factores de corrección
        """
        # Ángulo de declinación solar
        declination = 23.45 * np.sin(2*np.pi*(day_of_year - 81)/365)
        
        # Factor estacional
        seasonal_factor = np.cos(np.radians(latitude - declination))
        
        return {
            'temperature': 1.0 + 0.15 * seasonal_factor,
            'density': 1.0 - 0.1 * seasonal_factor,
            'pressure': 1.0 - 0.05 * seasonal_factor
        }
        
    def calculate_ionospheric_effects(self, altitude: float) -> Dict[str, float]:
        """
        Calcula efectos ionosféricos.
        
        Args:
            altitude: Altitud [m]
            
        Returns:
            Dict con parámetros ionosféricos
        """
        # Modelo simplificado de Chapman para densidad de electrones
        h_max = 300000  # Altura de máxima ionización [m]
        N_max = 1e12    # Densidad máxima de electrones [e/m³]
        H = 50000       # Altura de escala [m]
        
        z = (altitude - h_max) / H
        Ne = N_max * np.exp(0.5 * (1 - z - np.exp(-z)))
        
        # Efectos del viento solar (F10.7)
        f107_factor = self.config.get('f10.7', 150) / 150
        
        return {
            'electron_density': Ne * f107_factor,
            'ion_temp': 1000 * (1 + altitude/200000),  # Modelo simple
            'plasma_freq': 8.98 * np.sqrt(Ne)  # Frecuencia de plasma [Hz]
        }
        
    def get_conditions(self, altitude: float, time: datetime) -> AtmosphericConditions:
        """
        Obtiene condiciones atmosféricas completas.
        
        Args:
            altitude: Altitud [m]
            time: Tiempo local
            
        Returns:
            AtmosphericConditions
        """
        # Condiciones base
        base_temp = self.base_atmosphere.give_temp(altitude)
        base_press = self.base_atmosphere.give_press(altitude)
        base_dens = self.base_atmosphere.give_dens(altitude)
        
        # Factores de corrección
        diurnal = self.calculate_diurnal_variation(altitude, time)
        seasonal = self.calculate_seasonal_effects(
            time.timetuple().tm_yday,
            self.config['latitude']
        )
        
        # Aplicar correcciones
        temperature = base_temp * diurnal['temperature'] * seasonal['temperature']
        pressure = base_press * diurnal['pressure'] * seasonal['pressure']
        density = base_dens * diurnal['density'] * seasonal['density']
        
        # Efectos ionosféricos si estamos suficientemente alto
        if altitude > 60000:  # Ionósfera
            iono = self.calculate_ionospheric_effects(altitude)
            ion_contribution = iono['electron_density'] * 1.67e-27  # masa protón
            density += ion_contribution
        else:
            iono = {'electron_density': 0, 'ion_temp': temperature}
        
        return AtmosphericConditions(
            temperature=temperature,
            pressure=pressure,
            density=density,
            wind_speed=self._calculate_wind_speed(altitude, time),
            wind_direction=self._calculate_wind_direction(altitude, time),
            ion_density=iono['electron_density'],
            electron_temp=iono['ion_temp']
        )
        
    def _calculate_wind_speed(self, altitude: float, time: datetime) -> float:
        """Calcula velocidad del viento considerando efectos térmicos"""
        base_speed = 5.0  # [m/s]
        
        # Efecto de la hora del día
        hour = time.hour + time.minute/60
        thermal_factor = np.sin(np.pi * (hour - 6) / 12)
        
        # Efecto de la altitud
        altitude_factor = np.log(1 + altitude/1000)/10
        
        return base_speed * (1 + thermal_factor) * (1 + altitude_factor)
        
    def _calculate_wind_direction(self, altitude: float, time: datetime) -> float:
        """Calcula dirección del viento con rotación de Ekman"""
        # Dirección base
        base_direction = np.pi/4  # 45° del Norte
        
        # Rotación de Ekman con la altura
        ekman_spiral = 0.1 * altitude/1000
        
        return (base_direction + ekman_spiral) % (2*np.pi)