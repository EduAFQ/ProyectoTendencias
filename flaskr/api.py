from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import HTTPException

from flaskr.services.parkingServices import Conflicto, NoEncontrado, ParkingServices, Validacion


api = Blueprint("api", __name__, url_prefix="/api")


def _servicio():
    return ParkingServices(current_app.extensions["parking_repository"])


def _json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise Validacion("El cuerpo debe ser un objeto JSON")
    return data


def _identificador(data, campo):
    value = data.get(campo)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise Validacion(f"El campo {campo} debe ser un identificador válido")
    return value


def _modelo(modelo):
    return {"id": modelo.id, **{key: value for key, value in vars(modelo).items() if key != "id"}}


def _serializar_estancias(estancias, servicio):
    vehiculos = {item.id: item for item in servicio.listar_vehiculos()}
    plazas = {item.id: item for item in servicio.listar_plazas()}
    clientes = {item.id: item for item in servicio.listar_clientes()}
    usuarios = {item.id: item for item in servicio.listar_usuarios()}
    resultado = []
    for estancia in estancias:
        vehiculo = vehiculos[estancia.vehiculo_id]
        cliente = clientes[vehiculo.cliente_id]
        plaza = plazas[estancia.plaza_id]
        usuario = usuarios[estancia.usuario_id]
        resultado.append({
            "id": estancia.id,
            "vehiculo_id": vehiculo.id,
            "matricula": vehiculo.matricula,
            "cliente": cliente.nombre,
            "plaza_id": plaza.id,
            "plaza": plaza.codigo,
            "usuario_id": usuario.id,
            "operador": usuario.nombre,
            "entrada": estancia.entrada.isoformat(),
            "salida": estancia.salida.isoformat() if estancia.salida else None,
        })
    return resultado


def _error(mensaje, status, codigo):
    return jsonify(error={"code": codigo, "message": mensaje}), status


@api.errorhandler(Validacion)
def _validacion(error):
    return _error(str(error), 400, "validation_error")


@api.errorhandler(NoEncontrado)
def _no_encontrado(error):
    return _error(str(error), 404, "not_found")


@api.errorhandler(Conflicto)
def _conflicto(error):
    return _error(str(error), 409, "conflict")


@api.errorhandler(HTTPException)
def _http_error(error):
    return _error(error.description, error.code or 500, "http_error")


@api.get("/dashboard")
def dashboard():
    servicio = _servicio()
    plazas = servicio.listar_plazas()
    activas = servicio.listar_estancias_activas()
    ocupadas = {estancia.plaza_id for estancia in activas}
    return jsonify(
        plazas_total=len(plazas),
        plazas_ocupadas=len(ocupadas),
        plazas_disponibles=len(plazas) - len(ocupadas),
        estancias_activas=_serializar_estancias(activas, servicio),
    )


@api.get("/estancias/activas")
def listar_estancias_activas():
    servicio = _servicio()
    return jsonify(_serializar_estancias(servicio.listar_estancias_activas(), servicio))


@api.post("/estancias")
def registrar_entrada():
    data = _json()
    servicio = _servicio()
    estancia = servicio.registrar_entrada(
        _identificador(data, "vehiculo_id"),
        _identificador(data, "plaza_id"),
        _identificador(data, "usuario_id"),
    )
    return jsonify(_serializar_estancias([estancia], servicio)[0]), 201


@api.post("/estancias/<int:estancia_id>/salida")
def registrar_salida(estancia_id):
    servicio = _servicio()
    estancia = servicio.registrar_salida(estancia_id)
    return jsonify(_serializar_estancias([estancia], servicio)[0])


@api.get("/clientes")
def listar_clientes():
    return jsonify([_modelo(item) for item in _servicio().listar_clientes()])


@api.post("/clientes")
def crear_cliente():
    data = _json()
    email = data.get("email")
    if email is not None and not isinstance(email, str):
        raise Validacion("El campo email debe ser texto")
    cliente = _servicio().crear_cliente(data.get("nombre"), email)
    return jsonify(_modelo(cliente)), 201


@api.get("/vehiculos")
def listar_vehiculos():
    servicio = _servicio()
    clientes = {item.id: item for item in servicio.listar_clientes()}
    return jsonify([
        {**_modelo(item), "cliente": clientes[item.cliente_id].nombre}
        for item in servicio.listar_vehiculos()
    ])


@api.post("/vehiculos")
def crear_vehiculo():
    data = _json()
    vehiculo = _servicio().crear_vehiculo(
        data.get("matricula"),
        _identificador(data, "cliente_id"),
    )
    return jsonify(_modelo(vehiculo)), 201


@api.get("/operadores")
def listar_operadores():
    return jsonify([_modelo(item) for item in _servicio().listar_usuarios()])


@api.post("/operadores")
def crear_operador():
    data = _json()
    usuario = _servicio().crear_usuario(data.get("nombre"))
    return jsonify(_modelo(usuario)), 201


@api.get("/plazas")
def listar_plazas():
    servicio = _servicio()
    ocupadas = {
        estancia.plaza_id for estancia in servicio.listar_estancias_activas()
    }
    plazas = servicio.listar_plazas()
    if request.args.get("disponibles", "").lower() == "true":
        plazas = [plaza for plaza in plazas if plaza.id not in ocupadas]
    return jsonify([
        {**_modelo(plaza), "ocupada": plaza.id in ocupadas}
        for plaza in plazas
    ])


@api.post("/plazas")
def crear_plaza():
    plaza = _servicio().crear_plaza(_json().get("codigo"))
    return jsonify({**_modelo(plaza), "ocupada": False}), 201


@api.patch("/plazas/<int:plaza_id>")
def actualizar_plaza(plaza_id):
    plaza = _servicio().actualizar_plaza(plaza_id, _json().get("codigo"))
    return jsonify(_modelo(plaza))


@api.delete("/plazas/<int:plaza_id>")
def eliminar_plaza(plaza_id):
    _servicio().eliminar_plaza(plaza_id)
    return "", 204
