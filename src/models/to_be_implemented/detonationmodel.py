import numpy as np
from typing import Dict, Any
import logging

class DetonationModel:
    """
    Modelo de detonación para ojivas.
    
    Referencias:
        - Kinney, G. F., & Graham, K. J. (1985). Explosive shocks in air
        - Baker, W. E. (1973). Explosions in air
    """
    
    def __init__(self, warhead_config: Dict[str, Any]):
        """
        Inicializa el modelo de detonación.
        
        Args:
            warhead_config: Configuración de la ojiva {
                "type": str,          # Tipo de ojiva
                "mass": float,        # Masa explosiva [kg]
                "velocity": float,    # Velocidad de detonación [m/s]
                "radius": float       # Radio efectivo [m]
            }
        """
        self._validate_config(warhead_config)
        self.config = warhead_config
        self.is_armed = False
        self.has_detonated = False
        
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Valida la configuración de la ojiva"""
        required = ["type", "mass", "velocity", "radius"]
        for param in required:
            if param not in config:
                raise ValueError(f"Falta parámetro: {param}")
                
        if config["mass"] <= 0 or config["velocity"] <= 0 or config["radius"] <= 0:
            raise ValueError("Los parámetros físicos deben ser positivos")
            
    def arm(self, current_altitude: float) -> bool:
        """
        Intenta armar la ojiva basado en condiciones de seguridad.
        
        Args:
            current_altitude: Altitud actual [m]
            
        Returns:
            bool: True si se armó exitosamente
        """
        min_safe_altitude = 1000  # [m]
        
        if current_altitude < min_safe_altitude:
            logging.warning(f"Altitud {current_altitude}m insuficiente para armado")
            return False
            
        self.is_armed = True
        return True
        
    def calculate_blast_effects(self, distance: float, altitude: float) -> Dict[str, float]:
        """
        Calcula los efectos de la explosión a una distancia dada.
        
        Args:
            distance: Distancia al punto de detonación [m]
            altitude: Altitud de detonación [m]
            
        Returns:
            Dict con efectos de la explosión
        """
        if not self.is_armed:
            return {"pressure": 0.0, "impulse": 0.0}
            
        # Factor de escala basado en altitud (densidad del aire)
        altitude_factor = np.exp(-altitude/7400)  # Escala de altura atmosférica
        
        # Presión de blast basada en TNT equivalente
        tnt_equivalent = self.config["mass"] * 4.184e6  # [J]
        scaled_distance = distance / (tnt_equivalent**(1/3))
        
        # Modelo de Kingery-Bulmash simplificado
        peak_pressure = 808 * (scaled_distance**-1.8) * altitude_factor
        positive_impulse = 0.067 * (scaled_distance**-1.4) * altitude_factor
        
        return {
            "pressure": peak_pressure,        # [kPa]
            "impulse": positive_impulse,      # [kPa·s]
            "radius": self.config["radius"],  # [m]
            "altitude": altitude              # [m]
        }
        
    def trigger_detonation(self, altitude: float) -> Dict[str, Any]:
        """
        Intenta detonar la ojiva.
        
        Args:
            altitude: Altitud actual [m]
            
        Returns:
            Dict con resultados de la detonación
        """
        if self.has_detonated:
            return {"status": "already_detonated"}
            
        if not self.is_armed:
            return {"status": "not_armed"}
            
        self.has_detonated = True
        
        # Calcular efectos principales
        effects = self.calculate_blast_effects(
            distance=0,  # En el punto de detonación
            altitude=altitude
        )
        
        return {
            "status": "detonated",
            "time": None,  # A ser llenado por el simulador
            "location": None,  # A ser llenado por el simulador
            "effects": effects
        }