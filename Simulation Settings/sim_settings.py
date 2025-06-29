import streamlit as st

left_column, right_column = st.columns(2)
# You can use a column just like st.sidebar:
left_column.button('Press me!')
options = ["North", "East", "South", "West"]
left_column.text_input('Enter your name:', 'Type here...')
selection = left_column.pills("Directions", options, selection_mode="multi")
st.markdown(f"Your selected options: {selection}.")


# Or even better, call Streamlit functions inside a "with" block:
with right_column:
    chosen = st.radio(
        'Sorting hat',
        ("Gryffindor", "Ravenclaw", "Hufflepuff", "Slytherin"))
    st.write(f"You are in {chosen} house!")