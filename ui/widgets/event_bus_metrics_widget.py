"""Event Bus Metrics Dashboard - Debugging and monitoring widget for EventBus usage."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette
from ui.widgets import BaseWidget
from models.app_state import ApplicationState
from src.models.state import StateProvider
from src.utils.event_bus import EventType, get_metrics, reset_metrics, EventMetrics
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class EventBusMetricsWidget(BaseWidget):
    """
    Debugging widget for monitoring EventBus usage and metrics.
    
    Features:
    - Real-time metrics display
    - Event type statistics
    - Error tracking
    - Reset metrics functionality
    - Export metrics to JSON
    - Most active events highlighting
    """
    
    def __init__(self, state: Optional[StateProvider] = None, parent=None):
        """
        Initialize the EventBus Metrics Dashboard.
        
        Args:
            state: Optional StateProvider instance
            parent: Optional parent widget
        """
        super().__init__(state=state, parent=parent)
        self._metrics: EventMetrics = get_metrics()
        self._timer: QTimer = QTimer(self)
        self._refresh_interval_ms: int = 1000  # 1 second
        
        self.init_ui()
        self._setup_timer()
        self.refresh_metrics()
    
    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        
        # ===== HEADER =====
        header = QLabel("📊 Event Bus Metrics Dashboard")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet("color: #0078d7; margin-bottom: 20px;")
        main_layout.addWidget(header)
        
        # ===== OVERVIEW GROUP =====
        overview_group = QGroupBox("Overview")
        overview_layout = QHBoxLayout()
        
        # Total Published
        self.total_published_label = QLabel("0")
        self.total_published_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_published_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2ecc71;")
        published_layout = QVBoxLayout()
        published_layout.addWidget(QLabel("Total Events Published"))
        published_layout.addWidget(self.total_published_label)
        published_widget = QWidget()
        published_widget.setLayout(published_layout)
        overview_layout.addWidget(published_widget, 1)
        
        # Total Subscribed
        self.total_subscribed_label = QLabel("0")
        self.total_subscribed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_subscribed_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #3498db;")
        subscribed_layout = QVBoxLayout()
        subscribed_layout.addWidget(QLabel("Total Subscriptions"))
        subscribed_layout.addWidget(self.total_subscribed_label)
        subscribed_widget = QWidget()
        subscribed_widget.setLayout(subscribed_layout)
        overview_layout.addWidget(subscribed_widget, 1)
        
        # Total Errors
        self.total_errors_label = QLabel("0")
        self.total_errors_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_errors_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #e74c3c;")
        errors_layout = QVBoxLayout()
        errors_layout.addWidget(QLabel("Total Callback Errors"))
        errors_layout.addWidget(self.total_errors_label)
        errors_widget = QWidget()
        errors_widget.setLayout(errors_layout)
        overview_layout.addWidget(errors_widget, 1)
        
        overview_group.setLayout(overview_layout)
        main_layout.addWidget(overview_group)
        
        # ===== LAST ERROR GROUP =====
        error_group = QGroupBox("Last Error")
        error_layout = QVBoxLayout()
        
        self.last_error_label = QLabel("No errors recorded")
        self.last_error_label.setWordWrap(True)
        self.last_error_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        error_layout.addWidget(self.last_error_label)
        
        error_group.setLayout(error_layout)
        main_layout.addWidget(error_group)
        
        # ===== EVENT TYPE STATISTICS =====
        stats_group = QGroupBox("Event Type Statistics")
        stats_layout = QVBoxLayout()
        
        # Published by Type Table
        self.published_table = QTableWidget()
        self.published_table.setColumnCount(2)
        self.published_table.setHorizontalHeaderLabels(["Event Type", "Published Count"])
        self.published_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.published_table.setAlternatingRowColors(True)
        self.published_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        stats_layout.addWidget(QLabel("Published Events by Type:"))
        stats_layout.addWidget(self.published_table)
        
        # Subscribed by Type Table
        self.subscribed_table = QTableWidget()
        self.subscribed_table.setColumnCount(2)
        self.subscribed_table.setHorizontalHeaderLabels(["Event Type", "Subscription Count"])
        self.subscribed_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.subscribed_table.setAlternatingRowColors(True)
        self.subscribed_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        stats_layout.addWidget(QLabel("Subscriptions by Type:"))
        stats_layout.addWidget(self.subscribed_table)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group, 1)  # Stretch factor
        
        # ===== ACTIONS =====
        actions_layout = QHBoxLayout()
        
        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.clicked.connect(self.refresh_metrics)
        actions_layout.addWidget(refresh_button)
        
        reset_button = QPushButton("🗑️ Reset Metrics")
        reset_button.setStyleSheet("background-color: #e74c3c; color: white;")
        reset_button.clicked.connect(self._on_reset_metrics)
        actions_layout.addWidget(reset_button)
        
        export_button = QPushButton("📥 Export to JSON")
        export_button.clicked.connect(self._on_export_metrics)
        actions_layout.addWidget(export_button)
        
        auto_refresh_check = self._create_auto_refresh_checkbox()
        actions_layout.addWidget(auto_refresh_check)
        
        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)
        
        # ===== INFO =====
        info_label = QLabel("Note: Metrics are tracked since application start or last reset.")
        info_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        self.setLayout(main_layout)
        self.setWindowTitle("Event Bus Metrics Dashboard")
    
    def _create_auto_refresh_checkbox(self):
        """Create auto-refresh checkbox."""
        from PyQt6.QtWidgets import QCheckBox
        checkbox = QCheckBox("Auto-refresh (1s)")
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(self._on_auto_refresh_changed)
        return checkbox
    
    def _setup_timer(self):
        """Set up the auto-refresh timer."""
        self._timer.timeout.connect(self.refresh_metrics)
        self._timer.start(self._refresh_interval_ms)
    
    def _on_auto_refresh_changed(self, state):
        """Handle auto-refresh toggle."""
        if state == Qt.CheckState.Checked:
            self._timer.start(self._refresh_interval_ms)
        else:
            self._timer.stop()
    
    def _on_reset_metrics(self):
        """Handle reset metrics button click."""
        reply = QMessageBox.question(
            self,
            "Reset Metrics",
            "Are you sure you want to reset all event bus metrics to zero?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            reset_metrics()
            self._metrics = get_metrics()  # Get fresh metrics object
            self.refresh_metrics()
            logger.info("Event bus metrics reset")
    
    def _on_export_metrics(self):
        """Handle export metrics button click."""
        try:
            metrics = get_metrics()
            metrics_dict = metrics.to_dict()
            metrics_dict['export_timestamp'] = datetime.now().isoformat()
            
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Export Event Bus Metrics",
                f"event_bus_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if filepath:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(metrics_dict, f, indent=4, ensure_ascii=False)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Metrics exported to:\n{filepath}"
                )
                logger.info(f"Event bus metrics exported to: {filepath}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export metrics: {str(e)}"
            )
            logger.error(f"Error exporting event bus metrics: {e}")
    
    def refresh_metrics(self):
        """Refresh all metrics displays."""
        try:
            # Get fresh metrics
            self._metrics = get_metrics()
            
            # Update overview labels
            self.total_published_label.setText(str(self._metrics.total_published))
            self.total_subscribed_label.setText(str(self._metrics.total_subscribed))
            self.total_errors_label.setText(str(self._metrics.total_errors))
            
            # Update last error
            if self._metrics.last_error:
                self.last_error_label.setText(self._metrics.last_error)
                self.last_error_label.setStyleSheet("color: #e74c3c;")
            else:
                self.last_error_label.setText("No errors recorded")
                self.last_error_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            
            # Update published by type table
            self._update_table(
                self.published_table,
                self._metrics.published_by_type,
                "Published Events"
            )
            
            # Update subscribed by type table
            self._update_table(
                self.subscribed_table,
                self._metrics.subscribed_by_type,
                "Subscriptions"
            )
            
            logger.debug("Event bus metrics refreshed")
        except Exception as e:
            logger.error(f"Error refreshing event bus metrics: {e}")
    
    def _update_table(self, table: QTableWidget, data: Dict[Enum, int], column_title: str):
        """Update a table with event type statistics."""
        try:
            # Sort by count (descending)
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
            
            table.setRowCount(len(sorted_items))
            
            for row, (event_type, count) in enumerate(sorted_items):
                # Event type name
                item_name = QTableWidgetItem(event_type.name)
                item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 0, item_name)
                
                # Count
                item_count = QTableWidgetItem(str(count))
                item_count.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                # Highlight high-count events
                if count > 10:
                    item_count.setBackground(QColor(230, 240, 230))  # Light green
                elif count > 5:
                    item_count.setBackground(QColor(240, 240, 230))  # Light yellow
                
                table.setItem(row, 1, item_count)
            
            # Resize columns to content
            table.resizeColumnsToContents()
        except Exception as e:
            logger.error(f"Error updating {column_title} table: {e}")
    
    def closeEvent(self, event):
        """Clean up when widget is closed."""
        if self._timer and self._timer.isActive():
            self._timer.stop()
        super().closeEvent(event)


# Import QMessageBox and QFileDialog for the methods that use them
from PyQt6.QtWidgets import QMessageBox, QFileDialog
