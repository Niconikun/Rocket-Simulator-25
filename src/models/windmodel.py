import numpy as np
from typing import Dict, Tuple

class WindModel:
    """Modelo de viento por capas atmosféricas"""
    
    def __init__(self):
        # Capas atmosféricas típicas [m]
        self.layers = {
            "surface": (0, 100),      # Capa superficial
            "boundary": (100, 1000),  # Capa límite
            "troposphere": (1000, 11000),  # Troposfera
            "stratosphere": (11000, 50000)  # Estratosfera
        }
        
    def get_wind_conditions(self, altitude: float) -> Dict[str, float]:
        """
        Calcula condiciones de viento según altitud.
        
        Args:
            altitude (float): Altitud actual [m]
            
        Returns:
            Dict con velocidad [m/s] y dirección [rad] del viento
        """
        # Identificar capa
        layer = self._get_layer(altitude)
        
        # Modelo de viento por capa
        if layer == "surface":
            speed = self._surface_wind()
        elif layer == "boundary":
            speed = self._boundary_wind(altitude)
        else:
            speed = self._upper_wind(altitude)
            
        # Dirección variable con altitud
        direction = self._wind_direction(altitude)
        
        return {
            "speed": speed,
            "direction": direction
        }
        
    def _get_layer(self, altitude: float) -> str:
        """Determina la capa atmosférica"""
        for layer, (min_alt, max_alt) in self.layers.items():
            if min_alt <= altitude < max_alt:
                return layer
        return "stratosphere"
        
    def _surface_wind(self) -> float:
        """Modelo de viento superficial"""
        # Distribución Weibull típica
        return np.random.weibull(2.0) * 5.0
        
    def _boundary_wind(self, altitude: float) -> float:
        """Modelo de viento en capa límite"""
        # Ley potencial
        v_ref = 10.0  # Velocidad referencia a 10m
        h_ref = 10.0  # Altura referencia
        alpha = 0.143  # Exponente según terreno
        
        return v_ref * (altitude/h_ref)**alpha
        
    def _upper_wind(self, altitude: float) -> float:
        """Modelo de viento en altura"""
        # Modelo simplificado de jet stream
        max_speed = 50.0  # Velocidad máxima del jet
        jet_height = 10000  # Altura típica del jet
        width = 2000  # Ancho del jet
        
        return max_speed * np.exp(-(altitude - jet_height)**2 / (2*width**2))
        
    def _wind_direction(self, altitude: float) -> float:
        """Calcula dirección del viento"""
        # Giro de Ekman simplificado
        base_direction = np.random.uniform(0, 2*np.pi)
        ekman_spiral = 0.1 * altitude/1000  # 0.1 rad/km
        
        return (base_direction + ekman_spiral) % (2*np.pi)