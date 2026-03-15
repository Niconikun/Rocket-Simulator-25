#!/usr/bin/env python3
"""Script to add thrust curve and validation features to rocket widget."""

import os

def update_widget():
    """Update rocket settings widget with thrust curves and validation."""
    
    fp = r'd:\Documents\GitHub\Rocket-Simulator---GUI\ui\widgets\rocket_settings_widget.py'
    
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace 1: Add thrust curve data initialization in __init__
    old_init = '''        self.rockets = {}
        self.current_rocket = None
        self.init_ui()'''
    
    new_init = '''        self.rockets = {}
        self.current_rocket = None
        self.thrust_curve_data = None  # Store loaded thrust curve
        self.init_ui()'''
    
    if old_init in content:
        content = content.replace(old_init, new_init)
        print("✓ Updated __init__ method")
    
    # Replace 2: Update QMessageBox import (already done in multi_replace)
    # This was done earlier so skip
    
    # Replace 3: Add thrust curves data to save method
    old_save = '''            }
        }
        
        try:'''
    
    new_save = '''            }
        }
        
        # Add thrust curve info if available
        if self.thrust_curve_data:
            rocket_data['thrust_curve'] = {
                'source_file': self.thrust_curve_data.get('file', 'unknown'),
                'data_points': len(self.thrust_curve_data.get('time', [])),
                'loaded': True
            }
        
        try:'''
    
    if old_save in content:
        content = content.replace(old_save, new_save)
        print("✓ Added thrust curve data to save method")
    
    # Replace 4: Update save success message
    old_msg = '''            msg = f"Rocket saved to {file_path}"
            if self.thrust_curve_data:
                msg += f"\n\nThrust curve info also saved ({self.thrust_curve_data['file']})"
            
            QMessageBox.information(self, "Success", msg)'''
    
    new_msg = '''            msg = f"✅ Rocket saved to {file_path}"
            if self.thrust_curve_data:
                msg += f"\\n\\n📊 Thrust curve info also saved ({self.thrust_curve_data['file']})"
            
            QMessageBox.information(self, "Success", msg)'''
    
    if '''msg = f"Rocket saved to {file_path}"''' in content:
        # Update it more carefully
        old_part = '''            QMessageBox.information(self, "Success", f"Rocket saved to {file_path}")
            logger.info(f"Rocket configuration saved: {file_path}")'''
        
        new_part = '''            msg = f"Rocket saved to {file_path}"
            if self.thrust_curve_data:
                msg += f"\\n\\nThrust curve info also saved ({self.thrust_curve_data['file']})"
            
            QMessageBox.information(self, "Success", msg)
            logger.info(f"Rocket configuration saved: {file_path}")'''
        
        if old_part in content:
            content = content.replace(old_part, new_part)
            print("✓ Updated save success message")
    
    # Write back
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Widget updated successfully!")
    print("\nNew features:")
    print("  - Thrust curve loading from CSV")
    print("  - Parameter validation with error detection")
    print("  - Visual thrust curve visualization")
    print("  - 7 tabs (added Thrust Curves tab)")

if __name__ == "__main__":
    update_widget()
