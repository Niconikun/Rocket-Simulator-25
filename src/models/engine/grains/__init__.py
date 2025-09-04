from .grains_to_be_implemented.endBurner import *
from .bates import *
from .grains_to_be_implemented.finocyl import *
from .grains_to_be_implemented.moonBurner import *
from .star import *
from .grains_to_be_implemented.xCore import *
from .grains_to_be_implemented.cGrain import *
from .grains_to_be_implemented.dGrain import *
from .grains_to_be_implemented.rodTube import *
from .conical import *
from .grains_to_be_implemented.custom import *

# Generate grain geometry name -> constructor lookup table
grainTypes = {}
grainClasses = [BatesGrain, EndBurningGrain, Finocyl, MoonBurner, StarGrain, XCore, CGrain, DGrain, RodTubeGrain,
                ConicalGrain, CustomGrain]
for grainType in grainClasses:
    grainTypes[grainType.geomName] = grainType
