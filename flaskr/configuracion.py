import os


class Configuracion:
    DATABASE_URL = os.environ.get("PARKING_DATABASE_URL", "sqlite:///parking.db")