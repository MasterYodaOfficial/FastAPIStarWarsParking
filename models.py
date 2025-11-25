from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class Client(Base):
    __tablename__ = "client"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    surname: Mapped[str] = mapped_column(String(50), nullable=False)
    credit_card: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    car_number: Mapped[str] = mapped_column(String(10))


class Parking(Base):
    __tablename__ = "parking"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    address: Mapped[str] = mapped_column(String(100), nullable=False)
    opened: Mapped[bool] = mapped_column(default=True)
    count_places: Mapped[int] = mapped_column(nullable=False)
    count_available_places: Mapped[int] = mapped_column(nullable=False)


class ClientParking(Base):
    __tablename__ = "client_parking"

    __table_args__ = (
        UniqueConstraint("client_id", "parking_id", name="unique_client_parking"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"))
    parking_id: Mapped[int] = mapped_column(ForeignKey("parking.id"))
    time_in: Mapped[datetime] = mapped_column()
    time_out: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    client: Mapped["Client"] = relationship(backref="parking_history")
    parking: Mapped["Parking"] = relationship(backref="client_history")
