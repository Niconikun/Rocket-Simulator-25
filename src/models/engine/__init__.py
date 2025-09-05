# SRM Engine Package
# This package contains the integrated SRM engine model

from .engine import Engine, EngineConfig

# Maintain backward compatibility
MotorConfig = EngineConfig

__all__ = ['Engine', 'EngineConfig', 'MotorConfig']
