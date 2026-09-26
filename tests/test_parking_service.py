from datetime import datetime, timedelta, timezone

import pytest

from flaskr.services.parkingServices import Conflicto, NoEncontrado, ParkingServices, Validacion
from flaskr.domain.models import Parking
from flaskr.infrastructure.adaptadorSalida.parkingRepositorySQL import ParkingRepositorySQL


def preparar(servicio):
    cliente = servicio.crear_cliente("Ada Lovelace", "ADA@example.com")
    vehiculo = servicio.crear_vehiculo(" ab 123 cd ", cliente.id)
    usuario = servicio.crear_usuario("Operador")
    plaza = servicio.crear_plaza("a-01")
    return vehiculo, usuario, plaza


def test_registra_entrada_salida_y_reutiliza_plaza(servicio):
    vehiculo, usuario, plaza = preparar(servicio)
    entrada = datetime(2026, 9, 25, 10, tzinfo=timezone.utc)
    estancia = servicio.registrar_entrada(vehiculo.id, plaza.id, usuario.id, entrada)

    assert estancia.entrada == entrada
    assert servicio.listar_plazas(disponibles=True) == []
    assert servicio.registrar_salida(estancia.id, entrada + timedelta(hours=1)).salida == entrada + timedelta(hours=1)
    assert servicio.listar_plazas(disponibles=True) == [plaza]
    assert servicio.registrar_entrada(vehiculo.id, plaza.id, usuario.id).id is not None


def test_normaliza_matricula_y_rechaza_matricula_duplicada(servicio):
    cliente = servicio.crear_cliente("Cliente")
    assert servicio.crear_vehiculo(" ab 123 cd ", cliente.id).matricula == "AB123CD"
    with pytest.raises(Conflicto, match="matrícula"):
        servicio.crear_vehiculo("AB123CD", cliente.id)


def test_no_permite_doble_entrada_ni_eliminar_plaza_ocupada(servicio):
    vehiculo, usuario, plaza = preparar(servicio)
    estancia = servicio.registrar_entrada(vehiculo.id, plaza.id, usuario.id)
    with pytest.raises(Conflicto, match="estancia activa"):
        servicio.registrar_entrada(vehiculo.id, plaza.id, usuario.id)
    with pytest.raises(Conflicto, match="ocupada"):
        servicio.eliminar_plaza(plaza.id)
    assert servicio.repositorio.obtener_estancia_activa(estancia.id) is not None


def test_valida_recursos_y_tiempos(servicio):
    with pytest.raises(NoEncontrado, match="vehículo"):
        servicio.registrar_entrada(99, 99, 99)
    with pytest.raises(Validacion, match="obligatorio"):
        servicio.crear_plaza(" ")
    vehiculo, usuario, plaza = preparar(servicio)
    entrada = datetime.now(timezone.utc)
    estancia = servicio.registrar_entrada(vehiculo.id, plaza.id, usuario.id, entrada)
    with pytest.raises(Validacion, match="anterior"):
        servicio.registrar_salida(estancia.id, entrada - timedelta(seconds=1))
    servicio.registrar_salida(estancia.id, entrada + timedelta(seconds=1))
    with pytest.raises(NoEncontrado, match="activa"):
        servicio.registrar_salida(estancia.id)


def test_no_permite_ocupar_plaza_con_otro_vehiculo(servicio):
    cliente = servicio.crear_cliente("Cliente")
    primero = servicio.crear_vehiculo("AA111AA", cliente.id)
    segundo = servicio.crear_vehiculo("BB222BB", cliente.id)
    usuario = servicio.crear_usuario("Operador")
    plaza = servicio.crear_plaza("P1")
    servicio.registrar_entrada(primero.id, plaza.id, usuario.id)
    with pytest.raises(Conflicto, match="plaza ya está ocupada"):
        servicio.registrar_entrada(segundo.id, plaza.id, usuario.id)


def test_persiste_horas_en_utc_y_aplica_indice_unico_sql(servicio):
    vehiculo, usuario, plaza = preparar(servicio)
    segunda_plaza = servicio.crear_plaza("P2")
    entrada_local = datetime(2026, 9, 25, 12, tzinfo=timezone(timedelta(hours=2)))
    estancia = servicio.registrar_entrada(vehiculo.id, plaza.id, usuario.id, entrada_local)
    assert estancia.entrada == datetime(2026, 9, 25, 10, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="Registro duplicado"):
        servicio.repositorio.crear_estancia(
            Parking(vehiculo.id, segunda_plaza.id, usuario.id, datetime.now(timezone.utc))
        )


def test_actualiza_plaza_y_no_borra_plaza_con_historial(servicio):
    plaza = servicio.crear_plaza("P1")
    assert servicio.actualizar_plaza(plaza.id, "p-01").codigo == "P-01"
    with pytest.raises(Conflicto, match="código de plaza"):
        servicio.crear_plaza("P-01")

    cliente = servicio.crear_cliente("Cliente")
    vehiculo = servicio.crear_vehiculo("CC333CC", cliente.id)
    usuario = servicio.crear_usuario("Operador")
    estancia = servicio.registrar_entrada(vehiculo.id, plaza.id, usuario.id)
    servicio.registrar_salida(estancia.id)
    with pytest.raises(Conflicto, match="estancias registradas"):
        servicio.eliminar_plaza(plaza.id)


def test_app_factory_construye_componentes_flask(tmp_path):
    from flaskr import create_app

    app = create_app({"TESTING": True, "DATABASE_URL": f"sqlite:///{tmp_path / 'app.db'}"})
    assert isinstance(app.extensions["parking_repository"], ParkingRepositorySQL)
    app.extensions["parking_engine"].dispose()