import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import qrcode
from io import BytesIO
import re
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="AgroCheck Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. DISEÑO "NOCHE ESTRELLADA" (Starry Night) ---
def cargar_diseño():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Poppins:wght@500;700&display=swap');

        :root {
            --bg-top: #020617;
            --bg-bottom: #1e3a8a;
            --border: #334155;
        }

        .stApp {
            background: linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 100%);
            background-attachment: fixed;
            color: #f1f5f9;
            font-family: 'Inter', sans-serif;
        }

        section[data-testid="stSidebar"] {
            background-color: #0b1120;
            border-right: 1px solid var(--border);
        }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] div {
            color: #e2e8f0 !important;
        }

        h1, h2, h3 {
            font-family: 'Poppins', sans-serif;
            color: #ffffff !important;
            font-weight: 700;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }
        h1 {
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 30px;
            background: linear-gradient(to right, #ffffff, #fbbf24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            backdrop-filter: blur(5px);
        }
        
        .menu-card-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #fbbf24;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .menu-card-desc {
            color: #cbd5e1;
            margin-bottom: 1.5rem;
            font-size: 0.95rem;
        }

        /* INPUTS BLANCOS */
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #94a3b8 !important;
            border-radius: 8px !important;
        }
        input {
            color: #000000 !important;
            caret-color: #000000;
        }
        div[data-baseweb="select"] span {
            color: #000000 !important;
        }
        label, .stMarkdown p {
            color: #e2e8f0 !important;
        }

        div[data-testid="stButton"] > button {
            border-radius: 8px;
            font-weight: 700;
            border: none;
            height: 3em;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #0f172a;
            box-shadow: 0 0 15px rgba(245, 158, 11, 0.4);
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            transform: scale(1.03);
            box-shadow: 0 0 25px rgba(245, 158, 11, 0.6);
        }
        div[data-testid="stButton"] > button[kind="secondary"] {
            background-color: transparent;
            border: 1px solid #60a5fa;
            color: #60a5fa;
        }
        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background-color: #60a5fa;
            color: white;
            box-shadow: 0 0 10px #60a5fa;
        }
        
        button[kind="secondary"]:has(div:contains("🗑️")) {
            border-color: #ff4545 !important;
            color: #ff4545 !important;
        }
        button[kind="secondary"]:has(div:contains("🗑️")):hover {
            background-color: #ff4545 !important;
            color: white !important;
            box-shadow: 0 0 15px #ff4545;
        }

        .qr-box {
            background-color: white;
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            margin-top: 20px;
            margin-bottom: 20px;
            box-shadow: 0 0 20px rgba(255, 255, 255, 0.2);
        }
        
        div[data-testid="stDataFrame"] {
            background-color: #0f172a;
            border: 1px solid var(--border);
            border-radius: 10px;
        }

        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

cargar_diseño()

# ---------------------------------------------------------
# ✅ TU BASE DE DATOS
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UFsJ0eQ40hfKfL31e2I9mjUGNnk-6E2PkBmK4rKONAM/edit"
# ---------------------------------------------------------

# --- CONEXIÓN ---
def get_db_connection():
    return st.connection("gsheets", type=GSheetsConnection)

# --- ESTADO ---
if 'vista' not in st.session_state: st.session_state.vista = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'destino_actual' not in st.session_state: st.session_state.destino_actual = ""

# --- FUNCIONES DE DATOS ---
def limpiar_columnas(df):
    if df.empty: return df
    df.columns = df.columns.str.strip()
    return df

def load_data():
    try:
        conn = get_db_connection()
        df_prod = conn.read(spreadsheet=SHEET_URL, worksheet="Productos", ttl=5)
        df_stock = conn.read(spreadsheet=SHEET_URL, worksheet="Stock_Real", ttl=5)
        df_mov = conn.read(spreadsheet=SHEET_URL, worksheet="Movimientos", ttl=5)
        
        df_prod = limpiar_columnas(df_prod)
        df_stock = limpiar_columnas(df_stock)
        df_mov = limpiar_columnas(df_mov)

        if not df_prod.empty and 'Cod Producto' not in df_prod.columns:
            for col in df_prod.columns:
                if col.lower() in ['codigo', 'cod_producto', 'id', 'cod']:
                    df_prod.rename(columns={col: 'Cod Producto'}, inplace=True)
                    break
        
        if not df_prod.empty and 'Cod Producto' not in df_prod.columns:
            st.error("🛑 Error: No encuentro la columna 'Cod Producto' en la hoja Productos.")
            st.stop()

        if df_prod.empty: df_prod = pd.DataFrame(columns=['Cod Producto', 'Nombre comercial'])
        if 'Fecha_Vencimiento' not in df_stock.columns: df_stock['Fecha_Vencimiento'] = None
        df_stock['Fecha_Vencimiento'] = pd.to_datetime(df_stock['Fecha_Vencimiento'], errors='coerce')
        if 'Fecha Hora' in df_mov.columns: df_mov['Fecha Hora'] = pd.to_datetime(df_mov['Fecha Hora'], errors='coerce')
        
        # --- FUERZA BRUTA DE MAYÚSCULAS AL LEER ---
        if not df_stock.empty and 'Numero de Lote' in df_stock.columns:
            df_stock['Numero de Lote'] = df_stock['Numero de Lote'].astype(str).str.strip().str.upper()
        if not df_mov.empty and 'Numero de Lote' in df_mov.columns:
            df_mov['Numero de Lote'] = df_mov['Numero de Lote'].astype(str).str.strip().str.upper()

        return df_prod, df_stock, df_mov
    except Exception as e:
        if "Quota exceeded" in str(e): st.warning("⚠️ Espera unos segundos..."); st.stop()
        st.error(f"Error cargando datos: {e}"); st.stop()

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
    except Exception as e: st.error(f"Error guardando: {e}")

def aplicar_semaforo(val):
    if pd.isna(val): return ''
    hoy = datetime.now()
    alerta = hoy + timedelta(days=90)
    if val < hoy: return 'color: #ff4545; font-weight: bold; text-shadow: 0 0 5px #ff4545;'
    elif val < alerta: return 'color: #ffd700; font-weight: bold;'
    else: return 'color: #4ade80; font-weight: bold;'

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 📱 AgroCheck Mobile")
    url_app = "https://agrocheck-portfolio.streamlit.app" 
    
    qr = qrcode.QRCode(version=1, box_size=8, border=0)
    qr.add_data(url_app); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white") 
    buf = BytesIO(); img.save(buf, format="PNG")
    
    st.markdown('<div class="qr-box">', unsafe_allow_html=True)
    st.image(buf.getvalue(), use_container_width=True)
    st.markdown('<p style="color:black; margin:0; font-weight:bold;">ESCANEAR ACCESO</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- VISTAS ---

def vista_menu():
    st.title("Gestión Depósito Agroquímicos")
    st.write("") 
    
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("""
                <div class="menu-card-title">🖥️ Oficina Técnica</div>
                <div class="menu-card-desc">Gestión administrativa, órdenes de egreso y altas.</div>
            """, unsafe_allow_html=True)
            if st.button("NUEVA ORDEN DE SALIDA", use_container_width=True, type="primary"):
                st.session_state.vista = "Carga"; st.rerun()
            if st.button("INGRESO DE MERCADERÍA", use_container_width=True):
                st.session_state.vista = "Ingreso"; st.rerun()
            
    with c2:
        with st.container(border=True):
            st.markdown("""
                <div class="menu-card-title">📦 Depósito / Operativa</div>
                <div class="menu-card-desc">Control de inventario físico y pedidos.</div>
            """, unsafe_allow_html=True)
            if st.button("ARMAR PEDIDOS", use_container_width=True):
                st.session_state.vista = "Espera"; st.rerun()
            if st.button("STOCK E HISTORIAL", use_container_width=True):
                st.session_state.vista = "Consultas"; st.rerun()

def vista_ingreso():
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("⬅️ Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c2: st.subheader("Ingreso de Stock")

    df_p, df_s, df_m = load_data()
    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict() if not df_p.empty else {}

    with st.container(border=True):
        col_switch, _ = st.columns([2,1])
        es_nuevo = col_switch.checkbox("➕ ¿Producto NUEVO?")

        if es_nuevo:
            c_new1, c_new2 = st.columns(2)
            cod_p = c_new1.text_input("Código Nuevo").strip()
            nom_p_display = c_new2.text_input("Nombre Comercial").strip()
        else:
            if df_p.empty: st.warning("Lista vacía."); cod_p = None
            else:
                c1, c2 = st.columns(2)
                cod_p = c1.selectbox("Producto", df_p['Cod Producto'].unique(), format_func=lambda x: f"{x} | {prod_map.get(x, '')}")
                nom_p_display = prod_map.get(cod_p, '')
                cuenta = c2.text_input("Cuenta / Propiedad")

        st.markdown("---")
        c3, c4, c5, c6 = st.columns(4)
        lote = c3.text_input("N° Lote")
        senasa = c4.text_input("SENASA")
        cod_barra = c5.text_input("GTIN/Cod Barra")
        fecha_venc = c6.date_input("Vencimiento")

    with st.container(border=True):
        st.markdown("**Calculadora de Cantidad**")
        cc1, cc2, cc3 = st.columns(3)
        n1 = cc1.number_input("Cant. Bultos", min_value=0.0, value=None, placeholder="0")
        n2 = cc2.number_input("Tamaño Unitario", min_value=0.0, value=None, placeholder="0")
        unidad = cc3.selectbox("Unidad", ["Litros", "Kilos", "Gramos", "Cm3 / Ml", "Unidad / Kit"])
        
        total_bruto = (n1 or 0) * (n2 or 0)
        cant_final = total_bruto / 1000 if unidad in ["Gramos", "Cm3 / Ml"] else total_bruto
        msg_unidad = "Kg/L" if unidad in ["Gramos", "Cm3 / Ml"] else unidad
        st.metric("Total a Ingresar", f"{cant_final:.2f} {msg_unidad}")

    if st.button("💾 GUARDAR", type="primary", use_container_width=True):
        if not lote or cant_final <= 0: st.error("Faltan datos."); return
        
        # --- FORZAR MAYÚSCULAS SIEMPRE ---
        lote_final = lote.strip().upper()

        if es_nuevo:
            df_p = pd.concat([df_p, pd.DataFrame([{'Cod Producto': cod_p, 'Nombre comercial': nom_p_display}])], ignore_index=True)

        mask = (df_s['Cod Producto'] == cod_p) & (df_s['Numero de Lote'] == lote_final)
        fecha_venc_dt = pd.to_datetime(fecha_venc)

        if mask.any():
            df_s.loc[mask, 'Cantidad'] += cant_final
            df_s.loc[mask, 'Fecha_Vencimiento'] = fecha_venc_dt
        else:
            new_row = {'Cod Producto': cod_p, 'Numero de Lote': lote_final, 'Cantidad': cant_final, 'SENASA': senasa, 'Cod_Barras': cod_barra, 'Fecha_Vencimiento': fecha_venc_dt}
            df_s = pd.concat([df_s, pd.DataFrame([new_row])], ignore_index=True)
        
        obs = f"Ingreso: {n1} x {n2} {unidad}"
        mov = {'Fecha Hora': datetime.now(), 'ID_Pedido': "INGRESO", 'Usuario': "Admin", 'Tipo de movimiento': "Compra", 'Cod Producto': cod_p, 'Cuenta/Entidad': locals().get('cuenta', ''), 'Numero de Lote': lote_final, 'Cantidad': cant_final, 'Destino Origen': "Depósito", 'Observaciones': obs, 'Estado_Prep': 'TERMINADO'}
        
        df_m = pd.concat([df_m, pd.DataFrame([mov])], ignore_index=True)
        save_all(df_p, df_s, df_m)
        st.success("Guardado!"); time.sleep(1); st.session_state.vista="Menu"; st.rerun()

def vista_carga():
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("⬅️ Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c2: st.subheader("Nueva Orden de Salida")

    df_p, df_s, _ = load_data()
    if df_p.empty: st.warning("Base de datos vacía."); return
    
    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict()

    with st.container(border=True):
        c1, c2 = st.columns(2)
        st.session_state.destino_actual = c1.text_input("Destino / Cliente:", value=st.session_state.destino_actual)
        cuenta = c2.text_input("Cuenta:")

    with st.container(border=True):
        c_prod, c_type = st.columns([2, 1])
        sel_prod = c_prod.selectbox("Producto", df_p['Cod Producto'].unique(), format_func=lambda x: f"{x} | {prod_map.get(x,'')}")
        tipo_op = c_type.selectbox("Motivo", ["Venta", "Transferencia", "Uso Interno"])

        stock_prod = df_s[df_s['Cod Producto'] == sel_prod].copy()
        if stock_prod.empty:
            st.warning("⚠️ Sin stock de este producto.")
            lote_selec = None
            stock_disp = 0
        else:
            stock_prod['Vence'] = pd.to_datetime(stock_prod['Fecha_Vencimiento']).dt.strftime('%d/%m/%Y')
            opciones = stock_prod.apply(lambda row: f"{row['Numero de Lote']} (Disp: {row['Cantidad']:.2f} | Vence: {row['Vence']})", axis=1).tolist()
            lote_str = st.selectbox("Seleccionar Lote", opciones)
            lote_selec = lote_str.split(" (")[0]
            stock_disp = stock_prod[stock_prod['Numero de Lote'] == lote_selec]['Cantidad'].values[0]

        cc1, cc2, cc3 = st.columns(3)
        n1 = cc1.number_input("Cant. Envases", min_value=0.0, value=None, placeholder="0")
        n2 = cc2.number_input("Lts/Kg Envase", min_value=0.0, value=None, placeholder="0")
        total = (n1 or 0) * (n2 or 0)
        cc3.metric("Total Salida", f"{total:.2f}")

    if st.button("➕ AGREGAR AL PEDIDO", type="secondary", use_container_width=True):
        if not lote_selec:
            st.error("⛔ Debe seleccionar un lote válido.")
        elif total <= 0:
            st.error("⛔ La cantidad total debe ser mayor a 0.")
        elif total > stock_disp:
            st.error(f"⛔ STOCK INSUFICIENTE. Pide {total:.2f} pero solo hay {stock_disp:.2f} en este lote.")
        else:
            st.session_state.carrito.append({"cod": sel_prod, "nom": prod_map.get(sel_prod), "cant": total, "lote_asig": lote_selec, "det": f"{n1} env x {n2}", "tipo": tipo_op, "cta": cuenta})

    if st.session_state.carrito:
        st.markdown("##### 🛒 Carrito (Items en preparación)")
        
        for i, item in enumerate(st.session_state.carrito):
            with st.container(border=True):
                c_data, c_del = st.columns([5, 1])
                with c_data:
                    st.markdown(f"**{item['nom']}**")
                    st.caption(f"Lote: {item['lote_asig']} | Cant: {item['cant']:.2f} | Detalle: {item['det']}")
                with c_del:
                    if st.button("🗑️", key=f"del_{i}", type="secondary"):
                        st.session_state.carrito.pop(i)
                        st.rerun()

        if st.button("✅ CONFIRMAR Y ENVIAR", type="primary", use_container_width=True):
            if not st.session_state.destino_actual:
                st.error("⛔ Faltan datos: Ingrese Destino / Cliente.")
            else:
                id_ped = f"PED-{int(time.time())}"
                conn = get_db_connection()
                df_m_live = conn.read(spreadsheet=SHEET_URL, worksheet="Movimientos", ttl=0)
                new_rows = []
                for item in st.session_state.carrito:
                    new_rows.append({'Fecha Hora': datetime.now(), 'ID_Pedido': id_ped, 'Usuario': "Oficina", 'Tipo de movimiento': item['tipo'], 'Cod Producto': item['cod'], 'Cuenta/Entidad': item['cta'], 'Numero de Lote': item['lote_asig'], 'Cantidad': item['cant'] * -1, 'Destino Origen': st.session_state.destino_actual, 'Observaciones': item['det'], 'Estado_Prep': 'PENDIENTE'})
                
                df_m_live = pd.concat([df_m_live, pd.DataFrame(new_rows)], ignore_index=True)
                save_all(df_p, df_s, df_m_live)
                
                st.session_state.carrito = [] 
                st.success("✅ Pedido Enviado Exitosamente!") 
                time.sleep(1)
                st.rerun()

def vista_espera():
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("⬅️ Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c2: st.subheader("Armado de Pedidos")

    df_p, df_s, df_m = load_data()
    if df_p.empty: st.info("Sin datos."); return
    
    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict()
    
    pendientes = df_m[df_m['Estado_Prep'] == 'PENDIENTE'].copy()
    if pendientes.empty: st.info("No hay pendientes."); return

    ped_id = st.selectbox("Seleccionar Pedido", pendientes['ID_Pedido'].unique())
    items = pendientes[pendientes['ID_Pedido'] == ped_id]
    st.info(f"Cliente: **{items.iloc[0]['Destino Origen']}**")

    for idx, row in items.iterrows():
        with st.container(border=True):
            c_info, c_action = st.columns([1, 2])
            
            cant_pedida = abs(row['Cantidad'])
            
            with c_info:
                st.markdown(f"**{prod_map.get(row['Cod Producto'], row['Cod Producto'])}**")
                st.caption(f"Lote Solicitado: {row['Numero de Lote']}")
                st.markdown(f"📦 Cant Pedida: **{cant_pedida:.2f}**")
            
            with c_action:
                c1, c2, c3 = st.columns(3)
                l_real = c1.text_input("Lote Real", key=f"l_{idx}")
                cant_env = c2.number_input("Cant. Envases", min_value=0.0, value=None, placeholder="0", key=f"c_{idx}")
                tam_env = c3.number_input("Lts/Kg Envase", min_value=0.0, value=None, placeholder="0", key=f"t_{idx}")
                
                # --- CALCULADORA Y VALIDACIÓN EN TIEMPO REAL ---
                real_total = (cant_env or 0) * (tam_env or 0)
                
                if real_total > 0:
                    diff = real_total - cant_pedida
                    # Si la diferencia es casi cero (tolerancia 0.01)
                    if abs(diff) < 0.01:
                        st.success(f"✅ Total: {real_total:.2f} (Correcto)")
                    else:
                        st.error(f"❌ Total: {real_total:.2f} (Difiere: {diff:.2f})")
                
                if st.button("Confirmar", key=f"b_{idx}", type="primary"):
                    error = False
                    # 1. Validación de Mayúsculas y Texto
                    if not l_real: 
                        st.error("Falta el Lote Real."); error = True
                    
                    # 2. Validación Estricta de Cantidad
                    if abs(real_total - cant_pedida) > 0.01:
                        st.error(f"⛔ Error: La cantidad preparada ({real_total}) no coincide con la pedida ({cant_pedida}).")
                        error = True
                    
                    if not error:
                        # --- FORZAR MAYÚSCULAS ---
                        lote_final = l_real.strip().upper()
                        
                        df_m.loc[idx, 'Estado_Prep'] = 'TERMINADO'
                        df_m.loc[idx, 'Numero de Lote'] = lote_final
                        df_m.loc[idx, 'Cantidad'] = real_total * -1
                        
                        mask = (df_s['Cod Producto'] == row['Cod Producto']) & (df_s['Numero de Lote'] == lote_final)
                        
                        if mask.any(): 
                            df_s.loc[mask, 'Cantidad'] -= real_total
                        else: 
                            # Si cambia el lote y no existe, se crea en negativo (ajuste stock)
                            df_s = pd.concat([df_s, pd.DataFrame([{'Cod Producto': row['Cod Producto'], 'Numero de Lote': lote_final, 'Cantidad': -real_total}])], ignore_index=True)
                        
                        save_all(df_p, df_s, df_m)
                        st.rerun()

def vista_consultas():
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("⬅️ Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c2: st.subheader("Stock & Historial")

    df_p, df_s, df_m = load_data()
    t1, t2 = st.tabs(["📦 STOCK REAL", "📋 HISTORIAL"])
    
    with t1:
        if not df_s.empty:
            df_view = df_s[df_s['Cantidad'] != 0].copy()
            for col in ['SENASA', 'Cod_Barras', 'Numero de Lote']:
                if col in df_view.columns:
                    df_view[col] = df_view[col].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '')

            st.dataframe(
                df_view.style.map(aplicar_semaforo, subset=['Fecha_Vencimiento'])
                .format({'Fecha_Vencimiento': lambda x: x.strftime('%d-%m-%Y') if pd.notnull(x) else '-'}),
                use_container_width=True, height=600,
                column_config={"Cantidad": st.column_config.NumberColumn(format="%.2f")}
            )
    with t2:
        if not df_m.empty:
            st.dataframe(df_m.sort_values('Fecha Hora', ascending=False), use_container_width=True, height=600, column_config={"Cantidad": st.column_config.NumberColumn(format="%.2f")})

# --- ROUTER ---
if st.session_state.vista == "Menu": vista_menu()
elif st.session_state.vista == "Ingreso": vista_ingreso()
elif st.session_state.vista == "Carga": vista_carga()
elif st.session_state.vista == "Espera": vista_espera()
elif st.session_state.vista == "Consultas": vista_consultas()
