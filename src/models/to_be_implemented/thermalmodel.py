import numpy as np
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class MaterialProperties:
    """Propiedades térmicas de materiales"""
    name: str
    density: float          # Densidad [kg/m³]
    specific_heat: float    # Calor específico [J/kg·K]
    conductivity: float     # Conductividad térmica [W/m·K]
    max_temp: float         # Temperatura máxima [K]
    emissivity: float      # Emisividad [-]

class ThermalModel:
    """Modelo térmico para cohetes"""
    
    def __init__(self, config: Dict):
        """
        Args:
            config: Configuración térmica {
                'ambient_temp': float,      # Temperatura ambiente [K]
                'time_step': float,         # Paso de tiempo [s]
                'components': List[Dict],    # Lista de componentes
                'materials': Dict           # Propiedades de materiales
            }
        """
        self.config = config
        self.ambient_temp = config['ambient_temp']
        self.dt = config['time_step']
        
        # Inicializar materiales
        self.materials = {
            name: MaterialProperties(**props)
            for name, props in config['materials'].items()
        }
        
        # Inicializar componentes
        self.components = self._init_components(config['components'])
        
        # Historial
        self.hist_temperatures = []
        self.hist_heat_flux = []
        
    def _init_components(self, components_config: List[Dict]) -> List[Dict]:
        """Inicializa componentes con temperaturas iniciales"""
        components = []
        for comp in components_config:
            material = self.materials[comp['material']]
            components.append({
                'name': comp['name'],
                'material': material,
                'volume': comp['volume'],
                'surface_area': comp['surface_area'],
                'temperature': self.ambient_temp,
                'mass': material.density * comp['volume'],
                'neighbors': comp.get('neighbors', [])
            })
        return components
        
    def calculate_aero_heating(self, mach: float, altitude: float, 
                             velocity: float) -> float:
        """
        Calcula calentamiento aerodinámico.
        
        Args:
            mach: Número Mach [-]
            altitude: Altitud [m]
            velocity: Velocidad [m/s]
            
        Returns:
            float: Flujo de calor [W/m²]
        """
        # Fórmula de Sutton-Graves para flujo de calor
        k = 1.7415e-4  # Constante de Sutton-Graves
        rho = 1.225 * np.exp(-altitude/7400)  # Densidad atmosférica
        
        q_dot = k * np.sqrt(rho) * (velocity**3)
        
        # Factor de corrección por número Mach
        if mach > 1:
            q_dot *= (1 + 0.15 * mach**2)
            
        return q_dot
        
    def calculate_radiation(self, T_surface: float) -> float:
        """Calcula pérdida de calor por radiación"""
        sigma = 5.67e-8  # Constante de Stefan-Boltzmann
        return sigma * T_surface**4
        
    def calculate_conduction(self, T1: float, T2: float, 
                           k: float, A: float, dx: float) -> float:
        """Calcula transferencia de calor por conducción"""
        return k * A * (T2 - T1) / dx
        
    def update(self, flight_conditions: Dict[str, float]) -> None:
        """
        Actualiza temperaturas de componentes.
        
        Args:
            flight_conditions: Condiciones de vuelo {
                'mach': float,
                'altitude': float,
                'velocity': float
            }
        """
        # Calentamiento aerodinámico
        q_aero = self.calculate_aero_heating(
            flight_conditions['mach'],
            flight_conditions['altitude'],
            flight_conditions['velocity']
        )
        
        # Actualizar cada componente
        for component in self.components:
            # Calor por aerodinámica
            Q_aero = q_aero * component['surface_area']
            
            # Calor por radiación
            Q_rad = self.calculate_radiation(component['temperature'])
            Q_rad *= component['material'].emissivity * component['surface_area']
            
            # Calor por conducción con vecinos
            Q_cond = 0
            for neighbor in component['neighbors']:
                other = next(c for c in self.components if c['name'] == neighbor)
                k_avg = (component['material'].conductivity + 
                        other['material'].conductivity) / 2
                A_contact = min(component['surface_area'], other['surface_area'])
                dx = 0.01  # Distancia característica [m]
                
                Q_cond += self.calculate_conduction(
                    component['temperature'],
                    other['temperature'],
                    k_avg, A_contact, dx
                )
            
            # Cambio neto de temperatura
            Q_net = Q_aero - Q_rad + Q_cond
            dT = Q_net * self.dt / (
                component['mass'] * component['material'].specific_heat
            )
            
            # Actualizar temperatura
            component['temperature'] += dT
            
            # Verificar límites
            if component['temperature'] > component['material'].max_temp:
                self.trigger_thermal_warning(component)
                
        # Guardar historia
        self.hist_temperatures.append([
            c['temperature'] for c in self.components
        ])
        self.hist_heat_flux.append(q_aero)
        
    def trigger_thermal_warning(self, component: Dict) -> None:
        """Maneja advertencias térmicas"""
        import logging
        logging.warning(
            f"¡Temperatura crítica en {component['name']}: "
            f"{component['temperature']:.1f}K"
        )