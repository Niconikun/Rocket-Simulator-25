import numpy as np

class RearSection:
    def __init__(self, length, base_diameter, end_diameter, shape="conical"):
        self.length = length
        self.base_diameter = base_diameter
        self.end_diameter = end_diameter
        self.shape = shape.lower()
    
    def volume(self):
        if self.shape == "conical":
            r1 = self.base_diameter / 2
            r2 = self.end_diameter / 2
            return (1/3) * np.pi * self.length * (r1**2 + r1*r2 + r2**2)
        elif self.shape == "boat-tail":
            # Aproximación simple
            r1 = self.base_diameter / 2
            r2 = self.end_diameter / 2
            return (np.pi * self.length / 2) * (r1**2 + r2**2)
        else:
            raise ValueError("Forma de sección trasera no soportada")
    
    def description(self):
        return f"Sección trasera {self.shape} de {self.length} mm, {self.base_diameter}→{self.end_diameter} mm"

# Ejemplo de uso:
# rear = RearSection(60, 40, 30, shape="boat-tail")