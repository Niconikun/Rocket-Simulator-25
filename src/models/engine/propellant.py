"""Propellant submodule that contains the propellant class."""

from scipy.optimize import fsolve

from .constants import gasConstant
import json
import os

# Load the data from data/propellant/propellant_data.json
propellant_data_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'data', 'propellant', 'propellant_data.json'
)
propellant_data_path = os.path.normpath(propellant_data_path)

with open(propellant_data_path, 'r', encoding='utf-8') as f:
    PROPELLANT_DATA = json.load(f)

class PropellantTab():
    """Contains the combustion properties of a propellant over a specified pressure range."""
    def __init__(self, minPressure, maxPressure, a, n, k, t, m):
        self.props = {}
        self.props['minPressure'] = minPressure #Minimum Pressure [Pa]
        self.props['maxPressure'] = maxPressure #Maximum Pressure [Pa]
        self.props['a'] = a #Burn rate Coefficient [m/(s*Pa^n)]
        self.props['n'] = n #Burn rate Exponent [-]
        self.props['k'] = k #Specific Heat Ratio [-]
        self.props['t'] = t #Combustion Temperature [K]
        self.props['m'] = m #Exhaust Molar Mass [g/mol]


class Propellant():
    """Contains the physical and thermodynamic properties of a propellant formula."""
    def __init__(self, name, density):
        self.props = {}
        self.props['name'] = name
        self.props['density'] = density #Density [kg/m^3]
        self.props['tabs'] = {
            PropellantTab.__name__: []
        }

    def getCStar(self, pressure):
        """Returns the propellant's characteristic velocity."""
        _, _, gamma, temp, molarMass = self.getCombustionProperties(pressure)
        num = (gamma * gasConstant / molarMass * temp)**0.5
        denom = gamma * ((2 / (gamma + 1))**((gamma + 1) / (gamma - 1)))**0.5
        return num / denom

    def getBurnRate(self, pressure):
        """Returns the propellant's burn rate for the given pressure"""
        ballA, ballN, _, _, _ = self.getCombustionProperties(pressure)
        return ballA * (pressure ** ballN)

    def getPressureFromKn(self, kn):
        density = self.density
        tabPressures = []
        for tab in self.getProperty('tabs'):
            ballA, ballN, gamma, temp, molarMass = tab['a'], tab['n'], tab['k'], tab['t'], tab['m']
            num = kn * density * ballA
            exponent = 1 / (1 - ballN)
            denom = ((gamma / ((gasConstant / molarMass) * temp)) * ((2 / (gamma + 1)) ** ((gamma + 1) / (gamma - 1)))) ** 0.5
            tabPressure = (num / denom) ** exponent
            # If the pressure that a burnrate produces falls into its range, we know it is the proper burnrate
            # Due to floating point error, we sometimes get a situation in which no burnrate produces the proper pressure
            # For this scenario, we go by whichever produces the least error
            minTabPressure = tab['minPressure']
            maxTabPressure = tab['maxPressure']
            if minTabPressure == self.getMinimumValidPressure() and tabPressure < maxTabPressure:
                return tabPressure
            if maxTabPressure == self.getMaximumValidPressure() and minTabPressure < tabPressure:
                return tabPressure
            if minTabPressure < tabPressure < maxTabPressure:
                return tabPressure
            tabPressures.append([min(abs(minTabPressure - tabPressure), abs(tabPressure - maxTabPressure)), tabPressure])

        tabPressures.sort(key=lambda x: x[0]) # Sort by the pressure error
        return tabPressures[0][1] # Return the pressure

    def getKnFromPressure(self, pressure):
        func = lambda kn: self.getPressureFromKn(kn) - pressure

        return fsolve(func, [250], maxfev=1000)

    def getCombustionProperties(self, pressure):
        """Returns the propellant's a, n, gamma, combustion temp and molar mass for a given pressure"""
        closest = {}
        closestPressure = 1e100
        for tab in self.getProperty('tabs'):
            if tab['minPressure'] < pressure < tab['maxPressure']:
                return tab['a'], tab['n'], tab['k'], tab['t'], tab['m']
            if abs(pressure - tab['minPressure']) < closestPressure:
                closest = tab
                closestPressure = abs(pressure - tab['minPressure'])
            if abs(pressure - tab['maxPressure']) < closestPressure:
                closest = tab
                closestPressure = abs(pressure - tab['maxPressure'])

        return closest['a'], closest['n'], closest['k'], closest['t'], closest['m']

    def getMinimumValidPressure(self):
        """Returns the lowest pressure value with associated combustion properties"""
        return min([tab['minPressure'] for tab in self.getProperty('tabs')])

    def getMaximumValidPressure(self):
        """Returns the highest pressure value with associated combustion properties"""
        return max([tab['maxPressure'] for tab in self.getProperty('tabs')])

    def addTab(self, tab):
        """Adds a set of combustion properties to the propellant"""
        self.props['tabs'].addTab(tab)
