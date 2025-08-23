import numpy as np

class NoseCone:
    def __init__(self, length, base_diameter, shape="conical"):
        self.length = length
        self.base_diameter = base_diameter
        self.shape = shape.lower()
    
    def volume(self):
        if self.shape == "conical":
            return (1/3) * np.pi * (self.base_diameter/2)**2 * self.length
        elif self.shape == "ogive":
            # Aproximación ogiva tangente
            R = (self.length**2 + (self.base_diameter/2)**2) / (self.base_diameter)
            return (np.pi/3) * (self.base_diameter/2)**2 * self.length * (1 + (self.length/R))
        elif self.shape == "parabolic":
            return (1/2) * np.pi * (self.base_diameter/2)**2 * self.length
        else:
            raise ValueError("Forma de ojiva no soportada")
    
    def description(self):
        return f"Ojiva {self.shape} de {self.length} mm x {self.base_diameter} mm"

# Ejemplo de uso:
# nose = NoseCone(120, 40, shape="ogive")