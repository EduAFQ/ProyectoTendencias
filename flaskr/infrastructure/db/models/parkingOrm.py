from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ClienteORM(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    vehiculos: Mapped[list["VehiculoORM"]] = relationship(back_populates="cliente")


class UsuarioORM(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)


class VehiculoORM(Base):
    __tablename__ = "vehiculos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    cliente: Mapped[ClienteORM] = relationship(back_populates="vehiculos")


class PlazaORM(Base):
    __tablename__ = "plazas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)


class ParkingORM(Base):
    __tablename__ = "estancias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehiculo_id: Mapped[int] = mapped_column(ForeignKey("vehiculos.id", ondelete="RESTRICT"), nullable=False)
    plaza_id: Mapped[int] = mapped_column(ForeignKey("plazas.id", ondelete="RESTRICT"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    entrada: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    salida: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index("uq_estancia_activa_vehiculo", ParkingORM.vehiculo_id, unique=True, sqlite_where=ParkingORM.salida.is_(None))
Index("uq_estancia_activa_plaza", ParkingORM.plaza_id, unique=True, sqlite_where=ParkingORM.salida.is_(None))