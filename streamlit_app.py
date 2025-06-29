import streamlit as st

rocket_page = st.Page("Simulation Settings/rocket_settings.py", title="Rocket", icon=":material/add_circle:")
sim_page = st.Page("Simulation Settings/sim_settings.py", title="Simulation", icon=":material/settings:")
dashboard_page = st.Page("Analysis/dashboard.py", title="Dashboard", icon=":material/delete:")

pg = st.navigation(
        {
            "Simulation Settings": [rocket_page, sim_page],
            "Analysis": [dashboard_page],
        }
    )

st.set_page_config(page_title="Data manager", page_icon=":material/edit:")
pg.run()