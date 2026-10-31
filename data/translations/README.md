# Rocket Simulator Pro - Translations

This directory contains translation files for the Rocket Simulator Pro application.

## Translation Files

- `rocket_simulator_es.ts` - Spanish translation (source file)
- `rocket_simulator_es.qm` - Spanish translation (compiled binary, generated)

## Adding New Translations

### 1. Create a New .ts File

Create a new translation source file named `rocket_simulator_<lang>.ts` where `<lang>` is the ISO 639-1 language code (e.g., `fr` for French, `de` for German).

Example structure:
```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="fr_FR">
<context>
    <name>RocketSimulator</name>
    <message>
        <source>Rocket Simulator Pro</source>
        <translation>Simulateur de Fusée Pro</translation>
    </message>
    <!-- Add more translations here -->
</context>
</TS>
```

### 2. Add Language to SUPPORTED_LANGUAGES

In `src/config/translations.py`, add your language to the `SUPPORTED_LANGUAGES` dictionary:

```python
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',  # Add your language here
    # ...
}
```

### 3. Add Fallback Translations (Optional)

For development purposes, you can add translations to the `FALLBACK_TRANSLATIONS` dictionary in `src/config/translations.py`:

```python
FALLBACK_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'es': {
        'Rocket Simulator Pro': 'Simulador de Cohetes Pro',
        # ...
    },
    'fr': {
        'Rocket Simulator Pro': 'Simulateur de Fusée Pro',
        # ...
    }
}
```

## Compiling Translation Files

### Method 1: Using Qt's lrelease Tool

If you have Qt installed with command-line tools:

```bash
# Navigate to the translations directory
cd data/translations

# Compile Spanish translation
lrelease rocket_simulator_es.ts -qm rocket_simulator_es.qm

# Compile all translations
lrelease *.ts -qm *.qm
```

### Method 2: Using PyQt6 Tools

If you have PyQt6-tools installed:

```bash
python -m PyQt6.pylrelease6 rocket_simulator_es.ts -o rocket_simulator_es.qm
```

### Method 3: Using the Compilation Script

Run the provided compilation script:

```bash
# Compile all translation files
python scripts/compile_translations.py

# Force recompilation (even if .qm files exist)
python scripts/compile_translations.py --force
```

The script will:
1. Look for `lrelease` in common Qt installation locations
2. Try PyQt6's `pylrelease6`
3. Compile all `.ts` files to `.qm` files
4. Report any errors

## Translation Workflow

1. **Extract strings**: Use Qt Linguist or `pylupdate6` to extract strings from source files
2. **Translate**: Edit the `.ts` files with translations
3. **Compile**: Run `lrelease` or the compilation script to generate `.qm` files
4. **Test**: Run the application and verify translations

## Currently Translated Strings

The following UI elements are translated for Spanish:

### Main Window
- Window title
- All menu items (File, Edit, View, Language, Help)
- All menu actions (New Simulation, Open, Save, Exit, etc.)
- All tab names

### Simulation Widget
- All group box titles
- All parameter labels
- All button texts
- All status messages

### Other Widgets
- Rocket Settings
- Location Settings
- Wind Settings
- Parachute Settings
- Monte Carlo
- Dashboard
- Units Converter
- Wind Scenario Editor

## Language Support

Currently supported languages:
- English (en) - Default
- Spanish (es) - Complete
- French (fr) - Not yet translated
- German (de) - Not yet translated
- Portuguese (pt) - Not yet translated
- Russian (ru) - Not yet translated
- Chinese (zh) - Not yet translated
- Japanese (ja) - Not yet translated

## Notes

- `.ts` files are human-readable XML files that can be edited with Qt Linguist or any text editor
- `.qm` files are binary files that are loaded by Qt at runtime for better performance
- The application will fall back to the `FALLBACK_TRANSLATIONS` dictionary if `.qm` files are not available
- For production, always compile `.ts` files to `.qm` files
