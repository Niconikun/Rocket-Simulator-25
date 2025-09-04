"""Contains the motor class and a supporting configuration property collection."""
from .grains import grainTypes
from .nozzle import Nozzle
from .propellant import Propellant
from . import geometry
from .simResult import SimulationResult
from .grains import EndBurningGrain
from .constants import gasConstant
from scipy.optimize import newton
import numpy as np

class MotorConfig():
    """Contains the settings required for simulation, including environmental conditions and details about
    how to run the simulation."""
    def __init__(self, maxPressure, maxMassFlux, maxMachNumber, minPortThroat, flowSeparationWarnPercent, burnoutWebThres, burnoutThrustThres, timestep, ambPressure, mapDim, sepPressureRatio):
        # Limits
        self.maxPressure = maxPressure #Max Allowed Pressure [Pa]
        self.maxMassFlux = maxMassFlux #Maximum Allowed Mass Flux [kg/(m^2*s)]
        self.maxMachNumber = maxMachNumber #Maximum Allowed Core Mach Number [-]
        self.minPortThroat = minPortThroat #Minimum Allowed Port/Throat Ratio [-]
        self.flowSeparationWarnPercent = flowSeparationWarnPercent #Flow Separation Warning Threshold [-]
        # Simulation
        self.burnoutWebThres = burnoutWebThres #Web Burnout Threshold [m]
        self.burnoutThrustThres = burnoutThrustThres #Thrust Burnout Threshold [%]
        self.timestep = timestep #Simulation Timestep [s]
        self.ambPressure = ambPressure #Ambient Pressure [Pa]
        self.mapDim = mapDim #Grain Map Dimension [-]
        self.sepPressureRatio = sepPressureRatio #Separation Pressure Ratio [-]



class Motor():
    """The motor class stores a number of grains, a nozzle instance, a propellant, and a configuration that it uses
    to run simulations. Simulations return a simRes object that includes any warnings or errors associated with the
    simulation and the data. The propellant field may be None if the motor has no propellant set, and the grains list
    is allowed to be empty. The nozzle field and config must be filled, even if they are empty property collections."""
    def __init__(self):
        self.grains = []
        self.propellant = Propellant()
        self.nozzle = Nozzle()
        self.config = MotorConfig()

    def calcBurningSurfaceArea(self, regDepth):
        burnoutThres = self.config.getProperty('burnoutWebThres')
        gWithReg = zip(self.grains, regDepth)
        perGrain = [gr.getSurfaceAreaAtRegression(reg) * int(gr.isWebLeft(reg, burnoutThres)) for gr, reg in gWithReg]
        return sum(perGrain)

    def calcKN(self, regDepth, dThroat):
        """Returns the motor's Kn when it has each grain has regressed by its value in regDepth, which should be a list
        with the same number of elements as there are grains in the motor."""
        burningSurfaceArea = self.calcBurningSurfaceArea(regDepth)
        nozzleArea = self.nozzle.getThroatArea(dThroat)
        return burningSurfaceArea / nozzleArea

    def calcIdealPressure(self, regDepth, dThroat, kn=None):
        """Returns the steady-state pressure of the motor at a given reg. Kn is calculated automatically, but it can
        optionally be passed in to save time on motors where calculating surface area is expensive."""
        if kn is None:
            kn = self.calcKN(regDepth, dThroat)
        return self.propellant.getPressureFromKn(kn)

    def calcForce(self, chamberPres, dThroat, exitPres=None):
        """Calculates the force of the motor at a given regression depth per grain. Calculates exit pressure by
        default, but can also use a value passed in."""
        _, _, gamma, _, _ = self.propellant.getCombustionProperties(chamberPres)
        ambPressure = self.config.getProperty('ambPressure')
        thrustCoeff = self.nozzle.getAdjustedThrustCoeff(chamberPres, ambPressure, gamma, dThroat, exitPres)
        thrust = thrustCoeff * self.nozzle.getThroatArea(dThroat) * chamberPres
        return max(thrust, 0)

    def calcFreeVolume(self, regDepth):
        """Calculates the volume inside of the motor not occupied by propellant for a set of regression depths."""
        return sum([grain.getFreeVolume(reg) for grain, reg in zip(self.grains, regDepth)])

    def calcTotalVolume(self):
        """Calculates the bounding-cylinder volume of the combustion chamber."""
        return sum([grain.getGrainBoundingVolume() for grain in self.grains])

    def calcMachNumber(self, chamberPres, massFlux):
        """Calculates the mach number in the core of a grain for a given chamber pressure and mass flux."""
        _, _, gamma, T, molarMass = self.propellant.getCombustionProperties(chamberPres)

        if chamberPres <= 1e-6:
            return 0

        def machFunc(M, chamberPres, massFlux, gamma, T, molarMass, gasConstant):
            A = chamberPres * (gamma * molarMass / (gasConstant * T)) ** 0.5
            B = 1.0 + ((gamma - 1.0) / 2.0) * M**2
            C = -(gamma + 1.0) / (2.0 * (gamma - 1.0))
            return A * M * (B ** C) - massFlux

        def machFuncDerivative(M, chamberPres, massFlux, gamma, T, molarMass, gasConstant):
            A = chamberPres * (gamma * molarMass / gasConstant / T) ** 0.5
            B = 1.0 + ((gamma - 1.0) / 2.0) * M**2
            C = -(gamma + 1.0) / (2.0 * (gamma - 1.0))
            dB_dM = (gamma - 1.0) * M
            return A * (B**C + M * C * (B**(C - 1.0)) * dB_dM)

        maxMassFlux = machFunc(1.0, chamberPres, massFlux, gamma, T, molarMass, gasConstant) + massFlux

        if massFlux >= maxMassFlux: # Boom
            return 1.0

        x0 = np.arcsin(massFlux / maxMassFlux) * 2 / np.pi
        M = newton(machFunc, fprime=machFuncDerivative, x0=x0, args=(chamberPres, massFlux, gamma, T, molarMass, gasConstant))

        return max(M, 0)

    def runSimulation(self, callback=None):
        """Runs a simulation of the motor and returns a simRes instance with the results. Constraints are checked,
        including the number of grains, if the motor has a propellant set, and if the grains have geometry errors. If
        all of these tests are passed, the motor's operation is simulated by calculating Kn, using this value to get
        pressure, and using pressure to determine thrust and other statistics. The next timestep is then prepared by
        using the pressure to determine how the motor will regress in the given timestep at the current pressure.
        This process is repeated and regression tracked until all grains have burned out, when the results and any
        warnings are returned."""
        burnoutWebThres = self.config.getProperty('burnoutWebThres')
        burnoutThrustThres = self.config.getProperty('burnoutThrustThres')
        dTime = self.config.getProperty('timestep')

        simRes = SimulationResult(self)

        # Pull the required numbers from the propellant
        density = self.propellant.getProperty('density')

        # Precalculate these are they don't change
        motorVolume = self.calcTotalVolume()

        # Generate coremaps for perforated grains
        for grain in self.grains:
            grain.simulationSetup(self.config)

        # Setup initial values
        perGrainReg = [0 for grain in self.grains]

        # At t = 0, the motor has ignited
        simRes.channels['time'].addData(0)
        simRes.channels['kn'].addData(self.calcKN(perGrainReg, 0))
        simRes.channels['pressure'].addData(self.calcIdealPressure(perGrainReg, 0, None))
        simRes.channels['force'].addData(0)
        simRes.channels['mass'].addData([grain.getVolumeAtRegression(0) * density for grain in self.grains])
        simRes.channels['volumeLoading'].addData(100 * (1 - (self.calcFreeVolume(perGrainReg) / motorVolume)))
        simRes.channels['massFlow'].addData([0 for grain in self.grains])
        simRes.channels['massFlux'].addData([0 for grain in self.grains])
        simRes.channels['regression'].addData([0 for grains in self.grains])
        simRes.channels['web'].addData([grain.getWebLeft(0) for grain in self.grains])
        simRes.channels['exitPressure'].addData(0)
        simRes.channels['dThroat'].addData(0)
        simRes.channels['machNumber'].addData([0 for grain in self.grains])

        # Check port/throat ratio and add a warning if it is not large enough
        aftPort = self.grains[-1].getPortArea(0)
        if aftPort is not None:
            minAllowed = self.config.getProperty('minPortThroat')
            ratio = aftPort / geometry.circleArea(self.nozzle.props['throat'].getValue())

        # Perform timesteps
        while simRes.shouldContinueSim(burnoutThrustThres):
            # Calculate regression
            massFlow = 0
            perGrainMass = [0 for grain in self.grains]
            perGrainMassFlow = [0 for grain in self.grains]
            perGrainMassFlux = [0 for grain in self.grains]
            perGrainWeb = [0 for grain in self.grains]
            for gid, grain in enumerate(self.grains):
                if grain.getWebLeft(perGrainReg[gid]) > burnoutWebThres:
                    # Calculate regression at the current pressure
                    reg = dTime * self.propellant.getBurnRate(simRes.channels['pressure'].getLast())
                    # Find the mass flux through the grain based on the mass flow fed into from grains above it
                    perGrainMassFlux[gid] = grain.getPeakMassFlux(massFlow, dTime, perGrainReg[gid], reg, density)
                    # Find the mass of the grain after regression
                    perGrainMass[gid] = grain.getVolumeAtRegression(perGrainReg[gid]) * density
                    # Add the change in grain mass to the mass flow
                    massFlow += (simRes.channels['mass'].getLast()[gid] - perGrainMass[gid]) / dTime
                    # Apply the regression
                    perGrainReg[gid] += reg
                    perGrainWeb[gid] = grain.getWebLeft(perGrainReg[gid])
                perGrainMassFlow[gid] = massFlow
            simRes.channels['regression'].addData(perGrainReg[:])
            simRes.channels['web'].addData(perGrainWeb)

            simRes.channels['volumeLoading'].addData(100 * (1 - (self.calcFreeVolume(perGrainReg) / motorVolume)))
            simRes.channels['mass'].addData(perGrainMass)
            simRes.channels['massFlow'].addData(perGrainMassFlow)
            simRes.channels['massFlux'].addData(perGrainMassFlux)

            # Calculate KN
            dThroat = simRes.channels['dThroat'].getLast()
            simRes.channels['kn'].addData(self.calcKN(perGrainReg, dThroat))

            # Calculate Pressure
            lastKn = simRes.channels['kn'].getLast()
            pressure = self.calcIdealPressure(perGrainReg, dThroat, lastKn)
            simRes.channels['pressure'].addData(pressure)

            # Calculate Mach Number
            perGrainMachNumber = [0 for grain in self.grains]
            for gid, grain in enumerate(self.grains):
                perGrainMachNumber[gid] = self.calcMachNumber(pressure, perGrainMassFlux[gid])
            simRes.channels['machNumber'].addData(perGrainMachNumber)

            # Calculate Exit Pressure
            _, _, gamma, _, _ = self.propellant.getCombustionProperties(pressure)
            exitPressure = self.nozzle.getExitPressure(gamma, pressure)
            simRes.channels['exitPressure'].addData(exitPressure)

            # Calculate force
            force = self.calcForce(simRes.channels['pressure'].getLast(), dThroat, exitPressure)
            simRes.channels['force'].addData(force)

            simRes.channels['time'].addData(simRes.channels['time'].getLast() + dTime)

            # Calculate any slag deposition or erosion of the throat
            if pressure == 0:
                slagRate = 0
            else:
                slagRate = (1 / pressure) * self.nozzle.getProperty('slagCoeff')
            erosionRate = pressure * self.nozzle.getProperty('erosionCoeff')
            change = dTime * ((-2 * slagRate) + (2 * erosionRate))
            simRes.channels['dThroat'].addData(dThroat + change)

            if callback is not None:
                # Uses the grain with the largest percentage of its web left
                progress = max([g.getWebLeft(r) / g.getWebLeft(0) for g, r in zip(self.grains, perGrainReg)])
                if callback(1 - progress): # If the callback returns true, it is time to cancel
                    return simRes

        simRes.success = True

        # Note that this only adds all errors found on the first datapoint where there were errors to avoid repeating
        # errors. It should be revisited if getPressureErrors ever returns multiple types of errors
        for pressure in simRes.channels['pressure'].getData():
            if pressure > 0:
                err = self.propellant.getPressureErrors(pressure)
                if len(err) > 0:
                    simRes.addAlert(err[0])
                    break

        return simRes

    def getQuickResults(self):
        results = {
            'volumeLoading': 0,
            'initialKn': 0,
            'propellantMass': 0,
            'portRatio': 0,
            'length': 0
        }

        simRes = SimulationResult(self)

        density = self.propellant.getProperty('density') if self.propellant is not None else None
        throatArea = self.nozzle.getThroatArea()
        motorVolume = self.calcTotalVolume()

        if motorVolume == 0:
            return results

        # Generate coremaps for perforated grains
        for grain in self.grains:
            grain.simulationSetup(self.config)

        perGrainReg = [0 for grain in self.grains]

        results['volumeLoading'] = 100 * (1 - (self.calcFreeVolume(perGrainReg) / motorVolume))
        if throatArea != 0:
            results['initialKn'] = self.calcKN(perGrainReg, 0)
            results['portRatio'] = simRes.getPortRatio()
        if density is not None:
            results['propellantMass'] = sum([grain.getVolumeAtRegression(0) * density for grain in self.grains])
        results['length'] = simRes.getPropellantLength()

        return results
