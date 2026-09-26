# Parking Flask

Capa inicial para gestionar clientes, vehículos, operadores, plazas y estancias de parking. La interfaz HTTP queda fuera de esta primera etapa.

## Entorno

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
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