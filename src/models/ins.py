import numpy as np
from typing import Dict, Any
from dataclasses import dataclass
from scipy.stats import norm

@dataclass
class IMUSensorSpecs:
    """Especificaciones de sensores IMU"""
    # Acelerómetro
    accel_noise: float      # Ruido [m/s²]
    accel_bias: float       # Bias [m/s²]
    accel_scale: float      # Error de escala [%]
    
    # Giróscopo
    gyro_noise: float       # Ruido [rad/s]
    gyro_bias: float       # Bias [rad/s]
    gyro_scale: float      # Error de escala [%]
    
    # Magnetómetro
    mag_noise: float        # Ruido [μT]
    mag_bias: float         # Bias [μT]
    mag_scale: float       # Error de escala [%]

class INS:
    """Sistema de Navegación Inercial"""
    
    def __init__(self, sensor_specs: Dict[str, Any]):
        """
        Args:
            sensor_specs: Especificaciones de sensores {
                'accel_noise': float,  # [m/s²]
                'gyro_noise': float,   # [rad/s]
                'mag_noise': float,    # [μT]
                ...
            }
        """
        # Configuración de sensores
        self.specs = IMUSensorSpecs(**sensor_specs)
        
        # Estados estimados
        self.position = np.zeros(3)    # [m]
        self.velocity = np.zeros(3)    # [m/s]
        self.attitude = np.zeros(3)    # [rad]
        
        # Errores de sensores
        self._init_sensor_errors()
        
        # Matrices de covarianza
        self.P = np.eye(9) * 0.01  # Covarianza del estado
        self.Q = np.eye(9) * 0.1   # Covarianza del proceso
        self.R = np.eye(6) * 0.01  # Covarianza de medición
        
        # Historial
        self.hist_position = []
        self.hist_velocity = []
        self.hist_attitude = []
        self.hist_bias = []
        
    def _init_sensor_errors(self):
        """Inicializa errores de sensores"""
        # Bias inicial
        self.accel_bias = norm.rvs(0, self.specs.accel_bias, size=3)
        self.gyro_bias = norm.rvs(0, self.specs.gyro_bias, size=3)
        self.mag_bias = norm.rvs(0, self.specs.mag_bias, size=3)
        
        # Factores de escala
        self.accel_scale = 1.0 + norm.rvs(0, self.specs.accel_scale/100, size=3)
        self.gyro_scale = 1.0 + norm.rvs(0, self.specs.gyro_scale/100, size=3)
        self.mag_scale = 1.0 + norm.rvs(0, self.specs.mag_scale/100, size=3)
        
    def simulate_measurements(self, 
                            true_accel: np.ndarray,
                            true_gyro: np.ndarray,
                            true_mag: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Simula mediciones de sensores con errores.
        
        Args:
            true_accel: Aceleración real [m/s²]
            true_gyro: Velocidad angular real [rad/s]
            true_mag: Campo magnético real [μT]
            
        Returns:
            Dict con mediciones simuladas
        """
        # Agregar ruido y bias
        accel_meas = (
            true_accel * self.accel_scale + 
            self.accel_bias + 
            norm.rvs(0, self.specs.accel_noise, size=3)
        )
        
        gyro_meas = (
            true_gyro * self.gyro_scale + 
            self.gyro_bias + 
            norm.rvs(0, self.specs.gyro_noise, size=3)
        )
        
        mag_meas = (
            true_mag * self.mag_scale + 
            self.mag_bias + 
            norm.rvs(0, self.specs.mag_noise, size=3)
        )
        
        return {
            'accel': accel_meas,
            'gyro': gyro_meas,
            'mag': mag_meas
        }
        
    def update(self, measurements: Dict[str, np.ndarray], dt: float):
        """
        Actualiza el estado usando un filtro de Kalman extendido.
        
        Args:
            measurements: Mediciones de sensores
            dt: Paso de tiempo [s]
        """
        # Predicción
        self._predict(measurements['gyro'], dt)
        
        # Corrección con acelerómetro y magnetómetro
        self._correct(measurements['accel'], measurements['mag'])
        
        # Guardar historia
        self.hist_position.append(self.position.copy())
        self.hist_velocity.append(self.velocity.copy())
        self.hist_attitude.append(self.attitude.copy())
        self.hist_bias.append(np.concatenate([
            self.accel_bias,
            self.gyro_bias
        ]))
        
    def _predict(self, gyro: np.ndarray, dt: float):
        """Etapa de predicción del filtro"""
        # Actualizar actitud usando giróscopos
        self.attitude += gyro * dt
        
        # Actualizar matriz de covarianza
        F = self._get_state_transition_matrix(dt)
        self.P = F @ self.P @ F.T + self.Q
        
    def _correct(self, accel: np.ndarray, mag: np.ndarray):
        """Etapa de corrección del filtro"""
        # Calcular innovación
        z = np.concatenate([accel, mag])
        h = self._measurement_model()
        y = z - h
        
        # Ganancia de Kalman
        H = self._get_measurement_matrix()
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        
        # Actualizar estado
        dx = K @ y
        self.position += dx[0:3]
        self.velocity += dx[3:6]
        self.attitude += dx[6:9]
        
        # Actualizar covarianza
        I = np.eye(9)
        self.P = (I - K @ H) @ self.P
        
    def _get_state_transition_matrix(self, dt: float) -> np.ndarray:
        """Matriz de transición de estado"""
        F = np.eye(9)
        F[0:3, 3:6] = np.eye(3) * dt
        return F
        
    def _get_measurement_matrix(self) -> np.ndarray:
        """Matriz de medición"""
        return np.concatenate([
            np.eye(3), np.zeros((3, 6)),  # Acelerómetro
            np.zeros((3, 6)), np.eye(3)   # Magnetómetro
        ])
        
    def _measurement_model(self) -> np.ndarray:
        """Modelo de medición no lineal"""
        # Modelo simplificado
        gravity = np.array([0, 0, -9.81])
        mag_field = np.array([22000, 0, 42000])  # Campo magnético típico [nT]
        
        return np.concatenate([
            gravity + self.accel_bias,
            mag_field + self.mag_bias
        ])