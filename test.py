import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import plotly.express as px

from shapely.geometry import	Polygon
import plotly.graph_objects as go
from dash import Dash, Input, Output, callback, html, dcc, no_update, State


# Read the KML file
gdf = gpd.read_file('Proyecto sin título.kml', driver='XML')

gdf_quiriquina = np.stack(gdf[gdf['Name'] == 'Quiriquina'].geometry.apply(np.array))
gdf_thno = np.stack(gdf[gdf['Name'] == 'Bahía de Talcahuano'].geometry.apply(np.array))
thno_coords = np.array(gdf_thno[0].exterior.coords)

quiriquina_coords = np.array(gdf_quiriquina[0].exterior.coords)
#gdf_talcahuano = gdf[gdf['Name'] == 'Bahía de Talcahuano']
print(type(quiriquina_coords))
print(quiriquina_coords)

ax = plt.figure().add_subplot(projection='3d')
ax.plot(quiriquina_coords[:, 0], quiriquina_coords[:, 1], zs=quiriquina_coords[:, 2], zdir='z', label='Quiriquina', color='blue')
ax.plot(thno_coords[:, 0], thno_coords[:, 1], zs=thno_coords[:, 2], zdir='z', label='Talcahuano', color='red')
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')   
ax.set_zlabel('Elevation')
ax.set_title('3D Plot of KML Data')
ax.legend()
ax.set_zlim([0, 100])
ax.set_ylim([-36.75, -36.6])
ax.set_xlim([-73.15, -72.95])
plt.show()
# Dash app to visualize the KML data in 3D

fig_map = px.line_3d(
    quiriquina_coords,
    x=quiriquina_coords[:, 0], y=quiriquina_coords[:, 1], z=quiriquina_coords[:, 2],
    labels={'x': 'Longitude', 'y': 'Latitude', 'z': 'Elevation'})

dcc.Graph(figure=fig_map)



'''# Plot the GeoDataFrame
plt.plot(df)
plt.ylim([-36.75, -36.6])
plt.xlim([-73.15, -72.95])
plt.title('KML Data Plot')
plt.show()
'''
