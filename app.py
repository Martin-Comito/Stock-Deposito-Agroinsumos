import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import qrcode
from io import BytesIO
import re
from streamlit_gsheets import GSheetsConnectio

st.set_page_config(page_title="AgroCheck Pro", layout="wide", initial_sidebar_state="expanded")

def cargar_diseño():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        :root {
            --primary: #0f4c81; 
            --bg-color: #f8fafc;
            --text-color: #1e293b;
            --card-bg: #ffffff;
            --border: #e2e8f0;
        }

        .stApp {
            background-color: var(--bg-color);
            font-family: 'Inter', sans-serif;
            color: var(--text-color);
        }

        h1, h2, h3 {
            color: var(--primary) !important;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        h1 {
            text-align: center;
            text-transform: uppercase;
            font-size: 2.2rem;
            margin-bottom: 30px;
            background: -webkit-linear-gradient(45deg, #0f4c81, #1e3a8a);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: var(--card-bg);
            border-radius: 10px;
            border: 1px solid var(--border);
            padding: 25px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }
        
        .menu-card-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .menu-card-desc {
            color: #64748b;
            margin-bottom: 1.5rem;
            font-size: 0.95rem;
        }

        div[data-testid="stButton"] > button {
            border-radius: 8px;
            font-weight: 600;
            height: 3em;
            border: none;
            transition: all 0.2s;
        }

        div[data-testid="stButton"] > button[kind="primary"] {
            background-color: var(--primary);
            color: white;
            box-shadow: 0 4px 6px rgba(15, 76, 129, 0.2);
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: #0c3b66;
            transform: translateY(-1px);
        }

        div[data-testid="stButton"] > button[kind="secondary"] {
            background-color: white;
            border: 1px solid #cbd5e1;
            color: #334155;
        }
        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            border-color: var(--primary);
            color: var(--primary);
            background-color: #f1f5f9;
        }

        section[data-testid="stSidebar"] {
            background-color: white;
            border-right: 1px solid var(--border);
        }

        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
            background-color: white !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 6px !important;
        }

        .qr-container {
            text-align: center;
            padding: 15px;
            background: white;
            border: 1px solid var(--border);
            border-radius: 10px;
            margin-bottom: 20px;
        }

        #MainMenu, footer, header {visibility: hidden;}
        
        /* Estilo especial para botón de borrar */
        button[kind="secondary"]:has(div:contains("🗑️")) {
            border-color: #ef4444 !important;
            color: #ef4444 !important;
        }
        button[kind="secondary"]:has(div:contains("🗑️")):hover {
            background-color: #fee2e2 !important;
        }
        </style>
    """, unsafe_allow_html=True)

cargar_diseño()

#BASE DE DATOS
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UFsJ0eQ40hfKfL31e2I9mjUGNnk-6E2PkBmK4rKONAM/edit"

#CONEXIÓN
def get_db_connection():
    return st.connection("gsheets", type=GSheetsConnection)

#ESTADO
if 'vista' not in st.session_state: st.session_state.vista = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'destino_actual' not in st.session_state: st.session_state.destino_actual = ""

#FUNCIONES DE DATOS
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
        
        if 'Fecha_Vencimiento' not in df_stock.columns: df_stock['Fecha_Vencimiento'] = None
        df_stock['Fecha_Vencimiento'] = pd.to_datetime(df_stock['Fecha_Vencimiento'], errors='coerce')
        if 'Fecha Hora' in df_mov.columns: df_mov['Fecha Hora'] = pd.to_datetime(df_mov['Fecha Hora'], errors='coerce')
        
        return df_prod, df_stock, df_mov
    except Exception as e:
        if "Quota exceeded" in str(e): st.warning("Espera unos segundos..."); return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        st.error(f"Error: {e}"); return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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
    if val < hoy: return 'color: #dc2626; font-weight: bold;' 
    elif val < alerta: return 'color: #d97706; font-weight: bold;'
    else: return 'color: #16a34a; font-weight: bold;'

#SIDEBAR
with st.sidebar:
    st.markdown("### 📱 AgroCheck App")
    url_app = "https://agrocheck-portfolio.streamlit.app" 
    
    qr = qrcode.QRCode(version=1, box_size=8, border=0)
    qr.add_data(url_app); qr.make(fit=True)
    img = qr.make_image(fill_color="#0f4c81", back_color="white") 
    buf = BytesIO(); img.save(buf, format="PNG")
    
    st.markdown('<div class="qr-container">', unsafe_allow_html=True)
    st.image(buf.getvalue(), use_container_width=True)
    st.caption("Escanear para acceder")
    st.markdown('</div>', unsafe_allow_html=True)

#VISTAS

def vista_menu():
    st.title("Gestión Depósito Agroquímicos")
    st.write("") 
    
    c1, c2 = st.columns(2)
    
    with c1:
        with st.container(border=True):
            st.markdown("""
                <div class="menu-card-title"> 🖥️  Oficina Técnica</div>
                <div class="menu-card-desc">Gestión administrativa, órdenes de egreso y altas.</div>
            """, unsafe_allow_html=True)
            
            if st.button("NUEVA ORDEN DE SALIDA", use_container_width=True, type="primary"):
                st.session_state.vista = "Carga"; st.rerun()
            if st.button("INGRESO DE MERCADERÍA", use_container_width=True):
                st.session_state.vista = "Ingreso"; st.rerun()
            
    with c2:
        with st.container(border=True):
            st.markdown("""
                <div class="menu-card-title"> 📦  Depósito / Operativa</div>
                <div class="menu-card-desc">Control de inventario físico y preparación de pedidos.</div>
            """, unsafe_allow_html=True)

            if st.button("ARMAR PEDIDOS", use_container_width=True):
                st.session_state.vista = "Espera"; st.rerun()
            if st.button("STOCK E HISTORIAL", use_container_width=True):
                st.session_state.vista = "Consultas"; st.rerun()

def vista_ingreso():
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c2: st.subheader("Ingreso de Stock")

    df_p, df_s, df_m = load_data()
    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict() if not df_p.empty else {}

    with st.container(border=True):
        col_switch, _ = st.columns([2,1])
        es_nuevo = col_switch.checkbox("¿Producto NUEVO?")

        if es_nuevo:
            c_new1, c_new2 = st.columns(2)
            cod_p = c_new1.text_input("Código Nuevo").strip()
            nom_p_display = c_new2.text_input("Nombre Comercial").strip()
        else:
            if df_p.empty: st.warning("Sin productos."); cod_p = None
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
        n1 = cc1.number_input("Cant. Bultos", min_value=0.0)
        n2 = cc2.number_input("Tamaño Unitario", min_value=0.0)
        unidad = cc3.selectbox("Unidad", ["Litros", "Kilos", "Gramos", "Cm3 / Ml", "Unidad / Kit"])
        
        total_bruto = (n1 or 0) * (n2 or 0)
        cant_final = total_bruto / 1000 if unidad in ["Gramos", "Cm3 / Ml"] else total_bruto
        msg_unidad = "Kg/L" if unidad in ["Gramos", "Cm3 / Ml"] else unidad
        st.metric("Total a Ingresar", f"{cant_final:.2f} {msg_unidad}")

    if st.button("GUARDAR", type="primary", use_container_width=True):
        if not lote or cant_final <= 0: st.error("Faltan datos."); return
        
        if es_nuevo:
            df_p = pd.concat([df_p, pd.DataFrame([{'Cod Producto': cod_p, 'Nombre comercial': nom_p_display}])], ignore_index=True)

        mask = (df_s['Cod Producto'] == cod_p) & (df_s['Numero de Lote'] == lote)
        fecha_venc_dt = pd.to_datetime(fecha_venc)

        if mask.any():
            df_s.loc[mask, 'Cantidad'] += cant_final
            df_s.loc[mask, 'Fecha_Vencimiento'] = fecha_venc_dt
        else:
            new_row = {'Cod Producto': cod_p, 'Numero de Lote': lote, 'Cantidad': cant_final, 'SENASA': senasa, 'Cod_Barras': cod_barra, 'Fecha_Vencimiento': fecha_venc_dt}
            df_s = pd.concat([df_s, pd.DataFrame([new_row])], ignore_index=True)
        
        obs = f"Ingreso: {n1} x {n2} {unidad}"
        mov = {'Fecha Hora': datetime.now(), 'ID_Pedido': "INGRESO", 'Usuario': "Admin", 'Tipo de movimiento': "Compra", 'Cod Producto': cod_p, 'Cuenta/Entidad': locals().get('cuenta', ''), 'Numero de Lote': lote, 'Cantidad': cant_final, 'Destino Origen': "Depósito", 'Observaciones': obs, 'Estado_Prep': 'TERMINADO'}
        
        df_m = pd.concat([df_m, pd.DataFrame([mov])], ignore_index=True)
        save_all(df_p, df_s, df_m)
        st.success("Guardado!"); time.sleep(1); st.session_state.vista="Menu"; st.rerun()

def vista_carga():
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c2: st.subheader("Nueva Orden de Salida")

    df_p, df_s, _ = load_data()
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
        if stock_prod.empty: st.warning("Sin stock"); lote_selec = None
        else:
            stock_prod['Vence'] = pd.to_datetime(stock_prod['Fecha_Vencimiento']).dt.strftime('%d/%m/%Y')
            opciones = stock_prod.apply(lambda row: f"{row['Numero de Lote']} (Disp: {row['Cantidad']:.2f} | Vence: {row['Vence']})", axis=1).tolist()
            lote_str = st.selectbox("Seleccionar Lote", opciones)
            lote_selec = lote_str.split(" (")[0]

        cc1, cc2, cc3 = st.columns(3)
        n1 = cc1.number_input("Cant. Envases", min_value=0.0)
        n2 = cc2.number_input("Lts/Kg Envase", min_value=0.0)
        total = (n1 or 0) * (n2 or 0)
        cc3.metric("Total Salida", f"{total:.2f}")

    if st.button("AGREGAR AL PEDIDO", type="secondary", use_container_width=True):
        if lote_selec and total > 0:
            st.session_state.carrito.append({"cod": sel_prod, "nom": prod_map.get(sel_prod), "cant": total, "lote_asig": lote_selec, "det": f"{n1} env x {n2}", "tipo": tipo_op, "cta": cuenta})

    if st.session_state.carrito:
        st.markdown("##### 🛒 Carrito (Items en preparación)")
        
        #índice para poder borrar
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

        if st.button("CONFIRMAR Y ENVIAR", type="primary", use_container_width=True):
            if st.session_state.destino_actual:
                id_ped = f"PED-{int(time.time())}"
                conn = get_db_connection()
                df_m_live = conn.read(spreadsheet=SHEET_URL, worksheet="Movimientos", ttl=0)
                new_rows = []
                for item in st.session_state.carrito:
                    new_rows.append({'Fecha Hora': datetime.now(), 'ID_Pedido': id_ped, 'Usuario': "Oficina", 'Tipo de movimiento': item['tipo'], 'Cod Producto': item['cod'], 'Cuenta/Entidad': item['cta'], 'Numero de Lote': item['lote_asig'], 'Cantidad': item['cant'] * -1, 'Destino Origen': st.session_state.destino_actual, 'Observaciones': item['det'], 'Estado_Prep': 'PENDIENTE'})
                
                df_m_live = pd.concat([df_m_live, pd.DataFrame(new_rows)], ignore_index=True)
                save_all(df_p, df_s, df_m_live)
                st.session_state.carrito = []; st.success("Enviado!"); time.sleep(1); st.rerun()
            else: st.error("Falta Destino")

def vista_espera():
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c2: st.subheader("Armado de Pedidos")

    df_p, df_s, df_m = load_data()
    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict()
    
    pendientes = df_m[df_m['Estado_Prep'] == 'PENDIENTE'].copy()
    if pendientes.empty: st.info("No hay pendientes."); return

    ped_id = st.selectbox("Seleccionar Pedido", pendientes['ID_Pedido'].unique())
    items = pendientes[pendientes['ID_Pedido'] == ped_id]
    st.info(f"Cliente: **{items.iloc[0]['Destino Origen']}**")

    for idx, row in items.iterrows():
        with st.container(border=True):
            c_info, c_action = st.columns([1, 2])
            with c_info:
                st.markdown(f"**{prod_map.get(row['Cod Producto'], row['Cod Producto'])}**")
                st.caption(f"Lote: {row['Numero de Lote']}")
                st.markdown(f"Cant: **{abs(row['Cantidad']):.2f}**")
            
            with c_action:
                c1, c2, c3 = st.columns(3)
                l_real = c1.text_input("Lote Real", key=f"l_{idx}")
                cant_env = c2.number_input("Envases", key=f"c_{idx}")
                tam_env = c3.number_input("Tam", key=f"t_{idx}")
                real_total = (cant_env or 0) * (tam_env or 0)
                
                if st.button("Confirmar", key=f"b_{idx}", type="primary"):
                    if l_real and real_total > 0:
                        df_m.loc[idx, 'Estado_Prep'] = 'TERMINADO'; df_m.loc[idx, 'Numero de Lote'] = l_real; df_m.loc[idx, 'Cantidad'] = real_total * -1
                        mask = (df_s['Cod Producto'] == row['Cod Producto']) & (df_s['Numero de Lote'] == l_real)
                        if mask.any(): df_s.loc[mask, 'Cantidad'] -= real_total
                        else: df_s = pd.concat([df_s, pd.DataFrame([{'Cod Producto': row['Cod Producto'], 'Numero de Lote': l_real, 'Cantidad': -real_total}])], ignore_index=True)
                        save_all(df_p, df_s, df_m); st.rerun()

def vista_consultas():
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Volver", type="secondary"): st.session_state.vista = "Menu"; st.rerun()
    with c2: st.subheader("Stock & Historial")

    df_p, df_s, df_m = load_data()
    t1, t2 = st.tabs(["📦 STOCK REAL", "📋 HISTORIAL"])
    
    with t1:
        if not df_s.empty:
            df_view = df_s[df_s['Cantidad'] != 0].copy()
            # Limpieza de ceros (.000)
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

#ROUTER
if st.session_state.vista == "Menu": vista_menu()
elif st.session_state.vista == "Ingreso": vista_ingreso()
elif st.session_state.vista == "Carga": vista_carga()
elif st.session_state.vista == "Espera": vista_espera()
elif st.session_state.vista == "Consultas": vista_consultas()
