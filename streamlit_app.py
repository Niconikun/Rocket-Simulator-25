import streamlit as st

rocket_page = st.Page("Simulation Settings/rocket_settings.py", title="Rocket", icon=":material/add_circle:")
sim_page = st.Page("Simulation Settings/sim_settings.py", title="Simulation", icon=":material/settings:")
location_page = st.Page("Simulation Settings/location_settings.py", title="Location", icon=":material/location_on:")
dashboard_page = st.Page("Analysis/dashboard.py", title="Dashboard", icon=":material/delete:")
risk_page = st.Page("Analysis/risk_analysis.py", title="Risk Analysis", icon=":material/analytics:")

pg = st.navigation(
        {
            "Simulation Settings": [rocket_page, location_page, sim_page],
            "Analysis": [dashboard_page, risk_page],
        }
    )

st.set_page_config(page_title="Data manager", page_icon=":material/edit:")

pg.run()