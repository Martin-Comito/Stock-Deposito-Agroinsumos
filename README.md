# AgroCheck Pro

**Gestión inteligente de stock para depósitos de agroquímicos.**

## Historia del Proyecto

Actualmente me encuentro trabajando en un depósito de agroquímicos. Hace un año, cuando arranqué a estudiar programación, empecé a ver mi entorno laboral con otros ojos y decidí buscarle una solución tecnológica a un problema real que enfrentamos todos los días: **el control de stock**.

En la logística diaria, el flujo de información suele cortarse o demorarse entre la oficina y el depósito. Esto genera el clásico problema donde el "Stock de Sistema" difiere del "Stock Real" físico.

Desarrollé **AgroCheck Pro** con un objetivo claro: **achicar considerablemente esa incidencia**. La herramienta digitaliza el proceso en el momento exacto en que ocurren los movimientos, obligando a una validación doble para asegurar que lo que sale del depósito es exactamente lo que se pidió.

## El Problema a Solucionar

* **Desincronización:** Diferencias constantes entre el Excel de la oficina y los bidones en el galpón.
* **Errores de Armado:** Confusión de lotes o productos similares al preparar pedidos con apuro.
* **Vencimientos:** Dificultad para visualizar rápidamente qué lotes están por vencer (riesgo de pérdida económica).
* **Falta de Herramientas:** El personal de depósito no suele tener computadoras a mano para verificar datos.

## Mi Solución

Creé una aplicación web accesible desde el celular que conecta ambas partes en tiempo real utilizando la nube.

### Funcionalidades Clave:
* ** Movilidad Total:** Implementé un sistema de login por **código QR** para que cualquier operario pueda usar la app desde su propio celular sin instalar nada.
* ** Validación Ciega (Blind Check):** Para evitar errores automáticos, el sistema no le dice al operario qué lote agarrar por defecto; el operario debe escanear/ingresar el lote que tiene en la mano. Si no coincide con el pedido, el sistema alerta y pide justificación.
* ** Base de Datos en Nube:** Migré la gestión de Excel local a **Google Sheets**, permitiendo que los datos persistan y sean accesibles 24/7 desde cualquier lugar.
* ** Semáforo de Vencimientos:** Una ayuda visual automática que prioriza la salida de productos próximos a vencer.

## Tecnologías que utilicé

* **Python 3.13** (Lógica del backend).
* **Streamlit** (Framework para el desarrollo rápido de la interfaz web).
* **Pandas** (Manipulación y análisis de datos).
* **Google Sheets API** (Base de datos en la nube).
* **QRCode** (Generación de accesos rápidos).

*Desarrollado por  Martin Ezequiel Comito - 2026*
