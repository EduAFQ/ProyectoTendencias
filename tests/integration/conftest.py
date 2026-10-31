"""Fixtures de integración con Flask y la base de datos SQL temporal."""

import pytest

from flaskr import create_app
from flaskr.infrastructure.adaptadorSalida.parkingRepositorySQL import ParkingRepositorySQL
from flaskr.infrastructure.db.engine import crear_engine
from flaskr.infrastructure.db.models.parkingOrm import Base
from flaskr.infrastructure.db.session import crear_fabrica_sesiones
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


@pytest.fixture
def servicio_sql(tmp_path):
    engine = crear_engine(f"sqlite:///{tmp_path / 'parking-integration-test.db'}")
    Base.metadata.create_all(engine)
    repositorio = ParkingRepositorySQL(crear_fabrica_sesiones(engine))
    yield ParkingServices(repositorio)
    engine.dispose()
