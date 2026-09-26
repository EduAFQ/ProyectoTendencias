from flaskr.infrastructure.db.models.parkingOrm import Base


def inicializar_bd(engine):
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    from flaskr import create_app

    aplicacion = create_app()
    inicializar_bd(aplicacion.extensions["parking_engine"])