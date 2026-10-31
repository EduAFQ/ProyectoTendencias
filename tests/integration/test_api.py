"""Pruebas de integración de la API HTTP."""

from datetime import datetime, timedelta, timezone

import pytest

from flaskr.services.parkingServices import ParkingServices


def test_frontend_se_entrega_desde_la_raiz(cliente_http):
    # Arrange
    rutas_estaticas = ("/", "/static/app.js", "/static/styles.css")

    # Action
    response = cliente_http.get("/")
    respuestas_estaticas = [
        cliente_http.get(ruta) for ruta in rutas_estaticas[1:]
    ]

    # Assertion
    assert response.status_code == 200
    assert b"Resumen del parqueadero" in response.data
    assert all(respuesta.status_code == 200 for respuesta in respuestas_estaticas)


def test_api_registra_y_cierra_estancia_y_actualiza_ocupacion(cliente_http):
    # Arrange
    datos_cliente = {
        "nombre": "Ada Lovelace",
        "email": "ADA@example.com",
    }

    # Action
    cliente = cliente_http.post("/api/clientes", json=datos_cliente)

    # Assertion
    assert cliente.status_code == 201
    assert cliente.json["email"] == "ada@example.com"

    # Arrange
    datos_vehiculo = {"matricula": "ab 123 cd", "cliente_id": cliente.json["id"]}

    # Action
    vehiculo = cliente_http.post("/api/vehiculos", json=datos_vehiculo)
    operador = cliente_http.post("/api/operadores", json={"nombre": "Operador"})
    plaza = cliente_http.post("/api/plazas", json={"codigo": "a-01"})

    # Assertion
    assert vehiculo.status_code == operador.status_code == plaza.status_code == 201

    # Arrange
    datos_entrada = {
        "vehiculo_id": vehiculo.json["id"],
        "plaza_id": plaza.json["id"],
        "usuario_id": operador.json["id"],
    }

    # Action
    entrada = cliente_http.post("/api/estancias", json=datos_entrada)

    # Assertion
    assert entrada.status_code == 201
    assert entrada.json["matricula"] == "AB123CD"
    assert entrada.json["cliente"] == "Ada Lovelace"
    assert entrada.json["plaza"] == "A-01"

    # Arrange
    estancia_id = entrada.json["id"]

    # Action
    tablero = cliente_http.get("/api/dashboard").json
    plazas_disponibles = cliente_http.get("/api/plazas?disponibles=true").json
    plazas = cliente_http.get("/api/plazas").json

    # Assertion
    assert tablero["plazas_total"] == 1
    assert tablero["plazas_ocupadas"] == 1
    assert tablero["plazas_disponibles"] == 0
    assert len(tablero["estancias_activas"]) == 1
    assert plazas_disponibles == []
    assert plazas[0]["ocupada"] is True

    # Arrange
    ruta_salida = f"/api/estancias/{estancia_id}/salida"

    # Action
    salida = cliente_http.post(ruta_salida)
    tablero_final = cliente_http.get("/api/dashboard").json
    estancias_activas = cliente_http.get("/api/estancias/activas").json

    # Assertion
    assert salida.status_code == 200
    assert salida.json["salida"] is not None
    assert tablero_final["plazas_disponibles"] == 1
    assert estancias_activas == []


def test_api_valida_entradas_y_devuelve_errores_consistentes(cliente_http):
    # Arrange
    solicitud_incompleta = {}

    # Action
    respuesta = cliente_http.post("/api/estancias", json=solicitud_incompleta)

    # Assertion
    assert respuesta.status_code == 400
    assert respuesta.json["error"]["code"] == "validation_error"

    # Arrange
    identificadores_inexistentes = {
        "vehiculo_id": 10,
        "plaza_id": 10,
        "usuario_id": 10,
    }

    # Action
    inexistente = cliente_http.post(
        "/api/estancias", json=identificadores_inexistentes
    )

    # Assertion
    assert inexistente.status_code == 404
    assert inexistente.json["error"]["code"] == "not_found"

    # Arrange
    cliente_http.post("/api/plazas", json={"codigo": "P1"})

    # Action
    duplicada = cliente_http.post("/api/plazas", json={"codigo": "p1"})

    # Assertion
    assert duplicada.status_code == 409
    assert duplicada.json["error"]["code"] == "conflict"

    # Arrange
    ruta_inexistente = "/api/plazas/999"

    # Action
    no_encontrada = cliente_http.delete(ruta_inexistente)

    # Assertion
    assert no_encontrada.status_code == 404
    assert no_encontrada.json["error"]["code"] == "not_found"


def test_api_permite_actualizar_y_eliminar_plaza_sin_historial(cliente_http):
    # Arrange
    plaza = cliente_http.post("/api/plazas", json={"codigo": "p1"}).json

    # Action
    actualizada = cliente_http.patch(
        f"/api/plazas/{plaza['id']}",
        json={"codigo": "p-01"},
    )

    # Assertion
    assert actualizada.status_code == 200
    assert actualizada.json["codigo"] == "P-01"

    # Arrange
    plaza_id = actualizada.json["id"]

    # Action
    eliminada = cliente_http.delete(f"/api/plazas/{plaza_id}")
    plazas_restantes = cliente_http.get("/api/plazas").json

    # Assertion
    assert eliminada.status_code == 204
    assert plazas_restantes == []


def test_api_historial_filtra_por_cliente_y_dia_local(cliente_http):
    # Arrange
    servicio = ParkingServices(cliente_http.application.extensions["parking_repository"])
    primer_cliente = servicio.crear_cliente("Ada Lovelace")
    segundo_cliente = servicio.crear_cliente("Grace Hopper")
    operador = servicio.crear_usuario("Operador")
    plaza = servicio.crear_plaza("A-01")
    fecha_entrada = datetime(2026, 10, 31, 5, tzinfo=timezone.utc)

    vehiculo_ada = servicio.crear_vehiculo("AA111AA", primer_cliente.id)
    estancia_ada = servicio.registrar_entrada(
        vehiculo_ada.id, plaza.id, operador.id, fecha_entrada
    )
    servicio.registrar_salida(estancia_ada.id, fecha_entrada + timedelta(minutes=45))

    plaza_dos = servicio.crear_plaza("A-02")
    vehiculo_grace = servicio.crear_vehiculo("BB222BB", segundo_cliente.id)
    estancia_grace = servicio.registrar_entrada(
        vehiculo_grace.id, plaza_dos.id, operador.id, fecha_entrada
    )
    servicio.registrar_salida(estancia_grace.id, fecha_entrada + timedelta(hours=1))

    for matricula, codigo, momento in (
        ("CC333CC", "A-03", datetime(2026, 10, 31, 4, 59, tzinfo=timezone.utc)),
        ("DD444DD", "A-04", datetime(2026, 11, 1, 5, tzinfo=timezone.utc)),
    ):
        plaza_limite = servicio.crear_plaza(codigo)
        vehiculo_limite = servicio.crear_vehiculo(matricula, primer_cliente.id)
        estancia_limite = servicio.registrar_entrada(
            vehiculo_limite.id, plaza_limite.id, operador.id, momento
        )
        servicio.registrar_salida(
            estancia_limite.id, momento + timedelta(minutes=5)
        )

    # Action
    respuesta = cliente_http.get(
        f"/api/estancias/historial?desde=2026-10-31&hasta=2026-10-31"
        f"&cliente_id={primer_cliente.id}"
    )

    # Assertion
    assert respuesta.status_code == 200
    assert respuesta.json["hay_mas"] is False
    assert respuesta.json["siguiente_cursor"] is None
    assert len(respuesta.json["estancias"]) == 1
    estancia = respuesta.json["estancias"][0]
    assert estancia["matricula"] == "AA111AA"
    assert estancia["cliente"] == "Ada Lovelace"
    assert estancia["duracion_segundos"] == 45 * 60


def test_api_historial_pagina_sin_duplicar_entradas_con_mismo_horario(cliente_http):
    # Arrange
    servicio = ParkingServices(cliente_http.application.extensions["parking_repository"])
    cliente = servicio.crear_cliente("Cliente")
    operador = servicio.crear_usuario("Operador")
    entrada = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
    for indice in range(3):
        vehiculo = servicio.crear_vehiculo(f"AA111A{indice}", cliente.id)
        plaza = servicio.crear_plaza(f"A-{indice}")
        estancia = servicio.registrar_entrada(
            vehiculo.id, plaza.id, operador.id, entrada
        )
        servicio.registrar_salida(estancia.id, entrada + timedelta(minutes=indice + 1))

    # Action
    primera = cliente_http.get("/api/estancias/historial?limite=1")
    segunda = cliente_http.get(
        f"/api/estancias/historial?limite=1&cursor={primera.json['siguiente_cursor']}"
    )
    tercera = cliente_http.get(
        f"/api/estancias/historial?limite=1&cursor={segunda.json['siguiente_cursor']}"
    )

    # Assertion
    identificadores = [
        primera.json["estancias"][0]["id"],
        segunda.json["estancias"][0]["id"],
        tercera.json["estancias"][0]["id"],
    ]

    assert primera.json["hay_mas"] is True
    assert segunda.json["hay_mas"] is True
    assert tercera.json["hay_mas"] is False
    assert len(set(identificadores)) == 3
    assert identificadores == sorted(identificadores, reverse=True)


@pytest.mark.parametrize("query", [
    "?desde=31-10-2026",
    "?desde=2026-10-31&hasta=2026-10-30",
    "?cliente_id=abc",
    "?limite=101",
    "?cursor=not-valid",
])
def test_api_historial_rechaza_parametros_invalidos(cliente_http, query):
    # Arrange
    ruta_historial = f"/api/estancias/historial{query}"

    # Action
    respuesta = cliente_http.get(ruta_historial)

    # Assertion
    assert respuesta.status_code == 400
    assert respuesta.json["error"]["code"] == "validation_error"
