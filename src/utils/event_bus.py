"""
Event Bus for Decoupled Widget Communication

Provides a global event bus using PyQt6 signals for decoupled communication
between widgets and components.

Usage:
    from src.utils.event_bus import EventBus, EventType
    
    # Subscribe to an event
    def on_simulation_started(data):
        print(f"Simulation started with: {data}")
    
    EventBus.subscribe(EventType.SIMULATION_STARTED, on_simulation_started)
    
    # Publish an event
    EventBus.publish(EventType.SIMULATION_STARTED, {"sim_id": "123"})
    
    # Unsubscribe
    EventBus.unsubscribe(EventType.SIMULATION_STARTED, on_simulation_started)
    
    # Get metrics
    metrics = EventBus.get_metrics()
"""

from PyQt6.QtCore import QObject, pyqtSignal, QMetaObject, Qt
from typing import Callable, Any, Dict, List, Optional, Tuple
from enum import Enum, auto
import logging
import weakref
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class EventMetrics:
    """
    Metrics for event bus usage tracking.
    
    Attributes:
        total_published: Total number of events published
        total_subscribed: Total number of subscriptions made
        total_errors: Total number of callback errors
        published_by_type: Dict mapping EventType to publish count
        subscribed_by_type: Dict mapping EventType to subscribe count
        errors_by_type: Dict mapping EventType to error count
        last_error: Last error that occurred (for debugging)
    """
    
    def __init__(self):
        self.total_published: int = 0
        self.total_subscribed: int = 0
        self.total_errors: int = 0
        self.published_by_type: Dict[Enum, int] = defaultdict(int)
        self.subscribed_by_type: Dict[Enum, int] = defaultdict(int)
        self.errors_by_type: Dict[Enum, int] = defaultdict(int)
        self.last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary for easy serialization."""
        return {
            'total_published': self.total_published,
            'total_subscribed': self.total_subscribed,
            'total_errors': self.total_errors,
            'published_by_type': {e.name: count for e, count in self.published_by_type.items()},
            'subscribed_by_type': {e.name: count for e, count in self.subscribed_by_type.items()},
            'errors_by_type': {e.name: count for e, count in self.errors_by_type.items()},
            'last_error': self.last_error
        }
    
    def get_most_active_events(self, n: int = 5) -> List[Tuple[str, int]]:
        """Get the n most actively published event types."""
        sorted_events = sorted(
            self.published_by_type.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [(e.name, count) for e, count in sorted_events[:n]]
    
    def get_most_subscribed_events(self, n: int = 5) -> List[Tuple[str, int]]:
        """Get the n most subscribed event types."""
        sorted_events = sorted(
            self.subscribed_by_type.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [(e.name, count) for e, count in sorted_events[:n]]
    
    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.total_published = 0
        self.total_subscribed = 0
        self.total_errors = 0
        self.published_by_type.clear()
        self.subscribed_by_type.clear()
        self.errors_by_type.clear()
        self.last_error = None


class EventType(Enum):
    """
    Standard event types for the Rocket Simulator application.
    
    Define custom event types as needed. Each event type represents
    a specific action or state change in the application.
    """
    
    # Simulation events
    SIMULATION_STARTED = auto()
    SIMULATION_STOPPED = auto()
    SIMULATION_PAUSED = auto()
    SIMULATION_RESUMED = auto()
    SIMULATION_COMPLETED = auto()
    SIMULATION_ERROR = auto()
    
    # Configuration events
    CONFIGURATION_LOADED = auto()
    CONFIGURATION_SAVED = auto()
    CONFIGURATION_CHANGED = auto()
    
    # Rocket events
    ROCKET_SELECTED = auto()
    ROCKET_CONFIG_CHANGED = auto()
    
    # Location events
    LOCATION_SELECTED = auto()
    LOCATION_CHANGED = auto()
    
    # Wind events
    WIND_SETTINGS_CHANGED = auto()
    WIND_SCENARIO_SELECTED = auto()
    
    # Parachute events
    PARACHUTE_CONFIG_CHANGED = auto()
    PARACHUTE_ENABLED_CHANGED = auto()
    
    # Monte Carlo events
    MONTE_CARLO_STARTED = auto()
    MONTE_CARLO_COMPLETED = auto()
    
    # Theme events
    THEME_CHANGED = auto()
    
    # Language events
    LANGUAGE_CHANGED = auto()
    
    # Tab events
    TAB_CHANGED = auto()


class EventBus(QObject):
    """
    Global event bus for decoupled communication between widgets.
    
    This class uses PyQt6's signal/slot mechanism to allow widgets to
    communicate without direct dependencies. It supports:
    
    - Publishing events with data
    - Subscribing to events with callbacks
    - Automatic cleanup of subscribers when widgets are destroyed
    - Metrics tracking for monitoring usage
    
    The event bus uses weak references to avoid memory leaks.
    
    Usage:
        # In widget A (publisher)
        EventBus.publish(EventType.SIMULATION_STARTED, {"time": 0})
        
        # In widget B (subscriber)
        EventBus.subscribe(EventType.SIMULATION_STARTED, self.on_sim_started)
        
        # Cleanup (optional, weak refs handle this automatically)
        EventBus.unsubscribe(EventType.SIMULATION_STARTED, self.on_sim_started)
        
        # Get metrics
        metrics = EventBus.get_metrics()
    """
    
    # Singleton instance
    _instance: Optional['EventBus'] = None
    
    # Signal for event publishing
    _event_signal = pyqtSignal(EventType, dict)
    
    def __new__(cls):
        """Singleton pattern - only one instance allowed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the event bus."""
        super().__init__()
        self._subscribers: Dict[EventType, List[weakref.ReferenceType[Callable]]] = {}
        self._metrics = EventMetrics()
        self._metrics_lock = Lock()
        # Connect the signal to the internal handler
        self._event_signal.connect(self._handle_event)
    
    @classmethod
    def get_instance(cls) -> 'EventBus':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def get_metrics(cls) -> EventMetrics:
        """
        Get the current event bus metrics.
        
        Returns:
            EventMetrics object with current statistics
        """
        instance = cls.get_instance()
        return instance._metrics
    
    @classmethod
    def reset_metrics(cls) -> None:
        """Reset all event bus metrics to zero."""
        instance = cls.get_instance()
        with instance._metrics_lock:
            instance._metrics.reset()
        logger.debug("Event bus metrics reset")
    
    def subscribe(self, event_type: EventType, callback: Callable[[Any], None]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The type of event to subscribe to
            callback: Function to call when the event is published.
                     The callback receives the event data as its argument.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        # Use weak reference to avoid memory leaks
        self._subscribers[event_type].append(weakref.ref(callback))
        
        # Update metrics
        with self._metrics_lock:
            self._metrics.total_subscribed += 1
            self._metrics.subscribed_by_type[event_type] += 1
        
        logger.debug(f"Subscribed to {event_type.name}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Any], None]) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: The type of event to unsubscribe from
            callback: The callback function to remove
        
        Returns:
            True if the callback was found and removed, False otherwise
        """
        if event_type in self._subscribers:
            # Find and remove the callback
            to_remove = []
            for i, ref in enumerate(self._subscribers[event_type]):
                cb = ref()
                if cb is None:
                    # Already garbage collected
                    to_remove.append(i)
                elif cb == callback:
                    to_remove.append(i)
            
            # Remove in reverse order to avoid index issues
            for i in sorted(to_remove, reverse=True):
                del self._subscribers[event_type][i]
            
            if to_remove:
                logger.debug(f"Unsubscribed from {event_type.name}")
                return True
        
        return False
    
    def publish(self, event_type: EventType, data: Optional[Dict] = None) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: The type of event to publish
            data: Optional data to send with the event
        """
        if data is None:
            data = {}
        
        # Update metrics
        with self._metrics_lock:
            self._metrics.total_published += 1
            self._metrics.published_by_type[event_type] += 1
        
        # Publish via signal for thread safety
        self._event_signal.emit(event_type, data)
        
        logger.debug(f"Published event: {event_type.name} with data: {data}")
    
    def _handle_event(self, event_type: EventType, data: Dict) -> None:
        """
        Internal handler that delivers events to subscribers.
        
        Args:
            event_type: The event type
            data: The event data
        """
        if event_type in self._subscribers:
            # Call all subscribers (clean up dead references)
            dead_refs = []
            for i, ref in enumerate(self._subscribers[event_type]):
                callback = ref()
                if callback is None:
                    dead_refs.append(i)
                else:
                    try:
                        callback(data)
                    except Exception as e:
                        # Update error metrics
                        with self._metrics_lock:
                            self._metrics.total_errors += 1
                            self._metrics.errors_by_type[event_type] += 1
                            self._metrics.last_error = str(e)
                        logger.error(f"Error in event handler for {event_type.name}: {e}")
            
            # Remove dead references
            for i in sorted(dead_refs, reverse=True):
                del self._subscribers[event_type][i]
    
    def clear_subscribers(self, event_type: Optional[EventType] = None) -> None:
        """
        Clear all subscribers for a specific event type or all types.
        
        Args:
            event_type: Specific event type to clear, or None for all
        """
        if event_type is None:
            self._subscribers.clear()
            logger.debug("Cleared all event subscribers")
        else:
            self._subscribers.pop(event_type, None)
            logger.debug(f"Cleared subscribers for {event_type.name}")
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """
        Get the number of subscribers for an event type.
        
        Args:
            event_type: The event type to check
        
        Returns:
            Number of subscribers (excluding dead references)
        """
        if event_type not in self._subscribers:
            return 0
        
        # Count only live references
        return sum(1 for ref in self._subscribers[event_type] if ref() is not None)


# Convenience functions for common use cases
def subscribe(event_type: EventType, callback: Callable[[Any], None]) -> None:
    """Subscribe to an event."""
    EventBus.get_instance().subscribe(event_type, callback)


def unsubscribe(event_type: EventType, callback: Callable[[Any], None]) -> bool:
    """Unsubscribe from an event."""
    return EventBus.get_instance().unsubscribe(event_type, callback)


def publish(event_type: EventType, data: Optional[Dict] = None) -> None:
    """Publish an event."""
    EventBus.get_instance().publish(event_type, data)


def get_metrics() -> EventMetrics:
    """Get the current event bus metrics."""
    return EventBus.get_metrics()


def reset_metrics() -> None:
    """Reset all event bus metrics to zero."""
    EventBus.reset_metrics()


# Create translation dictionary for event types (for debugging/logging)
EVENT_NAMES = {e: e.name for e in EventType}
