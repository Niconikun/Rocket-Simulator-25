# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 2: Mass Properties Component

"""
Mass Properties Module

This module provides mass property calculations for rockets, including:
- Mass distribution
- Center of mass (CoM) tracking
- Moments of inertia calculations
- Continuous interpolation during propellant burn

The MassProperties class implements the IMassProperties interface, providing
a clean abstraction for mass-related calculations.

Usage:
    from src.models.mass_properties import MassProperties
    
    # Create with before/after burn properties
    mass_props = MassProperties(
        mass_before=10.0,
        mass_after=7.0,
        cm_before=np.array([0.5, 0, 0]),
        cm_after=np.array([0.6, 0, 0]),
        inertia_before=np.array([0.1, 0.1, 0.05]),
        inertia_after=np.array([0.08, 0.08, 0.04])
    )
    
    # Get properties at 50% burn
    current_mass = mass_props.get_mass(0.5)
    current_com = mass_props.get_center_of_mass(0.5)
    current_inertia = mass_props.get_inertia(0.5)
"""

import numpy as np
from typing import Optional
from src.models.interfaces import IMassProperties
from src.utils.simulation_errors import InputValidationError


class MassProperties(IMassProperties):
    """
    Mass properties calculator with continuous interpolation.
    
    This class stores mass properties before and after propellant burn,
    and provides interpolated values based on the current burn fraction.
    
    Attributes:
        mass_before: Total mass before burn [kg]
        mass_after: Total mass after burn [kg]
        cm_before: Center of mass before burn [x, y, z] [m]
        cm_after: Center of mass after burn [x, y, z] [m]
        inertia_before: Moments of inertia before burn [Ixx, Iyy, Izz] [kg·m²]
        inertia_after: Moments of inertia after burn [Ixx, Iyy, Izz] [kg·m²]
        propellant_mass: Mass of propellant [kg]
    
    Example:
        >>> # Simple rocket with 10kg total mass, 3kg propellant
        >>> props = MassProperties(
        ...     mass_before=10.0,
        ...     mass_after=7.0,
        ...     cm_before=np.array([0.5, 0, 0]),
        ...     cm_after=np.array([0.6, 0, 0]),
        ...     inertia_before=np.array([0.1, 0.1, 0.05]),
        ...     inertia_after=np.array([0.08, 0.08, 0.04])
        ... )
        >>> props.get_mass(0.0)  # 100% propellant
        10.0
        >>> props.get_mass(1.0)  # 0% propellant
        7.0
        >>> props.get_mass(0.5) # 50% propellant
        8.5
    """
    
    def __init__(
        self,
        mass_before: float,
        mass_after: float,
        cm_before: np.ndarray,
        cm_after: np.ndarray,
        inertia_before: np.ndarray,
        inertia_after: np.ndarray,
        easing_function: Optional[str] = 'linear'
    ) -> None:
        """
        Initialize mass properties with before/after burn states.
        
        Args:
            mass_before: Total mass before propellant burn [kg]
            mass_after: Total mass after propellant burn [kg]
            cm_before: Center of mass before burn as [x, y, z] in body frame [m]
            cm_after: Center of mass after burn as [x, y, z] in body frame [m]
            inertia_before: Moments of inertia before burn [Ixx, Iyy, Izz] [kg·m²]
            inertia_after: Moments of inertia after burn [Ixx, Iyy, Izz] [kg·m²]
            easing_function: Type of easing for interpolation.
                           Options: 'linear' (default), 'cubic', 'quadratic'
        
        Raises:
            InputValidationError: If mass_after >= mass_before
            InputValidationError: If cm or inertia arrays have wrong dimensions
        """
        # Validate inputs
        if mass_after >= mass_before:
            raise InputValidationError(
                f"mass_after ({mass_after}) must be less than mass_before ({mass_before})"
            )
        
        if cm_before.shape != (3,) or cm_after.shape != (3,):
            raise InputValidationError("cm_before and cm_after must be 3-element arrays")
        
        if inertia_before.shape != (3,) or inertia_after.shape != (3,):
            raise InputValidationError("inertia_before and inertia_after must be 3-element arrays")
        
        # Store properties
        self.mass_before = float(mass_before)
        self.mass_after = float(mass_after)
        self.cm_before = np.array(cm_before, dtype=float)
        self.cm_after = np.array(cm_after, dtype=float)
        self.inertia_before = np.array(inertia_before, dtype=float)
        self.inertia_after = np.array(inertia_after, dtype=float)
        
        # Calculate propellant mass
        self.propellant_mass = self.mass_before - self.mass_after
        
        # Set easing function
        self.easing_function = easing_function
        
        # Pre-compute for optimization
        self._mass_range = self.mass_before - self.mass_after
    
    def _apply_easing(self, t: float) -> float:
        """
        Apply easing function to interpolation parameter.
        
        Args:
            t: Interpolation parameter in [0, 1]
        
        Returns:
            Eased interpolation parameter
        """
        if self.easing_function == 'linear':
            return t
        elif self.easing_function == 'quadratic':
            return t ** 2
        elif self.easing_function == 'cubic':
            return t ** 3
        elif self.easing_function == 'smoothstep':
            # Smoothstep easing: 3t² - 2t³
            return 3 * t ** 2 - 2 * t ** 3
        elif self.easing_function == 'ease_in_out':
            # Cubic ease in out
            if t < 0.5:
                return 4 * t ** 3
            else:
                return 1 - ((1 - t) * 2) ** 3 / 2
        else:
            return t
    
    def get_mass(self, burn_fraction: float) -> float:
        """
        Get current total mass based on burn fraction.
        
        Args:
            burn_fraction: Fraction of propellant burned (0.0 to 1.0) [-]
        
        Returns:
            float: Current total mass in kg [kg]
        """
        burn_fraction = np.clip(burn_fraction, 0.0, 1.0)
        return self.mass_before - burn_fraction * self._mass_range
    
    def get_center_of_mass(self, burn_fraction: float) -> np.ndarray:
        """
        Get current center of mass position in body frame.
        
        Uses easing function for smooth transitions.
        
        Args:
            burn_fraction: Fraction of propellant burned (0.0 to 1.0) [-]
        
        Returns:
            np.ndarray: Center of mass position [x, y, z] in body frame [m]
        """
        burn_fraction = np.clip(burn_fraction, 0.0, 1.0)
        t = self._apply_easing(burn_fraction)
        
        # Linear interpolation with easing
        com = self.cm_before * (1 - t) + self.cm_after * t
        return com.copy()
    
    def get_inertia(self, burn_fraction: float) -> np.ndarray:
        """
        Get current moments of inertia in body frame.
        
        Uses easing function for smooth transitions.
        
        Args:
            burn_fraction: Fraction of propellant burned (0.0 to 1.0) [-]
        
        Returns:
            np.ndarray: Moments of inertia [Ixx, Iyy, Izz] in body frame [kg·m²]
        """
        burn_fraction = np.clip(burn_fraction, 0.0, 1.0)
        t = self._apply_easing(burn_fraction)
        
        # Linear interpolation with easing
        inertia = self.inertia_before * (1 - t) + self.inertia_after * t
        return inertia.copy()
    
    def get_propellant_mass(self) -> float:
        """
        Get total propellant mass.
        
        Returns:
            float: Total propellant mass in kg [kg]
        """
        return self.propellant_mass
    
    def get_burn_fraction(self, current_mass: float) -> float:
        """
        Calculate burn fraction from current mass.
        
        Args:
            current_mass: Current total mass [kg]
        
        Returns:
            float: Burn fraction (0.0 to 1.0) [-]
        """
        if self._mass_range <= 0:
            return 0.0
        
        burn_fraction = (self.mass_before - current_mass) / self._mass_range
        return np.clip(burn_fraction, 0.0, 1.0)
    
    def get_mass_properties_dict(self, burn_fraction: float) -> dict:
        """
        Get all mass properties as a dictionary.
        
        Convenience method for getting all properties at once.
        
        Args:
            burn_fraction: Fraction of propellant burned (0.0 to 1.0) [-]
        
        Returns:
            dict: Dictionary containing:
                - 'mass': Current total mass [kg]
                - 'center_of_mass': Current CoM [x, y, z] [m]
                - 'inertia': Current moments of inertia [Ixx, Iyy, Izz] [kg·m²]
                - 'burn_fraction': Current burn fraction [-]
                - 'propellant_remaining': Remaining propellant [kg]
        """
        burn_fraction = np.clip(burn_fraction, 0.0, 1.0)
        
        return {
            'mass': self.get_mass(burn_fraction),
            'center_of_mass': self.get_center_of_mass(burn_fraction),
            'inertia': self.get_inertia(burn_fraction),
            'burn_fraction': burn_fraction,
            'propellant_remaining': self.propellant_mass * (1 - burn_fraction)
        }


__all__ = ['MassProperties']
