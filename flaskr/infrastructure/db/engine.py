from sqlalchemy import create_engine, event


def crear_engine(database_url):
    opciones = {"future": True}
    if database_url.startswith("sqlite:"):
        opciones["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **opciones)
    if database_url.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def activar_claves_foraneas(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine