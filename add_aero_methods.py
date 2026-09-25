# Read the file
with open('src/models/aerodynamics.py', 'r') as f:
    lines = f.readlines()

# Find the line with "def get_stability_margin" and add methods after it
new_lines = []
i = 0
while i < len(lines):
    new_lines.append(lines[i])
    
    # Check if this is the end of get_stability_margin method
    if i > 0 and 'def get_stability_margin' in lines[i-10:i]:
        if lines[i].strip() and not lines[i].startswith(' ') and not lines[i].startswith('\t') and not lines[i].startswith('\n'):
            # This is a new method, so add our methods before it
            # Add the missing methods
            new_lines.append('\n')
            new_lines.append('    @classmethod\n')
            new_lines.append('    def from_rocket_config(cls, rocket_config: Dict[str, Any]) -> "Aerodynamics":\n')
            new_lines.append('        """\n')
            new_lines.append('        Create Aerodynamics instance from rocket configuration.\n')
            new_lines.append('        \n')
            new_lines.append('        Args:\n')
            new_lines.append('            rocket_config: Dictionary containing rocket configuration with aerodynamics section\n')
            new_lines.append('            \n')
            new_lines.append('        Returns:\n')
            new_lines.append('            Aerodynamics: Instance initialized from configuration\n')
            new_lines.append('        """\n')
            new_lines.append('        aero_config = rocket_config.get("aerodynamics", {})\n')
            new_lines.append('        cd = aero_config.get("cd", 0.5)\n')
            new_lines.append('        cl = aero_config.get("cl", 0.0)\n')
            new_lines.append('        center_of_pressure_x = aero_config.get("center_of_pressure_x", 0.5)\n')
            new_lines.append('        stability_margin = aero_config.get("stability_margin", 1.0)\n')
            new_lines.append('        reference_area = rocket_config.get("reference_area", 0.01)\n')
            new_lines.append('        \n')
            new_lines.append('        return cls(\n')
            new_lines.append('            cd=cd,\n')
            new_lines.append('            cl=cl,\n')
            new_lines.append('            center_of_pressure_x=center_of_pressure_x,\n')
            new_lines.append('            stability_margin=stability_margin,\n')
            new_lines.append('            reference_area=reference_area\n')
            new_lines.append('        )\n')
            new_lines.append('\n')
            
            # Add setter methods
            new_lines.append('    def set_coefficients(self, cd: float, cl: float) -> None:\n')
            new_lines.append('        """Set drag and lift coefficients."""\n')
            new_lines.append('        self._cd = float(cd)\n')
            new_lines.append('        self._cl = float(cl)\n')
            new_lines.append('\n')
            new_lines.append('    def set_stability_margin(self, stability_margin: float) -> None:\n')
            new_lines.append('        """Set stability margin."""\n')
            new_lines.append('        self._stability_margin = float(stability_margin)\n')
            new_lines.append('\n')
            new_lines.append('    def set_reference_area(self, reference_area: float) -> None:\n')
            new_lines.append('        """Set reference area."""\n')
            new_lines.append('        if self._use_geometry:\n')
            new_lines.append('            self.ref_area = float(reference_area)\n')
            new_lines.append('        else:\n')
            new_lines.append('            self._reference_area = float(reference_area)\n')
            new_lines.append('\n')
            new_lines.append('    def set_center_of_pressure(self, x: float, y: float = 0.0, z: float = 0.0) -> None:\n')
            new_lines.append('        """Set center of pressure position."""\n')
            new_lines.append('        self._xcp = np.array([x, y, z])\n')
            new_lines.append('        self._center_of_pressure_x = float(x)\n')
            
            # Skip any blank lines after get_stability_margin
            i += 1
            while i < len(lines) and lines[i].strip() == '':
                i += 1
            continue
    
    i += 1

# Write back
with open('src/models/aerodynamics.py', 'w') as f:
    f.writelines(new_lines)

print("Methods added successfully")
