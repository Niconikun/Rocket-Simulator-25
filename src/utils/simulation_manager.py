"""
Simulation Data Management

Utilities for saving, loading, and managing simulation results with
automatic versioning using timestamps and UUIDs.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid
import logging

logger = logging.getLogger(__name__)


class SimulationManager:
    """
    Manages simulation data persistence and retrieval.
    
    Features:
    - Save simulation results with UUID + timestamp
    - Load simulation by ID
    - List all simulations with metadata
    - Delete simulations
    - Export/import simulation data
    """
    
    def __init__(self, data_dir: str = "data/simulations"):
        """Initialize the simulation manager."""
        self.data_dir = Path(data_dir)
        self.metadata_file = self.data_dir / "simulations_metadata.json"
        self._ensure_directories()
        self._load_metadata()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory: {self.data_dir}")
    
    def _load_metadata(self):
        """Load metadata from file or create new."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata: Dict[str, Dict[str, Any]] = json.load(f)
                logger.info(f"Loaded metadata for {len(self.metadata)} simulations")
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
                self.metadata = {}
        else:
            self.metadata = {}
    
    def _save_metadata(self):
        """Save metadata to file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False, default=str)
            logger.debug("Metadata saved successfully")
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def reload_metadata(self):
        """Reload metadata from disk, picking up changes from other instances."""
        self._load_metadata()
    
    def save_simulation(self, simulation_data: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[str]:
        """
        Save simulation data with automatic ID generation.
        
        Args:
            simulation_data: Dictionary containing simulation results
            metadata: Dictionary with simulation info (rocket, location, etc.)
        
        Returns:
            Simulation ID (timestamp_uuid format) or None if failed
        """
        # Generate unique ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        sim_id = f"sim_{timestamp}_{unique_id}"
        
        # Save data file
        data_file = self.data_dir / f"{sim_id}.json"
        
        try:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(simulation_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Update metadata
            self.metadata[sim_id] = {
                "timestamp": datetime.now().isoformat(),
                "rocket": metadata.get("rocket", "Unknown"),
                "location": metadata.get("location", "Unknown"),
                "max_altitude": metadata.get("max_altitude", 0.0),
                "max_velocity": metadata.get("max_velocity", 0.0),
                "max_range": metadata.get("max_range", 0.0),
                "max_mach": metadata.get("max_mach", 0.0),
                "max_accel_g": metadata.get("max_accel_g", 0.0),
                "flight_duration": metadata.get("flight_duration", 0.0),
                "temperature": metadata.get("temperature", 20.0),
                "pressure": metadata.get("pressure", 101325.0),
                "parachute_enabled": metadata.get("parachute_enabled", False),
                "parachute_deployed": metadata.get("parachute_deployed", False),
                "parachute_deployment_time": metadata.get("parachute_deployment_time", None),
                "parachute_deployment_altitude": metadata.get("parachute_deployment_altitude", None),
                "parachute_deployment_velocity": metadata.get("parachute_deployment_velocity", None),
                "drogue_deployed": metadata.get("drogue_deployed", False),
                "drogue_deployment_time": metadata.get("drogue_deployment_time", None),
                "drogue_deployment_altitude": metadata.get("drogue_deployment_altitude", None),
                "notes": metadata.get("notes", "")
            }
            self._save_metadata()
            
            logger.info(f"Simulation saved: {sim_id}")
            return sim_id
            
        except Exception as e:
            logger.error(f"Error saving simulation: {e}")
            return None
    
    def load_simulation(self, sim_id: str) -> Optional[Dict[str, Any]]:
        """
        Load simulation data by ID.
        
        Args:
            sim_id: Simulation ID
        
        Returns:
            Dictionary with simulation data or None if not found
        """
        data_file = self.data_dir / f"{sim_id}.json"
        
        if not data_file.exists():
            logger.warning(f"Simulation not found: {sim_id}")
            return None
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded simulation: {sim_id}")
            return data
        except Exception as e:
            logger.error(f"Error loading simulation: {e}")
            return None
    
    def list_simulations(self) -> List[Dict[str, Any]]:
        """
        Get list of all simulations with metadata.
        
        Returns:
            List of simulation metadata dictionaries
        """
        simulations = []
        for sim_id, meta in self.metadata.items():
            meta['id'] = sim_id
            simulations.append(meta)
        
        # Sort by timestamp (newest first)
        simulations.sort(
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        
        return simulations
    
    def get_recent_simulation(self) -> Optional[Dict[str, Any]]:
        """Get the most recent simulation."""
        simulations = self.list_simulations()
        if simulations:
            return simulations[0]
        return None
    
    def delete_simulation(self, sim_id: str) -> bool:
        """
        Delete simulation by ID.
        
        Args:
            sim_id: Simulation ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            data_file = self.data_dir / f"{sim_id}.json"
            if data_file.exists():
                data_file.unlink()
            
            if sim_id in self.metadata:
                del self.metadata[sim_id]
                self._save_metadata()
            
            logger.info(f"Deleted simulation: {sim_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting simulation: {e}")
            return False
    
    def export_simulation(self, sim_id: str, export_path: str) -> bool:
        """
        Export simulation data to external location.
        
        Args:
            sim_id: Simulation ID
            export_path: Path to export to
        
        Returns:
            True if successful
        """
        data = self.load_simulation(sim_id)
        if not data:
            return False
        
        try:
            meta = self.metadata.get(sim_id, {})
            export_data = {
                'metadata': meta,
                'data': data
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported simulation to: {export_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting simulation: {e}")
            return False
    
    def import_simulation(self, import_path: str) -> Optional[str]:
        """
        Import simulation from external file.
        
        Args:
            import_path: Path to import from
        
        Returns:
            New simulation ID or None if failed
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            metadata = import_data.get('metadata', {})
            data = import_data.get('data', {})
            
            return self.save_simulation(data, metadata)
        except Exception as e:
            logger.error(f"Error importing simulation: {e}")
            return None
