"""
Simple EventBus Tests - Can be run without PyQt6 installed.

These tests verify the core functionality of the EventBus without
requiring Qt to be installed. They test:
- Singleton pattern
- EventType enum
- EventMetrics class
- Basic subscription/publishing logic (mocking Qt signals)
"""

import unittest
from unittest.mock import Mock, patch
from typing import Any, Dict

# Test imports without Qt
from src.utils.event_bus import (
    EventBus,
    EventType,
    EventMetrics,
)


class TestEventTypeEnum(unittest.TestCase):
    """Test EventType enum."""
    
    def test_all_event_types_exist(self):
        """Test that all documented event types exist."""
        expected_types = [
            'SIMULATION_STARTED', 'SIMULATION_STOPPED', 'SIMULATION_PAUSED',
            'SIMULATION_RESUMED', 'SIMULATION_COMPLETED', 'SIMULATION_ERROR',
            'CONFIGURATION_LOADED', 'CONFIGURATION_SAVED', 'CONFIGURATION_CHANGED',
            'ROCKET_SELECTED', 'ROCKET_CONFIG_CHANGED',
            'LOCATION_SELECTED', 'LOCATION_CHANGED',
            'WIND_SETTINGS_CHANGED', 'WIND_SCENARIO_SELECTED',
            'PARACHUTE_CONFIG_CHANGED', 'PARACHUTE_ENABLED_CHANGED',
            'MONTE_CARLO_STARTED', 'MONTE_CARLO_COMPLETED',
            'THEME_CHANGED', 'LANGUAGE_CHANGED', 'TAB_CHANGED'
        ]
        
        actual_types = [e.name for e in EventType]
        
        for expected in expected_types:
            self.assertIn(expected, actual_types, f"Event type {expected} not found")
    
    def test_event_types_unique(self):
        """Test that all event type names are unique."""
        names = [e.name for e in EventType]
        self.assertEqual(len(names), len(set(names)))
    
    def test_event_types_are_enum_members(self):
        """Test that all event types are proper Enum members."""
        for event_type in EventType:
            self.assertTrue(hasattr(EventType, event_type.name))


class TestEventMetricsSimple(unittest.TestCase):
    """Test EventMetrics class without Qt."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = EventMetrics()
    
    def test_initial_values(self):
        """Test that metrics start at zero."""
        self.assertEqual(self.metrics.total_published, 0)
        self.assertEqual(self.metrics.total_subscribed, 0)
        self.assertEqual(self.metrics.total_errors, 0)
        self.assertEqual(len(self.metrics.published_by_type), 0)
        self.assertEqual(len(self.metrics.subscribed_by_type), 0)
        self.assertEqual(len(self.metrics.errors_by_type), 0)
        self.assertIsNone(self.metrics.last_error)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        self.metrics.total_published = 5
        self.metrics.total_subscribed = 3
        self.metrics.published_by_type[EventType.SIMULATION_STARTED] = 2
        
        result = self.metrics.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['total_published'], 5)
        self.assertEqual(result['total_subscribed'], 3)
        self.assertIn('SIMULATION_STARTED', result['published_by_type'])
    
    def test_reset(self):
        """Test resetting metrics."""
        self.metrics.total_published = 10
        self.metrics.total_subscribed = 5
        self.metrics.total_errors = 3
        self.metrics.published_by_type[EventType.SIMULATION_STARTED] = 5
        self.metrics.last_error = "Test error"
        
        self.metrics.reset()
        
        self.assertEqual(self.metrics.total_published, 0)
        self.assertEqual(self.metrics.total_subscribed, 0)
        self.assertEqual(self.metrics.total_errors, 0)
        self.assertEqual(len(self.metrics.published_by_type), 0)
        self.assertIsNone(self.metrics.last_error)
    
    def test_most_active_events(self):
        """Test getting most active events."""
        self.metrics.published_by_type[EventType.SIMULATION_STARTED] = 10
        self.metrics.published_by_type[EventType.SIMULATION_COMPLETED] = 5
        self.metrics.published_by_type[EventType.ROCKET_SELECTED] = 15
        
        result = self.metrics.get_most_active_events(2)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], 'ROCKET_SELECTED')
        self.assertEqual(result[0][1], 15)
        self.assertEqual(result[1][0], 'SIMULATION_STARTED')
        self.assertEqual(result[1][1], 10)
    
    def test_most_subscribed_events(self):
        """Test getting most subscribed events."""
        self.metrics.subscribed_by_type[EventType.SIMULATION_STARTED] = 10
        self.metrics.subscribed_by_type[EventType.SIMULATION_COMPLETED] = 5
        self.metrics.subscribed_by_type[EventType.ROCKET_SELECTED] = 15
        
        result = self.metrics.get_most_subscribed_events(2)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], 'ROCKET_SELECTED')
        self.assertEqual(result[0][1], 15)


class TestEventBusSingletonSimple(unittest.TestCase):
    """Test EventBus singleton pattern without Qt."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset the singleton for testing
        EventBus._instance = None
    
    def tearDown(self):
        """Clean up after tests."""
        EventBus._instance = None
    
    def test_singleton_pattern(self):
        """Test that only one instance is created."""
        # Create instances directly (not via get_instance)
        # This tests the __new__ method
        with patch.object(EventBus, '_EventBus__init__', lambda self: None):
            bus1 = EventBus()
            bus2 = EventBus()
            
            self.assertIs(bus1, bus2)
    
    def test_get_instance_creates_instance(self):
        """Test that get_instance creates instance if none exists."""
        EventBus._instance = None
        bus = EventBus.get_instance()
        
        self.assertIsNotNone(bus)
        self.assertIsInstance(bus, EventBus)
    
    def test_get_instance_returns_singleton(self):
        """Test that get_instance returns the same instance."""
        bus1 = EventBus.get_instance()
        bus2 = EventBus.get_instance()
        
        self.assertIs(bus1, bus2)


class TestEventBusMethodsWithoutQt(unittest.TestCase):
    """Test EventBus methods that don't require Qt signals."""
    
    def setUp(self):
        """Set up test fixtures."""
        EventBus._instance = None
        # We can't fully test EventBus without Qt, but we can test some methods
    
    def tearDown(self):
        """Clean up after tests."""
        EventBus._instance = None
    
    def test_get_subscriber_count_empty(self):
        """Test getting subscriber count when no subscribers exist."""
        bus = EventBus.get_instance()
        # Clear any existing subscribers
        bus.clear_subscribers()
        
        count = bus.get_subscriber_count(EventType.SIMULATION_STARTED)
        self.assertEqual(count, 0)
    
    def test_clear_subscribers(self):
        """Test clearing subscribers."""
        bus = EventBus.get_instance()
        
        # This should not raise an error
        bus.clear_subscribers()
        bus.clear_subscribers(EventType.SIMULATION_STARTED)
    
    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing a callback that doesn't exist."""
        bus = EventBus.get_instance()
        
        def callback(data):
            pass
        
        # This should not raise an error
        result = bus.unsubscribe(EventType.SIMULATION_STARTED, callback)
        self.assertFalse(result)


class TestEventBusMetricsWithoutQt(unittest.TestCase):
    """Test EventBus metrics methods without Qt."""
    
    def setUp(self):
        """Set up test fixtures."""
        EventBus._instance = None
    
    def tearDown(self):
        """Clean up after tests."""
        EventBus._instance = None
    
    def test_get_metrics(self):
        """Test getting metrics via class method."""
        metrics = EventBus.get_metrics()
        self.assertIsInstance(metrics, EventMetrics)
    
    def test_reset_metrics(self):
        """Test resetting metrics via class method."""
        # This should not raise an error
        EventBus.reset_metrics()
        
        metrics = EventBus.get_metrics()
        self.assertEqual(metrics.total_published, 0)
        self.assertEqual(metrics.total_subscribed, 0)


if __name__ == '__main__':
    unittest.main()
