# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.


from dash import Dash, Input, Output, callback, html, dcc, no_update
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import dash_leaflet as dl
from dash_extensions.enrich import DashProxy
import numpy as np
from cmath import pi
import datetime as dt

import MatTools as Mat
from Clock import Clock
from Planet import Planet
from Atmosphere import Atmosphere
from Rocket import Rocket

#app = Dash()
app = DashProxy()

app.layout = html.Div(children=[
    html.Section(children=[
        html.Div(children=[
            html.H1(dt.datetime.now().strftime('%Y-%m-%d'), style={'font-family': 'Times New Roman','opacity': '0.5','color': 'black', 'fontSize': 12}),
            html.H1(dt.datetime.now().strftime('%H:%M:%S'), style={'font-family': 'Times New Roman','opacity': '0.5','color': 'black', 'fontSize': 12}),
            html.H6('Daily Updates')
        ], style={'float': 'right'}),
        html.H2('Configuración de la Simulación'),
        html.Form(children=[
            html.Div(children=[
                html.Label('Dropdown'),
                dcc.Dropdown(['New York City', 'Montréal', 'San Francisco'], 'Montréal'),

                html.Br(),
                html.Label('Multi-Select Dropdown'),
                dcc.Dropdown(['New York City', 'Montréal', 'San Francisco'],
                     ['Montréal', 'San Francisco'],
                     multi=True),

                html.Br(),
                html.Label('Radio Items'),
                dcc.RadioItems(['New York City', 'Montréal', 'San Francisco'], 'Montréal'),
                ], style={'padding': 10, 'flex': 1}),

                html.Div(children=[
                    html.Label('Checkboxes'),
                    dcc.Checklist(['New York City', 'Montréal', 'San Francisco'],
                      ['Montréal', 'San Francisco']
                ),

                html.Br(),
                html.Label('Text Input'),
                my_input := dcc.Input(value='MTL', type='text'),

                html.Br(),
                html.Label('Slider'),
                dcc.Slider(
                    min=0,
                    max=9,
                    marks={i: f'Label {i}' if i == 1 else str(i) for i in range(1, 6)},
                    value=5,
                ),

                html.Br(),
                html.Label('Time'),
                dcc.DatePickerSingle(
                    date='2025-06-21',
                    display_format='DD-MM-YYYY'
                ),
                html.Br(),
                html.Label('Time'),
                html.Time(n_clicks=0, id='time-input'),

            ]), 
            html.Div(
                html.Div(children=[
                    html.Label('Leaflet Map'),
                    dl.Map([dl.TileLayer(), dl.Polyline(positions=[[-36.671778, -73.097569], [-37, -73.097569]])], center=[-36.671778, -73.097569], zoom=15, style={'width': '100%', 'height': '500px'}),
                ])
            )  
        ], className='inputs-grid'),
    ], className='inputs-section'),
    
    html.Section(children=[
        html.Label('Submit button'),
        html.Button('Submit', id='submit-button', n_clicks=0),
    ], className='inputs-section'),
    
    html.Section(children=[
        html.H2('Dashboard Output'),
        html.Div(children=[
            html.P("Aca se mostrara la figura"),
        ], className='figure-placeholder'),

    ], className='outputs-section'),

], className='dashboard-container')

if __name__ == '__main__':
    app.run(debug=True)

    # Auxiliary functions
    deg2rad = pi/180
    rad2deg = 180/pi

    Start=0                     # [s]  # Starting time of simulation

    