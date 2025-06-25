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

dict_map = dict({
    'data':[{type:'line3d',
            'x': quiriquina_coords[:, 0].tolist(),
            'y': quiriquina_coords[:, 1].tolist(),
            'z': quiriquina_coords[:, 2].tolist(),
           },
           {
            'type': 'line3d',
            'x': thno_coords[:, 0].tolist(),
            'y': thno_coords[:, 1].tolist(),
            'z': thno_coords[:, 2].tolist(),
           }],
    'layout': {'title': {'text':'3D Plot of KML Data'}
           }
})

 

fig_map = go.Figure()

fig_map.add_trace(go.Scatter3d(
    x=quiriquina_coords[:, 0], y=quiriquina_coords[:, 1], z=quiriquina_coords[:, 2],
    mode='lines',
    name='Line 1',
    line=dict(color='blue', width=4)
))

fig_map.add_trace(go.Scatter3d(
    x=thno_coords[:, 0], y=thno_coords[:, 1], z=thno_coords[:, 2],
    mode='lines',
    name='Line 2',
    line=dict(color='red', width=4)
))

# Update layout for better visuals
fig_map.update_layout(
    title='3D Plot with Two Lines',
    scene=dict(
        xaxis=dict(title='Longitude', range=[-73.15, -72.95]),
        yaxis=dict(title='Latitude', range=[-36.75, -36.6]),
        zaxis=dict(title='Elevation', range=[0, 50])
    ),
    margin=dict(l=0, r=0, b=0, t=40)
)

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
                html.Label('Simulation Runtime'),
                sim_runtime := dcc.Slider(
                    id='sim-runtime',
                    min=0,
                    max=60,
                    marks={i: str(i) for i in range(1, 60)},
                    value=30,
                ),
                html.Label('Step size'),
                step_size := dcc.Input(id='step-size', value='1', type='number'),
                
                html.Br(),
                html.Label('Date'),
                sim_date := dcc.DatePickerSingle(id='sim-date', 
                    date='2025-06-21',
                    display_format='DD-MM-YYYY'
                ),
                
                html.Label('Time (hh:mm:ss)'),
                sim_time := dcc.Input(id='sim-time', value='00:00:00', type='text'),

                html.Br(),
                html.Label('Timezone'),
                dcc.Dropdown(['New York City', 'Montréal', 'San Francisco'],
                     'Montréal', id='timezone')
                
            ]),
            dcc.Tab(label='Location Conditions & Orientation', value='tab-2', children=[
                html.Div(children=[
                    html.Label('Radio Items'),
                    dcc.RadioItems(['Preselected', 'Manual'], 'Preselected', id='location-radio'),
                    html.Br(),
                    html.Label('Dropdown'),
                    dcc.Dropdown(['El Álamo', 'Club de Aeromodelos'], 'El Álamo', id='location-dropdown'),
                    html.Br(),
                    html.Label('Latitude'),
                    launch_site_lat := dcc.Input(id='launch-site-lat', value='1', type='number'),
                    html.Br(),
                    html.Label('Longitude'),
                    launch_site_lon := dcc.Input(id='launch-site-lon', value='1', type='number'),
                    html.Br(),
                    html.Label('Average Temperature'),
                    average_temperature := dcc.Input(id='avg-temp', value='1', type='number'),
                    html.Br(),
                    html.Label('Launch Angle'),
                    launch_angle := dcc.Input(id='launch-angle', value='1', type='number'),
                    html.Br(),
                    html.Label('Platform Orientation (from the north)'),
                    launch_site_orientation := dcc.Input(id='launch-site-orientation', value='1', type='number')
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
                dcc.RadioItems(['Preselected', 'Manual'], 'Preselected', id='preselected-radio'),
                html.Br(),
                html.Label('Dropdown'),
                dcc.Dropdown(['Rayo', 'Campanil 1A'], 'Campanil 1A', id='rocket-dropdown'),
                html.Br(),
                html.H3(children='Manual Input'),
                html.H4(children='Rocket Properties'),
                html.Br(),
                html.Label('Burn time'),
                burn_time := dcc.Input(value='1', type='number', id='burn-time'),
                html.Br(),
                html.Label('Initial mass'),
                initial_mass := dcc.Input(value='1', type='number', id='initial-mass'),
                html.Br(),
                html.Label('Reference area (Lift & Drag)'),
                cross_section_area := dcc.Input(value='1', type='number', id='cross-section-area'),
                html.Br(),
                html.Label('Inertia before burning'),
                inertia_before_burn := dcc.Input(value='1', type='number', id='inertia-initial'),
                html.Br(),
                html.Label('Centre of Mass (CoM) before burning'),
                com_before_burn := dcc.Input(value='1', type='number', id='com_initial'),
                html.Br(),
                html.Label('Inertia after burning'),
                inertia_after_burn := dcc.Input(value='1', type='number', id='inertia-final'),
                html.Br(),
                html.Label('Centre of Mass (CoM) after burning'),
                com_after_burn := dcc.Input(value='1', type='number', id='com-final'),
                
                html.H4(children='Rocket Geometry'),
                html.Br(),
                html.Label('Length of warhead or distance from tip of nose to base of nose'),
                len_warhead := dcc.Input(value='1', type='number', id='len-warhead'),
                html.Br(),
                html.Label('Length between nose cone tip and the point where the fin leading edge meets the body tube'),
                len_nosecone_fins := dcc.Input(value='1', type='number', id='len-nosecone-fins'),
                html.Br(),
                html.Label('Length between nose tip to rear'),
                len_nosecone_rear := dcc.Input(value='1', type='number', id='len-nosecone-rear'),
                

                html.Br(),
                html.Label('Length of body tube (not considering rear)'),
                len_bodytube_wo_rear := dcc.Input(value='1', type='number', id='len_bodytube-wo-rear'),
                html.Br(),
                html.Label('Fins aerodynamic chord at root'),
                fins_chord_root := dcc.Input(value='1', type='number', id='fins-chord-root'),
                html.Br(),
                html.Label('Fins aerodynamic mid-chord'),
                fins_mid_chord := dcc.Input(value='1', type='number', id='fins-mid-chord'),
                html.Br(),
                html.Label('Length of rear'),
                len_rear := dcc.Input(value='1', type='number', id='len-rear'),
                html.Br(),
                html.Label('Fins span'),
                fins_span := dcc.Input(value='1', type='number', id='fins-span'),
                html.Br(),
                html.Label('Diameter of base of warhead'),
                diameter_warhead_base := dcc.Input(value='1', type='number', id='diam-warhead-base'),
                html.Br(),
                html.Label('Diameter of body tube'),
                diameter_bodytube := dcc.Input(value='1', type='number', id='diam-bodytube'),
                html.Br(),
                html.Label('Diameter of body tube where fins are met'),
                diameter_bodytube_fins := dcc.Input(value='1', type='number', id='diam-bodytube-fins'),
                html.Br(),
                html.Label('Diameter of rear where it meets body tube'),
                diameter_rear_bodytube := dcc.Input(value='1', type='number', id='diam-rear-bodytube'),
                html.Br(),
                html.Label('End diameter rear'),
                end_diam_rear := dcc.Input(value='1', type='number', id='end-diameter-rear'),
                html.Br(),
                html.Label('Normal force coefficient gradient for warhead'),
                normal_f_coef_warhead := dcc.Input(value='1', type='number', id='normal-force-coef-warhead'),
                html.Br(),
                html.Label('Number of fins'),
                N_fins := dcc.Input(value='1', type='number', id='n-fins')
            ]),
        ], colors={
            "border": "red",
            "primary": "red",
            "background": "red"
        }),
        html.Div(id='tabs-content-props1')]),

    html.Section(children=[
        html.Button(children='Submit', id='submit-button', n_clicks=0),
        html.Button(children='Clear', id='clear-button', n_clicks=0), #aca agregar los resultados de la simulacion
        html.Div(id='output-state')
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
        dcc.Graph(figure=fig_map, id='trajectory-graph'),
        
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
                    dcc.Graph(figure=fig, id='bodyframe-velocities-graph'),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Altitude vs Range', value='tab-5', children=[
                html.Div(children=[
                dcc.Graph(figure=fig, id='altitude-range-graph'),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Lift vs Time', value='tab-6', children=[
                html.Div(children=[
                dcc.Graph(figure=fig, id='lift-graph'),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Pitch, Altitude vs Time', value='tab-7', children=[
                html.Div(children=[
                dcc.Graph(figure=fig, id='pitch-altitude-graph'),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Pitch vs Time', value='tab-8', children=[
                html.Div(children=[
                dcc.Graph(figure=fig, id='pitch-graph'),
        ], className='figure-placeholder')
            ]),
            dcc.Tab(label='Alpha vs Time', value='tab-9', children=[
                html.Div(children=[
                dcc.Graph(figure=fig, id='alpha-graph'),
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
        Output("div-loading", "children"),
        Output('projection-map', "Map"),
	    Output('trajectory-graph', 'Figure'),
        Output('risk-map', 'Map'),
        Output('bodyframe-velocities-graph', 'Figure'),
        Output('altitude-range-graph', 'Figure'),
        Output('lift-graph', 'Figure'),
        Output('pitch-altitude-graph', 'Figure'),
        Output('pitch-graph', 'Figure'),
        Output('alpha-graph', 'Figure'),

        # Simulation Parameters
        
        Input('submit-button', 'n_clicks'),
        Input('clear-button', 'n_clicks'),
        Input("div-app", "loading_state"),
        State('sim-runtime', 'value'),
       	State('step-size', 'value'),
	    State('sim-date', 'value'),
        State('sim-time', 'value'),
        State('timezone', 'value'),
        
        # Location Conditions & Orientation}
	    State('location-radio', 'value'),
        State('location-dropdown', 'value'),
        State('launch-site-lat', 'value'),
        State('launch-site-lon', 'value'),
        State('avg-temp', 'value'),
        State('launch-angle', 'value'),
        State('launch-site-orientation', 'value'),


        # Rocket Parameters
        State('preselected-radio', 'value'),
        State('rocket-dropdown', 'value'),
        State('burn-time'),
        State('initial-mass'),
        State('cross-section-area'),
        State('inertia-initial'),
        State('com_initial'),
        State('inertia-final', 'value'),
        State('com-final', 'value'),

        State('len-warhead', 'value'),
        State('len-nosecone-fins', 'value'),
        State('len-nosecone-rear', 'value'),
        State('len_bodytube-wo-rear', 'value'),
        State('fins-chord-root', 'value'),
        State('fins-mid-chord', 'value'),
        State('len-rear', 'value'),
        State('fins-span', 'value'),
        State('diam-warhead-base', 'value'),
        State('diam-bodytube', 'value'),
        State('diam-bodytube-fins', 'value'),
        State('diam-rear-bodytube', 'value'),
        State('end-diameter-rear', 'value'),
        State('normal-force-coef-warhead', 'value'),
        State('n-fins', 'value'),
        
        State("div-loading", "children"),
    )

def hide_loading_after_startup(loading_state, children):
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

    