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
        self.diameter = diameter
        self.Cd = Cd
        self.deployment_altitude = deployment_altitude
        self.deployment_time = deployment_time
        self.is_deployed = False
        
        # Calcular área
        self.area = np.pi * (diameter/2)**2
        
        # Tiempo de despliegue (típicamente 0.5-1.5s)
        self.deployment_duration = 1.0
        self.deployment_start_time = None