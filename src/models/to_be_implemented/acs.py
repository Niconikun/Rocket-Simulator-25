import numpy as np
from typing import Dict, List, Tuple
from abc import ABC, abstractmethod

class AttitudeController(ABC):
    """Interfaz base para controladores de actitud"""
    
    @abstractmethod
    def calculate_control_torque(self, 
                               current_state: Dict[str, np.ndarray],
                               target_state: Dict[str, np.ndarray]) -> np.ndarray:
        """Calcula el torque de control necesario"""
        pass

class PIDAttitudeController(AttitudeController):
    """Controlador PID para actitud"""
    
    def __init__(self, gains: Dict[str, float]):
        """
        Args:
            gains: Ganancias del controlador {
                'Kp': float,  # Ganancia proporcional
                'Ki': float,  # Ganancia integral
                'Kd': float   # Ganancia derivativa
            }
        """
        self.Kp = gains['Kp']
        self.Ki = gains['Ki']
        self.Kd = gains['Kd']
        self.error_sum = np.zeros(3)
        self.last_error = np.zeros(3)
        self.dt = 0.01  # Paso de tiempo [s]
        
    def calculate_control_torque(self, 
                               current_state: Dict[str, np.ndarray],
                               target_state: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Calcula torque de control usando PID.
        
        Args:
            current_state: Estado actual {
                'attitude': np.ndarray,  # Ángulos de Euler [rad]
                'angular_velocity': np.ndarray  # Velocidad angular [rad/s]
            }
            target_state: Estado deseado (mismo formato)
            
        Returns:
            np.ndarray: Torque de control [N·m]
        """
        # Calcular error
        error = target_state['attitude'] - current_state['attitude']
        error_rate = (error - self.last_error) / self.dt
        self.error_sum += error * self.dt
        
        # Calcular componentes PID
        P = self.Kp * error
        I = self.Ki * self.error_sum
        D = self.Kd * error_rate
        
        # Actualizar último error
        self.last_error = error
        
        return P + I + D

class FinActuator:
    """Actuador de aleta de control"""
    
    def __init__(self, config: Dict[str, float]):
        """
        Args:
            config: Configuración del actuador {
                'max_deflection': float,  # Deflexión máxima [deg]
                'max_rate': float,        # Velocidad máxima [deg/s]
                'time_constant': float    # Constante de tiempo [s]
            }
        """
        self.config = config
        self.current_angle = 0.0
        self.target_angle = 0.0
        
    def set_deflection(self, angle: float) -> None:
        """Establece ángulo objetivo de la aleta"""
        self.target_angle = np.clip(
            angle,
            -self.config['max_deflection'],
            self.config['max_deflection']
        )
        
    def update(self, dt: float) -> None:
        """Actualiza posición de la aleta"""
        max_change = self.config['max_rate'] * dt
        delta = self.target_angle - self.current_angle
        
        if abs(delta) > max_change:
            delta = max_change * np.sign(delta)
            
        self.current_angle += delta

class AttitudeControlSystem:
    """Sistema completo de control de actitud"""
    
    def __init__(self, config: Dict):
        """
        Args:
            config: Configuración del sistema {
                'controller': Dict,  # Configuración del controlador
                'actuators': Dict   # Configuración de actuadores
            }
        """
        # Inicializar controlador
        self.controller = PIDAttitudeController(config['controller'])
        
        # Inicializar actuadores (4 aletas típicamente)
        self.actuators = [
            FinActuator(config['actuators']) 
            for _ in range(4)
        ]
        
        # Estados
        self.is_active = False
        self.control_mode = 'stabilization'  # o 'maneuver'
        
    def activate(self) -> None:
        """Activa el sistema de control"""
        self.is_active = True
        
    def deactivate(self) -> None:
        """Desactiva el sistema de control"""
        self.is_active = False
        for actuator in self.actuators:
            actuator.set_deflection(0.0)
            
    def update(self, current_state: Dict, target_state: Dict, dt: float) -> None:
        """
        Actualiza el sistema de control.
        
        Args:
            current_state: Estado actual del cohete
            target_state: Estado objetivo
            dt: Paso de tiempo [s]
        """
        if not self.is_active:
            return
            
        # Calcular torque de control necesario
        control_torque = self.controller.calculate_control_torque(
            current_state, target_state
        )
        
        # Convertir torque a deflexiones de aletas
        fin_angles = self._torque_to_fin_angles(control_torque)
        
        # Actualizar actuadores
        for actuator, angle in zip(self.actuators, fin_angles):
            actuator.set_deflection(angle)
            actuator.update(dt)
            
    def _torque_to_fin_angles(self, torque: np.ndarray) -> List[float]:
        """Convierte torque deseado a ángulos de aletas"""
        # Implementar lógica de conversión
        # Este es un modelo simplificado
        yaw_component = torque[0]
        pitch_component = torque[1]
        
        angles = [
            yaw_component + pitch_component,  # Aleta 1
            -yaw_component + pitch_component, # Aleta 2
            -yaw_component - pitch_component, # Aleta 3
            yaw_component - pitch_component  # Aleta 4
        ]
        
        return angles