import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import qrcode
from io import BytesIO
import re
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="AgroCheck Pro", layout="wide", initial_sidebar_state="expanded")

# --- 2. CAPA DE DISEÑO (ESTILO INDUSTRIAL CLEAN / SAAS) ---
def cargar_diseño():
    st.markdown("""
        <style>
        /* IMPORTAR FUENTES MODERNAS (Google Fonts) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@600;700&display=swap');

        /* --- VARIABLES DE COLOR (Tema Stripe/SaaS) --- */
        :root {
            --primary-color: #2563eb; /* Azul Royal Moderno */
            --primary-hover: #1d4ed8;
            --background-color: #f1f5f9; /* Gris azulado muy pálido (Slate 100) */
            --card-bg: #ffffff;
            --text-dark: #0f172a; /* Slate 900 (Casi negro) */
            --text-medium: #334155; /* Slate 700 */
            --border-color: #e2e8f0;
        }

        /* --- ESTILOS GENERALES --- */
        .stApp {
            background-color: var(--background-color);
            font-family: 'Inter', sans-serif;
            color: var(--text-dark);
        }

        /* TÍTULOS */
        h1, h2, h3 {
            font-family: 'Poppins', sans-serif;
            color: var(--text-dark) !important;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        h1 {
            text-transform: uppercase;
            background: linear-gradient(90deg, #1e293b, #334155);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1.5rem;
            text-align: center;
        }

        /* --- TARJETAS (CARD UI) --- */
        /* Convertimos los bloques de Streamlit en tarjetas flotantes */
        div[data-testid="stMetric"], div[data-testid="stDataFrame"], .stForm {
            background-color: var(--card-bg);
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
            border: 1px solid var(--border-color);
        }
        
        /* Contenedores generales (border=True de Streamlit) */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        }

        /* --- BOTONES MODERNOS --- */
        div[data-testid="stButton"] > button {
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            padding: 0.5rem 1rem;
            transition: all 0.2s ease-in-out;
            border: none;
            height: 3em;
        }

        /* Botón Primario (Azul SaaS) */
        div[data-testid="stButton"] > button[kind="primary"] {
            background-color: var(--primary-color);
            color: white;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: var(--primary-hover);
            transform: translateY(-1px);
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
        }

        /* Botón Secundario (Blanco limpio) */
        div[data-testid="stButton"] > button[kind="secondary"] {
            background-color: white;
            color: var(--text-medium);
            border: 1px solid var(--border-color);
        }
        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background-color: #f8fafc;
            border-color: #94a3b8;
            color: var(--primary-color);
        }

        /* --- SIDEBAR --- */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid var(--border-color);
        }
        
        /* --- QR CONTAINER (Resaltado) --- */
        .qr-container {
            background-color: white;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            text-align: center;
            margin-bottom: 20px;
            margin-top: 10px;
        }

        /* --- INPUTS --- */
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            color: var(--text-dark) !important;
        }
        input { color: var(--text-dark) !important; }
        
        /* Ocultar elementos default */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# Activamos el diseño
cargar_diseño()

# ---------------------------------------------------------
# ✅ TU BASE DE DATOS
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UFsJ0eQ40hfKfL31e2I9mjUGNnk-6E2PkBmK4rKONAM/edit"
# ---------------------------------------------------------

# --- CONEXIÓN GOOGLE SHEETS ---
def get_db_connection():
    return st.connection("gsheets", type=GSheetsConnection)

# --- ESTADO DE SESIÓN ---
if 'vista' not in st.session_state: st.session_state.vista = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'destino_actual' not in st.session_state: st.session_state.destino_actual = ""

# --- FUNCIONES DE DATOS ---
def load_data():
    try:
        conn = get_db_connection()
        df_prod = conn.read(spreadsheet=SHEET_URL, worksheet="Productos", ttl=5)
        df_stock = conn.read(spreadsheet=SHEET_URL, worksheet="Stock_Real", ttl=5)
        df_mov = conn.read(spreadsheet=SHEET_URL, worksheet="Movimientos", ttl=5)
        
        if not df_prod.empty: df_prod.columns = df_prod.columns.str.strip()
        if not df_stock.empty: df_stock.columns = df_stock.columns.str.strip()
        if not df_mov.empty: df_mov.columns = df_mov.columns.str.strip()

        if df_prod.empty: df_prod = pd.DataFrame(columns=['Cod Producto', 'Nombre comercial'])
        
        if 'Cod Producto' not in df_prod.columns and not df_prod.empty:
            st.error(f"⚠️ Error: No encuentro 'Cod Producto'.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        if 'Fecha_Vencimiento' not in df_stock.columns:
            df_stock['Fecha_Vencimiento'] = None
        df_stock['Fecha_Vencimiento'] = pd.to_datetime(df_stock['Fecha_Vencimiento'], errors='coerce')
        
        if 'Fecha Hora' in df_mov.columns:
            df_mov['Fecha Hora'] = pd.to_datetime(df_mov['Fecha Hora'], errors='coerce')
        
        return df_prod, df_stock, df_mov
    except Exception as e:
        if "Quota exceeded" in str(e):
            st.warning("⚠️ Google está pidiendo un respiro. Espera 10 segundos y recarga.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def save_all(df_p, df_s, df_m):
    try:
        conn = get_db_connection()
        conn.update(spreadsheet=SHEET_URL, worksheet="Productos", data=df_p)
        
        df_s_export = df_s.copy()
        df_s_export['Fecha_Vencimiento'] = df_s_export['Fecha_Vencimiento'].astype(str).replace('NaT', '')
        conn.update(spreadsheet=SHEET_URL, worksheet="Stock_Real", data=df_s_export)
        
        df_m_export = df_m.copy()
        df_m_export['Fecha Hora'] = df_m_export['Fecha Hora'].astype(str).replace('NaT', '')
        conn.update(spreadsheet=SHEET_URL, worksheet="Movimientos", data=df_m_export)
        
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al guardar en la nube: {e}")

def aplicar_semaforo(val):
    if pd.isna(val): return ''
    hoy = datetime.now()
    alerta = hoy + timedelta(days=90)
    # Colores SaaS (Flat UI colors)
    if val < hoy: return 'background-color: #fee2e2; color: #b91c1c; font-weight: 600;' # Rojo suave
    elif val < alerta: return 'background-color: #fef3c7; color: #b45309; font-weight: 600;' # Ambar
    else: return 'background-color: #dcfce7; color: #15803d; font-weight: 600;' # Verde Esmeralda

# --- SIDEBAR (CON QR MEJORADO) ---
with st.sidebar:
    st.markdown("### 📱 **AgroCheck Mobile**")
    url_app = "https://agrocheck-portfolio.streamlit.app" 
    
    # Generamos QR
    qr = qrcode.QRCode(version=1, box_size=8, border=1)
    qr.add_data(url_app); qr.make(fit=True)
    img = qr.make_image(fill_color="#1e293b", back_color="white")
    buf = BytesIO(); img.save(buf, format="PNG")
    
    # Contenedor especial para el QR
    st.markdown('<div class="qr-container">', unsafe_allow_html=True)
    st.image(buf.getvalue(), caption="Escanear Acceso", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("v2.0 Industrial Build")

# --- VISTAS ---

def vista_menu():
    st.title("Gestión Depósito Agroquímicos")
    st.write("") 
    
    c1, c2 = st.columns(2)
    
    with c1:
        with st.container(border=True):
            st.info("🏢 **Oficina Técnica**")
            if st.button("NUEVA ORDEN DE SALIDA", use_container_width=True, type="primary"):
                st.session_state.vista = "Carga"; st.rerun()
            if st.button("INGRESO DE MERCADERÍA", use_container_width=True):
                st.session_state.vista = "Ingreso"; st.rerun()
            
    with c2:
        with st.container(border=True):
            st.success("📦 **Depósito / Operativa**")
            if st.button("ARMAR PEDIDOS", use_container_width=True):
                st.session_state.vista = "Espera"; st.rerun()
            if st.button("STOCK E HISTORIAL", use_container_width=True):
                st.session_state.vista = "Consultas"; st.rerun()

def vista_ingreso():
    c_head1, c_head2 = st.columns([1, 4])
    with c_head1:
        if st.button("⬅️ Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c_head2:
        st.subheader("Ingreso de Stock")
        
    df_p, df_s, df_m = load_data()
    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict() if not df_p.empty else {}

    # Tarjeta de Alta
    with st.container(border=True):
        col_switch, _ = st.columns([2,1])
        es_nuevo = col_switch.checkbox("➕ ¿Es un producto NUEVO? (Alta Rápida)")

        if es_nuevo:
            st.markdown("##### 🆕 Alta de Producto")
            c_new1, c_new2 = st.columns(2)
            cod_p = c_new1.text_input("Definir Nuevo Código", placeholder="Ej: FUNG_NUEVO").strip()
            nom_p_display = c_new2.text_input("Nombre Comercial", placeholder="Ej: Fungicida Nuevo 5L").strip()
        else:
            if df_p.empty:
                st.warning("No hay productos."); cod_p = None
            else:
                c1, c2 = st.columns(2)
                cod_p = c1.selectbox("Producto Existente", df_p['Cod Producto'].unique(), format_func=lambda x: f"{x} | {prod_map.get(x, '')}")
                nom_p_display = prod_map.get(cod_p, '')
                cuenta = c2.text_input("Cuenta / Propiedad")

        st.markdown("---")
        st.markdown("##### 🏷️ Datos del Lote")
        c3, c4, c5, c6 = st.columns(4)
        lote = c3.text_input("N° Lote")
        senasa = c4.text_input("SENASA")
        cod_barra = c5.text_input("GTIN/Cod Barra")
        fecha_venc = c6.date_input("Fecha Vencimiento")

    # Tarjeta Calculadora
    with st.container(border=True):
        st.markdown("##### 🧮 Calculadora de Cantidad")
        col_calc1, col_calc2, col_calc3 = st.columns(3)
        n1 = col_calc1.number_input("Cant. Bultos", min_value=0.0, placeholder="0")
        n2 = col_calc2.number_input("Tamaño Unitario", min_value=0.0, placeholder="0")
        unidad = col_calc3.selectbox("Unidad", ["Litros", "Kilos", "Gramos", "Cm3 / Ml", "Unidad / Kit"])
        
        val_n1 = n1 if n1 else 0.0; val_n2 = n2 if n2 else 0.0
        total_bruto = val_n1 * val_n2
        
        if unidad in ["Gramos", "Cm3 / Ml"]: cant_final = total_bruto / 1000; msg_unidad = "Kg/L"
        else: cant_final = total_bruto; msg_unidad = unidad

        st.metric(label=f"Total a Ingresar ({msg_unidad})", value=f"{cant_final:.2f}")

    if st.button("💾 GUARDAR INGRESO", type="primary", use_container_width=True):
        error = False
        if not lote or cant_final <= 0: st.error("❌ Faltan datos."); error = True
        
        if es_nuevo:
            if not cod_p or not nom_p_display: st.error("❌ Datos incompletos."); error = True
            elif cod_p in prod_map: st.error("❌ El código ya existe."); error = True
        
        if not error:
            if es_nuevo:
                df_p = pd.concat([df_p, pd.DataFrame([{'Cod Producto': cod_p, 'Nombre comercial': nom_p_display}])], ignore_index=True)
                st.toast(f"Producto '{nom_p_display}' creado!")

            mask = (df_s['Cod Producto'] == cod_p) & (df_s['Numero de Lote'] == lote)
            fecha_venc_dt = pd.to_datetime(fecha_venc)

            if mask.any():
                df_s.loc[mask, 'Cantidad'] += cant_final
                df_s.loc[mask, 'Fecha_Vencimiento'] = fecha_venc_dt
            else:
                new_row = {'Cod Producto': cod_p, 'Numero de Lote': lote, 'Cantidad': cant_final, 'SENASA': senasa, 'Cod_Barras': cod_barra, 'Fecha_Vencimiento': fecha_venc_dt}
                df_s = pd.concat([df_s, pd.DataFrame([new_row])], ignore_index=True)
            
            obs = f"Ingreso: {val_n1} x {val_n2} {unidad}" + (" (ALTA)" if es_nuevo else "")
            mov = {'Fecha Hora': datetime.now(), 'ID_Pedido': "INGRESO", 'Usuario': "Admin", 'Tipo de movimiento': "Compra", 'Cod Producto': cod_p, 'Cuenta/Entidad': locals().get('cuenta', ''), 'Numero de Lote': lote, 'Cantidad': cant_final, 'Destino Origen': "Depósito", 'Observaciones': obs, 'Estado_Prep': 'TERMINADO'}
            
            df_m = pd.concat([df_m, pd.DataFrame([mov])], ignore_index=True)
            save_all(df_p, df_s, df_m)
            st.success(f"✅ Guardado: {cant_final} {msg_unidad}"); time.sleep(1.5); st.session_state.vista="Menu"; st.rerun()

def vista_carga():
    c_head1, c_head2 = st.columns([1, 4])
    with c_head1:
        if st.button("⬅️ Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c_head2:
        st.subheader("Nueva Orden de Egreso")

    df_p, df_s, _ = load_data()
    if df_p.empty: st.warning("Error leyendo productos."); return
    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict()

    with st.container(border=True):
        c1, c2 = st.columns(2)
        st.session_state.destino_actual = c1.text_input("Destino / Cliente:", value=st.session_state.destino_actual)
        cuenta = c2.text_input("Cuenta a Descontar:")

    with st.container(border=True):
        col_a, col_b = st.columns([2, 1])
        sel_prod = col_a.selectbox("Seleccionar Producto", df_p['Cod Producto'].unique(), format_func=lambda x: f"{x} | {prod_map.get(x,'')}")
        tipo_op = col_b.selectbox("Tipo Movimiento", ["Venta", "Transferencia", "Uso Interno"])

        stock_prod = df_s[df_s['Cod Producto'] == sel_prod].copy()
        
        if stock_prod.empty:
            st.error("⚠️ No hay stock registrado.")
            lote_selec = None; stock_disp = 0
        else:
            stock_prod['Vence'] = pd.to_datetime(stock_prod['Fecha_Vencimiento']).dt.strftime('%d/%m/%Y')
            opciones_lote = stock_prod.apply(lambda row: f"{row['Numero de Lote']} (Disp: {row['Cantidad']:.2f} | Vence: {row['Vence']})", axis=1).tolist()
            lote_str = st.selectbox("Lote de Origen", opciones_lote)
            lote_selec = lote_str.split(" (")[0]
            stock_disp = stock_prod[stock_prod['Numero de Lote'] == lote_selec]['Cantidad'].values[0]

        st.markdown("---")
        cc1, cc2, cc3 = st.columns(3)
        cant_bultos = cc1.number_input("Cant. Envases", min_value=0.0, placeholder="0")
        tam_bultos = cc2.number_input("Litros/Kg por Envase", value=None, placeholder="0")
        
        v_cb = cant_bultos if cant_bultos else 0.0; v_tb = tam_bultos if tam_bultos else 0.0
        total_a_pedir = v_cb * v_tb
        cc3.metric("Total Solicitado", f"{total_a_pedir:.2f}")

    if st.button("➕ AGREGAR AL PEDIDO", type="secondary", use_container_width=True):
        if not lote_selec or total_a_pedir <= 0: st.error("Verifique lote y cantidad.")
        else:
            if total_a_pedir > stock_disp: st.warning(f"⚠️ Stock insuficiente (Hay {stock_disp})")
            st.session_state.carrito.append({"cod": sel_prod, "nom": prod_map.get(sel_prod), "cant": total_a_pedir, "lote_asig": lote_selec, "det": f"{v_cb} env x {v_tb}", "tipo": tipo_op, "cta": cuenta})

    if st.session_state.carrito:
        st.markdown("### 🛒 Carrito")
        st.table(pd.DataFrame(st.session_state.carrito))
        if st.button("✅ CONFIRMAR Y ENVIAR A DEPÓSITO", type="primary", use_container_width=True):
            if st.session_state.destino_actual:
                id_ped = f"PED-{int(time.time())}"
                conn = get_db_connection()
                df_m_live = conn.read(spreadsheet=SHEET_URL, worksheet="Movimientos", ttl=0)
                if not df_m_live.empty: df_m_live.columns = df_m_live.columns.str.strip()
                
                new_rows = []
                for item in st.session_state.carrito:
                    new_rows.append({'Fecha Hora': datetime.now(), 'ID_Pedido': id_ped, 'Usuario': "Oficina", 'Tipo de movimiento': item['tipo'], 'Cod Producto': item['cod'], 'Cuenta/Entidad': item['cta'], 'Numero de Lote': item['lote_asig'], 'Cantidad': item['cant'] * -1, 'Destino Origen': st.session_state.destino_actual, 'Observaciones': item['det'], 'Estado_Prep': 'PENDIENTE'})
                
                df_m_live = pd.concat([df_m_live, pd.DataFrame(new_rows)], ignore_index=True)
                save_all(df_p, df_s, df_m_live)
                st.session_state.carrito = []; st.success("✅ Orden enviada."); time.sleep(1); st.rerun()
            else: st.error("❌ Falta el Destino")

def vista_espera():
    c_head1, c_head2 = st.columns([1, 4])
    with c_head1:
        if st.button("⬅️ Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c_head2:
        st.subheader("Armado de Pedidos")

    df_p, df_s, df_m = load_data()
    if df_p.empty or df_m.empty: st.info("Cargando..."); return
    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict()

    if 'Estado_Prep' not in df_m.columns: st.error("Error columnas."); return
    pendientes = df_m[df_m['Estado_Prep'] == 'PENDIENTE'].copy()
    if pendientes.empty: st.info("✅ No hay pedidos pendientes."); return

    lista_pedidos = pendientes['ID_Pedido'].unique()
    pedido_selec = st.selectbox("Seleccionar Pedido a Armar", lista_pedidos)

    if pedido_selec:
        items = pendientes[pendientes['ID_Pedido'] == pedido_selec]
        st.info(f"📍 Destino: **{items.iloc[0]['Destino Origen']}**")
        
        for idx, row in items.iterrows():
            with st.container(border=True):
                col_info, col_accion = st.columns([1, 2])
                cant_pedida = abs(row['Cantidad'])
                
                with col_info:
                    st.markdown(f"**{prod_map.get(row['Cod Producto'], row['Cod Producto'])}**")
                    st.caption(f"Lote Pedido: {row['Numero de Lote']}")
                    st.markdown(f"📦 Cant: **{cant_pedida:.2f}**")

                with col_accion:
                    c_lote, c_cant1, c_cant2 = st.columns(3)
                    lote_real = c_lote.text_input("Lote Real", value="", key=f"l_{idx}")
                    cant_env = c_cant1.number_input("Envases", min_value=0.0, key=f"ce_{idx}")
                    tam_env = c_cant2.number_input("Tamaño", key=f"te_{idx}")
                    
                    cant_real = (cant_env or 0) * (tam_env or 0)
                    if cant_real > 0: st.write(f"Real: **{cant_real:.2f}**")
                    
                    obs_dep = st.text_input("Observaciones", key=f"obs_{idx}")
                    
                    if st.button("✅ Confirmar Item", key=f"btn_{idx}", type="primary"):
                        if lote_real and cant_real > 0:
                            lote_final = lote_real.strip().upper()
                            df_m.loc[idx, 'Estado_Prep'] = 'TERMINADO'
                            df_m.loc[idx, 'Numero de Lote'] = lote_final
                            df_m.loc[idx, 'Cantidad'] = cant_real * -1
                            df_m.loc[idx, 'Observaciones'] = f"{row['Observaciones']} | {obs_dep}"
                            
                            mask_stock = (df_s['Cod Producto'] == row['Cod Producto']) & (df_s['Numero de Lote'] == lote_final)
                            if mask_stock.any(): df_s.loc[mask_stock, 'Cantidad'] -= cant_real
                            else:
                                new_stk = {'Cod Producto': row['Cod Producto'], 'Numero de Lote': lote_final, 'Cantidad': -cant_real}
                                df_s = pd.concat([df_s, pd.DataFrame([new_stk])], ignore_index=True)
                            
                            save_all(df_p, df_s, df_m); st.rerun()
                        else: st.error("Ingrese Lote y Cantidad Real.")

def vista_consultas():
    c_head1, c_head2 = st.columns([1, 4])
    with c_head1:
        if st.button("⬅️ Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c_head2:
        st.subheader("Stock & Historial")

    df_p, df_s, df_m = load_data()
    t1, t2 = st.tabs(["📦 STOCK REAL", "📋 HISTORIAL"])
    
    with t1:
        if not df_s.empty:
            df_view = df_s[df_s['Cantidad'] != 0].copy()
            # Limpieza de ceros
            for c in ['SENASA', 'Cod_Barras', 'Numero de Lote']:
                if c in df_view.columns: df_view[c] = df_view[c].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '')

            if 'Fecha_Vencimiento' in df_view.columns:
                df_view = df_view.sort_values('Fecha_Vencimiento')
                st.dataframe(
                    df_view.style.map(aplicar_semaforo, subset=['Fecha_Vencimiento'])
                    .format({'Fecha_Vencimiento': lambda x: x.strftime('%d-%m-%Y') if pd.notnull(x) else '-'}),
                    use_container_width=True, height=600,
                    column_config={"Cantidad": st.column_config.NumberColumn(format="%.2f")}
                )
    with t2:
        if not df_m.empty:
            st.dataframe(df_m.sort_values('Fecha Hora', ascending=False), use_container_width=True, height=600, column_config={"Cantidad": st.column_config.NumberColumn(format="%.2f"), "Observaciones": st.column_config.TextColumn(width="large")})

# --- ROUTER ---
if st.session_state.vista == "Menu": vista_menu()
elif st.session_state.vista == "Ingreso": vista_ingreso()
elif st.session_state.vista == "Carga": vista_carga()
elif st.session_state.vista == "Espera": vista_espera()
elif st.session_state.vista == "Consultas": vista_consultas()
