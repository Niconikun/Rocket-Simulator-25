import numpy as np

class Parachute:
    def __init__(self, diameter, Cd, deployment_altitude, deployment_time=None):
        """
        Inicializa el paracaídas.
        
        Args:
            diameter (float): Diámetro del paracaídas desplegado [m]
            Cd (float): Coeficiente de arrastre del paracaídas [-]
            deployment_altitude (float): Altitud de despliegue [m]
            deployment_time (float, opcional): Tiempo de despliegue [s]
        """
        # Validar parámetros
        if diameter <= 0:
            raise ValueError("El diámetro debe ser positivo")
        if Cd <= 0:
            raise ValueError("El coeficiente de arrastre debe ser positivo")
        if deployment_altitude < 0:
            raise ValueError("La altitud de despliegue no puede ser negativa")
        
        self.diameter = diameter
        self.Cd = Cd
        self.deployment_altitude = deployment_altitude
        self.deployment_time = deployment_time or 1.0
        
        # Estados del paracaídas
        self.is_deployed = False
        self.is_deploying = False
        self.deployment_start_time = None
        
        # Calcular área
        self.area = np.pi * (diameter/2)**2
        
        # Parámetros de seguridad
        self.min_safe_velocity = 20.0  # [m/s]
        self.max_safe_velocity = 150.0  # [m/s]
        
    def _check_deployment_conditions(self, altitude, velocity):
        """
        Verifica si es seguro desplegar el paracaídas.
        
        Args:
            altitude (float): Altitud actual [m]
            velocity (float): Velocidad actual [m/s]
            
        Returns:
            bool: True si es seguro desplegar
        """
        # Verificar altitud
        if altitude < 0.1 * self.deployment_altitude:  # Muy bajo
            return False
            
        # Verificar velocidad
        if velocity < self.min_safe_velocity:  # Muy lento
            return False
        if velocity > self.max_safe_velocity:  # Muy rápido
            return False
            
        # Verificar si estamos en la altitud de despliegue
        return altitude <= self.deployment_altitude
        
    def start_deployment(self, current_time):
        """
        Inicia la secuencia de despliegue.
        
        Args:
            current_time (float): Tiempo actual de la simulación [s]
        """
        if not self.is_deployed and not self.is_deploying:
            self.is_deploying = True
            self.deployment_start_time = current_time
            
    def get_deployment_factor(self, current_time):
        """
        Calcula el factor de despliegue (0 = plegado, 1 = completamente desplegado).
        
        Args:
            current_time (float): Tiempo actual de la simulación [s]
            
        Returns:
            float: Factor de despliegue entre 0 y 1
        """
        if not self.is_deploying:
            return 0.0
            
        elapsed_time = current_time - self.deployment_start_time
        factor = min(1.0, elapsed_time / self.deployment_time)
        
        if factor >= 1.0:
            self.is_deployed = True
            self.is_deploying = False
            
        return factor
        
    def calculate_drag(self, density, velocity):
        """
        Calcula la fuerza de arrastre del paracaídas.
        
        Args:
            density (float): Densidad del aire [kg/m³]
            velocity (float): Velocidad [m/s]
            
        Returns:
            float: Fuerza de arrastre [N]
        """
        if not self.is_deploying and not self.is_deployed:
            return 0.0
            
        # Factor de efectividad basado en el despliegue
        if self.is_deploying:
            effectiveness = self.get_deployment_factor(self.deployment_start_time)
        else:
            effectiveness = 1.0
            
        # Cálculo de la fuerza
        q = 0.5 * density * velocity**2
        return q * self.area * self.Cd * effectiveness