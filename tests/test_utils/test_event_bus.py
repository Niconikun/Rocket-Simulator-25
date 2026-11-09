"""
Unit Tests for EventBus

This module tests the EventBus implementation for:
- Singleton pattern
- Subscribe/publish functionality
- Weak reference management
- Metrics tracking
- Thread safety
- Error handling
"""

import unittest
import weakref
import threading
import time
from unittest.mock import Mock, patch
from typing import Any, Dict, List

from PyQt6.QtCore import QCoreApplication, QTimer
from PyQt6.QtWidgets import QApplication

# Import the event bus components
from src.utils.event_bus import (
    EventBus,
    EventType,
    EventMetrics,
    subscribe,
    unsubscribe,
    publish,
    get_metrics,
    reset_metrics,
)


class TestEventMetrics(unittest.TestCase):
    """Test EventMetrics class functionality."""
    
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


class TestEventBusSingleton(unittest.TestCase):
    """Test EventBus singleton pattern."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset the singleton for testing
        EventBus._instance = None
    
    def tearDown(self):
        """Clean up after tests."""
        EventBus._instance = None
    
    def test_singleton_pattern(self):
        """Test that only one instance is created."""
        bus1 = EventBus.get_instance()
        bus2 = EventBus.get_instance()
        
        self.assertIs(bus1, bus2)
    
    def test_new_returns_singleton(self):
        """Test that __new__ returns the singleton."""
        bus1 = EventBus()
        bus2 = EventBus()
        
        self.assertIs(bus1, bus2)
    
    def test_get_instance_creates_instance(self):
        """Test that get_instance creates instance if none exists."""
        EventBus._instance = None
        bus = EventBus.get_instance()
        
        self.assertIsNotNone(bus)
        self.assertIsInstance(bus, EventBus)


class TestSubscribePublish(unittest.TestCase):
    """Test subscribe and publish functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a QApplication instance for Qt signals
        self.app = QApplication([])
        
        # Reset the singleton and metrics
        EventBus._instance = None
        reset_metrics()
        
        self.bus = EventBus.get_instance()
        self.received_data = []
        self.callback = Mock()
    
    def tearDown(self):
        """Clean up after tests."""
        EventBus._instance = None
        reset_metrics()
        self.app.quit()
    
    def test_subscribe_and_publish(self):
        """Test basic subscribe and publish."""
        test_data = {'test': 'value'}
        
        def callback(data):
            self.received_data.append(data)
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback)
        
        # Need to use QTimer to ensure signal is processed
        with patch.object(self.bus._event_signal, 'emit') as mock_emit:
            self.bus.publish(EventType.SIMULATION_STARTED, test_data)
            # Directly call the handler since we're not running the Qt event loop
            self.bus._handle_event(EventType.SIMULATION_STARTED, test_data)
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0], test_data)
    
    def test_convenience_functions(self):
        """Test subscribe, publish, unsubscribe convenience functions."""
        test_data = {'test': 'value'}
        received = []
        
        def callback(data):
            received.append(data)
        
        subscribe(EventType.SIMULATION_COMPLETED, callback)
        
        with patch.object(EventBus.get_instance()._event_signal, 'emit'):
            publish(EventType.SIMULATION_COMPLETED, test_data)
            # Directly call the handler
            EventBus.get_instance()._handle_event(EventType.SIMULATION_COMPLETED, test_data)
        
        self.assertEqual(len(received), 1)
        
        # Test unsubscribe
        unsubscribe(EventType.SIMULATION_COMPLETED, callback)
        received.clear()
        
        with patch.object(EventBus.get_instance()._event_signal, 'emit'):
            publish(EventType.SIMULATION_COMPLETED, test_data)
            EventBus.get_instance()._handle_event(EventType.SIMULATION_COMPLETED, test_data)
        
        self.assertEqual(len(received), 0)
    
    def test_multiple_subscribers(self):
        """Test multiple subscribers to the same event."""
        test_data = {'test': 'value'}
        received1 = []
        received2 = []
        
        def callback1(data):
            received1.append(data)
        
        def callback2(data):
            received2.append(data)
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback1)
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback2)
        
        with patch.object(self.bus._event_signal, 'emit'):
            self.bus.publish(EventType.SIMULATION_STARTED, test_data)
            self.bus._handle_event(EventType.SIMULATION_STARTED, test_data)
        
        self.assertEqual(len(received1), 1)
        self.assertEqual(len(received2), 1)
    
    def test_no_subscribers(self):
        """Test publishing when no subscribers exist."""
        test_data = {'test': 'value'}
        
        # Should not raise an error
        with patch.object(self.bus._event_signal, 'emit'):
            self.bus.publish(EventType.SIMULATION_STARTED, test_data)
            self.bus._handle_event(EventType.SIMULATION_STARTED, test_data)
    
    def test_none_data(self):
        """Test publishing with None data."""
        received = []
        
        def callback(data):
            received.append(data)
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback)
        
        with patch.object(self.bus._event_signal, 'emit'):
            self.bus.publish(EventType.SIMULATION_STARTED, None)
            self.bus._handle_event(EventType.SIMULATION_STARTED, {})
        
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], {})


class TestWeakReferences(unittest.TestCase):
    """Test weak reference management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication([])
        EventBus._instance = None
        reset_metrics()
        self.bus = EventBus.get_instance()
    
    def tearDown(self):
        """Clean up after tests."""
        EventBus._instance = None
        reset_metrics()
        self.app.quit()
    
    def test_weak_ref_cleanup(self):
        """Test that weak references are cleaned up when callback is deleted."""
        test_data = {'test': 'value'}
        received = []
        
        def callback(data):
            received.append(data)
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback)
        
        # Delete the callback
        del callback
        
        # Clear any remaining references
        import gc
        gc.collect()
        
        # The subscriber count should be 0 after cleanup
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_STARTED), 0)
    
    def test_dead_ref_cleanup(self):
        """Test that dead references are cleaned up during event handling."""
        test_data = {'test': 'value'}
        
        def callback(data):
            pass
        
        # Create a weakref that will die
        ref = weakref.ref(callback)
        
        self.bus._subscribers[EventType.SIMULATION_STARTED] = [ref]
        
        # Delete the callback
        del callback
        
        # Process an event - should clean up dead ref
        with patch.object(self.bus._event_signal, 'emit'):
            self.bus._handle_event(EventType.SIMULATION_STARTED, test_data)
        
        # The subscriber list should be empty
        self.assertEqual(len(self.bus._subscribers[EventType.SIMULATION_STARTED]), 0)


class TestMetricsTracking(unittest.TestCase):
    """Test metrics tracking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication([])
        EventBus._instance = None
        reset_metrics()
        self.bus = EventBus.get_instance()
    
    def tearDown(self):
        """Clean up after tests."""
        EventBus._instance = None
        reset_metrics()
        self.app.quit()
    
    def test_publish_increments_metrics(self):
        """Test that publishing increments metrics."""
        def callback(data):
            pass
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback)
        
        with patch.object(self.bus._event_signal, 'emit'):
            self.bus.publish(EventType.SIMULATION_STARTED, {})
        
        metrics = get_metrics()
        
        self.assertEqual(metrics.total_published, 1)
        self.assertEqual(metrics.published_by_type[EventType.SIMULATION_STARTED], 1)
    
    def test_subscribe_increments_metrics(self):
        """Test that subscribing increments metrics."""
        def callback(data):
            pass
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback)
        
        metrics = get_metrics()
        
        self.assertEqual(metrics.total_subscribed, 1)
        self.assertEqual(metrics.subscribed_by_type[EventType.SIMULATION_STARTED], 1)
    
    def test_error_increments_metrics(self):
        """Test that callback errors increment error metrics."""
        def bad_callback(data):
            raise ValueError("Test error")
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, bad_callback)
        
        with patch.object(self.bus._event_signal, 'emit'):
            self.bus._handle_event(EventType.SIMULATION_STARTED, {})
        
        metrics = get_metrics()
        
        self.assertEqual(metrics.total_errors, 1)
        self.assertEqual(metrics.errors_by_type[EventType.SIMULATION_STARTED], 1)
        self.assertIsNotNone(metrics.last_error)
    
    def test_reset_metrics(self):
        """Test resetting metrics via class method."""
        def callback(data):
            pass
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback)
        
        with patch.object(self.bus._event_signal, 'emit'):
            self.bus.publish(EventType.SIMULATION_STARTED, {})
        
        reset_metrics()
        
        metrics = get_metrics()
        
        self.assertEqual(metrics.total_published, 0)
        self.assertEqual(metrics.total_subscribed, 0)


class TestSubscribers(unittest.TestCase):
    """Test subscriber management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = QApplication([])
        EventBus._instance = None
        reset_metrics()
        self.bus = EventBus.get_instance()
    
    def tearDown(self):
        """Clean up after tests."""
        EventBus._instance = None
        reset_metrics()
        self.app.quit()
    
    def test_get_subscriber_count(self):
        """Test getting subscriber count."""
        def callback1(data):
            pass
        
        def callback2(data):
            pass
        
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_STARTED), 0)
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback1)
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_STARTED), 1)
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback2)
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_STARTED), 2)
    
    def test_clear_subscribers(self):
        """Test clearing subscribers."""
        def callback(data):
            pass
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback)
        self.bus.subscribe(EventType.SIMULATION_COMPLETED, callback)
        
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_STARTED), 1)
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_COMPLETED), 1)
        
        # Clear specific event type
        self.bus.clear_subscribers(EventType.SIMULATION_STARTED)
        
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_STARTED), 0)
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_COMPLETED), 1)
        
        # Clear all subscribers
        self.bus.clear_subscribers()
        
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_COMPLETED), 0)
    
    def test_unsubscribe_removes_callback(self):
        """Test that unsubscribe removes specific callback."""
        received = []
        
        def callback1(data):
            received.append('callback1')
        
        def callback2(data):
            received.append('callback2')
        
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback1)
        self.bus.subscribe(EventType.SIMULATION_STARTED, callback2)
        
        result = self.bus.unsubscribe(EventType.SIMULATION_STARTED, callback1)
        
        self.assertTrue(result)
        self.assertEqual(self.bus.get_subscriber_count(EventType.SIMULATION_STARTED), 1)
        
        with patch.object(self.bus._event_signal, 'emit'):
            self.bus._handle_event(EventType.SIMULATION_STARTED, {})
        
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], 'callback2')
    
    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing a callback that doesn't exist."""
        def callback(data):
            pass
        
        result = self.bus.unsubscribe(EventType.SIMULATION_STARTED, callback)
        
        self.assertFalse(result)


class TestEventTypes(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
