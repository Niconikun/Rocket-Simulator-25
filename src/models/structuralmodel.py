import numpy as np
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class FailureMode(Enum):
    """Modos de fallo estructural"""
    NONE = "none"
    BUCKLING = "buckling"         # Pandeo
    YIELD = "yield"              # Fluencia
    FATIGUE = "fatigue"          # Fatiga
    VIBRATION = "vibration"      # Vibración excesiva

@dataclass
class MaterialProperties:
    """Propiedades estructurales de materiales"""
    name: str
    yield_strength: float     # Límite de fluencia [Pa]
    ultimate_strength: float  # Resistencia última [Pa]
    elastic_modulus: float    # Módulo de Young [Pa]
    poisson_ratio: float     # Coeficiente de Poisson [-]
    density: float           # Densidad [kg/m³]
    fatigue_limit: float     # Límite de fatiga [Pa]
    damping_ratio: float     # Razón de amortiguamiento [-]

class StructuralModel:
    """Modelo estructural para cohetes"""
    
    def __init__(self, config: Dict):
        """
        Args:
            config: Configuración estructural {
                'materials': Dict,         # Propiedades de materiales
                'sections': List[Dict],    # Secciones del cohete
                'safety_factor': float     # Factor de seguridad
            }
        """
        self.config = config
        self.safety_factor = config['safety_factor']
        
        # Inicializar materiales
        self.materials = {
            name: MaterialProperties(**props)
            for name, props in config['materials'].items()
        }
        
        # Inicializar secciones
        self.sections = self._init_sections(config['sections'])
        
        # Histórico de cargas y daños
        self.load_history = []
        self.damage_history = []
        self.natural_frequencies = []
        
    def _init_sections(self, sections_config: List[Dict]) -> List[Dict]:
        """Inicializa secciones estructurales"""
        sections = []
        for section in sections_config:
            material = self.materials[section['material']]
            sections.append({
                'name': section['name'],
                'material': material,
                'length': section['length'],
                'radius': section['radius'],
                'thickness': section['thickness'],
                'accumulated_damage': 0.0,
                'cycle_count': 0
            })
        return sections
        
    def calculate_stress_state(self, section: Dict, 
                             forces: np.ndarray, 
                             moments: np.ndarray) -> Dict[str, float]:
        """
        Calcula estado de esfuerzos en una sección.
        
        Args:
            section: Sección a analizar
            forces: Fuerzas aplicadas [N]
            moments: Momentos aplicados [N·m]
            
        Returns:
            Dict con esfuerzos principales
        """
        # Área de la sección
        area = 2 * np.pi * section['radius'] * section['thickness']
        
        # Momento de inercia
        I = np.pi * section['radius']**3 * section['thickness']
        
        # Esfuerzo axial
        sigma_axial = forces[0] / area
        
        # Esfuerzo de flexión
        sigma_bending = (moments[1]**2 + moments[2]**2)**0.5 * section['radius'] / I
        
        # Esfuerzo cortante
        tau = (forces[1]**2 + forces[2]**2)**0.5 / area
        
        # Esfuerzo de Von Mises
        sigma_vm = (sigma_axial**2 + sigma_bending**2 - 
                   sigma_axial*sigma_bending + 3*tau**2)**0.5
        
        return {
            'axial': sigma_axial,
            'bending': sigma_bending,
            'shear': tau,
            'von_mises': sigma_vm
        }
        
    def check_buckling(self, section: Dict, axial_force: float) -> bool:
        """Verifica pandeo"""
        # Fórmula de Euler para pandeo
        L_eff = 0.7 * section['length']  # Longitud efectiva
        I = np.pi * section['radius']**3 * section['thickness']
        P_cr = np.pi**2 * section['material'].elastic_modulus * I / L_eff**2
        
        return abs(axial_force) < P_cr / self.safety_factor
        
    def calculate_natural_frequencies(self, section: Dict) -> np.ndarray:
        """Calcula frecuencias naturales"""
        # Modelo simplificado de viga
        L = section['length']
        E = section['material'].elastic_modulus
        I = np.pi * section['radius']**3 * section['thickness']
        m = section['material'].density * np.pi * section['radius']**2 * L
        
        # Primeros 3 modos
        freq = np.zeros(3)
        for i in range(3):
            beta = (i + 1) * np.pi
            freq[i] = (beta**2 / L**2) * np.sqrt(E * I / m)
            
        return freq
        
    def update_fatigue_damage(self, section: Dict, 
                            stress_amplitude: float) -> None:
        """Actualiza daño por fatiga"""
        if stress_amplitude > section['material'].fatigue_limit:
            # Regla de Miner
            N_f = 1e6 * (section['material'].fatigue_limit/stress_amplitude)**4
            section['accumulated_damage'] += 1/N_f
            section['cycle_count'] += 1
            
    def analyze_structure(self, flight_conditions: Dict) -> Dict[str, Any]:
        """
        Análisis estructural completo.
        
        Args:
            flight_conditions: Condiciones de vuelo {
                'forces': np.ndarray,      # Fuerzas [N]
                'moments': np.ndarray,     # Momentos [N·m]
                'acceleration': float,     # Aceleración [m/s²]
                'vibration_freq': float   # Frecuencia de vibración [Hz]
            }
        """
        results = {}
        
        for section in self.sections:
            # Análisis de esfuerzos
            stresses = self.calculate_stress_state(
                section, 
                flight_conditions['forces'],
                flight_conditions['moments']
            )
            
            # Verificar pandeo
            buckling_ok = self.check_buckling(
                section,
                flight_conditions['forces'][0]
            )
            
            # Frecuencias naturales
            nat_freq = self.calculate_natural_frequencies(section)
            
            # Actualizar fatiga
            self.update_fatigue_damage(
                section,
                stresses['von_mises']/2  # Amplitud aproximada
            )
            
            # Determinar modo de fallo
            failure_mode = FailureMode.NONE
            if not buckling_ok:
                failure_mode = FailureMode.BUCKLING
            elif stresses['von_mises'] > section['material'].yield_strength:
                failure_mode = FailureMode.YIELD
            elif section['accumulated_damage'] > 1.0:
                failure_mode = FailureMode.FATIGUE
            elif abs(flight_conditions['vibration_freq'] - nat_freq[0]) < 1.0:
                failure_mode = FailureMode.VIBRATION
                
            # Guardar resultados
            results[section['name']] = {
                'stresses': stresses,
                'natural_frequencies': nat_freq,
                'accumulated_damage': section['accumulated_damage'],
                'failure_mode': failure_mode
            }
            
        # Guardar historia
        self.load_history.append(results)
        
        return results