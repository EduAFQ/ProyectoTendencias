from sqlalchemy.orm import sessionmaker


def crear_fabrica_sesiones(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)