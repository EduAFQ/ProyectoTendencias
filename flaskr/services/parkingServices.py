from datetime import datetime, timezone

from flaskr.domain.models import Cliente, Parking, Plaza, Usuario, Vehiculo


class ErrorParking(Exception):
    """Error base para operaciones de parking inválidas."""


class NoEncontrado(ErrorParking):
    pass


class Conflicto(ErrorParking):
    pass


class Validacion(ErrorParking):
    pass


class ParkingServices:
    def __init__(self, repositorio):
        self.repositorio = repositorio

    def crear_cliente(self, nombre, email=None):
        self._texto_requerido(nombre, "nombre")
        email = email.strip().lower() if email else None
        return self._crear(lambda: self.repositorio.crear_cliente(Cliente(nombre.strip(), email)), "El email ya está registrado")

    def crear_usuario(self, nombre):
        self._texto_requerido(nombre, "nombre")
        return self.repositorio.crear_usuario(Usuario(nombre.strip()))

    def crear_vehiculo(self, matricula, cliente_id):
        placa = self._texto_requerido(matricula, "matrícula").replace(" ", "").upper()
        self._requerir(self.repositorio.obtener_cliente(cliente_id), "No existe el cliente")
        return self._crear(lambda: self.repositorio.crear_vehiculo(Vehiculo(placa, cliente_id)), "La matrícula ya está registrada")

    def crear_plaza(self, codigo):
        codigo_normalizado = self._texto_requerido(codigo, "código de plaza").upper()
        return self._crear(lambda: self.repositorio.crear_plaza(Plaza(codigo_normalizado)), "El código de plaza ya existe")

    def listar_plazas(self, disponibles=False):
        plazas = self.repositorio.listar_plazas()
        if not disponibles:
            return plazas
        return [plaza for plaza in plazas if self.repositorio.obtener_estancia_activa_plaza(plaza.id) is None]

    def actualizar_plaza(self, plaza_id, codigo):
        plaza = self._requerir(self.repositorio.obtener_plaza(plaza_id), "No existe la plaza")
        actualizada = Plaza(self._texto_requerido(codigo, "código de plaza").upper(), plaza.id)
        return self._crear(lambda: self.repositorio.actualizar_plaza(actualizada), "El código de plaza ya existe")

    def eliminar_plaza(self, plaza_id):
        plaza = self._requerir(self.repositorio.obtener_plaza(plaza_id), "No existe la plaza")
        if self.repositorio.obtener_estancia_activa_plaza(plaza_id):
            raise Conflicto("No se puede eliminar una plaza ocupada")
        try:
            self.repositorio.eliminar_plaza(plaza.id)
        except ValueError as error:
            raise Conflicto("No se puede eliminar una plaza con estancias registradas") from error

    def registrar_entrada(self, vehiculo_id, plaza_id, usuario_id, ahora=None):
        vehiculo = self._requerir(self.repositorio.obtener_vehiculo(vehiculo_id), "No existe el vehículo")
        plaza = self._requerir(self.repositorio.obtener_plaza(plaza_id), "No existe la plaza")
        self._requerir(self.repositorio.obtener_usuario(usuario_id), "No existe el usuario operador")
        if self.repositorio.obtener_estancia_activa_vehiculo(vehiculo.id):
            raise Conflicto("El vehículo ya tiene una estancia activa")
        if self.repositorio.obtener_estancia_activa_plaza(plaza.id):
            raise Conflicto("La plaza ya está ocupada")
        momento = self._momento_utc(ahora, "entrada")
        return self._crear(
            lambda: self.repositorio.crear_estancia(Parking(vehiculo.id, plaza.id, usuario_id, momento)),
            "El vehículo o la plaza ya tiene una estancia activa",
        )

    def registrar_salida(self, estancia_id, ahora=None):
        estancia = self._requerir(self.repositorio.obtener_estancia_activa(estancia_id), "No existe una estancia activa con ese identificador")
        momento = self._momento_utc(ahora, "salida")
        if momento < estancia.entrada:
            raise Validacion("La salida no puede ser anterior a la entrada")
        cerrada = self.repositorio.cerrar_estancia(estancia_id, momento)
        if cerrada is None:
            raise NoEncontrado("La estancia ya no está activa")
        return cerrada

    def listar_estancias_activas(self):
        return self.repositorio.listar_estancias_activas()

    @staticmethod
    def _texto_requerido(valor, campo):
        if not isinstance(valor, str) or not valor.strip():
            raise Validacion(f"El campo {campo} es obligatorio")
        return valor.strip()

    @staticmethod
    def _requerir(valor, mensaje):
        if valor is None:
            raise NoEncontrado(mensaje)
        return valor

    @staticmethod
    def _momento_utc(valor, campo):
        momento = valor or datetime.now(timezone.utc)
        if momento.tzinfo is None:
            raise Validacion(f"La fecha de {campo} debe incluir zona horaria")
        return momento.astimezone(timezone.utc)

    @staticmethod
    def _crear(operacion, mensaje_conflicto):
        try:
            return operacion()
        except (ValueError, KeyError) as error:
            raise Conflicto(mensaje_conflicto) from error