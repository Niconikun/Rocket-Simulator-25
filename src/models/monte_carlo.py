from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from .markov_models import AtmosphericMarkovModel, FailureMarkovModel, ParachuteMarkovModel
from .rocket import Rocket
from .wind_rose import WindRose, AltitudeWindProfile, WindRoseIntegrator, Season
from datetime import datetime
import json

class MonteCarloSimulation:
    def __init__(self, rocket: Rocket, n_sims: int, max_altitude: float,
                 location_name: str = "generic", season: Optional[Season] = None):
        """
        Inicializa la simulación Monte Carlo con modelo de rosa de vientos.
        
        Args:
            rocket: Instancia del cohete a simular
            n_sims: Número de simulaciones
            max_altitude: Altitud máxima [m]
            location_name: Nombre de la ubicación para patrones de viento específicos
            season: Estación del año para patrones de viento estacionales
        """
        self.rocket = rocket
        self.n_sims = n_sims
        self.max_altitude = max_altitude
        self.location_name = location_name
        
        # Determinar estación si no se proporciona
        if season is None:
            month = datetime.now().month
            if month in [3, 4, 5]:
                season = Season.SPRING
            elif month in [6, 7, 8]:
                season = Season.SUMMER
            elif month in [9, 10, 11]:
                season = Season.AUTUMN
            else:
                season = Season.WINTER
        self.season = season
        
        # Inicializar modelos de viento
        self.wind_rose = WindRose(location_name)
        self.altitude_profile = AltitudeWindProfile()
        self.wind_integrator = WindRoseIntegrator(self.wind_rose, self.altitude_profile)
        
        # Inicializar modelos de Markov (mantener compatibilidad)
        self.atm_model = AtmosphericMarkovModel()
        self.fail_model = FailureMarkovModel()
        self.chute_model = ParachuteMarkovModel()
        
        # Resultados mejorados
        self.landing_points: List[Tuple[float, float]] = []
        self.trajectories: List[Dict] = []
        self.wind_conditions: List[List[Dict]] = []  # Condiciones de viento por trayectoria
        self.failure_stats: Dict[str, int] = {state: 0 for state in self.fail_model.states}
        self.chute_stats: Dict[str, int] = {state: 0 for state in self.chute_model.states}
        
        # Estadísticas de viento
        self.wind_statistics = {
            'surface_winds': [],
            'max_altitude_winds': [],
            'average_wind_speed': [],
            'dominant_direction': []
        }
        
    def run_single_simulation(self, sim_index: int = 0) -> Dict:
        """
        Ejecuta una simulación individual con modelo de viento mejorado.
        
        Args:
            sim_index: Índice de la simulación (para variabilidad)
            
        Returns:
            Diccionario con datos de la trayectoria
        """
        trajectory = {
            'altitude': [],
            'x': [],
            'y': [],
            'time': [],
            'wind_east': [],
            'wind_north': [],
            'wind_speed': [],
            'wind_direction': [],
            'rocket_state': [],
            'chute_state': []
        }
        
        wind_conditions_sim = []
        
        # Reiniciar cohete
        self.rocket.reset()
        
        # Estado inicial
        rocket_state = "nominal"
        chute_state = "packed"
        
        # Tiempo de simulación
        dt = 0.1  # Paso de tiempo [s]
        time = 0.0
        
        # Agregar variabilidad temporal para cada simulación
        time_of_day = 12.0 + np.random.normal(0, 3.0)  # Variación alrededor del mediodía
        time_of_day = max(0, min(24, time_of_day))
        
        # Simulación hasta aterrizaje
        while self.rocket.r_enu[2] >= 0:  # Mientras esté en el aire
            current_altitude = self.rocket.r_enu[2]
            
            # Obtener condiciones de viento usando rosa de vientos
            wind_east, wind_north, wind_up = self.wind_integrator.get_wind_for_trajectory(
                altitude=current_altitude,
                season=self.season,
                time_of_day=time_of_day,
                add_turbulence=True
            )
            
            # Calcular parámetros de viento para estadísticas
            wind_speed = np.sqrt(wind_east**2 + wind_north**2)
            wind_direction = np.degrees(np.arctan2(wind_east, wind_north)) % 360
            
            # Almacenar condiciones de viento
            wind_condition = {
                'time': time,
                'altitude': current_altitude,
                'wind_east': wind_east,
                'wind_north': wind_north,
                'wind_up': wind_up,
                'wind_speed': wind_speed,
                'wind_direction': wind_direction
            }
            wind_conditions_sim.append(wind_condition)
            
            # Actualizar estados usando modelos de Markov (compatibilidad)
            rocket_state = self.fail_model.get_next_state(
                rocket_state,
                altitude=current_altitude,
                velocity=getattr(self.rocket, 'v_norm', 100),
                acceleration=getattr(self.rocket, 'a_norm', 20)
            )
            
            # Actualizar estado del paracaídas si corresponde
            if current_altitude > 100 and current_altitude < self.max_altitude:
                chute_state = self.chute_model.get_next_state(
                    chute_state,
                    velocity=getattr(self.rocket, 'v_norm', 50),
                    altitude=current_altitude
                )
            
            # Aplicar efectos del viento al cohete
            # Nota: Esto requeriría integración con el modelo de cohete existente
            # Por ahora, simulamos el efecto del viento en la posición
            if hasattr(self.rocket, 'apply_wind_forces'):
                self.rocket.apply_wind_forces(wind_east, wind_north, wind_up)
            else:
                # Simulación simplificada del efecto del viento
                self.rocket.r_enu[0] += wind_east * dt  # Desplazamiento este
                self.rocket.r_enu[1] += wind_north * dt  # Desplazamiento norte
            
            # Actualizar cohete (simplificado para demostración)
            if hasattr(self.rocket, 'update_state'):
                self.rocket.update_state()
            else:
                # Simulación básica de trayectoria
                if current_altitude < self.max_altitude and rocket_state == "nominal":
                    self.rocket.r_enu[2] += 10 * dt  # Ascenso
                else:
                    # Descenso con paracaídas
                    descent_rate = -5 if chute_state == "nominal" else -15
                    self.rocket.r_enu[2] += descent_rate * dt
            
            # Guardar estado en trayectoria
            trajectory['altitude'].append(current_altitude)
            trajectory['x'].append(self.rocket.r_enu[0])
            trajectory['y'].append(self.rocket.r_enu[1])
            trajectory['time'].append(time)
            trajectory['wind_east'].append(wind_east)
            trajectory['wind_north'].append(wind_north)
            trajectory['wind_speed'].append(wind_speed)
            trajectory['wind_direction'].append(wind_direction)
            trajectory['rocket_state'].append(rocket_state)
            trajectory['chute_state'].append(chute_state)
            
            time += dt
            
            # Protección contra bucles infinitos
            if time > 1000:  # Máximo 1000 segundos
                break
        
        # Almacenar condiciones de viento de esta simulación
        self.wind_conditions.append(wind_conditions_sim)
        
        # Calcular estadísticas de viento para esta simulación
        if wind_conditions_sim:
            wind_speeds = [wc['wind_speed'] for wc in wind_conditions_sim]
            wind_directions = [wc['wind_direction'] for wc in wind_conditions_sim]
            
            self.wind_statistics['surface_winds'].append(wind_conditions_sim[0])
            self.wind_statistics['max_altitude_winds'].append(
                max(wind_conditions_sim, key=lambda x: x['altitude'])
            )
            self.wind_statistics['average_wind_speed'].append(np.mean(wind_speeds))
            
            # Calcular dirección dominante (moda circular)
            direction_bins = np.arange(0, 361, 22.5)
            hist, _ = np.histogram(wind_directions, bins=direction_bins)
            dominant_idx = np.argmax(hist)
            dominant_direction = (direction_bins[dominant_idx] + direction_bins[dominant_idx + 1]) / 2
            self.wind_statistics['dominant_direction'].append(dominant_direction)
        
        return trajectory

    def run_simulations(self, progress_callback=None):
        """
        Ejecuta todas las simulaciones Monte Carlo con modelo de viento mejorado.
        
        Args:
            progress_callback: Función de callback para progreso
        """
        for i in range(self.n_sims):
            # Ejecutar simulación individual
            trajectory = self.run_single_simulation(sim_index=i)
            self.trajectories.append(trajectory)
            
            # Guardar punto de aterrizaje
            if trajectory['x'] and trajectory['y']:
                self.landing_points.append((
                    trajectory['x'][-1],
                    trajectory['y'][-1]
                ))
                
                # Actualizar estadísticas
                final_rocket_state = trajectory['rocket_state'][-1] if trajectory['rocket_state'] else "nominal"
                final_chute_state = trajectory['chute_state'][-1] if trajectory['chute_state'] else "packed"
                
                self.failure_stats[final_rocket_state] += 1
                self.chute_stats[final_chute_state] += 1
            
            # Actualizar progreso
            if progress_callback:
                progress_callback((i + 1) / self.n_sims)

    def analyze_results(self) -> Dict:
        """
        Analiza los resultados de las simulaciones con estadísticas de viento mejoradas.
        
        Returns:
            Diccionario con análisis completo de resultados
        """
        if not self.landing_points:
            return {
                'error': 'No hay datos de aterrizaje para analizar',
                'landing_points': pd.DataFrame(),
                'wind_statistics': {},
                'failure_stats': pd.Series(self.failure_stats),
                'chute_stats': pd.Series(self.chute_stats)
            }
        
        # Análisis de puntos de aterrizaje
        landing_df = pd.DataFrame(self.landing_points, columns=['X', 'Y'])
        
        # Calcular estadísticas de dispersión
        distances = np.sqrt(landing_df['X']**2 + landing_df['Y']**2)
        
        # Análisis de viento
        wind_analysis = self._analyze_wind_patterns()
        
        # Análisis de zona de aterrizaje
        landing_zone_analysis = self._analyze_landing_zone(landing_df)
        
        # Análisis de confiabilidad
        reliability_analysis = self._analyze_reliability()
        
        return {
            'landing_points': landing_df,
            'failure_stats': pd.Series(self.failure_stats),
            'chute_stats': pd.Series(self.chute_stats),
            'basic_statistics': {
                'mean_distance': distances.mean(),
                'max_distance': distances.max(),
                'std_distance': distances.std(),
                'median_distance': distances.median(),
                'percentile_95': np.percentile(distances, 95),
                'reliability': self.failure_stats.get('nominal', 0) / self.n_sims if self.n_sims > 0 else 0
            },
            'wind_analysis': wind_analysis,
            'landing_zone': landing_zone_analysis,
            'reliability': reliability_analysis,
            'seasonal_info': {
                'season': self.season.value,
                'location': self.location_name,
                'wind_rose_stats': self.wind_rose.get_seasonal_statistics(self.season)
            }
        }
    
    def _analyze_wind_patterns(self) -> Dict:
        """Analiza patrones de viento de todas las simulaciones"""
        if not self.wind_statistics['average_wind_speed']:
            return {}
        
        return {
            'mean_surface_wind_speed': np.mean([
                ws['wind_speed'] for ws in self.wind_statistics['surface_winds']
            ]),
            'mean_max_altitude_wind_speed': np.mean([
                ws['wind_speed'] for ws in self.wind_statistics['max_altitude_winds']
            ]),
            'average_wind_speed': np.mean(self.wind_statistics['average_wind_speed']),
            'dominant_direction_deg': np.mean(self.wind_statistics['dominant_direction']),
            'wind_speed_std': np.std(self.wind_statistics['average_wind_speed']),
            'direction_variability': np.std(self.wind_statistics['dominant_direction'])
        }
    
    def _analyze_landing_zone(self, landing_df: pd.DataFrame) -> Dict:
        """Analiza características de la zona de aterrizaje"""
        if landing_df.empty:
            return {}
        
        # Centro de masa de la zona de aterrizaje
        center_x = landing_df['X'].mean()
        center_y = landing_df['Y'].mean()
        
        # Elipse de confianza simplificada (95%)
        confidence_level = 0.95
        
        # Calcular covarianza
        cov_matrix = np.cov(landing_df['X'], landing_df['Y'])
        eigenvals, eigenvecs = np.linalg.eigh(cov_matrix)
        
        # Chi-squared value for 95% confidence (approximation)
        chi2_val = 5.991  # chi2(0.95, df=2) approximately
        
        # Semieje mayor y menor de la elipse
        semi_major = np.sqrt(chi2_val * np.max(eigenvals))
        semi_minor = np.sqrt(chi2_val * np.min(eigenvals))
        
        # Ángulo de orientación
        major_axis_angle = np.degrees(np.arctan2(eigenvecs[1, np.argmax(eigenvals)], 
                                                eigenvecs[0, np.argmax(eigenvals)]))
        
        return {
            'center_x': center_x,
            'center_y': center_y,
            'ellipse_semi_major': semi_major,
            'ellipse_semi_minor': semi_minor,
            'ellipse_orientation_deg': major_axis_angle,
            'area_95_confidence': np.pi * semi_major * semi_minor,
            'max_range_x': landing_df['X'].max() - landing_df['X'].min(),
            'max_range_y': landing_df['Y'].max() - landing_df['Y'].min()
        }
    
    def _analyze_reliability(self) -> Dict:
        """Analiza estadísticas de confiabilidad"""
        total_sims = sum(self.failure_stats.values())
        if total_sims == 0:
            return {}
        
        return {
            'mission_success_rate': self.failure_stats.get('nominal', 0) / total_sims,
            'engine_failure_rate': (
                self.failure_stats.get('engine_warning', 0) + 
                self.failure_stats.get('engine_failure', 0)
            ) / total_sims,
            'structural_failure_rate': (
                self.failure_stats.get('struct_warning', 0) + 
                self.failure_stats.get('struct_failure', 0)
            ) / total_sims,
            'parachute_success_rate': self.chute_stats.get('nominal', 0) / total_sims if total_sims > 0 else 0
        }
    
    def export_results(self, filename: str):
        """Exporta resultados completos a archivo JSON"""
        results = self.analyze_results()
        
        # Convertir DataFrames y arrays a formato serializable
        export_data = {
            'simulation_parameters': {
                'n_simulations': self.n_sims,
                'max_altitude': self.max_altitude,
                'location': self.location_name,
                'season': self.season.value
            },
            'landing_points': results['landing_points'].to_dict('records') if not results['landing_points'].empty else [],
            'statistics': results.get('basic_statistics', {}),
            'wind_analysis': results.get('wind_analysis', {}),
            'landing_zone': results.get('landing_zone', {}),
            'reliability': results.get('reliability', {}),
            'failure_stats': results['failure_stats'].to_dict(),
            'chute_stats': results['chute_stats'].to_dict()
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)