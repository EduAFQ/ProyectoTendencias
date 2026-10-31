# Parking Flask

Aplicación de gestión de parqueadero con una interfaz web adaptable y una API REST para clientes, vehículos, operadores, plazas y estancias.

## Entorno

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Para instalar también las herramientas de desarrollo, incluido Pylint:

```powershell
python -m pip install -r requirements-dev.txt
```

## Inicializar la base de datos

```powershell
python -m flaskr.inicializarBD
```

La configuración predeterminada usa `sqlite:///parking.db`. Para cambiarla, define `PARKING_DATABASE_URL` antes de inicializar.

## Ejecutar pruebas

```powershell
python -m pytest
```

## Revisar reglas de Pylint

La configuración del proyecto aplica `unused-variable`, `unused-import` y
`too-many-arguments` con un máximo de cinco argumentos por función:

```powershell
python -m pylint flaskr tests
```

En cada `push` a la rama `development`, GitHub Actions ejecuta Pylint sobre
`flaskr` y `tests`. El workflow requiere una puntuación superior al 80 %
(8.01 de 10 o más); una puntuación inferior hace fallar la ejecución.

## Iniciar la aplicación web

Inicializa primero la base de datos y ejecuta Flask:

```powershell
python -m flask --app flaskr:create_app run --debug
```

Abre <http://127.0.0.1:5000>. La interfaz y la API se sirven desde el mismo origen. Para una base de datos distinta a `parking.db`, configura `PARKING_DATABASE_URL` antes de inicializar y arrancar la aplicación.

## Desplegar con Docker y GHCR

La imagen utiliza Gunicorn y ejecuta la inicialización de las tablas al arrancar.
La base SQLite se almacena en un volumen persistente (`/data/parking.db`).

Para desarrollo local, con Docker Compose:

```powershell
docker compose up --build
```

La aplicación de desarrollo queda disponible en <http://localhost:5000>. El
código fuente se monta en el contenedor y Flask se ejecuta en modo debug.

El workflow `.github/workflows/publish-container.yml` construye la imagen en
cada pull request para verificar el Dockerfile, y publica en GHCR al hacer push
a `main` o `development`, o al crear una etiqueta `v*`. Las etiquetas de imagen
corresponden a la rama o etiqueta y al commit. El workflow usa
`GITHUB_TOKEN`; no requiere un secreto de publicación adicional. Asegúrate de
que Actions tenga permiso para escribir paquetes y configura como público el
paquete de GHCR si el servidor de despliegue debe descargarlo sin autenticarse.
La rama predeterminada también publica la etiqueta `latest`.

Para producción, configura el acceso a GHCR si el paquete es privado y despliega:

```powershell
docker login ghcr.io
docker compose -f compose.prod.yaml pull
docker compose -f compose.prod.yaml up -d
```

`PORT` permite cambiar el puerto publicado (por defecto `5000`) e
`IMAGE_NAME` permite seleccionar otra etiqueta de imagen; ambos se pueden
definir en el entorno o en un archivo `.env` local. El volumen `parking_data`
conserva los datos al reemplazar o reiniciar el contenedor. Esta configuración
SQLite está pensada para una única instancia de la aplicación; para escalar a
varias réplicas, usa una base de datos externa compatible con SQLAlchemy y
configura `PARKING_DATABASE_URL`.

## API REST

Las respuestas de error usan el formato `{"error":{"code":"...","message":"..."}}`.

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/api/dashboard` | Resumen de ocupación y estancias activas |
| `GET` | `/api/estancias/activas` | Lista estancias abiertas |
| `GET` | `/api/estancias/historial` | Historial de estancias finalizadas, ordenado de más reciente a más antigua |
| `POST` | `/api/estancias` | Registra entrada con `vehiculo_id`, `plaza_id`, `usuario_id` |
| `POST` | `/api/estancias/{id}/salida` | Registra la salida de una estancia activa |
| `GET`, `POST` | `/api/clientes` | Lista o crea clientes (`nombre`, `email` opcional) |
| `GET`, `POST` | `/api/vehiculos` | Lista o crea vehículos (`matricula`, `cliente_id`) |
| `GET`, `POST` | `/api/operadores` | Lista o crea operadores (`nombre`) |
| `GET` | `/api/plazas` | Lista plazas; admite `?disponibles=true` |
| `POST` | `/api/plazas` | Crea una plaza (`codigo`) |
| `PATCH` | `/api/plazas/{id}` | Actualiza el código de una plaza |
| `DELETE` | `/api/plazas/{id}` | Elimina una plaza sin estancias asociadas |

La interfaz permite registrar operadores desde el formulario de entrada, para que el flujo no dependa de cargar usuarios manualmente en la base de datos.

El historial admite `desde` y `hasta` (`AAAA-MM-DD`, inclusivos en la zona horaria
`America/Bogota`), `cliente_id`, `limite` (20 por defecto, máximo 100) y
`cursor` para cargar la siguiente página. La respuesta contiene `estancias`,
`hay_mas` y `siguiente_cursor`; cada estancia incluye `duracion_segundos`.

## Desplegar el servidor MCP

En FastMCP Cloud, configura `server.py` como **Entry point**. Ese archivo expone
el servidor `mcp` implementado en `flaskr/infrastructure/McpServers/ParkingMcpServer.py`.
Después de desplegarlo, la plataforma proporcionará el endpoint MCP.

## Uso del servicio

```python
from flaskr import create_app
from flaskr.services.parkingServices import ParkingServices

app = create_app()
servicio = ParkingServices(app.extensions["parking_repository"])
operador = servicio.crear_usuario("Operador")
cliente = servicio.crear_cliente("Ada Lovelace")
vehiculo = servicio.crear_vehiculo("ABC 123", cliente.id)
plaza = servicio.crear_plaza("A-01")
estancia = servicio.registrar_entrada(vehiculo.id, plaza.id, operador.id)
servicio.registrar_salida(estancia.id)
```