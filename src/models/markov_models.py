import numpy as np
from typing import List, Dict, Tuple
from .wind_rose import WindRose, Season, WindCondition

class AtmosphericMarkovModel:
    """
    Modelo de Markov para condiciones atmosféricas mejorado.
    
    Ahora actúa como wrapper/adaptador para el modelo de rosa de vientos,
    manteniendo compatibilidad con el código existente mientras proporciona
    capacidades mejoradas de modelado de viento.
    """
    def __init__(self, wind_rose: WindRose = None, season: Season = Season.SPRING):
        # Estados originales para compatibilidad
        self.states = ["calm", "moderate", "strong", "turbulent"]
        
        # Matriz de transición original (mantenida para compatibilidad)
        self.P = np.array([
            [0.7, 0.2, 0.08, 0.02],  # Desde calma
            [0.1, 0.6, 0.25, 0.05],  # Desde moderado
            [0.05, 0.15, 0.7, 0.1],  # Desde fuerte
            [0.02, 0.08, 0.3, 0.6]   # Desde turbulento
        ])
        
        # Integración con rosa de vientos
        self.wind_rose = wind_rose if wind_rose else WindRose()
        self.season = season
        
        # Características del viento por estado (actualizadas para consistencia)
        self.wind_properties = {
            "calm": {"speed_range": (0, 5), "gust_factor": 1.1},
            "moderate": {"speed_range": (5, 10), "gust_factor": 1.3},
            "strong": {"speed_range": (10, 15), "gust_factor": 1.5},
            "turbulent": {"speed_range": (15, 25), "gust_factor": 2.0}
        }
        
    def get_next_state(self, current_state: str) -> str:
        """Determina el siguiente estado atmosférico"""
        state_idx = self.states.index(current_state)
        return np.random.choice(self.states, p=self.P[state_idx])
    
    def get_wind_conditions(self, state: str, altitude: float = 0.0) -> Dict:
        """
        Genera condiciones de viento mejoradas usando rosa de vientos.
        
        Args:
            state: Estado atmosférico actual
            altitude: Altitud para condiciones de viento [m]
            
        Returns:
            Diccionario con condiciones de viento mejoradas
        """
        # Obtener condición de viento realista de la rosa de vientos
        wind_condition = self.wind_rose.get_wind_condition(self.season, altitude)
        
        # Mapear la condición realista al estado Markov para compatibilidad
        if wind_condition.speed < 5:
            markov_state = "calm"
        elif wind_condition.speed < 10:
            markov_state = "moderate"
        elif wind_condition.speed < 15:
            markov_state = "strong"
        else:
            markov_state = "turbulent"
        
        # Ajustar condiciones según el estado solicitado
        state_factor = self._get_state_adjustment_factor(state, markov_state)
        
        return {
            "base_speed": wind_condition.speed * state_factor,
            "gust_speed": wind_condition.speed * wind_condition.gust_factor * state_factor,
            "direction": wind_condition.direction,
            "altitude": altitude,
            "turbulence_intensity": wind_condition.turbulence_intensity,
            "wind_east": -wind_condition.speed * np.sin(np.radians(wind_condition.direction)) * state_factor,
            "wind_north": -wind_condition.speed * np.cos(np.radians(wind_condition.direction)) * state_factor,
            "wind_up": 0.0,
            "markov_state": markov_state,
            "requested_state": state
        }
    
    def _get_state_adjustment_factor(self, requested_state: str, natural_state: str) -> float:
        """
        Calcula factor de ajuste entre estado solicitado y estado natural del viento.
        
        Args:
            requested_state: Estado solicitado por el modelo Markov
            natural_state: Estado natural basado en rosa de vientos
            
        Returns:
            Factor multiplicativo para ajustar velocidad del viento
        """
        state_intensities = {
            "calm": 0.5,
            "moderate": 1.0,
            "strong": 1.5,
            "turbulent": 2.0
        }
        
        requested_intensity = state_intensities[requested_state]
        natural_intensity = state_intensities[natural_state]
        
        # Suavizar la transición para evitar cambios abruptos
        factor = 0.7 * (requested_intensity / natural_intensity) + 0.3
        return max(0.2, min(3.0, factor))  # Limitar factor entre 0.2 y 3.0
    
    def set_season(self, season: Season):
        """Actualiza la estación para el modelo de viento"""
        self.season = season
    
    def get_wind_rose_statistics(self) -> Dict:
        """Obtiene estadísticas de la rosa de vientos actual"""
        return self.wind_rose.get_seasonal_statistics(self.season)

class FailureMarkovModel:
    """Modelo de Markov para eventos de fallo"""
    def __init__(self):
        self.states = ["nominal", "engine_warning", "engine_failure", 
                      "struct_warning", "struct_failure"]
        
        # Matriz de transición (valores conservadores)
        self.P = np.array([
            [0.995, 0.003, 0.001, 0.0008, 0.0002],  # Desde nominal
            [0.1, 0.8, 0.08, 0.01, 0.01],           # Desde warning motor
            [0, 0, 1, 0, 0],                        # Desde fallo motor
            [0.1, 0.01, 0.01, 0.8, 0.08],          # Desde warning estructura
            [0, 0, 0, 0, 1]                         # Desde fallo estructura
        ])
        
    def get_next_state(self, current_state: str, altitude: float, 
                      velocity: float, acceleration: float) -> str:
        """
        Determina el siguiente estado basado en condiciones actuales
        """
        state_idx = self.states.index(current_state)
        base_probs = self.P[state_idx]
        
        # Modificar probabilidades según condiciones
        if velocity > 300:  # Velocidad crítica
            base_probs[3:] *= 1.5  # Aumenta prob. fallos estructurales
        if acceleration > 50:  # Aceleración crítica
            base_probs[1:3] *= 1.5  # Aumenta prob. fallos motor
            
        # Renormalizar probabilidades
        base_probs = base_probs / np.sum(base_probs)
        
        return np.random.choice(self.states, p=base_probs)

class ParachuteMarkovModel:
    """Modelo de Markov para comportamiento del paracaídas"""
    def __init__(self):
        self.states = ["packed", "deploying", "nominal", "damaged", "failed"]
        
        # Matriz de transición base
        self.P = np.array([
            [0.99, 0.008, 0, 0.001, 0.001],  # Desde empacado
            [0, 0.1, 0.85, 0.03, 0.02],      # Desde desplegando
            [0, 0, 0.99, 0.009, 0.001],      # Desde nominal
            [0, 0, 0, 0.9, 0.1],             # Desde dañado
            [0, 0, 0, 0, 1]                   # Desde fallado
        ])
        
    def get_next_state(self, current_state: str, velocity: float, 
                      altitude: float) -> str:
        """
        Determina el siguiente estado del paracaídas
        """
        state_idx = self.states.index(current_state)
        mod_probs = self.P[state_idx].copy()
        
        # Modificar probabilidades según condiciones
        if velocity > 150:  # Velocidad muy alta
            mod_probs[3:] *= 2  # Aumenta prob. daño/fallo
        if altitude < 100:  # Baja altitud
            mod_probs[1] *= 1.5  # Aumenta urgencia despliegue
            
        # Renormalizar
        mod_probs = mod_probs / np.sum(mod_probs)
        
        return np.random.choice(self.states, p=mod_probs)