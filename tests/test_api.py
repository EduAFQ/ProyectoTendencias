import pytest

from flaskr import create_app
from flaskr.infrastructure.db.models.parkingOrm import Base


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
