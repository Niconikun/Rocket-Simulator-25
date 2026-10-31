# Internationalization (i18n) Guide

## Overview

Rocket Simulator Pro supports multiple languages through Qt's built-in translation system. This guide explains how to add translations for new languages.

## Architecture

The translation system uses:
- **Qt's QTranslator**: Standard Qt translation mechanism
- **TranslationManager**: Centralized manager in `src/config/translations.py`
- **tr() function**: Convenience function for translating strings

## Adding a New Language

### Step 1: Create Translation Source File

1. Use Qt's `lupdate` tool to extract translatable strings from Python files:
   ```bash
   lupdate -noobsolete ui/ -ts data/translations/rocket_simulator_es.ts
   ```

2. This creates a `.ts` file (XML format) with all translatable strings.

### Step 2: Translate Strings

Open the `.ts` file with Qt Linguist or any text editor and add translations:

```xml
<context>
    <name>RocketSimulator</name>
    <message>
        <source>Simulation Parameters</source>
        <translation>Parámetros de Simulación</translation>
    </message>
</context>
```

### Step 3: Compile Translation File

Compile the `.ts` file to a `.qm` file (binary format):
```bash
lrelease data/translations/rocket_simulator_es.ts -qm data/translations/rocket_simulator_es.qm
```

### Step 4: Add Language to Supported List

Update `SUPPORTED_LANGUAGES` in `src/config/translations.py`:

```python
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',  # Add your language here
    # ...
}
```

### Step 5: Test the Translation

Run the application and select your language from the Language menu.

## Using Translations in Code

### Method 1: Using tr() function

```python
from src.config import tr

label = QLabel(tr("Simulation Parameters"))
button = QPushButton(tr("Run Simulation"))
```

### Method 2: Using BaseWidget.tr()

```python
from ui.widgets import BaseWidget

class MyWidget(BaseWidget):
    def __init__(self, state=None, parent=None):
        super().__init__(state=state, parent=parent)
        label = QLabel(self.tr("Simulation Parameters"))
```

### Method 3: For Static Strings

For strings defined at class level, use `tr_lazy()`:

```python
from src.config import tr_lazy

TITLE = tr_lazy("Simulation Parameters")

class MyWidget(BaseWidget):
    def __init__(self):
        self.setWindowTitle(TITLE())
```

## Translating Widgets

To translate an existing widget:

1. Import the translation function:
   ```python
   from src.config import tr
   ```

2. Wrap all user-facing strings with `tr()`:
   ```python
   # Before
   group = QGroupBox("Simulation Parameters")
   
   # After
   group = QGroupBox(tr("Simulation Parameters"))
   ```

3. For strings with context (to disambiguate identical strings):
   ```python
   # "Run" as a verb (button) vs "Run" as a noun (simulation run)
   button = QPushButton(tr("Run"))  # Context inferred from class
   label = QLabel(tr("Run", context="SimulationRun"))
   ```

## Best Practices

1. **Always use tr()** for any string that might be shown to users
2. **Avoid concatenating translated strings** - translate the complete sentence:
   ```python
   # Bad
   message = tr("Error:") + " " + error_msg
   
   # Good
   message = tr("Error: {0}").format(error_msg)
   ```
3. **Use context** when the same word has different meanings
4. **Test with all languages** before releasing
5. **Keep translations up to date** when adding new UI elements

## File Locations

- Translation source files: `data/translations/*.ts`
- Compiled translations: `data/translations/*.qm`
- Translation manager: `src/config/translations.py`
- Language menu: `ui/main_window.py`

## Tools

- **Qt Linguist**: GUI tool for translating `.ts` files
- **lupdate**: Extracts strings from source code to `.ts` files
- **lrelease**: Compiles `.ts` files to `.qm` files

## Supported Languages

Currently supported languages (in `SUPPORTED_LANGUAGES`):
- English (en) - default
- Spanish (es)
- French (fr)
- German (de)
- Portuguese (pt)
- Russian (ru)
- Chinese (zh)
- Japanese (ja)

To add support for a new language, follow the steps above and add it to the `SUPPORTED_LANGUAGES` dictionary.
