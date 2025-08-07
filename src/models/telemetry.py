import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

@dataclass
class SignalProperties:
    """Propiedades de la señal de telemetría"""
    frequency: float      # Frecuencia de transmisión [Hz]
    power: float         # Potencia de transmisión [W]
    wavelength: float    # Longitud de onda [m]
    noise_floor: float   # Piso de ruido [dBm]

class TelemetrySystem:
    """Sistema de telemetría para cohetes"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Configuración del sistema {
                'sampling_rate': float,    # Tasa de muestreo [Hz]
                'tx_power': float,         # Potencia de transmisión [W]
                'frequency': float,        # Frecuencia de operación [Hz]
                'antenna_gain': float,     # Ganancia de antena [dBi]
                'min_snr': float          # SNR mínimo requerido [dB]
            }
        """
        self.config = config
        self.signal = SignalProperties(
            frequency=config['frequency'],
            power=config['tx_power'],
            wavelength=3e8/config['frequency'],
            noise_floor=-110.0  # Típico para sistemas de telemetría
        )
        
        # Estado del sistema
        self.is_transmitting = False
        self.last_transmission = 0.0
        self.packet_counter = 0
        self.lost_packets = 0
        
        # Buffer de datos
        self.data_buffer: List[Dict] = []
        self.max_buffer_size = 1000
        
    def calculate_link_budget(self, distance: float, altitude: float) -> float:
        """
        Calcula el presupuesto de enlace.
        
        Args:
            distance: Distancia a la estación base [m]
            altitude: Altitud actual [m]
            
        Returns:
            float: Relación señal/ruido [dB]
        """
        # Pérdidas por espacio libre
        space_loss = 20 * np.log10(distance) + 20 * np.log10(self.signal.frequency) - 147.55
        
        # Pérdidas atmosféricas (simplificado)
        atm_loss = 0.1 * altitude/1000  # 0.1 dB/km
        
        # Ganancia total del sistema
        system_gain = (
            10 * np.log10(self.signal.power) +  # Potencia TX
            self.config['antenna_gain'] +        # Ganancia antena
            self.config['antenna_gain']          # Ganancia antena receptora
        )
        
        # SNR final
        snr = system_gain - space_loss - atm_loss - self.signal.noise_floor
        
        return snr
        
    def update(self, rocket_state: Dict[str, Any], time: float) -> Optional[Dict]:
        """
        Actualiza el sistema de telemetría.
        
        Args:
            rocket_state: Estado actual del cohete
            time: Tiempo actual [s]
            
        Returns:
            Dict | None: Paquete de telemetría si hay transmisión
        """
        # Verificar si es momento de transmitir
        if time - self.last_transmission < 1/self.config['sampling_rate']:
            return None
            
        # Calcular calidad del enlace
        distance = np.linalg.norm(rocket_state['position'])
        altitude = rocket_state['position'][2]
        snr = self.calculate_link_budget(distance, altitude)
        
        # Crear paquete de telemetría
        telemetry_packet = {
            'timestamp': time,
            'packet_id': self.packet_counter,
            'position': rocket_state['position'].copy(),
            'velocity': rocket_state['velocity'].copy(),
            'attitude': rocket_state['attitude'].copy(),
            'signal_quality': snr,
            'status': 'nominal'
        }
        
        # Simular pérdidas de paquetes
        if snr < self.config['min_snr']:
            probability_loss = 1 - (snr/self.config['min_snr'])**2
            if np.random.random() < probability_loss:
                self.lost_packets += 1
                telemetry_packet['status'] = 'lost'
                logging.warning(f"Paquete {self.packet_counter} perdido - SNR: {snr:.1f} dB")
                
        # Actualizar estado
        self.last_transmission = time
        self.packet_counter += 1
        
        # Almacenar en buffer
        self.data_buffer.append(telemetry_packet)
        if len(self.data_buffer) > self.max_buffer_size:
            self.data_buffer.pop(0)
            
        return telemetry_packet
    
    def get_statistics(self) -> Dict[str, float]:
        """Obtiene estadísticas del sistema"""
        total_packets = self.packet_counter
        lost_ratio = self.lost_packets/total_packets if total_packets > 0 else 0
        
        return {
            'total_packets': total_packets,
            'lost_packets': self.lost_packets,
            'packet_loss_ratio': lost_ratio,
            'effective_rate': self.config['sampling_rate'] * (1 - lost_ratio)
        }