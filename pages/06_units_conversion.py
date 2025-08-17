import streamlit as st
from src.utils import units

st.title("Conversor de Unidades")

# Inicializar historial en la sesión
if "conversion_history" not in st.session_state:
    st.session_state.conversion_history = []

# Selección de magnitud
magnitudes = list(units.unitLabels.keys())
magnitud = st.selectbox("Selecciona la magnitud", magnitudes, format_func=lambda x: units.unitLabels[x])

# Unidades disponibles para la magnitud seleccionada
unidades = units.getAllConversions(magnitud)
unidad_origen = st.selectbox("Unidad de origen", unidades)
unidad_destino = st.selectbox("Unidad de destino", unidades, index=1 if len(unidades) > 1 else 0)

# Ingreso de valor
valor = st.number_input(f"Valor en {unidad_origen}", value=1.0, format="%.6f")

# Conversión principal
try:
    resultado = units.convert(valor, unidad_origen, unidad_destino)
    st.success(f"{valor} {unidad_origen} = {resultado:.6f} {unidad_destino}")

    # Guardar en historial
    if st.button("Agregar al historial"):
        st.session_state.conversion_history.append(
            f"{valor} {unidad_origen} = {resultado:.6f} {unidad_destino}"
        )
except Exception as e:
    st.error(f"Error en la conversión: {e}")

# Mostrar historial
if st.session_state.conversion_history:
    st.markdown("#### Historial de conversiones")
    for item in reversed(st.session_state.conversion_history):
        st.write(item)

# Mostrar todas las conversiones posibles para el valor ingresado
st.markdown("#### Todas las conversiones posibles para este valor")
for unidad in unidades:
    if unidad != unidad_origen:
        try:
            conv = units.convert(valor, unidad_origen, unidad)
            st.write(f"{valor} {unidad_origen} = {conv:.6f} {unidad}")
        except Exception:
            continue

# Información adicional
st.markdown("#### Unidades disponibles")
for key, label in units.unitLabels.items():
    st.write(f"**{label}**: {', '.join(units.getAllConversions(key))}")