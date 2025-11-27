from typing import Optional

from pydantic import BaseModel, ConfigDict


class ClientBase(BaseModel):
    name: str
    surname: str
    credit_card: Optional[str] = None
    car_number: str


class ClientCreate(ClientBase):
    pass


class ClientResponse(ClientBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ParkingBase(BaseModel):
    address: str
    opened: bool
    count_places: int
    count_available_places: int


class ParkingCreate(ParkingBase):
    pass


class ParkingResponse(ParkingBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ParkingAction(BaseModel):
    client_id: int
    parking_id: int
