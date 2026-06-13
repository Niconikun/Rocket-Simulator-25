"""
Version information for Rocket Simulator Pro
Follows Semantic Versioning: MAJOR.MINOR.PATCH
"""

__version__ = "0.5.1"
__author__ = "Rocket Simulator Team"
__license__ = "MIT"

# Version components for easy access
VERSION_MAJOR = 0
VERSION_MINOR = 5
VERSION_PATCH = 7

def get_version_string():
    """Get full version string."""
    return f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

def get_version_tuple():
    """Get version as tuple."""
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)


if __name__ == "__main__":
    print(f"Rocket Simulator Pro v{get_version_string()}")
