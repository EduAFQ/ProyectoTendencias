from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import timezone

from flaskr.domain.models import Cliente, Parking, Plaza, Usuario, Vehiculo
from flaskr.infrastructure.db.models.parkingOrm import ClienteORM, ParkingORM, PlazaORM, UsuarioORM, VehiculoORM
from flaskr.repositories.parkingRepository import ParkingRepository


class ParkingRepositorySQL(ParkingRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def crear_cliente(self, cliente):
        return self._crear(ClienteORM(nombre=cliente.nombre, email=cliente.email), self._cliente)

    def obtener_cliente(self, cliente_id):
        return self._obtener(ClienteORM, cliente_id, self._cliente)

    def crear_usuario(self, usuario):
        return self._crear(UsuarioORM(nombre=usuario.nombre), self._usuario)

    def obtener_usuario(self, usuario_id):
        return self._obtener(UsuarioORM, usuario_id, self._usuario)

    def crear_vehiculo(self, vehiculo):
        return self._crear(VehiculoORM(matricula=vehiculo.matricula, cliente_id=vehiculo.cliente_id), self._vehiculo)

    def obtener_vehiculo(self, vehiculo_id):
        return self._obtener(VehiculoORM, vehiculo_id, self._vehiculo)

    def crear_plaza(self, plaza):
        return self._crear(PlazaORM(codigo=plaza.codigo), self._plaza)

    def obtener_plaza(self, plaza_id):
        return self._obtener(PlazaORM, plaza_id, self._plaza)

    def listar_plazas(self):
        with self.session_factory() as session:
            return [self._plaza(row) for row in session.scalars(select(PlazaORM).order_by(PlazaORM.codigo))]

    def actualizar_plaza(self, plaza):
        try:
            with self.session_factory.begin() as session:
                row = session.get(PlazaORM, plaza.id)
                if row is None:
                    return None
                row.codigo = plaza.codigo
                session.flush()
                resultado = self._plaza(row)
            return resultado
        except IntegrityError as error:
            raise ValueError("El código de plaza ya existe") from error

    def eliminar_plaza(self, plaza_id):
        try:
            with self.session_factory.begin() as session:
                row = session.get(PlazaORM, plaza_id)
                if row is not None:
                    session.delete(row)
                    session.flush()
        except IntegrityError as error:
            raise ValueError("La plaza tiene estancias asociadas") from error

    def obtener_estancia_activa_vehiculo(self, vehiculo_id):
        return self._estancia_activa(ParkingORM.vehiculo_id == vehiculo_id)

    def obtener_estancia_activa_plaza(self, plaza_id):
        return self._estancia_activa(ParkingORM.plaza_id == plaza_id)

    def obtener_estancia_activa(self, estancia_id):
        with self.session_factory() as session:
            row = session.scalar(select(ParkingORM).where(ParkingORM.id == estancia_id, ParkingORM.salida.is_(None)))
            return self._parking(row) if row else None

    def crear_estancia(self, estancia):
        row = ParkingORM(
            vehiculo_id=estancia.vehiculo_id,
            plaza_id=estancia.plaza_id,
            usuario_id=estancia.usuario_id,
            entrada=estancia.entrada,
            salida=estancia.salida,
        )
        return self._crear(row, self._parking)

    def cerrar_estancia(self, estancia_id, salida):
        try:
            with self.session_factory.begin() as session:
                row = session.scalar(select(ParkingORM).where(ParkingORM.id == estancia_id, ParkingORM.salida.is_(None)))
                if row is None:
                    return None
                row.salida = salida
                session.flush()
                result = self._parking(row)
            return result
        except IntegrityError as error:
            raise ValueError("Conflicto al cerrar estancia") from error

    def listar_estancias_activas(self):
        with self.session_factory() as session:
            rows = session.scalars(select(ParkingORM).where(ParkingORM.salida.is_(None)).order_by(ParkingORM.entrada))
            return [self._parking(row) for row in rows]

    def _estancia_activa(self, condicion):
        with self.session_factory() as session:
            row = session.scalar(select(ParkingORM).where(condicion, ParkingORM.salida.is_(None)))
            return self._parking(row) if row else None

    def _crear(self, row, convertir):
        try:
            with self.session_factory.begin() as session:
                session.add(row)
                session.flush()
                resultado = convertir(row)
            return resultado
        except IntegrityError as error:
            raise ValueError("Registro duplicado o referencia inexistente") from error

    def _obtener(self, modelo, identificador, convertir):
        with self.session_factory() as session:
            row = session.get(modelo, identificador)
            return convertir(row) if row else None

    @staticmethod
    def _cliente(row):
        return Cliente(row.nombre, row.email, row.id)

    @staticmethod
    def _usuario(row):
        return Usuario(row.nombre, row.id)

    @staticmethod
    def _vehiculo(row):
        return Vehiculo(row.matricula, row.cliente_id, row.id)

    @staticmethod
    def _plaza(row):
        return Plaza(row.codigo, row.id)

    @staticmethod
    def _parking(row):
        return Parking(
            row.vehiculo_id,
            row.plaza_id,
            row.usuario_id,
            ParkingRepositorySQL._utc(row.entrada),
            ParkingRepositorySQL._utc(row.salida),
            row.id,
        )

    @staticmethod
    def _utc(value):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value