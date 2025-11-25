from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from db import get_db

router = APIRouter()
db_dep = Depends(get_db)


@router.get("/", tags=["General"])
async def head():
    return "Привет от Yoda API PARKING STAR WARS (Async Edition)"


@router.get("/clients", response_model=List[schemas.ClientResponse], tags=["Clients"])
async def get_clients(db: AsyncSession = db_dep):
    query = select(models.Client)
    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/clients/{client_id}", response_model=schemas.ClientResponse, tags=["Clients"]
)
async def get_client_detail(client_id: int, db: AsyncSession = db_dep):
    client = await db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return client


@router.post(
    "/clients", response_model=schemas.ClientResponse, status_code=201, tags=["Clients"]
)
async def create_client(client_data: schemas.ClientCreate, db: AsyncSession = db_dep):
    new_client = models.Client(
        name=client_data.name,
        surname=client_data.surname,
        credit_card=client_data.credit_card,
        car_number=client_data.car_number,
    )
    db.add(new_client)
    await db.commit()
    await db.refresh(new_client)
    return new_client


@router.post(
    "/parkings",
    response_model=schemas.ParkingResponse,
    status_code=201,
    tags=["Parkings"],
)
async def create_parking(
    parking_data: schemas.ParkingCreate, db: AsyncSession = db_dep
):
    new_parking = models.Parking(
        address=parking_data.address,
        opened=parking_data.opened,
        count_places=parking_data.count_places,
        count_available_places=parking_data.count_available_places,
    )
    db.add(new_parking)
    await db.commit()
    await db.refresh(new_parking)
    return new_parking


@router.post("/client_parkings", status_code=201, tags=["Operations"])
async def enter_parking(action: schemas.ParkingAction, db: AsyncSession = db_dep):
    parking = await db.get(models.Parking, action.parking_id)
    client = await db.get(models.Client, action.client_id)

    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден, зарегистрируйте")
    if not parking:
        raise HTTPException(status_code=404, detail="Парковка не найдена")
    if not parking.opened:
        raise HTTPException(status_code=400, detail="Парковка закрыта")
    if parking.count_available_places <= 0:
        raise HTTPException(status_code=400, detail="Нет свободных мест")

    query = select(models.ClientParking).filter_by(
        client_id=action.client_id, parking_id=action.parking_id
    )
    result = await db.execute(query)
    existing_entry = result.scalars().first()

    if existing_entry and existing_entry.time_out is None:
        raise HTTPException(status_code=400, detail="Машина уже на парковке")

    entry = models.ClientParking(
        client_id=action.client_id, parking_id=action.parking_id, time_in=datetime.now()
    )

    try:
        parking.count_available_places -= 1
        if parking.count_available_places == 0:
            parking.opened = False

        db.add(entry)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Не удалось заехать. Ошибка БД: {str(e)}"
        )

    return {"message": "Заезд разрешен"}


@router.delete("/client_parkings", tags=["Operations"])
async def exit_parking(action: schemas.ParkingAction, db: AsyncSession = db_dep):
    client = await db.get(models.Client, action.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    if not client.credit_card:
        raise HTTPException(
            status_code=400, detail="Невозможно оплатить: не привязана карта"
        )

    query = select(models.ClientParking).filter_by(
        client_id=action.client_id, parking_id=action.parking_id, time_out=None
    )
    result = await db.execute(query)
    record = result.scalars().first()

    if not record:
        raise HTTPException(status_code=404, detail="Автомобиль не найден на парковке")

    record.time_out = datetime.now()

    parking = await db.get(models.Parking, action.parking_id)
    if parking:
        parking.count_available_places += 1
        parking.opened = True

    await db.commit()

    return {"message": "Оплата произведена, выезд разрешен"}
