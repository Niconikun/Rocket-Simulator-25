"""Contract tests for the pyqt-gui branch (review Gate 2).

These tests are AST/source based so they run without PyQt6/numpy, and they
pin the contracts between:

- raw state-key strings used via ``state.get('...')`` / ``state.set('...')``
  and ``Constants.StateKeys`` (src/config/constants.py),
- ``EventType`` members referenced across the repo and the members actually
  defined in src/utils/event_bus.py, plus publish/subscribe pairing,
- the SimulationWorker <-> SimulationWidget <-> MainWindow signal wiring.

A PyQt6-dependent runtime smoke is included but skipped when PyQt6 is not
installed.
"""

import ast
import importlib.util
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_ROOTS = ('workers', 'src', 'ui', 'models', 'main.py')

# Raw state keys used via state.get/set that are intentional legacy fallbacks
# and are NOT (yet) declared in Constants.StateKeys. New raw keys fail the
# contract test until they are either added to StateKeys or listed here.
KNOWN_RAW_STATE_KEYS = frozenset({
    'base_wind_model',          # wind_utils legacy fallback
    'config_validation_report', # worker diagnostic write
    'launch_altitude',          # wind_utils legacy fallback
    'model_type',               # wind_utils legacy fallback
    'random_seed',              # wind_utils legacy fallback
    'vertical_wind_speed',      # wind_utils legacy fallback
})

# Events that must have at least one subscriber somewhere in the app code.
CRITICAL_SUBSCRIBED_EVENTS = frozenset({
    'SIMULATION_STARTED',
    'SIMULATION_COMPLETED',
    'SIMULATION_ERROR',
    'TAB_CHANGED',
    'ROCKET_SELECTED',
    'LOCATION_CHANGED',
    'WIND_SETTINGS_CHANGED',
})


def iter_py_files():
    for root in SCAN_ROOTS:
        path = os.path.join(REPO_ROOT, root)
        if os.path.isfile(path):
            yield path
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            if '.git' in dirpath:
                continue
            for name in filenames:
                if name.endswith('.py'):
                    yield os.path.join(dirpath, name)


def parse(path):
    with open(path, encoding='utf-8') as f:
        return ast.parse(f.read())


def load_constants_module():
    """Load src/config/constants.py directly, bypassing src.config.__init__
    (which pulls in PyQt6 via translations)."""
    path = os.path.join(REPO_ROOT, 'src', 'config', 'constants.py')
    spec = importlib.util.spec_from_file_location('rs_constants', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def state_key_constants():
    module = load_constants_module()
    return {v for v in vars(module.StateKeyConstants).values() if isinstance(v, str)}


def event_type_members():
    """Return the member names of the EventType enum from event_bus.py."""
    tree = parse(os.path.join(REPO_ROOT, 'src', 'utils', 'event_bus.py'))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'EventType':
            return {
                stmt.targets[0].id
                for stmt in node.body
                if isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name)
            }
    raise AssertionError('EventType enum not found in event_bus.py')


def raw_state_keys():
    """Collect string literals passed to state-ish .get/.set calls."""
    keys = set()
    for path in iter_py_files():
        for node in ast.walk(parse(path)):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ('get', 'set') and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                receiver = ast.unparse(node.func.value)
                if 'state' in receiver:
                    keys.add(node.args[0].value)
    return keys


def referenced_statekeys_attrs():
    used = set()
    for path in iter_py_files():
        for node in ast.walk(parse(path)):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Attribute)
                    and node.value.attr == 'StateKeys'
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == 'Constants'):
                used.add(node.attr)
    return used


def event_type_references():
    """Return (referenced_names, published, subscribed) sets of EventType members."""
    referenced, published, subscribed = set(), set(), set()
    for path in iter_py_files():
        tree = parse(path)
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == 'EventType'):
                continue
            referenced.add(node.attr)
            call = parents.get(node)
            if isinstance(call, ast.Call):
                func_name = ast.unparse(call.func)
                if func_name.endswith('publish'):
                    published.add(node.attr)
                elif func_name.endswith('subscribe'):
                    subscribed.add(node.attr)
    return referenced, published, subscribed


def class_def(path, class_name):
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f'{class_name} not found in {path}')


class TestStateKeyContract(unittest.TestCase):
    def test_raw_state_keys_are_declared_or_known(self):
        unknown = raw_state_keys() - state_key_constants() - KNOWN_RAW_STATE_KEYS
        self.assertEqual(unknown, set(),
                         f'raw state keys missing from Constants.StateKeys: {sorted(unknown)}')

    def test_statekeys_attributes_exist(self):
        module = load_constants_module()
        defined = {n for n in dir(module.StateKeyConstants) if not n.startswith('_')}
        missing = referenced_statekeys_attrs() - defined
        self.assertEqual(missing, set(),
                         f'Constants.StateKeys attributes used but not defined: {sorted(missing)}')


class TestEventBusContract(unittest.TestCase):
    def test_referenced_event_types_are_defined(self):
        referenced, _, _ = event_type_references()
        missing = referenced - event_type_members()
        self.assertEqual(missing, set(),
                         f'EventType members referenced but not defined: {sorted(missing)}')

    def test_critical_events_have_subscribers(self):
        _, _, subscribed = event_type_references()
        missing = CRITICAL_SUBSCRIBED_EVENTS - subscribed
        self.assertEqual(missing, set(),
                         f'critical events with no subscriber: {sorted(missing)}')

    def test_rocket_config_changed_has_subscriber(self):
        # ROCKET_CONFIG_CHANGED is published by rocket_settings_widget on save;
        # MainWindow subscribes and invalidates the SimulationCache rocket
        # config entries so the next run does not use a stale cached config.
        _, _, subscribed = event_type_references()
        self.assertIn('ROCKET_CONFIG_CHANGED', subscribed)


class TestWorkerWidgetWiring(unittest.TestCase):
    def setUp(self):
        self.worker_src = os.path.join(REPO_ROOT, 'workers', 'simulation_worker.py')
        self.widget_src = os.path.join(REPO_ROOT, 'ui', 'widgets', 'simulation_widget.py')
        self.main_src = os.path.join(REPO_ROOT, 'ui', 'main_window.py')

    def test_worker_defines_signals_and_controls(self):
        cls = class_def(self.worker_src, 'SimulationWorker')
        assigned = {stmt.targets[0].id for stmt in cls.body
                    if isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name)}
        methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
        for signal in ('progress', 'finished', 'error'):
            self.assertIn(signal, assigned, f'SimulationWorker missing signal {signal}')
        for method in ('run', 'run_with_params', 'pause', 'resume', 'stop'):
            self.assertIn(method, methods, f'SimulationWorker missing method {method}')

    def test_simulation_widget_connects_worker_signals(self):
        tree = parse(self.widget_src)
        connected, called = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                if attr == 'connect':
                    target = ast.unparse(node.func.value)
                    if 'simulation_worker' in target:
                        connected.add(target.rsplit('.', 1)[-1])
                if isinstance(node.func.value, ast.Attribute) and 'simulation_worker' in ast.unparse(node.func.value):
                    called.add(attr)
        for signal in ('progress', 'finished', 'error'):
            self.assertIn(signal, connected, f'SimulationWidget does not connect worker.{signal}')
        for method in ('pause', 'resume', 'stop', 'isRunning', 'start'):
            self.assertIn(method, called, f'SimulationWidget never calls worker.{method}()')

    def test_main_window_connects_widget_signals(self):
        with open(self.main_src, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('simulation_widget.simulation_saved.connect', src)
        self.assertIn('simulation_widget.status_message.connect', src)


class TestWorkerRuntime(unittest.TestCase):
    def setUp(self):
        if importlib.util.find_spec('PyQt6') is None or importlib.util.find_spec('numpy') is None:
            self.skipTest('PyQt6/numpy not installed in this environment')

    def test_worker_instantiation_signals_and_controls(self):
        from workers.simulation_worker import SimulationWorker
        from src.models.state import MockStateProvider

        worker = SimulationWorker(MockStateProvider({'selected_rocket': 'agni-1'}), use_cache=False)
        for signal in ('progress', 'finished', 'error'):
            self.assertTrue(hasattr(SimulationWorker, signal))
        self.assertTrue(worker.is_running)
        worker.pause()
        self.assertTrue(worker.is_paused)
        worker.resume()
        self.assertFalse(worker.is_paused)
        worker.stop()
        self.assertFalse(worker.is_running)


if __name__ == '__main__':
    unittest.main()
