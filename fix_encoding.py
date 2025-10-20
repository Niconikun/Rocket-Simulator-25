import json
import os

def fix_json_encoding():
    """Fix encoding issues in JSON files"""
    try:
        # Read the file with different encodings to find the right one
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open('data/locations/launch_sites.json', 'r', encoding=encoding) as f:
                    data = json.load(f)
                print(f"Successfully read with encoding: {encoding}")
                
                # Write back with UTF-8
                with open('data/locations/launch_sites.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                print("File converted to UTF-8 successfully")
                return True
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error with {encoding}: {e}")
                continue
                
        print("Could not find suitable encoding")
        return False
        
    except Exception as e:
        print(f"Error fixing encoding: {e}")
        return False

if __name__ == "__main__":
    fix_json_encoding()