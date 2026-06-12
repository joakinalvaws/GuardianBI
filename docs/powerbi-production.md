# Power BI en producción — guía de adopción

Dashboard Guardian audita en el MVP una simulación de dashboards
(`dashboard_snapshots`, ver ADR-001). Esta guía describe cómo conectar el
agente a **Power BI real** en una organización. El código ya está listo:
`backend/app/scanner/powerbi_client.py` autentica por client credentials y
consulta datasets con DAX vía `executeQueries` — solo faltan las cuentas,
los permisos y el workspace que se describen aquí (ver ADR-005).

## Requisitos

- Tenant de **Microsoft Entra ID** (cualquier organización con Microsoft 365 ya tiene uno)
- Licencia **Power BI Pro** o capacidad **Fabric** para el workspace
- Permisos de administrador de Fabric para habilitar el acceso de service principals
- **Power BI Desktop** (Windows) para crear y publicar el reporte

> Power BI no acepta cuentas personales (Gmail/Outlook personal). Si no
> existe tenant, se puede crear uno gratuito con una cuenta de Azure
> (Etapa 1); el trial de Fabric dura 60 días.

## Etapa 1 — Cuenta y tenant (solo si no existe tenant organizacional)

1. Crear una cuenta gratuita de Azure en [azure.microsoft.com/free](https://azure.microsoft.com/free) —
   esto provisiona un tenant de Entra ID ("Default Directory").
2. En el portal de Azure → **Microsoft Entra ID → Users → New user**, crear un
   usuario organizacional, p. ej. `guardian@<tenant>.onmicrosoft.com`
   (el nombre del tenant aparece en Entra ID → Overview).
3. En **Entra ID → Roles and administrators → Fabric Administrator**, asignar
   ese rol al usuario (lo necesita para la Etapa 2, paso 4).
4. Iniciar sesión en [app.fabric.microsoft.com](https://app.fabric.microsoft.com)
   con ese usuario y activar la **prueba gratuita de Fabric** — sin esto no se
   pueden crear workspaces ni usar la API.

## Etapa 2 — Registrar la aplicación (service principal)

1. Azure → Entra ID → **App registrations → New registration**: nombre
   `dashboard-guardian-agent`, single tenant, sin redirect URI.
2. En la app → **Certificates & secrets → New client secret** — copiar el
   *Value* inmediatamente (solo se muestra una vez).
3. Entra ID → **Groups → New group**: nombre `powerbi-apps`, tipo Security,
   y agregar la app como miembro.
4. Con un usuario administrador de Fabric en [app.powerbi.com](https://app.powerbi.com)
   → ⚙️ → **Admin portal → Tenant settings → Developer settings →
   "Service principals can use Fabric APIs"** → Enabled, aplicado al grupo
   `powerbi-apps`.

> No se necesitan permisos delegados de API en la app: el acceso se otorga
> por workspace (Etapa 3) una vez habilitado el tenant setting.

## Etapa 3 — Workspace y dataset conectado a la fuente

1. En Power BI Desktop: **Get Data → PostgreSQL** y conectar a la base de
   datos fuente. Para Supabase, usar el host del *connection pooler*
   (`aws-0-<region>.pooler.supabase.com`, puerto 5432 en session mode,
   usuario `postgres.<ref-del-proyecto>`) — los datos de conexión están en
   el dashboard de Supabase → Connect.
2. Importar las tablas de negocio (`ventas`, `sedes`, `productos`) y crear
   las medidas que espejan las métricas auditadas (`ventas_totales_mes`,
   `unidades_mes`, `margen_mes`, margen por sede).
3. **Publish** al workspace del equipo (p. ej. "Dashboard Guardian").
4. En el workspace → **Manage access → Add people or groups**: agregar el
   grupo `powerbi-apps` (o la app directamente) con rol **Member**.
5. Anotar el **workspace ID** (en la URL: `app.powerbi.com/groups/<id>/...`)
   y el **dataset ID** (Settings del dataset semántico).

> Para refresh programado del dataset Import contra una fuente PostgreSQL
> se necesita un On-premises Data Gateway. Alternativa sin gateway:
> conexión en DirectQuery, que consulta la fuente en vivo.

## Etapa 4 — Conectar el agente

1. Rellenar en `backend/.env` (campos ya definidos en `app/config.py`):

   ```bash
   POWERBI_TENANT_ID=<tenant id de Entra ID>
   POWERBI_CLIENT_ID=<application id de la app>
   POWERBI_CLIENT_SECRET=<el client secret>
   POWERBI_WORKSPACE_ID=<id del workspace>
   ```

   En GitHub Actions, agregarlos como secrets del repo y exponerlos en el
   step "Correr auditoría" de `.github/workflows/scheduler.yml`.

2. Verificar la conexión:

   ```python
   from app.scanner.powerbi_client import PowerBIClient
   print(PowerBIClient().list_datasets())
   ```

3. Reemplazar la lectura de `dashboard_snapshots` por consultas reales:
   los valores "mostrados por el dashboard" que hoy salen de la tabla
   (`backend/app/scanner/snapshot.py` y `backend/app/agent/tools.py`)
   pasan a obtenerse con `PowerBIClient.execute_dax(dataset_id, consulta)`,
   por ejemplo:

   ```python
   client.execute_dax(dataset_id, "EVALUATE ROW(\"valor\", [ventas_totales_mes])")
   ```

   La fecha de última actualización del dataset (para `detect_stale_data`)
   sale de `GET /datasets/{id}/refreshes` (top 1). El resto del sistema
   —agente, informe PDF, Telegram, web— no cambia (ADR-001).
