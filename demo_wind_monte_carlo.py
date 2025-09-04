# Simple Wind Rose Demo without numpy dependency
# This demonstrates the wind rose concept using only Python standard library

import random
import math
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class Season(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"

@dataclass
class SimpleWindCondition:
    """Simple wind condition data structure"""
    speed: float  # [m/s]
    direction: float  # [degrees] from North
    altitude: float  # [m]
    gust_factor: float
    turbulence_intensity: float

class SimpleWindRose:
    """Simplified Wind Rose Model for demonstration"""
    
    def __init__(self, location_name: str = "generic"):
        self.location_name = location_name
        
        # Simple 8-direction model instead of 16
        self.directions = [0, 45, 90, 135, 180, 225, 270, 315]  # N, NE, E, SE, S, SW, W, NW
        self.direction_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        
        # Simplified seasonal patterns (probabilities must sum to 1)
        self.seasonal_patterns = {
            Season.SPRING: [0.1, 0.1, 0.1, 0.1, 0.15, 0.15, 0.2, 0.1],  # W dominant
            Season.SUMMER: [0.15, 0.1, 0.1, 0.1, 0.15, 0.15, 0.15, 0.1],  # More balanced
            Season.AUTUMN: [0.1, 0.1, 0.1, 0.1, 0.15, 0.15, 0.25, 0.05],  # W very dominant
            Season.WINTER: [0.05, 0.1, 0.1, 0.1, 0.15, 0.15, 0.3, 0.05]   # W extremely dominant
        }
        
        # Average wind speeds by direction and season
        self.speed_patterns = {
            Season.SPRING: [6, 5, 4, 5, 7, 8, 9, 7],
            Season.SUMMER: [4, 3, 3, 4, 5, 6, 7, 5],
            Season.AUTUMN: [7, 6, 5, 6, 8, 9, 10, 8],
            Season.WINTER: [8, 7, 6, 7, 9, 10, 12, 9]
        }
        
        self.calm_probability = {
            Season.SPRING: 0.05,
            Season.SUMMER: 0.08,
            Season.AUTUMN: 0.04,
            Season.WINTER: 0.02
        }
    
    def get_wind_condition(self, season: Season, altitude: float = 0.0) -> SimpleWindCondition:
        """Generate a wind condition based on simple patterns"""
        
        # Check for calm conditions
        if random.random() < self.calm_probability[season]:
            return SimpleWindCondition(
                speed=random.uniform(0, 1),
                direction=random.uniform(0, 360),
                altitude=altitude,
                gust_factor=1.1,
                turbulence_intensity=0.1
            )
        
        # Select direction based on seasonal probabilities
        rand_val = random.random()
        cumulative = 0
        direction_idx = 0
        
        for i, prob in enumerate(self.seasonal_patterns[season]):
            cumulative += prob
            if rand_val <= cumulative:
                direction_idx = i
                break
        
        # Get base direction and add some variation
        base_direction = self.directions[direction_idx]
        direction = base_direction + random.uniform(-22.5, 22.5)
        direction = direction % 360
        
        # Get wind speed with some randomness
        base_speed = self.speed_patterns[season][direction_idx]
        speed = base_speed + random.uniform(-2, 2)
        speed = max(0, speed)
        
        # Apply altitude correction (simple power law)
        if altitude > 0:
            altitude_factor = (max(altitude, 1) / 10.0) ** 0.2
            speed *= min(altitude_factor, 2.0)  # Cap at 2x surface wind
        
        # Calculate other factors
        gust_factor = 1.3 + 0.02 * speed
        turbulence = max(0.05, 0.3 / max(speed, 1))
        
        return SimpleWindCondition(
            speed=speed,
            direction=direction,
            altitude=altitude,
            gust_factor=gust_factor,
            turbulence_intensity=min(turbulence, 0.8)
        )
    
    def get_wind_vector(self, season: Season, altitude: float = 0.0) -> Tuple[float, float, float]:
        """Get wind as East-North-Up components"""
        condition = self.get_wind_condition(season, altitude)
        
        # Convert meteorological direction to math direction and get components
        direction_rad = math.radians(condition.direction)
        
        # Meteorological: direction wind comes FROM, so negate components
        wind_east = -condition.speed * math.sin(direction_rad)
        wind_north = -condition.speed * math.cos(direction_rad)
        wind_up = 0.0  # Typically negligible
        
        # Add some turbulence
        if random.random() < 0.3:  # 30% chance of turbulence
            turb_std = condition.speed * condition.turbulence_intensity
            wind_east += random.uniform(-turb_std, turb_std)
            wind_north += random.uniform(-turb_std, turb_std)
        
        return wind_east, wind_north, wind_up
    
    def get_seasonal_statistics(self, season: Season) -> Dict:
        """Get basic statistics for a season"""
        patterns = self.seasonal_patterns[season]
        speeds = self.speed_patterns[season]
        
        # Find dominant direction
        max_prob_idx = patterns.index(max(patterns))
        dominant_direction = self.direction_names[max_prob_idx]
        
        return {
            'direction_frequencies': patterns,
            'direction_names': self.direction_names,
            'mean_speeds': speeds,
            'calm_probability': self.calm_probability[season],
            'dominant_direction': dominant_direction
        }

def run_simple_monte_carlo_demo(n_sims: int = 100, max_altitude: float = 2000, 
                               season: Season = Season.SPRING):
    """
    Run a simple Monte Carlo simulation demonstration
    """
    print(f"Running {n_sims} Monte Carlo simulations for {season.value}")
    print(f"Maximum altitude: {max_altitude} m")
    print("-" * 50)
    
    wind_rose = SimpleWindRose("Demo Location")
    landing_points = []
    wind_stats = {'speeds': [], 'directions': []}
    
    for i in range(n_sims):
        # Simple rocket trajectory simulation
        x, y, altitude = 0.0, 0.0, 0.0
        time = 0.0
        dt = 1.0  # 1 second time steps
        
        # Ascent phase
        while altitude < max_altitude:
            # Get wind at current altitude
            wind_east, wind_north, wind_up = wind_rose.get_wind_vector(season, altitude)
            
            # Apply wind drift
            x += wind_east * dt
            y += wind_north * dt
            
            # Simple ascent model
            altitude += 15 * dt  # 15 m/s ascent rate
            time += dt
            
            # Store wind statistics
            wind_speed = math.sqrt(wind_east**2 + wind_north**2)
            wind_direction = math.degrees(math.atan2(wind_east, wind_north)) % 360
            wind_stats['speeds'].append(wind_speed)
            wind_stats['directions'].append(wind_direction)
        
        # Descent phase
        while altitude > 0:
            # Get wind at current altitude
            wind_east, wind_north, wind_up = wind_rose.get_wind_vector(season, altitude)
            
            # Apply wind drift
            x += wind_east * dt
            y += wind_north * dt
            
            # Simple descent model (with parachute)
            altitude -= 8 * dt  # 8 m/s descent rate
            time += dt
            
            # Store wind statistics
            wind_speed = math.sqrt(wind_east**2 + wind_north**2)
            wind_direction = math.degrees(math.atan2(wind_east, wind_north)) % 360
            wind_stats['speeds'].append(wind_speed)
            wind_stats['directions'].append(wind_direction)
        
        # Store landing point
        landing_points.append((x, y))
        
        if (i + 1) % 20 == 0:
            print(f"Completed {i + 1}/{n_sims} simulations")
    
    # Analyze results
    distances = [math.sqrt(x**2 + y**2) for x, y in landing_points]
    
    # Calculate basic statistics
    mean_distance = sum(distances) / len(distances)
    max_distance = max(distances)
    min_distance = min(distances)
    
    # Standard deviation calculation
    variance = sum((d - mean_distance)**2 for d in distances) / len(distances)
    std_distance = math.sqrt(variance)
    
    # Wind statistics
    mean_wind_speed = sum(wind_stats['speeds']) / len(wind_stats['speeds'])
    
    # Print results
    print("\n" + "="*60)
    print("MONTE CARLO SIMULATION RESULTS")
    print("="*60)
    print(f"Number of simulations: {n_sims}")
    print(f"Season: {season.value.title()}")
    print(f"Maximum altitude: {max_altitude} m")
    print()
    print("LANDING ZONE STATISTICS:")
    print(f"  Mean landing distance: {mean_distance:.1f} m")
    print(f"  Maximum distance: {max_distance:.1f} m")
    print(f"  Minimum distance: {min_distance:.1f} m")
    print(f"  Standard deviation: {std_distance:.1f} m")
    print()
    print("WIND STATISTICS:")
    print(f"  Average wind speed: {mean_wind_speed:.1f} m/s")
    
    # Show some sample landing points
    print()
    print("SAMPLE LANDING POINTS (East, North):")
    for i in range(min(10, len(landing_points))):
        x, y = landing_points[i]
        dist = math.sqrt(x**2 + y**2)
        print(f"  Point {i+1}: ({x:6.1f}, {y:6.1f}) - Distance: {dist:.1f} m")
    
    # Wind rose statistics
    wind_rose_stats = wind_rose.get_seasonal_statistics(season)
    print()
    print("WIND ROSE INFORMATION:")
    print(f"  Dominant direction: {wind_rose_stats['dominant_direction']}")
    print(f"  Calm probability: {wind_rose_stats['calm_probability']:.1%}")
    
    return {
        'landing_points': landing_points,
        'distances': distances,
        'wind_stats': wind_stats,
        'mean_distance': mean_distance,
        'std_distance': std_distance,
        'max_distance': max_distance
    }

if __name__ == "__main__":
    print("Simple Wind Rose Monte Carlo Demonstration")
    print("=" * 50)
    
    # Run demonstrations for different seasons
    seasons_to_test = [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]
    
    for season in seasons_to_test:
        results = run_simple_monte_carlo_demo(n_sims=50, season=season)
        print(f"\nSeason {season.value}: Mean distance = {results['mean_distance']:.1f} m")
    
    print("\nDemonstration complete!")
    print("\nThis simplified model demonstrates:")
    print("- Seasonal wind pattern variations")
    print("- Altitude-dependent wind scaling")
    print("- Monte Carlo trajectory propagation")
    print("- Landing zone statistical analysis")