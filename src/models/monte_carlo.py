from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from .markov_models import AtmosphericMarkovModel, FailureMarkovModel, ParachuteMarkovModel
from .rocket import Rocket

class MonteCarloSimulation:
    def __init__(self, rocket: Rocket, n_sims: int, max_altitude: float):
        """
        Inicializa la simulación Monte Carlo
        
        Args:
            rocket: Instancia del cohete a simular
            n_sims: Número de simulaciones
            max_altitude: Altitud máxima [m]
        """
        self.rocket = rocket
        self.n_sims = n_sims
        self.max_altitude = max_altitude
        
        # Inicializar modelos de Markov
        self.atm_model = AtmosphericMarkovModel()
        self.fail_model = FailureMarkovModel()
        self.chute_model = ParachuteMarkovModel()
        
        # Resultados
        self.landing_points: List[Tuple[float, float]] = []
        self.trajectories: List[Dict] = []
        self.failure_stats: Dict[str, int] = {state: 0 for state in self.fail_model.states}
        self.chute_stats: Dict[str, int] = {state: 0 for state in self.chute_model.states}
        
    def run_single_simulation(self, wind_initial: str) -> Dict:
        """Ejecuta una simulación individual"""
        trajectory = {
            'altitude': [],
            'x': [],
            'y': [],
            'wind_state': [],
            'rocket_state': [],
            'chute_state': []
        }
        
        # Reiniciar cohete
        self.rocket.reset()
        
        # Estado inicial
        wind_state = wind_initial
        rocket_state = "nominal"
        chute_state = "packed"
        
        while self.rocket.r_enu[2] >= 0:  # Mientras esté en el aire
            # Actualizar estados
            wind_state = self.atm_model.get_next_state(wind_state)
            wind_cond = self.atm_model.get_wind_conditions(wind_state)
            
            rocket_state = self.fail_model.get_next_state(
                rocket_state, 
                altitude=self.rocket.r_enu[2],
                velocity=self.rocket.v_norm,
                acceleration=self.rocket.a_norm
            )
            
            # Actualizar cohete
            self.rocket.update_state(wind_cond)
            
            # Guardar estado
            trajectory['altitude'].append(self.rocket.r_enu[2])
            trajectory['x'].append(self.rocket.r_enu[0])
            trajectory['y'].append(self.rocket.r_enu[1])
            trajectory['wind_state'].append(wind_state)
            trajectory['rocket_state'].append(rocket_state)
            trajectory['chute_state'].append(chute_state)
            
        return trajectory

    def run_simulations(self, wind_initial: str, progress_callback=None):
        """Ejecuta todas las simulaciones"""
        for i in range(self.n_sims):
            # Ejecutar simulación
            trajectory = self.run_single_simulation(wind_initial)
            self.trajectories.append(trajectory)
            
            # Guardar punto de aterrizaje
            self.landing_points.append((
                trajectory['x'][-1],
                trajectory['y'][-1]
            ))
            
            # Actualizar estadísticas
            self.failure_stats[trajectory['rocket_state'][-1]] += 1
            self.chute_stats[trajectory['chute_state'][-1]] += 1
            
            # Actualizar progreso
            if progress_callback:
                progress_callback((i + 1) / self.n_sims)

    def analyze_results(self) -> Dict:
        """Analiza los resultados de las simulaciones"""
        landing_df = pd.DataFrame(self.landing_points, columns=['X', 'Y'])
        
        # Calcular estadísticas
        distances = np.sqrt(landing_df['X']**2 + landing_df['Y']**2)
        
        return {
            'landing_points': landing_df,
            'failure_stats': pd.Series(self.failure_stats),
            'chute_stats': pd.Series(self.chute_stats),
            'statistics': {
                'mean_distance': distances.mean(),
                'max_distance': distances.max(),
                'std_distance': distances.std(),
                'reliability': self.failure_stats['nominal'] / self.n_sims
            }
        }