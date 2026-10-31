from datetime import datetime, timedelta, timezone

import pytest

from flaskr import create_app
from flaskr.infrastructure.db.models.parkingOrm import Base
from flaskr.services.parkingServices import ParkingServices


@pytest.fixture
def cliente_http(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'api-test.db'}",
    })
    Base.metadata.create_all(app.extensions["parking_engine"])
    yield app.test_client()
    app.extensions["parking_engine"].dispose()


def test_frontend_se_entrega_desde_la_raiz(cliente_http):
    response = cliente_http.get("/")

    assert response.status_code == 200
    assert b"Resumen del parqueadero" in response.data
    assert cliente_http.get("/static/app.js").status_code == 200
    assert cliente_http.get("/static/styles.css").status_code == 200


def test_api_registra_y_cierra_estancia_y_actualiza_ocupacion(cliente_http):
    cliente = cliente_http.post("/api/clientes", json={
        "nombre": "Ada Lovelace",
        "email": "ADA@example.com",
    })
    assert cliente.status_code == 201
    assert cliente.json["email"] == "ada@example.com"

    vehiculo = cliente_http.post("/api/vehiculos", json={
        "matricula": "ab 123 cd",
        "cliente_id": cliente.json["id"],
    })
    operador = cliente_http.post("/api/operadores", json={"nombre": "Operador"})
    plaza = cliente_http.post("/api/plazas", json={"codigo": "a-01"})
    assert vehiculo.status_code == operador.status_code == plaza.status_code == 201

    entrada = cliente_http.post("/api/estancias", json={
        "vehiculo_id": vehiculo.json["id"],
        "plaza_id": plaza.json["id"],
        "usuario_id": operador.json["id"],
    })
    assert entrada.status_code == 201
    assert entrada.json["matricula"] == "AB123CD"
    assert entrada.json["cliente"] == "Ada Lovelace"
    assert entrada.json["plaza"] == "A-01"

    tablero = cliente_http.get("/api/dashboard").json
    assert tablero["plazas_total"] == 1
    assert tablero["plazas_ocupadas"] == 1
    assert tablero["plazas_disponibles"] == 0
    assert len(tablero["estancias_activas"]) == 1
    assert cliente_http.get("/api/plazas?disponibles=true").json == []
    assert cliente_http.get("/api/plazas").json[0]["ocupada"] is True

    salida = cliente_http.post(f"/api/estancias/{entrada.json['id']}/salida")
    assert salida.status_code == 200
    assert salida.json["salida"] is not None
    assert cliente_http.get("/api/dashboard").json["plazas_disponibles"] == 1
    assert cliente_http.get("/api/estancias/activas").json == []


def test_api_valida_entradas_y_devuelve_errores_consistentes(cliente_http):
    respuesta = cliente_http.post("/api/estancias", json={})
    assert respuesta.status_code == 400
    assert respuesta.json["error"]["code"] == "validation_error"

    inexistente = cliente_http.post("/api/estancias", json={
        "vehiculo_id": 10,
        "plaza_id": 10,
        "usuario_id": 10,
    })
    assert inexistente.status_code == 404
    assert inexistente.json["error"]["code"] == "not_found"

    cliente_http.post("/api/plazas", json={"codigo": "P1"})
    duplicada = cliente_http.post("/api/plazas", json={"codigo": "p1"})
    assert duplicada.status_code == 409
    assert duplicada.json["error"]["code"] == "conflict"

    no_encontrada = cliente_http.delete("/api/plazas/999")
    assert no_encontrada.status_code == 404
    assert no_encontrada.json["error"]["code"] == "not_found"


def test_api_permite_actualizar_y_eliminar_plaza_sin_historial(cliente_http):
    plaza = cliente_http.post("/api/plazas", json={"codigo": "p1"}).json
    actualizada = cliente_http.patch(
        f"/api/plazas/{plaza['id']}",
        json={"codigo": "p-01"},
    )
    assert actualizada.status_code == 200
    assert actualizada.json["codigo"] == "P-01"

    eliminada = cliente_http.delete(f"/api/plazas/{plaza['id']}")
    assert eliminada.status_code == 204
    assert cliente_http.get("/api/plazas").json == []


def test_api_historial_filtra_por_cliente_y_dia_local(cliente_http):
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

    respuesta = cliente_http.get(
        f"/api/estancias/historial?desde=2026-10-31&hasta=2026-10-31"
        f"&cliente_id={primer_cliente.id}"
    )

    assert respuesta.status_code == 200
    assert respuesta.json["hay_mas"] is False
    assert respuesta.json["siguiente_cursor"] is None
    assert len(respuesta.json["estancias"]) == 1
    estancia = respuesta.json["estancias"][0]
    assert estancia["matricula"] == "AA111AA"
    assert estancia["cliente"] == "Ada Lovelace"
    assert estancia["duracion_segundos"] == 45 * 60


def test_api_historial_pagina_sin_duplicar_entradas_con_mismo_horario(cliente_http):
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

    primera = cliente_http.get("/api/estancias/historial?limite=1")
    segunda = cliente_http.get(
        f"/api/estancias/historial?limite=1&cursor={primera.json['siguiente_cursor']}"
    )
    tercera = cliente_http.get(
        f"/api/estancias/historial?limite=1&cursor={segunda.json['siguiente_cursor']}"
    )
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
    respuesta = cliente_http.get(f"/api/estancias/historial{query}")

    assert respuesta.status_code == 400
    assert respuesta.json["error"]["code"] == "validation_error"
