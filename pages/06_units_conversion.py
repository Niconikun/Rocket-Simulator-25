import streamlit as st
from src.utils import units

st.title("Conversor de Unidades")

# Inicializar historial en la sesión
if "conversion_history" not in st.session_state:
    st.session_state.conversion_history = []

col1, col2 = st.columns(2)

# Selección de magnitud
magnitudes = list(units.unitLabels.keys())
magnitud = col1.selectbox("Selecciona la magnitud", magnitudes, format_func=lambda x: units.unitLabels[x])

# Unidades disponibles para la magnitud seleccionada
unidades = units.getAllConversions(magnitud)
unidad_origen = col1.selectbox("Unidad de origen", unidades)
unidad_destino = col1.selectbox("Unidad de destino", unidades, index=1 if len(unidades) > 1 else 0)

# Ingreso de valor
valor = col1.number_input(f"Valor en {unidad_origen}", value=1.0, format="%.6f")

# Conversión principal
try:
    resultado = units.convert(valor, unidad_origen, unidad_destino)
    col1.success(f"{valor} {unidad_origen} = {resultado:.6f} {unidad_destino}")

    # Guardar en historial
    if col1.button("Agregar al historial"):
        col1.session_state.conversion_history.append(
            f"{valor} {unidad_origen} = {resultado:.6f} {unidad_destino}"
        )
except Exception as e:
    col1.error(f"Error en la conversión: {e}")

# Mostrar historial
if st.session_state.conversion_history:
    col1.markdown("#### Historial de conversiones")
    for item in reversed(col1.session_state.conversion_history):
        col1.write(item)

# Mostrar todas las conversiones posibles para el valor ingresado
col2.markdown("#### Todas las conversiones posibles para este valor")
for unidad in unidades:
    if unidad != unidad_origen:
        try:
            conv = units.convert(valor, unidad_origen, unidad)
            col2.write(f"{valor} {unidad_origen} = {conv:.6f} {unidad}")
        except Exception:
            continue

# Información adicional
st.markdown("#### Unidades disponibles")
for key, label in units.unitLabels.items():
    st.write(f"**{label}**: {', '.join(units.getAllConversions(key))}")