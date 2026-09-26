import pytest

from flaskr.infrastructure.adaptadorSalida.parkingRepositorySQL import ParkingRepositorySQL
from flaskr.infrastructure.db.engine import crear_engine
from flaskr.infrastructure.db.models.parkingOrm import Base
from flaskr.infrastructure.db.session import crear_fabrica_sesiones
from flaskr.services.parkingServices import ParkingServices


@pytest.fixture
def servicio(tmp_path):
    engine = crear_engine(f"sqlite:///{tmp_path / 'parking-test.db'}")
    Base.metadata.create_all(engine)
    repositorio = ParkingRepositorySQL(crear_fabrica_sesiones(engine))
    yield ParkingServices(repositorio)
    engine.dispose()