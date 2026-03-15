#!/usr/bin/env python3
"""Test script for enhanced rocket settings widget."""

import sys
import json
import os
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_widget_import():
    """Test that the widget imports correctly."""
    print("\n" + "="*60)
    print("TEST 1: Widget Import")
    print("="*60)
    
    try:
        from ui.widgets.rocket_settings_widget import RocketSettingsWidget
        print("✅ RocketSettingsWidget imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_json_loading():
    """Test loading rocket JSON files."""
    print("\n" + "="*60)
    print("TEST 2: JSON File Loading")
    print("="*60)
    
    configs_path = 'data/rockets/configs'
    if not os.path.exists(configs_path):
        print(f"⚠️  Config path doesn't exist: {configs_path}")
        return False
    
    json_files = [f for f in os.listdir(configs_path) if f.endswith('.json')]
    print(f"Found {len(json_files)} JSON files:")
    
    for filename in json_files:
        try:
            filepath = os.path.join(configs_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check required fields
            required_fields = ['name', 'initial_mass', 'reference_area']
            missing = [f for f in required_fields if f not in data]
            
            if missing:
                print(f"⚠️  {filename}: Missing fields {missing}")
            else:
                print(f"✅ {filename}: All required fields present")
                # Show structure
                print(f"   Sections: {', '.join(data.keys())}")
        except json.JSONDecodeError as e:
            print(f"❌ {filename}: Invalid JSON - {e}")
        except Exception as e:
            print(f"❌ {filename}: Error - {e}")
    
    return True

def test_data_schema():
    """Test that JSON data matches expected schema."""
    print("\n" + "="*60)
    print("TEST 3: Data Schema Validation")
    print("="*60)
    
    configs_path = 'data/rockets/configs'
    
    # Expected schema structure
    schema = {
        'name': str,
        'initial_mass': (int, float),
        'reference_area': (int, float),
        'I_before_burn': dict,
        'CoM_before_burn': dict,
        'I_after_burn': dict,
        'CoM_after_burn': dict,
        'engine': dict,
        'geometry': dict,
        'fuselage': dict,
        'rear_section': dict,
        'nosecone': dict,
        'fins': dict,
    }
    
    test_file = os.path.join(configs_path, 'agni-1.json')
    
    if not os.path.exists(test_file):
        print(f"⚠️  Test file not found: {test_file}")
        return False
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        missing_fields = []
        for field, expected_type in schema.items():
            if field not in data:
                missing_fields.append(field)
            else:
                value = data[field]
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        print(f"⚠️  Wrong type for '{field}': expected {expected_type}, got {type(value)}")
                else:
                    if not isinstance(value, expected_type):
                        print(f"⚠️  Wrong type for '{field}': expected {expected_type}, got {type(value)}")
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        else:
            print("✅ All required fields present in schema")
            
            # Count total parameters
            param_count = sum(len(v) if isinstance(v, dict) else 1 for v in data.values())
            print(f"✅ Total parameters across all sections: {param_count}")
            return True
            
    except Exception as e:
        print(f"❌ Error validating schema: {e}")
        return False

def test_widget_ui_creation():
    """Test that widget can create tabs without errors."""
    print("\n" + "="*60)
    print("TEST 4: Widget UI Tab Creation")
    print("="*60)
    
    from PyQt6.QtWidgets import QApplication
    
    # Create a QApplication (required for PyQt6)
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    try:
        from ui.widgets.rocket_settings_widget import RocketSettingsWidget
        
        # Create widget
        widget = RocketSettingsWidget()
        
        # Check tabs
        tab_count = widget.tabs.count()
        print(f"✅ Widget created with {tab_count} tabs")
        
        # List tabs
        for i in range(tab_count):
            tab_name = widget.tabs.tabText(i)
            print(f"   Tab {i+1}: {tab_name}")
        
        # Check critical UI elements
        critical_elements = [
            ('name_edit', 'Rocket name input'),
            ('tabs', 'Tab widget'),
            ('initial_mass_spinbox', 'Initial mass input'),
            ('fin_type', 'Fin type selector'),
            ('nosecone_type', 'Nosecone type selector'),
        ]
        
        missing_elements = []
        for attr, desc in critical_elements:
            if not hasattr(widget, attr):
                missing_elements.append(f"{attr} ({desc})")
        
        if missing_elements:
            print(f"❌ Missing UI elements: {missing_elements}")
            return False
        else:
            print("✅ All critical UI elements present")
            return True
            
    except Exception as e:
        print(f"❌ Error creating widget: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("ROCKET SETTINGS WIDGET - COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    tests = [
        ("Widget Import", test_widget_import),
        ("JSON Loading", test_json_loading),
        ("Data Schema", test_data_schema),
        ("Widget UI", test_widget_ui_creation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
