from datetime import datetime, timezone

import pytest

from flaskr import create_app
from flaskr.domain.models import Parking
from flaskr.infrastructure.adaptadorSalida.parkingRepositorySQL import ParkingRepositorySQL
from flaskr.infrastructure.db.engine import crear_engine
from flaskr.infrastructure.db.models.parkingOrm import Base
from flaskr.infrastructure.db.session import crear_fabrica_sesiones
from flaskr.services.parkingServices import ParkingServices


@pytest.fixture
def servicio_sql(tmp_path):
    engine = crear_engine(f"sqlite:///{tmp_path / 'parking-infrastructure-test.db'}")
    Base.metadata.create_all(engine)
    repositorio = ParkingRepositorySQL(crear_fabrica_sesiones(engine))
    yield ParkingServices(repositorio)
    engine.dispose()


def test_persistencia_sql_normaliza_horas_a_utc_y_aplica_indice_unico(
    servicio_sql,
):
    # Arrange
    cliente = servicio_sql.crear_cliente("Ada Lovelace")
    vehiculo = servicio_sql.crear_vehiculo("AA111AA", cliente.id)
    operador = servicio_sql.crear_usuario("Operador")
    plaza = servicio_sql.crear_plaza("A-01")
    segunda_plaza = servicio_sql.crear_plaza("A-02")
    entrada_local = datetime.fromisoformat("2026-09-25T12:00:00+02:00")

    # Action
    estancia = servicio_sql.registrar_entrada(
        vehiculo.id, plaza.id, operador.id, entrada_local
    )

    # Assertion
    assert estancia.entrada == datetime(
        2026, 9, 25, 10, tzinfo=timezone.utc
    )
    with pytest.raises(ValueError, match="Registro duplicado"):
        servicio_sql.repositorio.crear_estancia(
            Parking(
                vehiculo.id,
                segunda_plaza.id,
                operador.id,
                datetime.now(timezone.utc),
            )
        )


def test_app_factory_construye_componentes_flask(tmp_path):
    # Arrange
    configuracion = {
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'app.db'}",
    }

    # Action
    app = create_app(configuracion)

    # Assertion
    assert isinstance(app.extensions["parking_repository"], ParkingRepositorySQL)
    app.extensions["parking_engine"].dispose()
