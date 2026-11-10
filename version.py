"""
Version information for Rocket Simulator Pro
Follows Semantic Versioning: MAJOR.MINOR.PATCH
"""

__version__ = "2.0.4"
__author__ = "Rocket Simulator Team"
__license__ = "MIT"

# Version components for easy access
# Synchronized with __version__ above
VERSION_MAJOR = 2
VERSION_MINOR = 0
VERSION_PATCH = 4

def get_version_string():
    """Get full version string."""
    return f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

def get_version_tuple():
    """Get version as tuple."""
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)


if __name__ == "__main__":
    print(f"Rocket Simulator Pro v{get_version_string()}")
