"""Pruebas unitarias de las reglas del servicio de parqueadero."""

from datetime import datetime, timedelta, timezone

import pytest

from flaskr.services.parkingServices import Conflicto, NoEncontrado, Validacion


def preparar(servicio):
    cliente = servicio.crear_cliente("Ada Lovelace", "ada@example.com")
    vehiculo = servicio.crear_vehiculo("AA111AA", cliente.id)
    operador = servicio.crear_usuario("Operador")
    plaza = servicio.crear_plaza("A-01")
    return cliente, vehiculo, operador, plaza


def test_crear_cliente_normaliza_nombre_y_correo(servicio):
    # Arrange
    nombre = "  Ada Lovelace  "
    correo = " ADA@EXAMPLE.COM "

    # Action
    cliente = servicio.crear_cliente(nombre, correo)

    # Assertion
    assert cliente.nombre == "Ada Lovelace"
    assert cliente.email == "ada@example.com"


def test_crear_cliente_rechaza_nombre_vacio(servicio):
    # Arrange
    nombre = "  "

    # Action
    with pytest.raises(Validacion, match="nombre.*obligatorio"):
        servicio.crear_cliente(nombre)

    # Assertion
    assert servicio.listar_clientes() == []


def test_crear_cliente_rechaza_correo_duplicado(servicio):
    # Arrange
    servicio.crear_cliente("Ada Lovelace", "ada@example.com")

    # Action
    with pytest.raises(Conflicto, match="email ya está registrado"):
        servicio.crear_cliente("Grace Hopper", "ADA@example.com")

    # Assertion
    assert len(servicio.listar_clientes()) == 1


def test_crear_usuario_rechaza_nombre_vacio(servicio):
    # Arrange
    nombre = ""

    # Action
    with pytest.raises(Validacion, match="nombre.*obligatorio"):
        servicio.crear_usuario(nombre)

    # Assertion
    assert servicio.listar_usuarios() == []


def test_crear_vehiculo_normaliza_matricula(servicio):
    # Arrange
    cliente = servicio.crear_cliente("Ada Lovelace")

    # Action
    vehiculo = servicio.crear_vehiculo(" ab 123 cd ", cliente.id)

    # Assertion
    assert vehiculo.matricula == "AB123CD"
    assert vehiculo.cliente_id == cliente.id


def test_crear_vehiculo_rechaza_matricula_duplicada(servicio):
    # Arrange
    cliente = servicio.crear_cliente("Ada Lovelace")
    servicio.crear_vehiculo("AB123CD", cliente.id)

    # Action
    with pytest.raises(Conflicto, match="matrícula ya está registrada"):
        servicio.crear_vehiculo(" ab 123 cd ", cliente.id)

    # Assertion
    assert len(servicio.listar_vehiculos()) == 1


def test_crear_vehiculo_rechaza_cliente_inexistente(servicio):
    # Arrange
    cliente_inexistente = 99

    # Action
    with pytest.raises(NoEncontrado, match="No existe el cliente"):
        servicio.crear_vehiculo("AB123CD", cliente_inexistente)

    # Assertion
    assert servicio.listar_vehiculos() == []


def test_crear_vehiculo_rechaza_matricula_vacia(servicio):
    # Arrange
    cliente = servicio.crear_cliente("Ada Lovelace")

    # Action
    with pytest.raises(Validacion, match="matrícula.*obligatorio"):
        servicio.crear_vehiculo("  ", cliente.id)

    # Assertion
    assert servicio.listar_vehiculos() == []


def test_crear_plaza_normaliza_codigo(servicio):
    # Arrange
    codigo = " a-01 "

    # Action
    plaza = servicio.crear_plaza(codigo)

    # Assertion
    assert plaza.codigo == "A-01"
    assert servicio.listar_plazas() == [plaza]


def test_crear_plaza_rechaza_codigo_duplicado(servicio):
    # Arrange
    servicio.crear_plaza("A-01")

    # Action
    with pytest.raises(Conflicto, match="código de plaza ya existe"):
        servicio.crear_plaza("a-01")

    # Assertion
    assert len(servicio.listar_plazas()) == 1


def test_crear_plaza_rechaza_codigo_vacio(servicio):
    # Arrange
    codigo = "  "

    # Action
    with pytest.raises(Validacion, match="código de plaza.*obligatorio"):
        servicio.crear_plaza(codigo)

    # Assertion
    assert servicio.listar_plazas() == []


def test_actualizar_plaza_normaliza_codigo(servicio):
    # Arrange
    plaza = servicio.crear_plaza("P1")

    # Action
    actualizada = servicio.actualizar_plaza(plaza.id, " p-01 ")

    # Assertion
    assert actualizada.codigo == "P-01"
    assert servicio.listar_plazas() == [actualizada]


def test_actualizar_plaza_rechaza_codigo_duplicado(servicio):
    # Arrange
    primera = servicio.crear_plaza("A-01")
    segunda = servicio.crear_plaza("A-02")

    # Action
    with pytest.raises(Conflicto, match="código de plaza ya existe"):
        servicio.actualizar_plaza(segunda.id, primera.codigo)

    # Assertion
    assert servicio.listar_plazas() == [primera, segunda]


def test_eliminar_plaza_inexistente_es_rechazado(servicio):
    # Arrange
    plaza_inexistente = 99

    # Action
    with pytest.raises(NoEncontrado, match="No existe la plaza"):
        servicio.eliminar_plaza(plaza_inexistente)

    # Assertion
    assert servicio.listar_plazas() == []


def test_eliminar_plaza_ocupada_es_rechazado(servicio):
    # Arrange
    _, vehiculo, operador, plaza = preparar(servicio)
    servicio.registrar_entrada(vehiculo.id, plaza.id, operador.id)

    # Action
    with pytest.raises(Conflicto, match="plaza ocupada"):
        servicio.eliminar_plaza(plaza.id)

    # Assertion
    assert servicio.listar_plazas() == [plaza]


def test_eliminar_plaza_con_historial_es_rechazado(servicio):
    # Arrange
    _, vehiculo, operador, plaza = preparar(servicio)
    estancia = servicio.registrar_entrada(vehiculo.id, plaza.id, operador.id)
    servicio.registrar_salida(estancia.id)

    # Action
    with pytest.raises(Conflicto, match="estancias registradas"):
        servicio.eliminar_plaza(plaza.id)

    # Assertion
    assert servicio.listar_plazas() == [plaza]


def test_entrada_normaliza_instante_a_utc(servicio):
    # Arrange
    _, vehiculo, operador, plaza = preparar(servicio)
    entrada_local = datetime(
        2026, 9, 25, 12, tzinfo=timezone(timedelta(hours=2))
    )

    # Action
    estancia = servicio.registrar_entrada(
        vehiculo.id, plaza.id, operador.id, entrada_local
    )

    # Assertion
    assert estancia.entrada == datetime(2026, 9, 25, 10, tzinfo=timezone.utc)


def test_entrada_rechaza_fecha_sin_zona_horaria(servicio):
    # Arrange
    _, vehiculo, operador, plaza = preparar(servicio)
    entrada_sin_zona = datetime(2026, 9, 25, 10)

    # Action
    with pytest.raises(Validacion, match="entrada debe incluir zona horaria"):
        servicio.registrar_entrada(
            vehiculo.id, plaza.id, operador.id, entrada_sin_zona
        )

    # Assertion
    assert servicio.listar_estancias_activas() == []


def test_entrada_rechaza_vehiculo_inexistente(servicio):
    # Arrange
    operador = servicio.crear_usuario("Operador")
    plaza = servicio.crear_plaza("A-01")

    # Action
    with pytest.raises(NoEncontrado, match="No existe el vehículo"):
        servicio.registrar_entrada(99, plaza.id, operador.id)

    # Assertion
    assert servicio.listar_estancias_activas() == []


def test_entrada_rechaza_plaza_inexistente(servicio):
    # Arrange
    cliente = servicio.crear_cliente("Ada Lovelace")
    vehiculo = servicio.crear_vehiculo("AA111AA", cliente.id)
    operador = servicio.crear_usuario("Operador")

    # Action
    with pytest.raises(NoEncontrado, match="No existe la plaza"):
        servicio.registrar_entrada(vehiculo.id, 99, operador.id)

    # Assertion
    assert servicio.listar_estancias_activas() == []


def test_entrada_rechaza_operador_inexistente(servicio):
    # Arrange
    cliente = servicio.crear_cliente("Ada Lovelace")
    vehiculo = servicio.crear_vehiculo("AA111AA", cliente.id)
    plaza = servicio.crear_plaza("A-01")

    # Action
    with pytest.raises(NoEncontrado, match="No existe el usuario operador"):
        servicio.registrar_entrada(vehiculo.id, plaza.id, 99)

    # Assertion
    assert servicio.listar_estancias_activas() == []


def test_entrada_no_permite_un_vehiculo_con_dos_estancias_activas(servicio):
    # Arrange
    _, vehiculo, operador, plaza = preparar(servicio)
    otra_plaza = servicio.crear_plaza("A-02")
    servicio.registrar_entrada(vehiculo.id, plaza.id, operador.id)

    # Action
    with pytest.raises(Conflicto, match="vehículo ya tiene una estancia activa"):
        servicio.registrar_entrada(vehiculo.id, otra_plaza.id, operador.id)

    # Assertion
    assert len(servicio.listar_estancias_activas()) == 1


def test_entrada_no_permite_ocupar_una_plaza_ya_usada(servicio):
    # Arrange
    cliente = servicio.crear_cliente("Ada Lovelace")
    primer_vehiculo = servicio.crear_vehiculo("AA111AA", cliente.id)
    segundo_vehiculo = servicio.crear_vehiculo("BB222BB", cliente.id)
    operador = servicio.crear_usuario("Operador")
    plaza = servicio.crear_plaza("A-01")
    servicio.registrar_entrada(primer_vehiculo.id, plaza.id, operador.id)

    # Action
    with pytest.raises(Conflicto, match="plaza ya está ocupada"):
        servicio.registrar_entrada(segundo_vehiculo.id, plaza.id, operador.id)

    # Assertion
    assert len(servicio.listar_estancias_activas()) == 1


def test_salida_anterior_a_entrada_es_rechazada(servicio):
    # Arrange
    _, vehiculo, operador, plaza = preparar(servicio)
    entrada = datetime(2026, 9, 25, 10, tzinfo=timezone.utc)
    estancia = servicio.registrar_entrada(
        vehiculo.id, plaza.id, operador.id, entrada
    )

    # Action
    with pytest.raises(Validacion, match="salida no puede ser anterior"):
        servicio.registrar_salida(
            estancia.id, entrada - timedelta(seconds=1)
        )

    # Assertion
    assert servicio.listar_estancias_activas() == [estancia]


def test_salida_cierra_estancia_y_libera_plaza(servicio):
    # Arrange
    _, vehiculo, operador, plaza = preparar(servicio)
    entrada = datetime(2026, 9, 25, 10, tzinfo=timezone.utc)
    estancia = servicio.registrar_entrada(
        vehiculo.id, plaza.id, operador.id, entrada
    )
    salida = entrada + timedelta(hours=1)

    # Action
    estancia_cerrada = servicio.registrar_salida(estancia.id, salida)

    # Assertion
    assert estancia_cerrada.salida == salida
    assert servicio.listar_estancias_activas() == []
    assert servicio.listar_plazas(disponibles=True) == [plaza]
    nueva_estancia = servicio.registrar_entrada(
        vehiculo.id, plaza.id, operador.id, salida
    )
    assert nueva_estancia.id != estancia.id


def test_salida_rechaza_estancia_inexistente_o_ya_cerrada(servicio):
    # Arrange
    _, vehiculo, operador, plaza = preparar(servicio)
    estancia = servicio.registrar_entrada(vehiculo.id, plaza.id, operador.id)
    servicio.registrar_salida(estancia.id)

    # Action
    with pytest.raises(NoEncontrado, match="No existe una estancia activa"):
        servicio.registrar_salida(estancia.id)

    # Assertion
    assert servicio.listar_estancias_activas() == []


def test_salida_detecta_estancia_cerrada_concurrentemente(servicio):
    # Arrange
    _, vehiculo, operador, plaza = preparar(servicio)
    estancia = servicio.registrar_entrada(vehiculo.id, plaza.id, operador.id)
    servicio.repositorio.cerrar_estancia = lambda _estancia_id, _salida: None

    # Action
    with pytest.raises(NoEncontrado, match="ya no está activa"):
        servicio.registrar_salida(estancia.id)

    # Assertion
    assert servicio.listar_estancias_activas() == [estancia]


def test_listar_plazas_disponibles_y_activas(servicio):
    # Arrange
    _, vehiculo, operador, plaza_ocupada = preparar(servicio)
    plaza_disponible = servicio.crear_plaza("A-02")
    servicio.registrar_entrada(vehiculo.id, plaza_ocupada.id, operador.id)

    # Action
    disponibles = servicio.listar_plazas(disponibles=True)
    activas = servicio.listar_plazas_activas()
    todas = servicio.listar_plazas()

    # Assertion
    assert disponibles == [plaza_disponible]
    assert activas == [plaza_ocupada]
    assert todas == [plaza_ocupada, plaza_disponible]
