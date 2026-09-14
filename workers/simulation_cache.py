"""
Simulation Object Cache
======================

Caching system for expensive physics model objects used in Monte Carlo simulations.

This module provides a caching layer to avoid recreating expensive objects
(Planet, Atmosphere, Rocket, Engine, etc.) when running multiple simulations
with the same or similar parameters.

Cache Keys:
- Rocket configs are cached by rocket_name
- Planet objects are cached by (latitude, longitude, date, time)
- Atmosphere objects are cached by temperature profile
- Engine objects are cached by engine configuration hash

Usage:
    from workers.simulation_cache import SimulationCache
    
    cache = SimulationCache.get_instance()
    
    # Get cached rocket config or load it
    rocket_config = cache.get_rocket_config(rocket_name)
    
    # Get cached atmosphere
    atmosphere = cache.get_atmosphere(temperature)
    
    # Get cached planet
    planet = cache.get_planet(latitude, longitude, date, gmst_0)

The cache is automatically cleared when:
- A new simulation batch starts
- Memory pressure is detected
- Explicitly via cache.clear()
"""

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import date, time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Statistics for cache monitoring."""
    rocket_configs: int = 0
    planets: int = 0
    atmospheres: int = 0
    engines: int = 0
    rockets: int = 0
    wind_models: int = 0
    
    hits: int = 0
    misses: int = 0
    
    def to_dict(self) -> dict:
        return {
            'rocket_configs': self.rocket_configs,
            'planets': self.planets,
            'atmospheres': self.atmospheres,
            'engines': self.engines,
            'rockets': self.rockets,
            'wind_models': self.wind_models,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0.0
        }


def _make_hash(*args, **kwargs) -> str:
    """Create a consistent hash from arbitrary arguments."""
    key_parts = []
    
    for arg in args:
        if isinstance(arg, (str, int, float, bool, type(None))):
            key_parts.append(str(arg))
        elif isinstance(arg, (list, tuple)):
            key_parts.append(str(tuple(arg)))
        elif isinstance(arg, dict):
            # Sort dict for consistent hash
            sorted_items = sorted(arg.items())
            key_parts.append(str(tuple(sorted_items)))
        elif isinstance(arg, np.ndarray):
            key_parts.append(str(arg.tolist()))
        elif isinstance(arg, (date, time)):
            key_parts.append(arg.isoformat())
        else:
            key_parts.append(str(type(arg)))
    
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}={_make_hash(value)}")
    
    return hashlib.md5('|'.join(key_parts).encode()).hexdigest()


class SimulationCache:
    """Thread-safe cache for simulation objects.
    
    This is a singleton class that provides caching for expensive objects
    created during Monte Carlo simulations.
    """
    
    _instance: Optional['SimulationCache'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'SimulationCache':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._initialized = True
        self._cache_lock = threading.RLock()
        self._stats = CacheStats()
        
        # Configuration cache: rocket_name -> rocket_config
        self._rocket_config_cache: Dict[str, Dict[str, Any]] = {}
        
        # Planet cache: (lat, lon, date_str, gmst_0) -> Planet
        self._planet_cache: Dict[str, Any] = {}
        
        # Atmosphere cache: temperature -> Atmosphere
        self._atmosphere_cache: Dict[str, Any] = {}
        
        # Engine cache: engine_config_hash -> Engine
        self._engine_cache: Dict[str, Any] = {}
        
        # Wind model cache: wind_config_hash -> WindModel
        self._wind_cache: Dict[str, Any] = {}
        
        # Rocket object cache: rocket_config_hash + overrides_hash -> Rocket
        self._rocket_cache: Dict[str, Any] = {}
        
        # Max cache sizes
        self._max_rocket_configs = 10
        self._max_planets = 20
        self._max_atmospheres = 10
        self._max_engines = 20
        self._max_wind_models = 10
        self._max_rockets = 50
        
        logger.info("SimulationCache initialized")
    
    @classmethod
    def get_instance(cls) -> 'SimulationCache':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        assert cls._instance is not None
        return cls._instance
    
    @property
    def stats(self) -> CacheStats:
        """Get current cache statistics."""
        return self._stats
    
    def clear(self) -> None:
        """Clear all caches."""
        with self._cache_lock:
            self._rocket_config_cache.clear()
            self._planet_cache.clear()
            self._atmosphere_cache.clear()
            self._engine_cache.clear()
            self._wind_cache.clear()
            self._rocket_cache.clear()
            
            self._stats = CacheStats()
            logger.info("SimulationCache cleared")
    
    def clear_rockets(self) -> None:
        """Clear only rocket object cache (most memory-intensive)."""
        with self._cache_lock:
            self._rocket_cache.clear()
            self._stats.rockets = 0
    
    # -------------------------------------------------------------------------
    # Rocket Configuration Cache
    # -------------------------------------------------------------------------
    
    def get_rocket_config(self, rocket_name: str) -> Optional[Dict[str, Any]]:
        """Get rocket configuration from cache or load from file."""
        with self._cache_lock:
            if rocket_name in self._rocket_config_cache:
                self._stats.hits += 1
                logger.debug(f"Cache hit: rocket config '{rocket_name}'")
                return self._rocket_config_cache[rocket_name]
            
            self._stats.misses += 1
            config = self._load_rocket_config_from_disk(rocket_name)
            
            if config:
                # Evict oldest if at capacity
                if len(self._rocket_config_cache) >= self._max_rocket_configs:
                    oldest_key = next(iter(self._rocket_config_cache))
                    del self._rocket_config_cache[oldest_key]
                    self._stats.rocket_configs -= 1
                
                self._rocket_config_cache[rocket_name] = config
                self._stats.rocket_configs += 1
                logger.debug(f"Cache miss: loaded rocket config '{rocket_name}'")
            
            return config
    
    def _load_rocket_config_from_disk(self, rocket_name: str) -> Optional[Dict[str, Any]]:
        """Load rocket configuration from JSON file."""
        # Try multiple possible paths
        config_paths = [
            f"data/rockets/configs/{rocket_name}.json",
            f"data/rockets/{rocket_name}.json",
            f"src/models/rockets/{rocket_name}.json",
            f"models/rockets/{rocket_name}.json",
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    logger.debug(f"Loaded rocket config from {path}")
                    return config
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load rocket config from {path}: {e}")
                    continue
        
        logger.warning(f"Could not find rocket configuration: {rocket_name}")
        return None
    
    def invalidate_rocket_config(self, rocket_name: str) -> None:
        """Remove a rocket config from cache."""
        with self._cache_lock:
            if rocket_name in self._rocket_config_cache:
                del self._rocket_config_cache[rocket_name]
                self._stats.rocket_configs -= 1
    
    # -------------------------------------------------------------------------
    # Planet Cache
    # -------------------------------------------------------------------------
    
    def get_planet(self, latitude: float, longitude: float, gmst_0: float) -> Any:
        """Get or create a Planet object with caching."""
        cache_key = _make_hash(latitude, longitude, gmst_0)
        
        with self._cache_lock:
            if cache_key in self._planet_cache:
                self._stats.hits += 1
                logger.debug(f"Cache hit: Planet({latitude}, {longitude}, {gmst_0})")
                return self._planet_cache[cache_key]
            
            self._stats.misses += 1
            
            # Import here to avoid circular imports
            from src.models.planet import Planet
            
            planet = Planet(gmst_0)
            
            # Evict if at capacity
            if len(self._planet_cache) >= self._max_planets:
                oldest_key = next(iter(self._planet_cache))
                del self._planet_cache[oldest_key]
                self._stats.planets -= 1
            
            self._planet_cache[cache_key] = planet
            self._stats.planets += 1
            logger.debug(f"Cache miss: created Planet({latitude}, {longitude}, {gmst_0})")
            
            return planet
    
    # -------------------------------------------------------------------------
    # Atmosphere Cache
    # -----------------------------------------------------------------------------
    
    def get_atmosphere(self, temperature: float) -> Any:
        """Get or create an Atmosphere object with caching."""
        cache_key = f"atm_{temperature:.2f}"
        
        with self._cache_lock:
            if cache_key in self._atmosphere_cache:
                self._stats.hits += 1
                logger.debug(f"Cache hit: Atmosphere({temperature})")
                return self._atmosphere_cache[cache_key]
            
            self._stats.misses += 1
            
            # Import here to avoid circular imports
            from src.models.atmosphere import Atmosphere
            
            atmosphere = Atmosphere(temperature)
            
            # Evict if at capacity
            if len(self._atmosphere_cache) >= self._max_atmospheres:
                oldest_key = next(iter(self._atmosphere_cache))
                del self._atmosphere_cache[oldest_key]
                self._stats.atmospheres -= 1
            
            self._atmosphere_cache[cache_key] = atmosphere
            self._stats.atmospheres += 1
            logger.debug(f"Cache miss: created Atmosphere({temperature})")
            
            return atmosphere
    
    # -------------------------------------------------------------------------
    # Engine Cache
    # -------------------------------------------------------------------------
    
    def get_engine(self, engine_config: Dict[str, Any]) -> Any:
        """Get or create an Engine object with caching."""
        cache_key = _make_hash(engine_config)
        
        with self._cache_lock:
            if cache_key in self._engine_cache:
                self._stats.hits += 1
                logger.debug(f"Cache hit: Engine({cache_key[:8]})")
                return self._engine_cache[cache_key]
            
            self._stats.misses += 1
            
            # Import here to avoid circular imports
            from src.models.engine import EnhancedEngine
            
            # EnhancedEngine needs the live ambient pressure/time normally supplied
            # by Rocket at each simulation step; use sea-level/t=0 defaults here since
            # this cache builds a template engine from static config only.
            engine = EnhancedEngine(
                time=engine_config.get('time', 0.0),
                burn_time=engine_config.get('burn_time', 0.0),
                ambient_pressure=engine_config.get('ambient_pressure', 101325.0),
                nozzle_exit_diameter=engine_config.get('nozzle_exit_diameter', 0.0),
                propellant_mass=engine_config.get('propellant_mass', 0.0),
                specific_impulse=engine_config.get('specific_impulse', 0.0),
                mean_thrust=engine_config.get('mean_thrust', 0.0),
                max_thrust=engine_config.get('max_thrust', 0.0),
                mean_chamber_pressure=engine_config.get('mean_chamber_pressure', 0.0),
                max_chamber_pressure=engine_config.get('max_chamber_pressure', 0.0),
                thrust_to_weight_ratio=engine_config.get('thrust_to_weight_ratio', 0.0),
                thrust_curve_file=engine_config.get('thrust_curve_file'),
                thrust_curve_unit=engine_config.get('thrust_curve_unit', 'N'),
            )
            
            # Evict if at capacity
            if len(self._engine_cache) >= self._max_engines:
                oldest_key = next(iter(self._engine_cache))
                del self._engine_cache[oldest_key]
                self._stats.engines -= 1
            
            self._engine_cache[cache_key] = engine
            self._stats.engines += 1
            logger.debug(f"Cache miss: created Engine({cache_key[:8]})")
            
            return engine
    
    def _get_thrust_at_time(self, t: float, engine_config: Dict[str, Any]) -> float:
        """Get thrust at time t from engine configuration."""
        # If thrust_curve is provided as a list
        if 'thrust_curve' in engine_config:
            thrust_data = engine_config['thrust_curve']
            if isinstance(thrust_data, list):
                if len(thrust_data) == 2:
                    # Simple (time, thrust) pairs
                    times, thrusts = thrust_data
                    idx = np.searchsorted(times, t)
                    if idx == 0:
                        return thrusts[0]
                    elif idx >= len(times):
                        return 0.0
                    else:
                        # Linear interpolation
                        t0, t1 = times[idx-1], times[idx]
                        f0, f1 = thrusts[idx-1], thrusts[idx]
                        return f0 + (f1 - f0) * (t - t0) / (t1 - t0) if t1 > t0 else f0
                else:
                    return thrust_data[0] if t < thrust_data[1] else 0.0
        
        # Default: constant thrust based on other parameters
        max_thrust = engine_config.get('max_thrust', 0)
        burn_time = engine_config.get('burn_time', 0)
        return max_thrust if t < burn_time else 0.0
    
    # -------------------------------------------------------------------------
    # Wind Model Cache
    # -------------------------------------------------------------------------
    
    def get_wind_model(self, wind_config: Dict[str, Any]) -> Any:
        """Get or create a Wind model object with caching."""
        cache_key = _make_hash(wind_config)
        
        with self._cache_lock:
            if cache_key in self._wind_cache:
                self._stats.hits += 1
                logger.debug(f"Cache hit: WindModel({cache_key[:8]})")
                return self._wind_cache[cache_key]
            
            self._stats.misses += 1
            
            # Import here to avoid circular imports
            from src.utils.wind_utils import create_wind_model_from_state
            
            wind = create_wind_model_from_state(wind_config)
            
            # Evict if at capacity
            if len(self._wind_cache) >= self._max_wind_models:
                oldest_key = next(iter(self._wind_cache))
                del self._wind_cache[oldest_key]
                self._stats.wind_models -= 1
            
            self._wind_cache[cache_key] = wind
            self._stats.wind_models += 1
            logger.debug(f"Cache miss: created WindModel({cache_key[:8]})")
            
            return wind


# ---------------------------------------------------------------------------
# Decorator for caching expensive computations
# ---------------------------------------------------------------------------

def cached_rocket_config(func):
    """Decorator to cache rocket configuration loading."""
    cache = {}
    lock = threading.RLock()
    
    def wrapper(self, rocket_name):
        with lock:
            if rocket_name not in cache:
                cache[rocket_name] = func(self, rocket_name)
            return cache[rocket_name]
    
    return wrapper


# Global cache instance access
_cache_instance: Optional[SimulationCache] = None


def get_cache() -> SimulationCache:
    """Get the global simulation cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SimulationCache.get_instance()
    return _cache_instance


def clear_cache() -> None:
    """Clear the global simulation cache."""
    global _cache_instance
    if _cache_instance is not None:
        _cache_instance.clear()
