import pytest

from flaskr.domain.models import Cliente, Parking, Plaza, Usuario, Vehiculo
from flaskr.services.parkingServices import ParkingServices


class RepositorioEnMemoria:
    def __init__(self):
        self.clientes = {}
        self.usuarios = {}
        self.vehiculos = {}
        self.plazas = {}
        self.estancias = {}
        self._ids = {tipo: 1 for tipo in ("cliente", "usuario", "vehiculo", "plaza", "estancia")}

    def _siguiente_id(self, tipo):
        identificador = self._ids[tipo]
        self._ids[tipo] += 1
        return identificador

    def crear_cliente(self, cliente):
        if cliente.email and any(item.email == cliente.email for item in self.clientes.values()):
            raise ValueError("El email ya está registrado")
        resultado = Cliente(cliente.nombre, cliente.email, self._siguiente_id("cliente"))
        self.clientes[resultado.id] = resultado
        return resultado

    def obtener_cliente(self, cliente_id):
        return self.clientes.get(cliente_id)

    def listar_clientes(self):
        return list(self.clientes.values())

    def crear_usuario(self, usuario):
        resultado = Usuario(usuario.nombre, self._siguiente_id("usuario"))
        self.usuarios[resultado.id] = resultado
        return resultado

    def obtener_usuario(self, usuario_id):
        return self.usuarios.get(usuario_id)

    def listar_usuarios(self):
        return list(self.usuarios.values())

    def crear_vehiculo(self, vehiculo):
        if any(item.matricula == vehiculo.matricula for item in self.vehiculos.values()):
            raise ValueError("La matrícula ya está registrada")
        resultado = Vehiculo(
            vehiculo.matricula, vehiculo.cliente_id, self._siguiente_id("vehiculo")
        )
        self.vehiculos[resultado.id] = resultado
        return resultado

    def obtener_vehiculo(self, vehiculo_id):
        return self.vehiculos.get(vehiculo_id)

    def listar_vehiculos(self):
        return list(self.vehiculos.values())

    def crear_plaza(self, plaza):
        if any(item.codigo == plaza.codigo for item in self.plazas.values()):
            raise ValueError("El código de plaza ya existe")
        resultado = Plaza(plaza.codigo, self._siguiente_id("plaza"))
        self.plazas[resultado.id] = resultado
        return resultado

    def obtener_plaza(self, plaza_id):
        return self.plazas.get(plaza_id)

    def listar_plazas(self):
        return list(self.plazas.values())

    def actualizar_plaza(self, plaza):
        if any(
            item.id != plaza.id and item.codigo == plaza.codigo
            for item in self.plazas.values()
        ):
            raise ValueError("El código de plaza ya existe")
        if plaza.id not in self.plazas:
            return None
        self.plazas[plaza.id] = plaza
        return plaza

    def eliminar_plaza(self, plaza_id):
        if any(item.plaza_id == plaza_id for item in self.estancias.values()):
            raise ValueError("La plaza tiene estancias asociadas")
        self.plazas.pop(plaza_id, None)

    def obtener_estancia_activa_vehiculo(self, vehiculo_id):
        return next((
            item for item in self.estancias.values()
            if item.vehiculo_id == vehiculo_id and item.salida is None
        ), None)

    def obtener_estancia_activa_plaza(self, plaza_id):
        return next((
            item for item in self.estancias.values()
            if item.plaza_id == plaza_id and item.salida is None
        ), None)

    def obtener_estancia_activa(self, estancia_id):
        estancia = self.estancias.get(estancia_id)
        return estancia if estancia and estancia.salida is None else None

    def crear_estancia(self, estancia):
        if self.obtener_estancia_activa_vehiculo(estancia.vehiculo_id):
            raise ValueError("El vehículo ya tiene una estancia activa")
        if self.obtener_estancia_activa_plaza(estancia.plaza_id):
            raise ValueError("La plaza ya está ocupada")
        resultado = Parking(
            estancia.vehiculo_id,
            estancia.plaza_id,
            estancia.usuario_id,
            estancia.entrada,
            estancia.salida,
            self._siguiente_id("estancia"),
        )
        self.estancias[resultado.id] = resultado
        return resultado

    def cerrar_estancia(self, estancia_id, salida):
        estancia = self.obtener_estancia_activa(estancia_id)
        if estancia is None:
            return None
        resultado = Parking(
            estancia.vehiculo_id,
            estancia.plaza_id,
            estancia.usuario_id,
            estancia.entrada,
            salida,
            estancia.id,
        )
        self.estancias[estancia_id] = resultado
        return resultado

    def listar_estancias_activas(self):
        return [item for item in self.estancias.values() if item.salida is None]

    def listar_estancias_finalizadas(
        self, desde=None, hasta=None, cliente_id=None, antes_de=None, limite=20
    ):
        raise NotImplementedError("El repositorio de pruebas solo implementa reglas del dominio")


@pytest.fixture
def servicio():
    return ParkingServices(RepositorioEnMemoria())
