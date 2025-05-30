import geopandas as gpd
import matplotlib.pyplot as plt

# Read the KML file
gdf = gpd.read_file('countries-land-2m5.geo.json')

# Plot the GeoDataFrame
gdf.plot()
plt.show()
