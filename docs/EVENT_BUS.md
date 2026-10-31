# Event Bus for Decoupled Widget Communication

## Overview

The Event Bus provides a way for widgets and components to communicate without direct dependencies. It uses PyQt6's signal/slot mechanism internally but provides a simpler, more Pythonic interface.

## Architecture

- **EventBus**: Singleton class that manages event subscriptions and publishing
- **EventType**: Enum of standard event types
- **subscribe()**: Subscribe a callback to an event type
- **unsubscribe()**: Remove a callback from an event type
- **publish()**: Publish an event with data to all subscribers

## Usage Examples

### Basic Usage

```python
from src.utils.event_bus import EventType, subscribe, unsubscribe, publish

# Subscribe to an event
def on_simulation_started(data):
    print(f"Simulation started at: {data.get('timestamp')}")

subscribe(EventType.SIMULATION_STARTED, on_simulation_started)

# Publish an event
publish(EventType.SIMULATION_STARTED, {"timestamp": "2024-01-01T12:00:00"})

# Unsubscribe when done
unsubscribe(EventType.SIMULATION_STARTED, on_simulation_started)
```

### In Widgets

```python
from ui.widgets import BaseWidget
from src.utils.event_bus import EventType, subscribe, unsubscribe

class DashboardWidget(BaseWidget):
    def __init__(self, state=None, parent=None):
        super().__init__(state=state, parent=parent)
        
        # Subscribe to simulation events
        subscribe(EventType.SIMULATION_STARTED, self.on_simulation_started)
        subscribe(EventType.SIMULATION_COMPLETED, self.on_simulation_completed)
    
    def on_simulation_started(self, data):
        self.status_label.setText(f"Simulation started: {data.get('timestamp')}")
    
    def on_simulation_completed(self, data):
        results = data.get('results')
        self.update_charts(results)
    
    def cleanup(self):
        # Clean up subscriptions
        unsubscribe(EventType.SIMULATION_STARTED, self.on_simulation_started)
        unsubscribe(EventType.SIMULATION_COMPLETED, self.on_simulation_completed)
```

### Using the Singleton Directly

```python
from src.utils.event_bus import EventBus, EventType

# Get the singleton instance
bus = EventBus.get_instance()

# Subscribe
def callback(data):
    print(f"Received: {data}")

bus.subscribe(EventType.WIND_SETTINGS_CHANGED, callback)

# Publish
bus.publish(EventType.WIND_SETTINGS_CHANGED, {"wind_speed": 5.0})

# Get subscriber count
count = bus.get_subscriber_count(EventType.WIND_SETTINGS_CHANGED)
```

## Event Types

The following standard event types are defined in `EventType`:

### Simulation Events
- `SIMULATION_STARTED` - Published when a simulation begins
- `SIMULATION_STOPPED` - Published when a simulation is stopped by user
- `SIMULATION_PAUSED` - Published when a simulation is paused
- `SIMULATION_RESUMED` - Published when a paused simulation resumes
- `SIMULATION_COMPLETED` - Published when a simulation finishes successfully
- `SIMULATION_ERROR` - Published when a simulation fails

### Configuration Events
- `CONFIGURATION_LOADED` - Published when a configuration is loaded
- `CONFIGURATION_SAVED` - Published when a configuration is saved
- `CONFIGURATION_CHANGED` - Published when configuration settings change

### Rocket Events
- `ROCKET_SELECTED` - Published when a different rocket is selected
- `ROCKET_CONFIG_CHANGED` - Published when rocket configuration changes

### Location Events
- `LOCATION_SELECTED` - Published when a location is selected
- `LOCATION_CHANGED` - Published when location settings change

### Wind Events
- `WIND_SETTINGS_CHANGED` - Published when wind settings change
- `WIND_SCENARIO_SELECTED` - Published when a wind scenario is selected

### Parachute Events
- `PARACHUTE_CONFIG_CHANGED` - Published when parachute configuration changes
- `PARACHUTE_ENABLED_CHANGED` - Published when parachute enable state changes

### Monte Carlo Events
- `MONTE_CARLO_STARTED` - Published when Monte Carlo simulation starts
- `MONTE_CARLO_COMPLETED` - Published when Monte Carlo simulation finishes

### UI Events
- `THEME_CHANGED` - Published when theme changes (dark/light mode)
- `LANGUAGE_CHANGED` - Published when language changes
- `TAB_CHANGED` - Published when the active tab changes

## Adding Custom Event Types

To add a new event type:

```python
from src.utils.event_bus import EventType

# Extend the EventType enum
class CustomEventType(EventType):
    CUSTOM_EVENT = auto()

# Or add to the existing enum (better approach)
# In src/utils/event_bus.py:
# MY_CUSTOM_EVENT = auto()
```

## Event Data

Event data is a dictionary (`Dict[str, Any]`) that can contain any serializable data:

```python
# Good: Simple data
publish(EventType.SIMULATION_STARTED, {"timestamp": "2024-01-01T12:00:00"})

# Good: Complex data
publish(EventType.SIMULATION_COMPLETED, {
    "results": results_dict,
    "duration": 60.5,
    "success": True
})

# Bad: Non-serializable data
publish(EventType.SOMETHING, {"widget": self})  # Don't pass widget references!
```

## Best Practices

1. **Use standard event types** when possible instead of creating custom ones
2. **Keep event data serializable** - avoid passing objects or widget references
3. **Clean up subscriptions** when widgets are destroyed (optional due to weak refs)
4. **Use try-except in callbacks** to prevent one bad callback from breaking others
5. **Log events** for debugging using the built-in logging

## Thread Safety

The event bus uses PyQt6 signals internally, which are thread-safe. Events published from background threads will be delivered in the main thread (where Qt widgets live).

```python
# This works even if called from a background thread
publish(EventType.SIMULATION_STARTED, {"timestamp": datetime.now().isoformat()})
```

## Memory Management

The event bus uses **weak references** for subscribers, so:
- You don't need to manually unsubscribe in most cases
- Subscribers are automatically cleaned up when garbage collected
- No memory leaks from forgotten subscriptions

However, for long-lived objects or when you want explicit control, use `unsubscribe()`.

## Debugging

To debug event bus issues:

```python
import logging
from src.utils.event_bus import EventBus

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Check subscriber counts
bus = EventBus.get_instance()
print(f"SIMULATION_STARTED subscribers: {bus.get_subscriber_count(EventType.SIMULATION_STARTED)}")

# Clear all subscribers (useful for testing)
bus.clear_subscribers()
```

## Example: Dashboard Updates on Simulation Start

```python
from src.utils.event_bus import EventType, subscribe
from ui.widgets.dashboard_widget import DashboardWidget

class DashboardWidget(DashboardWidget):
    def __init__(self, state=None, parent=None):
        super().__init__(state=state, parent=parent)
        
        # Subscribe to simulation events
        subscribe(EventType.SIMULATION_STARTED, self.clear_results)
        subscribe(EventType.SIMULATION_COMPLETED, self.display_results)
    
    def clear_results(self, data):
        """Clear dashboard when a new simulation starts."""
        self.clear_charts()
        self.status_label.setText("Running simulation...")
    
    def display_results(self, data):
        """Display results when simulation completes."""
        results = data.get('results')
        if results:
            self.update_charts(results)
            self.status_label.setText("Simulation complete")
```

## Files

- Event bus implementation: `src/utils/event_bus.py`
- EventType enum: `src/utils/event_bus.py`
- Convenience functions: `src/utils/event_bus.py`
- Import in utils: `src/utils/__init__.py`
