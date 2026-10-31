"""
State Management Interfaces

This module defines abstract interfaces for state management to enable
dependency injection and better testability.

The StateProvider interface allows different implementations of state
management (singleton, per-request, mock, etc.) while maintaining
a consistent API.

Usage:
    from src.models.state import StateProvider, ApplicationState
    
    # Use the real implementation
    state = ApplicationState.get_instance()
    
    # Or use a mock for testing
    state = MockStateProvider(initial_state={'key': 'value'})
    
    # Both implement the same interface
    value = state.get('key')
    state.set('key', new_value)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class StateProvider(ABC):
    """
    Abstract base class for state management providers.
    
    This interface defines the contract that all state management implementations
    must fulfill. It enables dependency injection and makes the codebase more
    testable by allowing mock implementations.
    
    Attributes:
        None - all state is accessed via methods
    
    Example:
        >>> class MyComponent:
        ...     def __init__(self, state: StateProvider):
        ...         self.state = state
        ...     
        ...     def do_something(self):
        ...         value = self.state.get('some_key')
        ...         self.state.set('some_key', new_value)
    """
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a state value by key.
        
        Args:
            key: The key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            The value associated with the key, or default if not found
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Set a state value by key.
        
        Args:
            key: The key to set
            value: The value to store
        """
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire state dictionary.
        
        Returns:
            A copy of the entire state dictionary
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """
        Reset all state to defaults.
        """
        pass
    
    def load_from_file(self, filepath: str = None) -> bool:
        """
        Load state from a JSON file.
        
        Args:
            filepath: Path to load file.
        
        Returns:
            True if successful, False otherwise
            
        Default implementation returns False (not supported).
        Override in implementations that support persistence.
        """
        return False
    
    def save_to_file(self, filepath: str = None) -> bool:
        """
        Save state to a JSON file.
        
        Args:
            filepath: Path to save file.
        
        Returns:
            True if successful, False otherwise
            
        Default implementation returns False (not supported).
        Override in implementations that support persistence.
        """
        return False
    
    # Optional methods with default implementations
    
    def set_multiple(self, updates: Dict[str, Any]) -> None:
        """
        Set multiple state values at once.
        
        Default implementation calls set() for each key-value pair.
        Override for more efficient bulk updates.
        
        Args:
            updates: Dictionary of key-value pairs to update
        """
        for key, value in updates.items():
            self.set(key, value)
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update state from a dictionary, only setting keys that exist.
        
        This is a convenience method for selectively updating state
        without overwriting everything.
        
        Args:
            data: Dictionary of key-value pairs to update
        """
        for key, value in data.items():
            if self.get(key) is not None or key in self.get_all():
                self.set(key, value)


class ReadOnlyStateProvider(ABC):
    """
    Abstract base class for read-only state providers.
    
    Use this when you only need to read state but not modify it.
    This can help prevent accidental mutations.
    """
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value by key."""
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """Get the entire state dictionary."""
        pass


class MockStateProvider(StateProvider):
    """
    Mock implementation of StateProvider for testing.
    
    This class provides a lightweight, isolated state container that can be
    used in unit tests without affecting the global ApplicationState singleton.
    
    Features:
    - No singleton pattern - create multiple instances freely
    - No persistence - state is purely in-memory
    - Full StateProvider interface implementation
    - Optional default state initialization
    
    Example:
        >>> state = MockStateProvider(initial_state={'key': 'value'})
        >>> state.get('key')
        'value'
        >>> state.set('key', 'new_value')
        >>> state.get('key')
        'new_value'
        >>> state.get_all()
        {'key': 'new_value'}
    """
    
    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        """
        Initialize mock state provider.
        
        Args:
            initial_state: Optional dictionary to initialize state with
        """
        self._state: Dict[str, Any] = {}
        if initial_state:
            self._state.update(initial_state)
        logger.debug(f"MockStateProvider initialized with {len(self._state)} keys")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value by key."""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a state value by key."""
        old_value = self._state.get(key)
        self._state[key] = value
        logger.debug(f"MockState: {key} = {value} (was: {old_value})")
    
    def get_all(self) -> Dict[str, Any]:
        """Get the entire state dictionary."""
        return self._state.copy()
    
    def reset(self) -> None:
        """Reset all state to empty."""
        self._state.clear()
        logger.debug("MockStateProvider reset to empty")
    
    def set_initial_state(self, initial_state: Dict[str, Any]) -> None:
        """
        Set the initial state (clears existing state first).
        
        Args:
            initial_state: Dictionary to initialize state with
        """
        self._state.clear()
        self._state.update(initial_state)
        logger.debug(f"MockStateProvider initialized with {len(self._state)} keys")


class StateProxy(StateProvider):
    """
    Proxy implementation of StateProvider that overlays overrides on a base state.
    
    This class is used for scenarios where you need to temporarily modify
    certain state values without affecting the base state. It's particularly
    useful for:
    - Monte Carlo simulations with parameter variations
    - Testing with modified state values
    - Any scenario where you need isolated state modifications
    
    The proxy maintains a base StateProvider and a set of overrides.
    When getting a value:
    - If the key exists in overrides, return the override value
    - Otherwise, return the value from the base state
    
    When setting a value:
    - By default, writes go to the override layer only (write-through mode)
    - This prevents polluting the base state (especially important for singleton)
    
    Example:
        >>> base = ApplicationState.get_instance()
        >>> base.set('temperature', 20.0)
        >>> proxy = StateProxy(base, {'temperature': 25.0})
        >>> proxy.get('temperature')
        25.0
        >>> base.get('temperature')  # Unchanged
        20.0
        >>> proxy.set('wind_speed', 10.0)
        >>> proxy.get('wind_speed')
        10.0
        >>> base.get('wind_speed')  # Not in base
        None
    """
    
    def __init__(self, base_state: StateProvider, overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize state proxy.
        
        Args:
            base_state: The base StateProvider to proxy
            overrides: Optional dictionary of override values
        """
        self._base = base_state
        self._overrides: Dict[str, Any] = {}
        if overrides:
            self._overrides.update(overrides)
        logger.debug(f"StateProxy created with {len(overrides or {})} overrides")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a state value by key.
        
        Checks overrides first, then falls back to base state.
        """
        if key in self._overrides:
            return self._overrides[key]
        return self._base.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a state value by key.
        
        Writes go to the override layer only. This prevents polluting
        the base state (especially important when base is a singleton).
        """
        # Store in override layer - don't modify base state
        self._overrides[key] = value
        logger.debug(f"StateProxy override: {key} = {value}")
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire state dictionary (merged base + overrides).
        
        Returns a new dictionary with all base state values,
        with overrides applied on top.
        """
        # Get base state (already a copy from get_all())
        merged = self._base.get_all()
        # Apply overrides on top
        merged.update(self._overrides)
        return merged
    
    def reset(self) -> None:
        """
        Reset all overrides (does not affect base state).
        """
        self._overrides.clear()
        logger.debug("StateProxy overrides cleared")
    
    @property
    def overrides(self) -> Dict[str, Any]:
        """Get the current overrides dictionary."""
        return self._overrides.copy()
    
    @property
    def base_state(self) -> StateProvider:
        """Get the base state provider."""
        return self._base
