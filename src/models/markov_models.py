import numpy as np
from typing import List, Dict, Tuple

class AtmosphericMarkovModel:
    """Modelo de Markov para condiciones atmosféricas"""
    def __init__(self):
        # Estados: [calma, moderado, fuerte, turbulento]
        self.states = ["calm", "moderate", "strong", "turbulent"]
        
        # Matriz de transición (valores típicos basados en datos meteorológicos)
        self.P = np.array([
            [0.7, 0.2, 0.08, 0.02],  # Desde calma
            [0.1, 0.6, 0.25, 0.05],  # Desde moderado
            [0.05, 0.15, 0.7, 0.1],  # Desde fuerte
            [0.02, 0.08, 0.3, 0.6]   # Desde turbulento
        ])
        
        # Características del viento por estado
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
    
    def get_wind_conditions(self, state: str) -> Dict:
        """Genera condiciones de viento basadas en el estado"""
        props = self.wind_properties[state]
        base_speed = np.random.uniform(*props["speed_range"])
        gust_speed = base_speed * props["gust_factor"]
        return {
            "base_speed": base_speed,
            "gust_speed": gust_speed,
            "direction": np.random.uniform(0, 360)
        }

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