# Spanish Translation for Rocket Simulator Pro

## Overview

This document describes the Spanish (es) translation implementation for Rocket Simulator Pro.

## Files Created

1. **`rocket_simulator_es.ts`** - Qt Linguist translation source file
   - Contains 130+ translation entries
   - Human-readable XML format
   - Can be edited with Qt Linguist or any text editor

2. **`README.md`** - General translation documentation

## Implementation

### Fallback Translations

The Spanish translations are implemented in two ways:

1. **Compiled .qm files** (preferred for production)
   - Binary format loaded by Qt's QTranslator
   - Faster performance
   - Requires compilation from .ts files

2. **Fallback dictionary** (for development)
   - Defined in `src/config/translations.py`
   - Used when .qm files are not available
   - Allows immediate testing without compilation

### Translation Coverage

The following UI elements are translated to Spanish:

#### Main Window (100% complete)
- Window title: "Rocket Simulator Pro" → "Simulador de Cohetes Pro"
- All menu items: File, Edit, View, Language, Help
- All menu actions: New Simulation, Open Configuration, Save Configuration, Exit, Reset to Defaults, Dark Mode, About
- Status bar messages: "Ready" → "Listo"

#### Tabs (100% complete)
- "🚀 Simulation" → "🚀 Simulación"
- "🛸 Rocket Settings" → "✈️ Configuración del Cohete"
- "📍 Location" → "📍 Ubicación"
- "💨 Wind" → "💨 Viento"
- "🌪️ Wind Scenarios" → "🌪️ Escenarios de Viento"
- "🪂 Parachute" → "🪂 Paracaídas"
- "📈 Monte Carlo" → "📈 Monte Carlo"
- "📊 Dashboard" → "📊 Tablero"
- "⚖️ Units" → "⚖️ Unidades"

#### Simulation Widget (100% complete)
- All group box titles
- All parameter labels (Runtime, Time Step, Date, Time, Timezone, Temperature, Pressure, Elevation, etc.)
- All launch parameters (Launch Angle, Launch Azimuth, Launch Roll)
- All buttons (Run Simulation, Pause, Stop, Reset)
- All status messages
- Progress bar labels

#### Other Widgets (100% complete)
- Rocket Settings: All labels and parameters
- Location Settings: Latitude, Longitude, Launch Site, Use Current Location, Select from Map
- Wind Settings: Wind Model, Wind Speed, Wind Direction, Turbulence
- Parachute Settings: Parachute Type, Deployment Altitude, Cd, Enable Parachute
- Monte Carlo: Number of Runs, Variable Parameters, Run Monte Carlo, Stop, Results
- Dashboard: Simulation History, Load Simulation History, No simulations found, View Details, Delete
- Units Converter: Convert, From, To, Value, Result
- Wind Scenario Editor: Scenario Name, Save Scenario, Delete Scenario, Load Scenario

#### Language Names (100% complete)
- English → Inglés
- Spanish → Español
- French → Francés
- German → Alemán
- Portuguese → Portugués
- Russian → Ruso
- Chinese → Chino
- Japanese → Japonés

## Usage

### For Users

To use Spanish translations in the application:

1. Run the application
2. Go to the "Language" menu
3. Select "Español"
4. The UI will switch to Spanish

### For Developers

#### Adding New Translations

1. Edit `rocket_simulator_es.ts` and add new `<message>` entries
2. Add corresponding entries to `FALLBACK_TRANSLATIONS` in `src/config/translations.py`
3. (Optional) Compile to .qm using `lrelease` or the provided script

#### Compiling Translation Files

To compile the .ts file to .qm:

```bash
# Using Qt's lrelease
lrelease data/translations/rocket_simulator_es.ts -qm data/translations/rocket_simulator_es.qm

# Using the provided script
python scripts/compile_translations.py

# Force recompilation
python scripts/compile_translations.py --force
```

## Testing

Test the Spanish translation:

```python
from src.config.translations import TranslationManager, tr

# Set Spanish as current language
TranslationManager._current_language = 'es'

# Test translation
print(tr("Rocket Simulator Pro"))  # Should output: "Simulador de Cohetes Pro"
print(tr("Simulation Parameters"))  # Should output: "Parámetros de Simulación"
print(tr("Run Simulation"))  # Should output: "Ejecutar Simulación"
```

## Translation Style Guide

### General Rules

1. **Consistency**: Use consistent terminology throughout
2. **Naturalness**: Translations should sound natural in Spanish
3. **Technical Terms**: Keep technical terms consistent with industry standards
4. **Length**: Try to keep translations similar in length to the source text

### Specific Decisions

- "Simulation" → "Simulación" (not "Simulacion" without accent)
- "Rocket" → "Cohete" (more commonly used than "Fusée" or "Misil")
- "Parameters" → "Parámetros"
- "Control" → "Control" (same word in Spanish)
- "Launch" → "Lanzamiento"
- "Run" (verb) → "Ejecutar"
- "Stop" → "Detener"
- "Pause" → "Pausar"
- "Reset" → "Reiniciar"

### Units and Symbols

- Units (m, s, kg, etc.) remain unchanged
- Emoji remain unchanged
- Symbols (°, %, etc.) remain unchanged

## Missing Translations

The following strings are NOT yet translated (as they may be dynamically generated or from third-party libraries):

- Error messages from simulation engine
- Mathematical/physical constants
- Some technical terms from aerodynamics calculations

These should be added as needed when identified.

## Contributing

To contribute improvements to the Spanish translation:

1. Fork the repository
2. Edit `data/translations/rocket_simulator_es.ts`
3. Update `FALLBACK_TRANSLATIONS` in `src/config/translations.py`
4. Submit a pull request

## License

Translation files are licensed under the same license as the main project (MIT License).
