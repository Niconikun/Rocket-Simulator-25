# utils/thrust_processor.py
import pandas as pd
import numpy as np
import logging

class ThrustCurveProcessor:
    """Process and validate experimental thrust curve data"""
    
    @staticmethod
    def process_csv_file(file_path, time_column='Tiempo', thrust_column='Fuerza'):
        """Process CSV file and return cleaned thrust curve data"""
        try:
            df = pd.read_csv(file_path)
            
            # Clean data
            df = df.dropna()
            df[time_column] = pd.to_numeric(df[time_column], errors='coerce')
            df[thrust_column] = pd.to_numeric(df[thrust_column], errors='coerce')
            df = df.dropna()
            
            # Ensure time starts at 0
            time_data = df[time_column].values - df[time_column].values[0]
            thrust_data = df[thrust_column].values
            
            # Convert kg-f to Newtons if needed
            if np.max(np.abs(thrust_data)) < 1000:  # Likely kg-f
                thrust_data = thrust_data * 9.80665
                
            return {
                'time': time_data.tolist(),
                'thrust': thrust_data.tolist(),
                'duration': time_data[-1],
                'max_thrust': np.max(thrust_data),
                'total_impulse': np.trapz(thrust_data, time_data)
            }
            
        except Exception as e:
            logging.error(f"Error processing thrust curve: {e}")
            return None
    
    @staticmethod
    def validate_thrust_curve(thrust_data, expected_propellant_mass, expected_isp):
        """Validate thrust curve against expected performance"""
        total_impulse = thrust_data['total_impulse']
        expected_impulse = expected_propellant_mass * expected_isp * 9.80665
        
        impulse_error = abs(total_impulse - expected_impulse) / expected_impulse
        
        validation = {
            'valid': impulse_error < 0.2,  # Allow 20% error
            'impulse_error_percent': impulse_error * 100,
            'measured_impulse': total_impulse,
            'expected_impulse': expected_impulse,
            'measured_avg_thrust': total_impulse / thrust_data['duration'],
            'expected_avg_thrust': expected_impulse / thrust_data['duration']
        }
        
        return validation