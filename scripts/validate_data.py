import json
import os
from jsonschema import validate, ValidationError

def load_schema(schema_name):
    """Carga un esquema JSON"""
    schema_path = os.path.join('data', 'schemas', f'{schema_name}.schema.json')
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_rocket_config(config_file):
    """Valida un archivo de configuración de cohete"""
    try:
        # Cargar esquema y datos
        schema = load_schema('rocket')
        with open(config_file, 'r', encoding='utf-8') as f:
            rocket_data = json.load(f)
        
        # Validar
        validate(instance=rocket_data, schema=schema)
        print(f"✅ Archivo válido: {os.path.basename(config_file)}")
        return True
    except ValidationError as e:
        print(f"❌ Error en {os.path.basename(config_file)}:")
        print(f"   {e.message}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado en {os.path.basename(config_file)}:")
        print(f"   {str(e)}")
        return False

def validate_all_rockets():
    """Valida todos los archivos de configuración de cohetes"""
    configs_dir = os.path.join('data', 'rockets', 'configs')
    valid_count = 0
    total_count = 0
    
    for filename in os.listdir(configs_dir):
        if filename.endswith('.json'):
            total_count += 1
            if validate_rocket_config(os.path.join(configs_dir, filename)):
                valid_count += 1
    
    print(f"\nResumen: {valid_count}/{total_count} archivos válidos")

def validate_file(file_path, schema_name):
    """Valida un archivo contra un esquema dado"""
    try:
        # Cargar esquema y datos
        schema = load_schema(schema_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validar
        validate(instance=data, schema=schema)
        print(f"✅ Archivo válido: {os.path.basename(file_path)}")
        return True
    except ValidationError as e:
        print(f"❌ Error en {os.path.basename(file_path)}:")
        print(f"   {e.message}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado en {os.path.basename(file_path)}:")
        print(f"   {str(e)}")
        return False

def validate_all_data():
    """Valida todos los archivos de configuración"""
    print("Validando configuraciones de cohetes...")
    validate_all_rockets()
    
    print("\nValidando configuraciones de paracaídas...")
    validate_file('rockets/parachutes/chutes.json', 'parachute')
    
    print("\nValidando sitios de lanzamiento...")
    validate_file('locations/launch_sites.json', 'launch_sites')

if __name__ == '__main__':
    validate_all_data()