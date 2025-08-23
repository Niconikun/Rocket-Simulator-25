import numpy as np

class Fins:
    def __init__(self, number, root_chord, tip_chord, span, thickness=2.0, shape="trapezoidal", airfoil="flat"):
        self.number = number
        self.root_chord = root_chord
        self.tip_chord = tip_chord
        self.span = span
        self.thickness = thickness
        self.shape = shape.lower()
        self.airfoil = airfoil.lower()
    
    def area(self):
        # Área de una aleta trapezoidal
        return 0.5 * (self.root_chord + self.tip_chord) * self.span
    
    def mean_aerodynamic_chord(self):
        # MAC para aleta trapezoidal
        return (2/3) * self.root_chord * ((1 + self.tip_chord/self.root_chord + (self.tip_chord/self.root_chord)**2) /
                                          (1 + self.tip_chord/self.root_chord))
    
    def description(self):
        return f"{self.number} aletas {self.shape}, perfil {self.airfoil}, cuerda raíz {self.root_chord} mm, cuerda punta {self.tip_chord} mm, envergadura {self.span} mm"

# Ejemplo de uso:
# fins = Fins(4, 60, 30, 40, shape="trapezoidal", airfoil="NACA0012")