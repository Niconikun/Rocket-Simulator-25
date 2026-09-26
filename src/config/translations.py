"""
Internationalization (i18n) Support for Rocket Simulator Pro

Provides translation support using Qt's QTranslator for UI strings.

Usage:
    from src.config.translations import TranslationManager, tr
    
    # In widget initialization
    TranslationManager.load_translation('es')  # Load Spanish
    
    # For translatable strings
    label = QLabel(tr("Simulation Parameters"))
    button = QPushButton(tr("Run Simulation"))
"""

from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo, QCoreApplication
from typing import Optional, Dict, Any
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Español',
}


# Fallback translation dictionaries for when .qm files are not available
# These are used if Qt translation files cannot be loaded
FALLBACK_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'es': {
        # Main Window
        'Rocket Simulator Pro': 'Simulador de Cohetes Pro',
        '🚀 Simulation': '🚀 Simulación',
        '🛸 Rocket Settings': '✈️ Configuración del Cohete',
        '📍 Location': '📍 Ubicación',
        '💨 Wind': '💨 Viento',
        '🌪️ Wind Scenarios': '🌪️ Escenarios de Viento',
        '🪂 Parachute': '🪂 Paracaídas',
        '📈 Monte Carlo': '📈 Monte Carlo',
        '📊 Dashboard': '📊 Tablero',
        '⚖️ Units': '⚖️ Unidades',
        'File': 'Archivo',
        'New Simulation': 'Nueva Simulación',
        'Open Configuration...': 'Abrir Configuración...',
        'Save Configuration...': 'Guardar Configuración...',
        'Exit': 'Salir',
        'Edit': 'Editar',
        'Reset to Defaults': 'Restablecer a Predeterminados',
        'View': 'Ver',
        'Dark Mode': 'Modo Oscuro',
        'Language': 'Idioma',
        'Help': 'Ayuda',
        'About': 'Acerca de',
        'Ready': 'Listo',
        
        # Simulation Widget
        'Simulation Parameters': 'Parámetros de Simulación',
        'Simulation Runtime:': 'Tiempo de Ejecución:',
        ' seconds': ' segundos',
        'Time Step:': 'Paso de Tiempo:',
        ' s': ' s',
        'Launch Date & Time': 'Fecha y Hora de Lanzamiento',
        'Date:': 'Fecha:',
        'Time:': 'Hora:',
        'Timezone:': 'Zona Horaria:',
        'Environmental Conditions': 'Condiciones Ambientales',
        'Temperature:': 'Temperatura:',
        ' °C': ' °C',
        'Pressure:': 'Presión:',
        ' Pa': ' Pa',
        'Elevation:': 'Altitud:',
        ' m': ' m',
        'Launch Parameters': 'Parámetros de Lanzamiento',
        'Launch Angle:': 'Ángulo de Lanzamiento:',
        ' °': ' °',
        'Launch Azimuth:': 'Acimut de Lanzamiento:',
        'Launch Roll:': 'Rol de Lanzamiento:',
        'Simulation Control': 'Control de Simulación',
        'Progress:': 'Progreso:',
        '▶️ Run Simulation': '▶️ Ejecutar Simulación',
        'Run Simulation': 'Ejecutar Simulación',
        '⏸️ Pause': '⏸️ Pausar',
        'Pause': 'Pausar',
        '⏹️ Stop': '⏹️ Detener',
        'Stop': 'Detener',
        '🔄 Reset': '🔄 Reiniciar',
        'Reset': 'Reiniciar',
        
        # Messages
        'Starting simulation...': 'Iniciando simulación...',
        'Simulation Running': 'Simulación en Ejecución',
        'A simulation is already running.': 'Ya hay una simulación en ejecución.',
        'Simulation started': 'Simulación iniciada',
        'Simulation completed successfully!': '¡Simulación completada con éxito!',
        'Results saved with ID:': 'Resultados guardados con ID:',
        'You can view them in the Dashboard.': 'Puede verlos en el Tablero.',
        'Simulation completed but failed to save results:': 'Simulación completada pero falló al guardar los resultados:',
        'Simulation Error': 'Error de Simulación',
        'Error: ': 'Error: ',
        'Simulation resumed': 'Simulación reanudada',
        'Simulation paused': 'Simulación pausada',
        'Stopping simulation': 'Deteniendo simulación',
        'Simulation finished': 'Simulación finalizada',
        

        
        # Other widgets
        'Simulation History': 'Historial de Simulaciones',
        'Load Simulation History': 'Cargar Historial de Simulaciones',
        'No simulations found': 'No se encontraron simulaciones',
        'View Details': 'Ver Detalles',
        'Delete': 'Eliminar',
        'Rocket Settings': 'Configuración del Cohete',
        'Basic Parameters': 'Parámetros Básicos',
        'Rocket Name:': 'Nombre del Cohete:',
        'Diameter:': 'Diámetro:',
        'Length:': 'Longitud:',
        'Mass:': 'Masa:',
        ' CG': ' Centro de Gravedad',
        'Inertia:': 'Inercia:',
        'Motor Configuration': 'Configuración del Motor',
        'Motor:': 'Motor:',
        'Thrust Curve:': 'Curva de Empuje:',
        'Aerodynamics': 'Aerodinámica',
        'Cd:': 'Coeficiente de Arrastre (Cd):',
        'CP:': 'Centro de Presión (CP):',
        'Location Settings': 'Configuración de Ubicación',
        'Latitude:': 'Latitud:',
        'Longitude:': 'Longitud:',
        'Launch Site:': 'Sitio de Lanzamiento:',
        'Use Current Location': 'Usar Ubicación Actual',
        'Select from Map': 'Seleccionar del Mapa',
        'Monte Carlo Analysis': 'Análisis de Monte Carlo',
        'Number of Runs:': 'Número de Ejecuciones:',
        'Variable Parameters': 'Parámetros Variables',
        'Run Monte Carlo': 'Ejecutar Monte Carlo',
        'Stop': 'Detener',
        'Results': 'Resultados',
        'Wind Settings': 'Configuración de Viento',
        'Wind Model:': 'Modelo de Viento:',
        'Constant Wind': 'Viento Constante',
        'Wind Gradient': 'Gradiente de Viento',
        'Wind Speed:': 'Velocidad del Viento:',
        'm/s': 'm/s',
        'Wind Direction:': 'Dirección del Viento:',
        'degrees': 'grados',
        'Turbulence:': 'Turbulencia:',
        'Parachute Settings': 'Configuración de Paracaídas',
        'Parachute Type:': 'Tipo de Paracaídas:',
        'Drogue': 'Frenado',
        'Main': 'Principal',
        'Deployment Altitude:': 'Altitud de Despliegue:',
        'Enable Parachute': 'Activar Paracaídas',
        'Units Converter': 'Convertidor de Unidades',
        'Convert': 'Convertir',
        'From:': 'De:',
        'To:': 'A:',
        'Value:': 'Valor:',
        'Result:': 'Resultado:',
        'Wind Scenario Editor': 'Editor de Escenarios de Viento',
        'Scenario Name:': 'Nombre del Escenario:',
        'Save Scenario': 'Guardar Escenario',
        'Delete Scenario': 'Eliminar Escenario',
        'Load Scenario': 'Cargar Escenario',
        'Wind scenario applied: ': 'Escenario de viento aplicado: ',
    }
}


class TranslationManager:
    """
    Manages translations for the application using Qt's QTranslator.
    
    This class provides:
    - Loading translations from .qm files
    - Installing translators for the application
    - Fallback to English if translation not found
    
    Translation files should be named: rocket_simulator_<lang>.qm
    and placed in the data/translations/ directory.
    """
    
    _translators: Dict[str, QTranslator] = {}
    _current_language: str = 'en'
    _app = None  # Reference to QApplication instance
    
    @classmethod
    def initialize(cls, app) -> None:
        """
        Initialize the translation manager with the QApplication instance.
        
        Args:
            app: The QApplication instance
        """
        cls._app = app
        # Load Qt's built-in translations
        cls._load_qt_translations()
    
    @classmethod
    def _load_qt_translations(cls) -> None:
        """Load Qt's built-in translations for the current locale."""
        if cls._app is None:
            return
        
        locale = QLocale.system()
        qt_translator = QTranslator()
        
        # Try to load Qt translations for common modules
        translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if qt_translator.load(locale, 'qt', '_', translations_path):
            cls._app.installTranslator(qt_translator)
            cls._translators['qt'] = qt_translator
            logger.info(f"Loaded Qt translations for locale: {locale.name()}")
    
    @classmethod
    def load_translation(cls, language_code: str) -> bool:
        """
        Load a translation file for the specified language.
        
        Args:
            language_code: ISO 639-1 language code (e.g., 'en', 'es', 'fr')
        
        Returns:
            True if translation was loaded successfully, False otherwise
        """
        if cls._app is None:
            logger.warning("TranslationManager not initialized. Call initialize() first.")
            return False
        
        # Remove previous application translator if exists
        if 'app' in cls._translators:
            cls._app.removeTranslator(cls._translators['app'])
            del cls._translators['app']
        
        # Don't load for English (default)
        if language_code == 'en':
            cls._current_language = 'en'
            logger.info("Using default language: English")
            return True
        
        # Try to load the translation file
        translator = QTranslator()
        translations_dir = 'data/translations'
        
        # Try different file naming conventions
        filenames = [
            f'rocket_simulator_{language_code}.qm',
            f'rocket_simulator_{language_code}.qm',
        ]
        
        loaded = False
        for filename in filenames:
            filepath = f'{translations_dir}/{filename}'
            try:
                if os.path.exists(filepath) and translator.load(filepath):
                    cls._app.installTranslator(translator)
                    cls._translators['app'] = translator
                    cls._current_language = language_code
                    loaded = True
                    logger.info(f"Loaded translation: {filepath}")
                    break
            except Exception as e:
                logger.debug(f"Failed to load {filepath}: {e}")
        
        # If .qm file not found but .ts file exists, log it
        if not loaded:
            ts_filename = f'rocket_simulator_{language_code}.ts'
            ts_filepath = f'{translations_dir}/{ts_filename}'
            
            if os.path.exists(ts_filepath):
                logger.info(
                    f"Translation .ts file found but .qm not available: {ts_filepath}\n"
                    f"To compile: Run 'python scripts/compile_translations.py'\n"
                    f"Fallback dictionary translations will be used for Spanish"
                )
        
        # Log status
        if not loaded:
            logger.warning(f"Translation file not found for language: {language_code}")
            # Set current language anyway so fallback translations work
            cls._current_language = language_code
        
        return loaded
    
    @classmethod
    def get_current_language(cls) -> str:
        """Get the current language code."""
        return cls._current_language
    
    @classmethod
    def get_supported_languages(cls) -> Dict[str, str]:
        """Get dictionary of supported languages (code -> name)."""
        return SUPPORTED_LANGUAGES.copy()


# Convenience function for translating strings
def tr(text: str, context: Optional[str] = None) -> str:
    """
    Translate a string using Qt's translation system with fallback support.
    
    This function wraps QCoreApplication.translate() for convenience.
    If Qt translation system is not available or no translation is found,
    it falls back to the FALLBACK_TRANSLATIONS dictionary.
    
    Args:
        text: The text to translate
        context: Optional context for disambiguation (usually class name)
    
    Returns:
        The translated string, or the original if no translation found
    
    Usage:
        label = QLabel(tr("Simulation Parameters"))
        button = QPushButton(tr("Run"))
    """
    from PyQt6.QtCore import QCoreApplication
    
    # Try Qt's translation system first
    if QCoreApplication.instance():
        translated = QCoreApplication.translate(context or 'RocketSimulator', text)
        # If translation worked and returned something different, use it
        if translated != text:
            return translated
    
    # Fallback to dictionary-based translations
    current_lang = TranslationManager.get_current_language()
    if current_lang in FALLBACK_TRANSLATIONS:
        translations = FALLBACK_TRANSLATIONS[current_lang]
        if text in translations:
            return translations[text]
    
    # Return original text if no translation found
    return text


# Lazy translation function for UI strings defined at class level
# This allows strings to be translated when the UI is created, not when the module is loaded
def tr_lazy(text: str, context: Optional[str] = None) -> str:
    """
    Lazy translation function that returns a translation function.
    
    This is useful for strings that are defined at class level but need to be
    translated when the UI is actually created.
    
    Args:
        text: The text to translate
        context: Optional context for disambiguation
    
    Returns:
        A callable that returns the translated string when called
    
    Usage:
        TITLE = tr_lazy("Simulation Parameters")
        
        def __init__(self):
            self.setWindowTitle(TITLE())
    """
    def translate() -> str:
        return tr(text, context)
    return translate
