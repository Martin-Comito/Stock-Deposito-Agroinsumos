import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import qrcode
from io import BytesIO
import re
from streamlit_gsheets import GSheetsConnection

#CONFIGURACIÓN INICIAL
st.set_page_config(page_title="AgroCheck Pro", layout="wide")

# Diseño css
def cargar_diseño():
    st.markdown("""
        <style>
        /* FONDO GENERAL */
        .stApp {
            background-color: #f4f6f9;
        }

        /* TÍTULOS */
        h1, h2, h3 {
            color: #2e7d32; /* Verde Agro */
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            font-weight: 700;
        }
        h1 {
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }

        /* BOTONES PERSONALIZADOS */
        div[data-testid="stButton"] > button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            height: 3em;
        }
        /* Botón Primario */
        div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #2e7d32;
            border: none;
            color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: #1b5e20;
            transform: translateY(-2px);
        }
        /* Botón Secundario */
        div[data-testid="stButton"] > button[kind="secondary"] {
            background-color: #ffffff;
            border: 1px solid #2e7d32;
            color: #2e7d32;
        }
        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background-color: #e8f5e9;
        }

        /* TARJETAS DE MÉTRICAS */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 15px;
            border-left: 5px solid #2e7d32;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
        div[data-testid="stMetricValue"] {
            color: #1b5e20;
        }

        /* LIMPIEZA INTERFAZ */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# Activa el diseño
cargar_diseño()

#BASE DE DATOS
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UFsJ0eQ40hfKfL31e2I9mjUGNnk-6E2PkBmK4rKONAM/edit"

#CONEXIÓN GOOGLE SHEETS
def get_db_connection():
    return st.connection("gsheets", type=GSheetsConnection)

#ESTADO DE SESIÓN
if 'vista' not in st.session_state: st.session_state.vista = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'destino_actual' not in st.session_state: st.session_state.destino_actual = ""

#FUNCIONES DE DATOS
def load_data():
    try:
        conn = get_db_connection()
        #memoria de 5 segundos (ttl=5)
        df_prod = conn.read(spreadsheet=SHEET_URL, worksheet="Productos", ttl=5)
        df_stock = conn.read(spreadsheet=SHEET_URL, worksheet="Stock_Real", ttl=5)
        df_mov = conn.read(spreadsheet=SHEET_URL, worksheet="Movimientos", ttl=5)
        
        # Limpieza automática de títulos
        if not df_prod.empty: df_prod.columns = df_prod.columns.str.strip()
        if not df_stock.empty: df_stock.columns = df_stock.columns.str.strip()
        if not df_mov.empty: df_mov.columns = df_mov.columns.str.strip()

        # Validación básica
        if df_prod.empty: 
            df_prod = pd.DataFrame(columns=['Cod Producto', 'Nombre comercial'])
        
        if 'Cod Producto' not in df_prod.columns and not df_prod.empty:
            st.error(f"Error: No encuentro 'Cod Producto'. Columnas leídas: {df_prod.columns.tolist()}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        if 'Fecha_Vencimiento' not in df_stock.columns:
            df_stock['Fecha_Vencimiento'] = None
        df_stock['Fecha_Vencimiento'] = pd.to_datetime(df_stock['Fecha_Vencimiento'], errors='coerce')
        
        # Aseguramos que Fecha Hora sea datetime para poder ordenarla
        if 'Fecha Hora' in df_mov.columns:
            df_mov['Fecha Hora'] = pd.to_datetime(df_mov['Fecha Hora'], errors='coerce')
        
        return df_prod, df_stock, df_mov
    except Exception as e:
        if "Quota exceeded" in str(e):
            st.warning("Google está pidiendo un respiro. Espera 10 segundos y recarga.")
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
        
        #Convierte fecha de movimientos a string antes de guardar para evitar problemas
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
    if val < hoy: return 'background-color: #ff4b4b; color: white'
    elif val < alerta: return 'background-color: #ffd700; color: black'
    else: return 'background-color: #90ee90; color: black'

#SIDEBAR
with st.sidebar:
    st.title("📲 Móvil")
    url_app = "https://agrocheck-portfolio.streamlit.app" 
    
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(url_app); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO(); img.save(buf, format="PNG")
    st.image(buf.getvalue(), caption="Escanear para conectar")
    st.caption("Desarrollado con Python & Streamlit")

#VISTAS

def vista_menu():
    st.markdown("<h1 style='text-align: center;'>Gestión Depósito Agroquímicos</h1>", unsafe_allow_html=True)
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("NUEVA ORDEN (OFICINA)", use_container_width=True, type="primary"):
            st.session_state.vista = "Carga"; st.rerun()
        if st.button("INGRESO MERCADERÍA", use_container_width=True):
            st.session_state.vista = "Ingreso"; st.rerun()
    with col2:
        if st.button("ARMAR PEDIDOS (DEPÓSITO)", use_container_width=True):
            st.session_state.vista = "Espera"; st.rerun()
        if st.button("STOCK E HISTORIAL", use_container_width=True):
            st.session_state.vista = "Consultas"; st.rerun()

def vista_ingreso():
    if st.button("Volver al Menú Principal"): st.session_state.vista = "Menu"; st.rerun()
    st.subheader("Ingreso de Stock")
    df_p, df_s, df_m = load_data()
    
    if not df_p.empty:
        prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict()
    else:
        prod_map = {}

    #OPCIÓN DE PRODUCTO NUEVO
    col_switch, _ = st.columns([2,1])
    es_nuevo = col_switch.checkbox("➕ ¿Es un producto NUEVO?")

    if es_nuevo:
        st.markdown("### Alta de Producto Nuevo")
        c_new1, c_new2 = st.columns(2)
        cod_p_input = c_new1.text_input("Definir Nuevo Código (Corto)", placeholder="Ej: FUNG_NUEVO")
        nom_p_input = c_new2.text_input("Nombre Comercial Completo", placeholder="Ej: Fungicida Nuevo 5L")
        
        cod_p = cod_p_input.strip()
        nom_p_display = nom_p_input.strip()
    else:
        # Selección normal
        if df_p.empty:
            st.warning("No hay productos. Marca la casilla de arriba para crear uno.")
            cod_p = None
            nom_p_display = ""
        else:
            c1, c2 = st.columns(2)
            cod_p = c1.selectbox("Producto", df_p['Cod Producto'].unique(), format_func=lambda x: f"{x} | {prod_map.get(x, '')}")
            nom_p_display = prod_map.get(cod_p, '')
            cuenta = c2.text_input("Cuenta / Propiedad")

    if not es_nuevo:
        st.markdown("---")

    #DATOS DEL LOTE
    c3, c4, c5, c6 = st.columns(4)
    lote = c3.text_input("N° Lote")
    senasa = c4.text_input("SENASA")
    cod_barra = c5.text_input("GTIN/Cod Barra")
    fecha_venc = c6.date_input("Fecha Vencimiento")

    st.info("Calculadora de Cantidad Inteligente")
    
    #SECCIÓN DE UNIDADES CON CONVERSIÓN
    col_calc1, col_calc2, col_calc3 = st.columns(3)
    n1 = col_calc1.number_input("Cant. de Envases/Bultos", min_value=0.0, value=None, placeholder="0")
    n2 = col_calc2.number_input("Tamaño por Envase", min_value=0.0, value=None, placeholder="0")
    unidad = col_calc3.selectbox("Unidad de Medida", ["Litros", "Kilos", "Gramos", "Cm3 / Ml", "Unidad / Kit"])
    
    val_n1 = n1 if n1 is not None else 0.0
    val_n2 = n2 if n2 is not None else 0.0
    total_bruto = val_n1 * val_n2
    
    # Conversión
    if unidad == "Gramos" or unidad == "Cm3 / Ml":
        cant_final = total_bruto / 1000
        msg_unidad = "Kg/L (Convertido autom.)"
    else:
        cant_final = total_bruto
        msg_unidad = unidad

    st.metric(label=f"Total a Ingresar ({msg_unidad})", value=f"{cant_final:.2f}")

    if st.button("Guardar Ingreso", type="primary"):
        error = False
        if not lote or cant_final <= 0:
            st.error("Faltan datos: Lote o Cantidad."); error = True
        
        if es_nuevo:
            if not cod_p or not nom_p_display:
                st.error("Para productos nuevos, Código y Nombre son obligatorios."); error = True
            if cod_p in prod_map:
                st.error("¡Ese código ya existe! Úsalo desde la lista o cambia el código."); error = True
        
        if not error:
            # 1. Alta de Producto (si aplica)
            if es_nuevo:
                new_prod_row = {'Cod Producto': cod_p, 'Nombre comercial': nom_p_display}
                df_p = pd.concat([df_p, pd.DataFrame([new_prod_row])], ignore_index=True)
                st.toast(f"Producto '{nom_p_display}' creado!")

            # 2. Guardar Stock
            mask = (df_s['Cod Producto'] == cod_p) & (df_s['Numero de Lote'] == lote)
            fecha_venc_dt = pd.to_datetime(fecha_venc)

            if mask.any():
                df_s.loc[mask, 'Cantidad'] += cant_final
                df_s.loc[mask, 'Fecha_Vencimiento'] = fecha_venc_dt
            else:
                new_row = {'Cod Producto': cod_p, 'Numero de Lote': lote, 'Cantidad': cant_final, 'SENASA': senasa, 'Cod_Barras': cod_barra, 'Fecha_Vencimiento': fecha_venc_dt}
                df_s = pd.concat([df_s, pd.DataFrame([new_row])], ignore_index=True)
            
            # 3. Guardar Movimiento
            obs_detalle = f"Ingreso: {val_n1} envases de {val_n2} {unidad}"
            if es_nuevo: obs_detalle += " (ALTA DE PRODUCTO)"
            cta_mov = "Stock Inicial" if es_nuevo else (locals().get('cuenta') or "")

            mov = {
                'Fecha Hora': datetime.now(), 'ID_Pedido': "INGRESO", 
                'Usuario': "Admin", 'Tipo de movimiento': "Compra", 'Cod Producto': cod_p, 
                'Cuenta/Entidad': cta_mov, 'Numero de Lote': lote, 'Cantidad': cant_final, 
                'Destino Origen': "Depósito", 'Observaciones': obs_detalle, 'Estado_Prep': 'TERMINADO'
            }
            df_m = pd.concat([df_m, pd.DataFrame([mov])], ignore_index=True)
            
            save_all(df_p, df_s, df_m)
            st.success(f"Guardado exitosamente: {cant_final} {msg_unidad}"); time.sleep(1.5); st.session_state.vista="Menu"; st.rerun()

def vista_carga():
    if st.button("Volver al Menú Principal"): st.session_state.vista = "Menu"; st.rerun()
    st.subheader("Nueva Orden de Egreso (Oficina)")
    df_p, df_s, _ = load_data()
    
    if df_p.empty: st.warning("Error leyendo productos."); return

    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict()

    c1, c2 = st.columns(2)
    st.session_state.destino_actual = c1.text_input("Destino / Cliente:", value=st.session_state.destino_actual)
    cuenta = c2.text_input("Cuenta a Descontar:")

    st.divider()
    col_a, col_b = st.columns([2, 1])
    sel_prod = col_a.selectbox("Seleccionar Producto", df_p['Cod Producto'].unique(), format_func=lambda x: f"{x} | {prod_map.get(x,'')}")
    tipo_op = col_b.selectbox("Tipo", ["Venta", "Transferencia", "Uso Interno"])

    st.markdown("Seleccionar Lote de Origen:")
    stock_prod = df_s[df_s['Cod Producto'] == sel_prod].copy()
    
    if stock_prod.empty:
        st.error("No hay stock registrado de este producto.")
        lote_selec = None; stock_disp = 0
    else:
        stock_prod['Vence'] = pd.to_datetime(stock_prod['Fecha_Vencimiento']).dt.strftime('%d/%m/%Y')
        # La cantidad se vera con 2 decimales
        opciones_lote = stock_prod.apply(lambda row: f"{row['Numero de Lote']} (Disp: {row['Cantidad']:.2f} | Vence: {row['Vence']})", axis=1).tolist()
        lote_str = st.selectbox("Lote a utilizar", opciones_lote)
        lote_selec = lote_str.split(" (")[0]
        stock_disp = stock_prod[stock_prod['Numero de Lote'] == lote_selec]['Cantidad'].values[0]

    st.markdown("Calculadora de Cantidad:")
    cc1, cc2, cc3 = st.columns(3)
    
    cant_bultos = cc1.number_input("Cant. Envases/Bolsas", min_value=0.0, value=None, placeholder="0")
    tam_bultos = cc2.number_input("Litros/Kg por Envase", value=None, placeholder="0")
    
    v_cb = cant_bultos if cant_bultos is not None else 0.0
    v_tb = tam_bultos if tam_bultos is not None else 0.0
    total_a_pedir = v_cb * v_tb
    cc3.metric("Total Solicitado", f"{total_a_pedir:.2f}")

    if st.button("AGREGAR AL PEDIDO"):
        if not lote_selec: st.error("Debe seleccionar un lote con stock.")
        elif total_a_pedir <= 0: st.error("La cantidad debe ser mayor a 0.")
        else:
            if total_a_pedir > stock_disp: st.warning(f"CUIDADO: Pide {total_a_pedir}, hay {stock_disp}.")
            st.session_state.carrito.append({
                "cod": sel_prod, "nom": prod_map.get(sel_prod), "cant": total_a_pedir, 
                "lote_asig": lote_selec, "det": f"{v_cb} env x {v_tb}", "tipo": tipo_op, "cta": cuenta
            })

    if st.session_state.carrito:
        st.write("### Items en Orden")
        st.table(pd.DataFrame(st.session_state.carrito))
        if st.button("CONFIRMAR Y ENVIAR A DEPÓSITO", type="primary"):
            if st.session_state.destino_actual:
                id_ped = f"PED-{int(time.time())}"
                
                conn = get_db_connection()
                df_m_live = conn.read(spreadsheet=SHEET_URL, worksheet="Movimientos", ttl=0)
                if not df_m_live.empty: df_m_live.columns = df_m_live.columns.str.strip()
                
                new_rows = []
                for item in st.session_state.carrito:
                    new_rows.append({
                        'Fecha Hora': datetime.now(), 'ID_Pedido': id_ped, 
                        'Usuario': "Oficina", 'Tipo de movimiento': item['tipo'], 'Cod Producto': item['cod'],
                        'Cuenta/Entidad': item['cta'], 'Numero de Lote': item['lote_asig'],
                        'Cantidad': item['cant'] * -1, 'Destino Origen': st.session_state.destino_actual,
                        'Observaciones': item['det'], 'Estado_Prep': 'PENDIENTE'
                    })
                df_m_live = pd.concat([df_m_live, pd.DataFrame(new_rows)], ignore_index=True)
                save_all(df_p, df_s, df_m_live)
                st.session_state.carrito = []
                st.success("Orden enviada exitosamente."); time.sleep(1); st.rerun()
            else: st.error("Falta el Destino")

def vista_espera():
    if st.button("Volver al Menú Principal"): st.session_state.vista = "Menu"; st.rerun()
    st.subheader("Armado de Pedidos (Depósito)")
    df_p, df_s, df_m = load_data()
    
    if df_p.empty or df_m.empty: st.info("Cargando datos..."); return
    
    prod_map = df_p.set_index('Cod Producto')['Nombre comercial'].to_dict()

    if 'Estado_Prep' not in df_m.columns: 
        st.error("No encuentro columna Estado_Prep en Movimientos")
        return

    pendientes = df_m[df_m['Estado_Prep'] == 'PENDIENTE'].copy()
    if pendientes.empty: st.info("No hay pedidos pendientes."); return

    lista_pedidos = pendientes['ID_Pedido'].unique()
    pedido_selec = st.selectbox("Seleccionar Pedido a Armar", lista_pedidos)

    if pedido_selec:
        items_pedido = pendientes[pendientes['ID_Pedido'] == pedido_selec]
        st.info(f"Destino: **{items_pedido.iloc[0]['Destino Origen']}**")
        
        for idx, row in items_pedido.iterrows():
            with st.container(border=True):
                col_info, col_accion = st.columns([1, 2])
                cant_solicitada_abs = abs(row['Cantidad'])
                lote_solicitado = str(row['Numero de Lote'])
                prod_nom = prod_map.get(row['Cod Producto'], row['Cod Producto'])
                
                with col_info:
                    st.markdown(f"**Prod:** {prod_nom}")
                    st.markdown(f"**Lote PEDIDO:** `{lote_solicitado}`")
                    st.markdown(f"**Cant PEDIDA:** `{cant_solicitada_abs:.2f}`")

                with col_accion:
                    c_lote, c_cant1, c_cant2 = st.columns(3)
                    lote_real = c_lote.text_input("Escanear Lote Real", value="", placeholder="Escanear...", key=f"l_{idx}")
                    cant_env = c_cant1.number_input("Cant. Envases", min_value=0.0, value=None, placeholder="0", key=f"ce_{idx}")
                    tam_env = c_cant2.number_input("Tamaño (Lts/Kg)", value=None, placeholder="0", key=f"te_{idx}")
                    
                    v_ce = cant_env if cant_env is not None else 0.0
                    v_te = tam_env if tam_env is not None else 0.0
                    cant_real_total = v_ce * v_te
                    
                    if cant_real_total > 0: st.write(f" Real: **{cant_real_total:.2f}**")
                    
                    alerta_stock = False; msg_alerta = ""
                    if abs(cant_real_total - cant_solicitada_abs) > 0.01 and cant_real_total > 0:
                        st.warning("Diferencia de Cantidad"); alerta_stock = True; msg_alerta += "Dif Cant. "
                    if lote_real:
                        l_real_norm = lote_real.strip().upper()
                        l_sol_norm = lote_solicitado.strip().upper()
                        if l_real_norm != l_sol_norm:
                            st.warning("Lote Distinto"); alerta_stock = True; msg_alerta += "Lote Distinto. "

                    obs_deposito = st.text_input("Obs (Obligatorio si hay cambios)", key=f"obs_{idx}")
                    
                    if st.button(f"Confirmar {prod_nom}", key=f"btn_{idx}"):
                        error = False
                        if not lote_real: st.error("Debe ingresar el Lote Real."); error = True
                        if alerta_stock and len(obs_deposito) < 3: st.error("Falta observación."); error = True
                        if cant_real_total <= 0: st.error("Cantidad inválida."); error = True
                            
                        if not error:
                            lote_final = lote_real.strip().upper()
                            df_m.loc[idx, 'Estado_Prep'] = 'TERMINADO'
                            df_m.loc[idx, 'Numero de Lote'] = lote_final
                            df_m.loc[idx, 'Cantidad'] = cant_real_total * -1
                            df_m.loc[idx, 'Observaciones'] = f"{row['Observaciones']} | {obs_deposito} {msg_alerta}"
                            
                            mask_stock = (df_s['Cod Producto'] == row['Cod Producto']) & (df_s['Numero de Lote'] == lote_final)
                            if mask_stock.any(): df_s.loc[mask_stock, 'Cantidad'] -= cant_real_total
                            else:
                                new_stk = {'Cod Producto': row['Cod Producto'], 'Numero de Lote': lote_final, 'Cantidad': -cant_real_total}
                                df_s = pd.concat([df_s, pd.DataFrame([new_stk])], ignore_index=True)
                            
                            save_all(df_p, df_s, df_m)
                            st.success("Item Confirmado"); time.sleep(1); st.rerun()

def vista_consultas():
    if st.button("⬅️ Volver al Menú Principal"): st.session_state.vista = "Menu"; st.rerun()
    st.subheader("Semáforo de Vencimientos y Stock")
    df_p, df_s, df_m = load_data()
    t1, t2 = st.tabs(["STOCK & VENCIMIENTOS", "MOVIMIENTOS"])
    
    with t1:
        if not df_s.empty:
            st.markdown("🔴 Vencido | 🟡 Vence < 90 días | 🟢 Vence > 90 días")
            df_view = df_s[df_s['Cantidad'] != 0].copy()
            
            # LIMPIEZA DE CÓDIGOS
            cols_to_clean = ['SENASA', 'Cod_Barras', 'Numero de Lote']
            for col in cols_to_clean:
                if col in df_view.columns:
                    df_view[col] = df_view[col].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '')

            if 'Fecha_Vencimiento' in df_view.columns:
                df_view = df_view.sort_values(by='Fecha_Vencimiento', ascending=True)
                
                st.dataframe(
                    df_view.style.map(aplicar_semaforo, subset=['Fecha_Vencimiento'])
                    .format({'Fecha_Vencimiento': lambda x: x.strftime('%d-%m-%Y') if pd.notnull(x) else '-'}), 
                    use_container_width=True, 
                    height=500,
                    column_config={
                        "Cantidad": st.column_config.NumberColumn("Cantidad", format="%.2f"),
                        "SENASA": st.column_config.TextColumn("SENASA"),
                        "Cod_Barras": st.column_config.TextColumn("Cod_Barras"),
                        "Numero de Lote": st.column_config.TextColumn("Numero de Lote")
                    }
                )
            else:
                st.dataframe(df_view, use_container_width=True)
        else: st.warning("Sin stock registrado.")
    with t2:
        if not df_m.empty and 'Fecha Hora' in df_m.columns:
            st.markdown("Historial Completo de Movimientos")
            st.dataframe(
                df_m.sort_values(by='Fecha Hora', ascending=False), 
                use_container_width=True,
                height=800, 
                column_config={
                    "Fecha Hora": st.column_config.DatetimeColumn("Fecha", format="D MMM YYYY, h:mm a"),
                    "Cantidad": st.column_config.NumberColumn(format="%.2f"),
                    "ID_Pedido": st.column_config.TextColumn("ID", width="medium"),
                    "Observaciones": st.column_config.TextColumn("Observaciones", width="large"), 
                    "Cod Producto": st.column_config.TextColumn("Producto", width="medium"),
                    "Numero de Lote": st.column_config.TextColumn("Lote"),
                }
            )
        else:
            st.dataframe(df_m, use_container_width=True)

#Router
if st.session_state.vista == "Menu": vista_menu()
elif st.session_state.vista == "Ingreso": vista_ingreso()
elif st.session_state.vista == "Carga": vista_carga()
elif st.session_state.vista == "Espera": vista_espera()
elif st.session_state.vista == "Consultas": vista_consultas()
