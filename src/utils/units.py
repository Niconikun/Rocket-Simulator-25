"""This module contains tables of units and their long form names, their conversion rates with other units, and
functions for performing conversion."""

import collections

# The keys in this dictionary specify the units that all calculations are done in internally
unitLabels = {
    'm': 'Length',
    'm^3': 'Volume',
    'm/s': 'Velocity',
    'N': 'Force',
    'Ns': 'Impulse',
    'Pa': 'Pressure',
    'kg': 'Mass',
    'kg/m^3': 'Density',
    'kg/s': 'Mass Flow',
    'kg/(m^2*s)': 'Mass Flux',
    'm/(s*Pa^n)': 'Burn Rate Coefficient',
    '(m*Pa)/s': 'Nozzle Slag Coefficient',
    'm/(s*Pa)': 'Nozzle Erosion Coefficient',
    'J': 'Energía',
    'W': 'Potencia',
    'K': 'Temperatura',
    'rad': 'Ángulo',
    's': 'Tiempo',
}

unitTable = [
    ('m', 'cm', 100),
    ('m', 'mm', 1000),
    ('m', 'in', 39.37),
    ('m', 'ft', 3.28),

    ('m^3', 'cm^3', 100**3),
    ('m^3', 'mm^3', 1000**3),
    ('m^3', 'in^3', 39.37**3),
    ('m^3', 'ft^3', 3.28**3),

    ('m/s', 'cm/s', 100),
    ('m/s', 'mm/s', 1000),
    ('m/s', 'ft/s', 3.28),
    ('m/s', 'in/s', 39.37),

    ('N', 'lbf', 0.2248),

    ('Ns', 'lbfs', 0.2248),

    ('Pa', 'MPa', 1/1000000),
    ('Pa', 'psi', 1/6895),

    ('kg', 'g', 1000),
    ('kg', 'lb', 2.205),
    ('kg', 'oz', 2.205 * 16),

    ('kg/m^3', 'lb/in^3', 3.61273e-5),
    ('kg/m^3', 'g/cm^3', 0.001),

    ('kg/s', 'lb/s', 2.205),
    ('kg/s', 'g/s', 1000),

    ('kg/(m^2*s)', 'lb/(in^2*s)', 0.001422),

    ('(m*Pa)/s', '(m*MPa)/s', 1000000),
    ('(m*Pa)/s', '(in*psi)/s', 0.00571014715),

    ('m/(s*Pa)', 'thou/(s*psi)', 271447138),
    ('m/(s*Pa)', 'um/(s*mPa)', 1E9),

    ('m/(s*Pa^n)', 'in/(s*psi^n)', 39.37), # Ratio converts m/s to in/s. The pressure conversion must be done separately
    ('m/(s*Pa^n)', 'mm/(s*Pa^n)', 1000),

    ('J', 'kJ', 1/1000),
    ('J', 'cal', 1/4.184),
    ('J', 'Wh', 1/3600),
    ('J', 'BTU', 1/1055.06),

    # Potencia
    ('W', 'kW', 1/1000),
    ('W', 'hp', 1/745.7),

    # Temperatura (solo diferencias, no valores absolutos)
    ('K', '°C', 1),
    ('K', '°F', 9/5),

    # Ángulo
    ('rad', 'deg', 180/3.141592653589793),
    ('deg', 'rad', 3.141592653589793/180),

    # Tiempo
    ('s', 'min', 1/60),
    ('min', 'h', 1/60),
    ('s', 'h', 1/3600)
]

# Some base units are... not well chosen because any reasonable value in them will have too many/few digits to edit,
# leading to them getting truncated. They all have conversions that work much better, so just don't show them in the UI
internalOnlyUnits = ['m/(s*Pa^n)', 'm/(s*Pa)']

def getAllConversions(unit):
    """Returns a list of all units that the passed unit can be converted to (directa o indirectamente)."""
    # Construir grafo de conversiones
    graph = collections.defaultdict(set)
    for u1, u2, _ in unitTable:
        graph[u1].add(u2)
        graph[u2].add(u1)
    # BFS para encontrar todas las unidades alcanzables
    visited = set()
    queue = [unit]
    while queue:
        current = queue.pop(0)
        if current not in visited:
            visited.add(current)
            queue.extend(graph[current] - visited)
    # Eliminar unidades internas
    for internalOnlyUnit in internalOnlyUnits:
        if internalOnlyUnit in visited:
            visited.remove(internalOnlyUnit)
    return list(visited)

def getConversion(originUnit, destUnit, _visited=None):
    """Returns the ratio to convert between the two units, directa o indirectamente."""
    if originUnit == destUnit:
        return 1
    # Búsqueda directa
    for conversion in unitTable:
        if conversion[0] == originUnit and conversion[1] == destUnit:
            return conversion[2]
        if conversion[1] == originUnit and conversion[0] == destUnit:
            return 1/conversion[2]
    # Búsqueda indirecta (recursiva)
    if _visited is None:
        _visited = set()
    _visited.add(originUnit)
    for conversion in unitTable:
        if conversion[0] == originUnit and conversion[1] not in _visited:
            try:
                factor = conversion[2] * getConversion(conversion[1], destUnit, _visited)
                return factor
            except KeyError:
                continue
        if conversion[1] == originUnit and conversion[0] not in _visited:
            try:
                factor = (1/conversion[2]) * getConversion(conversion[0], destUnit, _visited)
                return factor
            except KeyError:
                continue
    raise KeyError(f"Cannot find conversion from <{originUnit}> to <{destUnit}>")

def convert(quantity, originUnit, destUnit):
    """Returns the value of 'quantity' when it is converted from 'originUnit' to 'destUnit'."""
    return quantity * getConversion(originUnit, destUnit)

def convertAll(quantities, originUnit, destUnit):
    """Converts a list of values from 'originUnit' to 'destUnit'."""
    convRate = getConversion(originUnit, destUnit)
    return [q * convRate for q in quantities]

def convFormat(quantity, originUnit, destUnit, places=3):
    """Takes in a quantity in originUnit, converts it to destUnit and outputs a rounded and formatted string that
    includes the unit appended to the end."""
    rounded = round(convert(quantity, originUnit, destUnit), places)
    return '{} {}'.format(rounded, destUnit)
