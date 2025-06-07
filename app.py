# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.


from dash import Dash, Input, Output, callback, html, dcc, no_update, State
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import dash_leaflet as dl
from dash_extensions.enrich import DashProxy
import numpy as np
from cmath import pi
import datetime as dt
import dash_loading_spinners
import json
import urllib.request
import plotly.graph_objects as go
import geopandas as gpd

import MatTools as Mat
from Clock import Clock
from Planet import Planet
from Atmosphere import Atmosphere
from Rocket import Rocket

#Load and read the geojson file for your map
gdf = gpd.read_file('Proyecto sin título.kml', driver='XML')

gdf_quiriquina = np.stack(gdf[gdf['Name'] == 'Quiriquina'].geometry.apply(np.array))
gdf_thno = np.stack(gdf[gdf['Name'] == 'Bahía de Talcahuano'].geometry.apply(np.array))
thno_coords = np.array(gdf_thno[0].exterior.coords)
quiriquina_coords = np.array(gdf_quiriquina[0].exterior.coords)

dict_map = {
    'type': 'FeatureCollection',
    'features': [
        {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [quiriquina_coords.tolist()]
            },
            'properties': {'name': 'Quiriquina'}
        },
        {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [thno_coords.tolist()]
            },
            'properties': {'name': 'Bahía de Talcahuano'}
        }
    ]
}



fig_map = px.line_3d(
    quiriquina_coords,
    x=quiriquina_coords[:, 0], y=quiriquina_coords[:, 1], z=quiriquina_coords[:, 2],
    labels={'x': 'Longitude', 'y': 'Latitude', 'z': 'Elevation'})
fig_map.add_trace(
    px.line_3d(thno_coords,
        x=thno_coords[:, 0], y=thno_coords[:, 1], z=thno_coords[:, 2]
    )
)
#fix the map figure to show the two locations

fig = go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[4, 1, 2])])

#app = Dash()
app = DashProxy()

app.layout = html.Div(children=[ #fix this layout. Focus on creating the divs first, then the tabs.
        html.Div(
                 id="div-loading",
                 children=[
                     dash_loading_spinners.Pacman(
                         fullscreen=True, 
                         id="loading-whole-app"
                     )
                 ]
             ),
             html.Div(
                 className="div-app",
                 id="div-app",
                 children = [ #  app layout here
                ]
             ),
    
    html.Section(children=[
        #Titulo y Header
        html.H1(children='Rocket Simulation Dashboard'),
    ]),
    html.Div(children=[
        #Tabs for different sections
        dcc.Tabs(id="tabs-inputs", value='tab-1', children=[
            dcc.Tab(label='Simulation Parameters', value='tab-1', children=[
                html.H3('Simulation Parameters'),

                html.Br(),
                html.Label('Slider'),
                dcc.Slider(
                    min=0,
                    max=9,
                    marks={i: f'Label {i}' if i == 1 else str(i) for i in range(1, 6)},
                    value=5,
                ),
                html.Label('Step size'),
                my_input := dcc.Input(value='1', type='number'),
                
                html.Br(),
                html.Label('Date'),
                dcc.DatePickerSingle(
                    date='2025-06-21',
                    display_format='DD-MM-YYYY'
                ),
                
                html.Label('Time (hh:mm:ss)'),
                my_input := dcc.Input(value='00:00:00', type='text'),

                html.Br(),
                html.Label('Timezone'),
                dcc.Dropdown(['New York City', 'Montréal', 'San Francisco'],
                     'Montréal')
                
            ]),
            dcc.Tab(label='Location Conditions & Orientation', value='tab-2', children=[
                html.Div(children=[
                    html.Label('Radio Items'),
                    dcc.RadioItems(['New York City', 'Montréal', 'San Francisco'], 'Montréal'),
                    html.Br(),
                    html.Label('Dropdown'),
                    dcc.Dropdown(['New York City', 'Montréal', 'San Francisco'], 'Montréal'),
                    html.Br(),
                    html.Label('Latitude'),
                    my_input := dcc.Input(value='1', type='number'),
                    html.Br(),
                    html.Label('Longitude'),
                    my_input := dcc.Input(value='1', type='number'),
                    html.Br(),
                    html.Label('Average Temperature'),
                    my_input := dcc.Input(value='1', type='number'),
                    html.Br(),
                    html.Label('Launch Angle'),
                    my_input := dcc.Input(value='1', type='number'),
                    html.Br(),
                    html.Label('Platform Orientation (from the north)'),
                    my_input := dcc.Input(value='1', type='number')
                ]),
                
                html.Div(children=[
                    html.Div(children=[
                    html.Label('Leaflet Map'),
                    dl.Map([
                        dl.TileLayer(),
                        dl.Polyline(positions=[[-36.671778, -73.097569], [-37, -73.097569]])
                        ], center=[-36.671778, -73.097569], zoom=15, style={'width': '100%', 'height': '500px'}, id='projection-map'),
                ])
                ]),
                
                

            ]),
            dcc.Tab(label='Rocket Parameters', value='tab-3', children=[
                html.Label('Radio Items'),
                dcc.RadioItems(['Preselected', 'Manual'], 'Preselected'),
                html.Br(),
                html.Label('Dropdown'),
                dcc.Dropdown(['Rayo', 'Campanil 1A'], 'Campanil 1A'),
                html.Br(),
                html.H3(children='Manual Input'),
                html.H4(children='Rocket Properties'),
                html.Br(),
                html.Label('Burn time'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Initial mass'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Reference area (Lift & Drag)'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Inertia before burning'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Centre of Mass (CoM) before burning'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Inertia after burning'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Centre of Mass (CoM) after burning'),
                my_input := dcc.Input(value='1', type='number'),
                html.H4(children='Rocket Geometry'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number'),
                html.Br(),
                html.Label('Latitude'),
                my_input := dcc.Input(value='1', type='number')
            ]),
        ], colors={
            "border": "red",
            "primary": "red",
            "background": "red"
        }),
        html.Div(id='tabs-content-props1')]),

    html.Section(children=[
        html.Button('Submit', id='submit-button', n_clicks=0),
        html.Button('Clear', id='clear-button', n_clicks=0) #aca agregar los resultados de la simulacion
    ]),

    html.Section(children=[
        #Titulo y Header
        html.H1(children='Launch Overview'),
        html.Table(children=[
            html.Tr(children=[
                html.Th('Parameter'),
                html.Th('Value')
            ]),
            html.Tr(children=[
                html.Td('Launch Date'),
                html.Td(id='launch-date', children='2025-06-21')
            ]),
            html.Tr(children=[
                html.Td('Launch Time'),
                html.Td(id='launch-time', children='00:00:00')
            ]),
            html.Tr(children=[
                html.Td('Location'),
                html.Td(id='launch-location', children='Montréal')
            ]),
            html.Tr(children=[
                html.Td('Rocket Name'),
                html.Td(id='rocket-name', children='Falcon 9'),
            ]),
        html.H1(children='Trajectory Overview'),
        dcc.Graph(figure=fig_map),
        
        html.H1(children='Risk Map'),
        
                    html.Div(children=[
                    html.Label('Leaflet Map'),
                    dl.Map([dl.TileLayer(), dl.Polyline(positions=[[-36.671778, -73.097569], [-37, -73.097569]]), dl.Polygon(positions=[[-36, -73], [-36.5, -73.5], [-37, -73.5], [-36.5, -74]]), dl.Circle(center=[-36.671778, -73.097569], radius=10000)], center=[-36.671778, -73.097569], zoom=15, style={'width': '1000px', 'height': '500px'}, id='risk-map'),
                    ])
                

        ]) #aca agregar los resultados de la simulacion
    ]),
    html.Div(children=[
        #Tabs for different sections
        dcc.Tabs(id="tabs-outputs", value='tab-1', children=[
            dcc.Tab(label='Bodyframe Velocities vs Time', value='tab-4', children=[
                html.Div(children=[
                    dcc.Graph(figure=fig),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Altitude vs Range', value='tab-5', children=[
                html.Div(children=[
                dcc.Graph(figure=fig),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Lift vs Time', value='tab-6', children=[
                html.Div(children=[
                dcc.Graph(figure=fig),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Pitch, Altitude vs Time', value='tab-7', children=[
                html.Div(children=[
                dcc.Graph(figure=fig),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Pitch vs Time', value='tab-8', children=[
                html.Div(children=[
                dcc.Graph(figure=fig),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Alpha vs Time', value='tab-9', children=[
                html.Div(children=[
                dcc.Graph(figure=fig),
        ], className='figure-placeholder')
            ]),
        ], colors={
            "border": "red",
            "primary": "red",
            "background": "red"
        }),
        html.Div(id='tabs-content-props2')])

    ], className='dashboard-container')

@callback(
        Output("div-loading", "children"),
        [
            Input("div-app", "loading_state")
        ],
        [
            State("div-loading", "children"),
        ]
    )

def hide_loading_after_startup(
    loading_state, 
    children
    ):
    if children:
        print("remove loading spinner!")
        return None
    print("spinner already gone!")
    raise PreventUpdate

if __name__ == '__main__':
    app.run(debug=True)

    # Auxiliary functions
    deg2rad = pi/180
    rad2deg = 180/pi

    Start=0                     # [s]  # Starting time of simulation

    