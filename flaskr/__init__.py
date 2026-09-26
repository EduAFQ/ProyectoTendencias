from flask import Flask

from flaskr.configuracion import Configuracion
from flaskr.infrastructure.adaptadorSalida.parkingRepositorySQL import ParkingRepositorySQL
from flaskr.infrastructure.db.engine import crear_engine
from flaskr.infrastructure.db.session import crear_fabrica_sesiones


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Configuracion)
    if test_config:
        app.config.update(test_config)

    engine = crear_engine(app.config["DATABASE_URL"])
    session_factory = crear_fabrica_sesiones(engine)
    app.extensions["parking_engine"] = engine
    app.extensions["parking_session_factory"] = session_factory
    app.extensions["parking_repository"] = ParkingRepositorySQL(session_factory)
    return app