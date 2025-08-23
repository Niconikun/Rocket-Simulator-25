import numpy as np

class Fuselage:
    def __init__(self, length, diameter, wall_thickness=2.0, material="Aluminum"):
        self.length = length
        self.diameter = diameter
        self.wall_thickness = wall_thickness
        self.material = material
    
    def volume(self):
        r_ext = self.diameter / 2
        r_int = r_ext - self.wall_thickness
        return np.pi * (r_ext**2 - r_int**2) * self.length
    
    def description(self):
        return f"Fuselaje de {self.length} mm x {self.diameter} mm, material: {self.material}"

# Ejemplo de uso:
# fus = Fuselage(800, 40, wall_thickness=2)