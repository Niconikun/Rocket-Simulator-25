import streamlit as st

rocket_page = st.Page("Simulation Settings/create.py", title="Rocket", icon=":material/add_circle:")
sim_page = st.Page("Simulation Settings/sim_settings.py", title="Simulation", icon=":material/settings:")
dashboard_page = st.Page("delete.py", title="Dashboard", icon=":material/delete:")

pg = st.navigation([rocket_page, sim_page, dashboard_page])
st.set_page_config(page_title="Data manager", page_icon=":material/edit:")
pg.run()