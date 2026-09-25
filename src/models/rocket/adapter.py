# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 3: Backward Compatibility Adapter

"""
Backward Compatibility Adapter for New Rocket Architecture

This module provides adapter classes that allow gradual migration from the
legacy monolithic Rocket class to the new component-based architecture.

For Phase 3, this adapter delegates to the legacy Rocket implementation
to maintain backward compatibility. In Phase 4, the simulation_worker
will be updated to use the new architecture directly.

Usage:
    # Existing code continues to work:
    from src.models.rocket import Rocket
    rocket = Rocket(r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, initial_mass)
    rocket.update_engine(rocket_name, engine_data)
    rocket.RK4_update(timestep)

Design Principles:
    - Maintain exact same interface as old Rocket class
    - Delegate to legacy implementation for backward compatibility
    - Provide foundation for gradual migration to new architecture
"""

import numpy as np
from typing import Optional, Any
import json
import logging

# For backward compatibility, delegate to legacy Rocket
from src.models.rocket_legacy import Rocket as LegacyRocket

logger = logging.getLogger(__name__)


class LegacyRocketAdapter:
    """
    Adapter that provides the old monolithic Rocket interface.
    
    For Phase 3, this simply delegates to the legacy Rocket class.
    In future phases, this will be updated to use the new architecture.
    """
    
    def __new__(cls, *args, **kwargs):
        """
        Create a new Rocket instance by delegating to legacy.
        
        This uses __new__ to ensure the instance is actually a LegacyRocket object
        with all its methods and attributes.
        """
        return LegacyRocket(*args, **kwargs)


# For backward compatibility
Rocket = LegacyRocket

__all__ = ['LegacyRocketAdapter', 'Rocket']
