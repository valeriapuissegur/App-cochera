import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta


# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Gestor cocheras",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- DATA FILE PATH ---
DATA_FILE = Path(__file__).parent / "cocheras.xlsx"


# --- DATA HANDLING FUNCTIONS ---
@st.cache_data(ttl=10)
def load_sheet_data(sheet_name):
    """Carga los datos de una hoja específica del archivo Excel."""
    if not DATA_FILE.exists():
        st.error(f"Error: No se encontró el archivo 'cocheras.xlsx'.")
        st.stop()
    try:
        df = pd.read_excel(DATA_FILE, sheet_name=sheet_name)
        df.fillna("", inplace=True)
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        return df
    except ValueError:
        st.error(f"Error: No se pudo encontrar la hoja '{sheet_name}'. Verifica el archivo.")
        st.stop()
    except Exception as e:
        st.error(f"Ocurrió un error al cargar los datos: {e}")
        st.stop()


def save_data(df_cocheras, df_creds):
    """Guarda ambos DataFrames actualizados en el archivo Excel."""
    try:
        with pd.ExcelWriter(DATA_FILE, engine='openpyxl') as writer:
            df_cocheras['Fecha'] = pd.to_datetime(df_cocheras['Fecha']).dt.date
            df_cocheras.to_excel(writer, sheet_name='Cocheras', index=False)
            df_creds.to_excel(writer, sheet_name='Credenciales', index=False)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al guardar los datos: {e}")

# --- AUTHENTICATION LOGIC ---
def login_form():
    """Muestra el formulario de login y maneja la lógica de autenticación."""
    st.header("🚗 Gestor de Cocheras")
    st.write("Por favor, inicia sesión para continuar.")

    with st.form("login_form"):
        username = st.text_input("Usuario (tu correo)", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        submitted = st.form_submit_button("Ingresar")

        if submitted:
            df_users = load_sheet_data("Credenciales")
            user_data = df_users[(df_users['Correo'].str.lower() == username.lower()) & (df_users['Contraseña'].astype(str) == password)]

            if not user_data.empty:
                st.session_state["logged_in"] = True
                user_record = user_data.iloc[0]
                st.session_state["user_email"] = user_record['Correo']
                st.session_state["user_type"] = user_record.get('Tipo usuario', 'comun')

                df_cocheras = load_sheet_data("Cocheras")
                user_profile = df_cocheras[df_cocheras['Correo'] == st.session_state["user_email"]]
                st.session_state["user_name"] = user_profile.iloc[0]['Nombre y apellido'] if not user_profile.empty else st.session_state["user_email"]

                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

# --- ADMIN VIEW ---
def admin_view():
    """Muestra el panel de administración para usuarios admin."""
    st.title("⚙️ Panel de Administración")

    # Load both dataframes at the start
    df_cocheras_actual = load_sheet_data("Cocheras")
    df_creds_actual = load_sheet_data("Credenciales")

    # Create tabs for better organization
    tab1, tab2 = st.tabs(["Gestionar Cocheras", "Gestionar Credenciales"])

    with tab1:
        st.header("Gestión de la Tabla 'Cocheras'")
        
        # --- SECTION 1: IMPORT AND REPLACE ---
        with st.expander("Importar y Reemplazar Tabla de Cocheras"):
            st.warning("Advertencia: Esta acción reemplazará **todos** los datos de la tabla 'Cocheras'.", icon="⚠️")
            uploaded_file = st.file_uploader("Selecciona un archivo Excel (.xlsx)", type=['xlsx'], key="cocheras_uploader")
            
            if uploaded_file:
                try:
                    df_new = pd.read_excel(uploaded_file)
                    df_new.fillna("", inplace=True)
                    if df_cocheras_actual.columns.tolist() == df_new.columns.tolist():
                        st.success("El archivo tiene el formato de columnas correcto.")
                        st.dataframe(df_new.head())
                        if st.button("Confirmar y Reemplazar 'Cocheras'", type="primary"):
                            save_data(df_new, df_creds_actual)
                            st.success("¡Datos de 'Cocheras' reemplazados!")
                            st.rerun()
                    else:
                        st.error("Error: Las columnas del archivo no coinciden.")
                        st.json({"esperadas": df_cocheras_actual.columns.tolist(), "encontradas": df_new.columns.tolist()})
                except Exception as e:
                    st.error(f"Error al leer el archivo: {e}")

        # --- SECTION 2: MASSIVE CHANGES ---
        with st.expander("Reemplazar asignaciones de usuario"):
            with st.form("massive_change_form"):
                all_users = sorted(df_cocheras_actual['Correo'].dropna().unique().tolist())
                user_to_replace = st.selectbox("Usuario a reemplazar:", all_users, index=None)
                new_user_email = st.text_input("Nuevo Correo")
                new_user_name = st.text_input("Nuevo Nombre y Apellido")
                
                if st.form_submit_button("Realizar Reemplazo"):
                    if user_to_replace and new_user_email and new_user_name:
                        indices = df_cocheras_actual[df_cocheras_actual['Correo'] == user_to_replace].index
                        if not indices.empty:
                            df_cocheras_actual.loc[indices, 'Correo'] = new_user_email
                            df_cocheras_actual.loc[indices, 'Nombre y apellido'] = new_user_name
                            save_data(df_cocheras_actual, df_creds_actual)
                            st.success(f"Se reasignaron {len(indices)} cocheras a '{new_user_email}'.")
                            st.rerun()
                        else:
                            st.warning(f"El usuario '{user_to_replace}' no tiene cocheras asignadas.")
                    else:
                        st.error("Completa todos los campos.")

        # --- SECTION 3: DATA EDITOR for Cocheras ---
        st.subheader("Editor de Tabla de Cocheras")
        edited_df_cocheras = st.data_editor(df_cocheras_actual, num_rows="dynamic", key="admin_cocheras_editor", use_container_width=True)
        if st.button("Guardar Cambios en 'Cocheras'", type="primary"):
            save_data(edited_df_cocheras, df_creds_actual)
            st.success("¡Tabla 'Cocheras' guardada!")
            st.rerun()

    with tab2:
        st.header("Gestión de la Tabla 'Credenciales'")
        st.info("Puedes agregar, eliminar o modificar usuarios. El 'Tipo usuario' debe ser 'admin' o 'comun'.")
        
        edited_df_creds = st.data_editor(df_creds_actual, num_rows="dynamic", key="admin_creds_editor", use_container_width=True)
        
        st.warning("Aviso: Si modificas tus propias credenciales, puede que necesites volver a iniciar sesión.", icon="💡")
        
        if st.button("Guardar Cambios en 'Credenciales'", type="primary"):
            save_data(df_cocheras_actual, edited_df_creds)
            st.success("¡Tabla 'Credenciales' guardada!")
            st.rerun()


# --- USER VIEW ---
def user_view():
    """Muestra la interfaz principal para usuarios comunes."""
    st.title("🚗 Panel de Gestión de Cocheras")

    # --- TEXTO INTRODUCTORIO ---
    st.markdown("---")
    st.markdown("#### 🙌 **Te damos la bienvenida al Panel de Gestión de Cocheras**")
    st.markdown("Acá vas a poder:")
    st.markdown("✔ Confirmar tu cochera asignada.")
    st.markdown("✔ Liberarla si no la vas a usar.")
    st.markdown("✔ Reservar una cochera disponible para tus días en la oficina si no contas con una asignada.")
    st.markdown("---")
    st.markdown("#### 👉 **De esta forma, aprovechamos mejor los espacios y nos aseguramos de que estén disponibles para quien los necesite.**")
    st.markdown("¡Gestioná tu lugar en segundos! 🚗💨")
    st.markdown("---")

    df_cocheras = load_sheet_data("Cocheras")

    # --- Date calculations for rules ---
    today = pd.Timestamp.now().normalize()
    start_of_current_week = today - pd.to_timedelta(today.dayofweek, unit='d')
    end_of_current_week = start_of_current_week + pd.to_timedelta(6, unit='d')
    end_of_next_week = end_of_current_week + pd.to_timedelta(7, unit='d')
    
    # --- SECTION 1: MY ASSIGNMENTS ---
    st.header("Mis Cocheras Asignadas")
    mis_cocheras_all = df_cocheras[(df_cocheras['Correo'] == st.session_state['user_email']) & (df_cocheras['Fecha'] >= today)].sort_values(by='Fecha')

    if 'show_all_assignments' not in st.session_state:
        st.session_state.show_all_assignments = False

    if st.session_state.show_all_assignments:
        mis_cocheras_display = mis_cocheras_all
    else:
        mis_cocheras_display = mis_cocheras_all[mis_cocheras_all['Fecha'] <= end_of_next_week]

    if mis_cocheras_display.empty:
        st.warning("No tienes cocheras asignadas para las próximas dos semanas. Presiona 'Ver Todas' para buscar a futuro.")
    else:
        for index, row in mis_cocheras_display.iterrows():
            with st.container(border=True):
                estado = row['Estado']
                fecha_cochera = row['Fecha']
                
                col1, col2 = st.columns([3, 2])
                with col1:
                    st.subheader(f"Fecha: {fecha_cochera.strftime('%d/%m/%Y')} ({row['Dia de uso']})")
                    st.write(f"**Cochera:** {row['Numero cochera']}{row['Letra cochera']}")
                    st.write(f"**Estado:** {estado}")
                    
                    if estado == 'Reasignada':
                        persona_reasignada = row['Persona reasignada']
                        if persona_reasignada:
                            st.write(f"**Asignada a:** {persona_reasignada}")
                with col2:
                    df_creds = load_sheet_data("Credenciales")
                    if estado == 'Pendiente':
                        if start_of_current_week <= fecha_cochera <= end_of_next_week:
                            if st.button("✅ Confirmar", key=f"confirm_{index}", use_container_width=True):
                                df_cocheras.loc[index, 'Estado'] = 'Confirmada'; save_data(df_cocheras, df_creds); st.rerun()
                            if st.button("❌ Liberar", key=f"liberar_p_{index}", use_container_width=True):
                                df_cocheras.loc[index, 'Estado'] = 'Liberado'; save_data(df_cocheras, df_creds); st.rerun()
                        elif fecha_cochera > end_of_next_week:
                            if st.button("❌ Liberar a Futuro", key=f"liberar_f_{index}", use_container_width=True):
                                df_cocheras.loc[index, 'Estado'] = 'Liberado'; save_data(df_cocheras, df_creds); st.rerun()
                    elif estado == 'Confirmada':
                        if st.button("🔄 Cambiar a Liberado", key=f"change_{index}", use_container_width=True):
                            df_cocheras.loc[index, 'Estado'] = 'Liberado'; save_data(df_cocheras, df_creds); st.rerun()

    if not mis_cocheras_all.empty and not mis_cocheras_display.equals(mis_cocheras_all):
        if st.button("Ver Todas las Futuras", use_container_width=True):
            st.session_state.show_all_assignments = True
            st.rerun()
    elif st.session_state.show_all_assignments:
        if st.button("Ver Menos (solo 2 semanas)", use_container_width=True):
            st.session_state.show_all_assignments = False
            st.rerun()

    st.divider()

    # --- SECTION 2: AVAILABLE PARKING SPOTS (LIBERADAS) ---
    st.header("Cocheras Disponibles para Ocupar")
    filtro_liberadas = (df_cocheras['Estado'] == 'Liberado') & \
                       (df_cocheras['Fecha'].between(today, end_of_next_week))
    cocheras_liberadas = df_cocheras[filtro_liberadas].copy().sort_values(by='Fecha')

    if cocheras_liberadas.empty:
        st.info("No hay cocheras liberadas para la semana en curso o la siguiente.")
    else:
        for index, row in cocheras_liberadas.iterrows():
            with st.container(border=True):
                propietario_original = row['Nombre y apellido'] or row['Correo']
                
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**Fecha:** {row['Fecha'].strftime('%d/%m/%Y')} ({row['Dia de uso']})")
                    if propietario_original:
                        st.write(f"**Asignada a:** {propietario_original}")
                with col2:
                    st.write(f"**Cochera:** {row['Numero cochera']}{row['Letra cochera']}")
                with col3:
                    if st.button("🙋‍♂️ Reservar", key=f"reservar_{index}", use_container_width=True):
                        df_cocheras.loc[index, 'Estado'] = 'Reasignada'
                        df_cocheras.loc[index, 'Persona reasignada'] = st.session_state['user_email']
                        df_creds = load_sheet_data("Credenciales")
                        save_data(df_cocheras, df_creds)
                        st.success(f"Cochera para el día {row['Fecha'].strftime('%d/%m')} reservada.")
                        st.rerun()
    st.divider()
    
    # --- SECTION 3: MY RESERVATIONS ---
    st.header("Cocheras que he Reservado")
    reservadas_por_mi = df_cocheras[(df_cocheras['Persona reasignada'] == st.session_state['user_email']) & (df_cocheras['Fecha'] >= today)].sort_values(by='Fecha')

    if reservadas_por_mi.empty:
        st.info("No has reservado ninguna cochera de otro usuario para fechas futuras.")
    else:
        for index, row in reservadas_por_mi.iterrows():
            propietario = row['Nombre y apellido'] or row['Correo']
            estado = row['Estado']
            
            with st.container(border=True):
                st.subheader(f"Fecha: {row['Fecha'].strftime('%d/%m/%Y')} ({row['Dia de uso']})")
                st.write(f"**Cochera:** {row['Numero cochera']}{row['Letra cochera']}")
                st.write(f"**Asignada a:** {propietario}")
                st.write(f"**Estado:** {estado}")


# --- MAIN EXECUTION LOGIC ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    st.sidebar.title("¡Hola!")
    st.sidebar.header(f"{st.session_state['user_name']}")
    
    if st.session_state.get("user_type") == "admin":
        st.sidebar.markdown("---")
        view_mode = st.sidebar.radio("Seleccionar Vista", ("Usuario", "Administrador"), key="view_mode")
    else:
        view_mode = "Usuario"
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.cache_data.clear()
        st.rerun()

    if view_mode == "Administrador":
        admin_view()
    else:
        user_view()
else:
    login_form()