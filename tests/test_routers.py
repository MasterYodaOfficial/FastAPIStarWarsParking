import pytest
from sqlalchemy import select

from models import Client, ClientParking, Parking
from schemas import ClientResponse
from tests.factories import ClientFactory, ParkingFactory


@pytest.mark.getters
@pytest.mark.parametrize("route", ["/clients", "/clients/1", "/"])
async def test_get_routes_status_200(client, init_data, route):
    """
    Проверка GET-методов
    """
    response = await client.get(route)
    assert response.status_code == 200


@pytest.mark.getters
async def test_get_clients(client, init_data):
    """
    Проверка списка клиентов
    """
    response = await client.get("/clients")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    clients_objects = [ClientResponse(**item) for item in data]

    enaken = next((c for c in clients_objects if c.name == "Энакен"), None)

    assert enaken is not None
    assert enaken.name == "Энакен"
    assert enaken.surname == "Скайуокер"


@pytest.mark.create
async def test_create_client(client, db_session):
    """
    Создание клиента.
    """
    data = {
        "name": "Люк",
        "surname": "Скайуокер",
        "credit_card": "1111-2222-3333-4444",
        "car_number": "M001MM186",
    }
    resp = await client.post("/clients", json=data)
    assert resp.status_code == 201

    stmt = select(Client).filter_by(car_number="M001MM186")
    result = await db_session.execute(stmt)
    created_client = result.scalars().first()

    assert created_client is not None
    assert created_client.name == "Люк"


@pytest.mark.create
async def test_create_parking(client, db_session):
    """
    Создание парковки.
    """
    data = {
        "address": "Космопорт Джедаев на Корусанте",
        "opened": True,
        "count_places": 50,
        "count_available_places": 50,
    }
    resp = await client.post("/parkings", json=data)
    assert resp.status_code == 201

    stmt = select(Parking).filter_by(address="Космопорт Джедаев на Корусанте")
    result = await db_session.execute(stmt)
    created_parking = result.scalars().first()

    assert created_parking is not None
    assert created_parking.count_places == 50


@pytest.mark.parking
async def test_enter_parking(client, db_session, init_data):
    """
    Заезд на парковку.
    """
    payload = {"client_id": 3, "parking_id": 1}

    parking = await db_session.get(Parking, 1)
    places_before = parking.count_available_places

    resp = await client.post("/client_parkings", json=payload)
    assert resp.status_code == 201
    assert resp.json()["message"] == "Заезд разрешен"

    await db_session.refresh(parking)

    assert parking.count_available_places == places_before - 1

    stmt = select(ClientParking).filter_by(client_id=3, parking_id=1)
    result = await db_session.execute(stmt)
    log = result.scalars().first()

    assert log is not None
    assert log.time_in is not None
    assert log.time_out is None


@pytest.mark.parking
async def test_exit_parking(client, db_session, init_data):
    """
    Выезд с парковки.
    """
    payload = {"client_id": 1, "parking_id": 1}

    parking = await db_session.get(Parking, 1)
    places_before = parking.count_available_places

    resp = await client.request("DELETE", "/client_parkings", json=payload)

    assert resp.status_code == 200
    assert "Оплата произведена" in resp.json()["message"]

    await db_session.refresh(parking)
    assert parking.count_available_places == places_before + 1

    stmt = select(ClientParking).filter_by(client_id=1, parking_id=1)
    result = await db_session.execute(stmt)
    log = result.scalars().first()

    assert log.time_out is not None


@pytest.mark.create
async def test_create_client_with_factory(client, db_session):
    """
    Тест создания клиента с данными из FactoryBoy.
    """
    client_data = ClientFactory.build()

    payload = {
        "name": client_data.name,
        "surname": client_data.surname,
        "credit_card": client_data.credit_card,
        "car_number": client_data.car_number,
    }

    resp = await client.post("/clients", json=payload)

    assert resp.status_code == 201

    stmt = select(Client).filter_by(car_number=client_data.car_number)
    result = await db_session.execute(stmt)
    created_client = result.scalars().first()

    assert created_client is not None
    assert created_client.name == client_data.name


@pytest.mark.create
async def test_create_parking_with_factory(client, db_session):
    """
    Тест создания парковки с данными из FactoryBoy.
    """
    parking_data = ParkingFactory.build()

    payload = {
        "address": parking_data.address,
        "opened": parking_data.opened,
        "count_places": parking_data.count_places,
        "count_available_places": parking_data.count_available_places,
    }

    resp = await client.post("/parkings", json=payload)
    assert resp.status_code == 201

    stmt = select(Parking).filter_by(address=parking_data.address)
    result = await db_session.execute(stmt)
    created_parking = result.scalars().first()

    assert created_parking is not None
    assert created_parking.count_places == parking_data.count_places


@pytest.mark.getters
async def test_get_client_not_found(client, db_session):
    """
    Попытка получить клиента по ID, которого нет.
    """
    response = await client.get("/clients/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Клиент не найден"


@pytest.mark.parking
async def test_enter_parking_client_not_found(client, db_session):
    """
    Заезд: Клиент не найден.
    """
    payload = {"client_id": 999999, "parking_id": 1}
    resp = await client.post("/client_parkings", json=payload)
    assert resp.status_code == 404
    assert "Клиент не найден" in resp.json()["detail"]


@pytest.mark.parking
async def test_enter_parking_not_found(client, db_session, init_data):
    """
    Заезд: Парковка не найдена.
    """
    payload = {"client_id": 1, "parking_id": 999999}
    resp = await client.post("/client_parkings", json=payload)
    assert resp.status_code == 404
    assert "Парковка не найдена" in resp.json()["detail"]


@pytest.mark.parking
async def test_enter_parking_closed(client, db_session, init_data):
    """
    Заезд: Парковка закрыта
    """
    parking = await db_session.get(Parking, 1)
    parking.opened = False
    await db_session.commit()

    payload = {"client_id": 3, "parking_id": 1}
    resp = await client.post("/client_parkings", json=payload)

    assert resp.status_code == 400
    assert "Парковка закрыта" in resp.json()["detail"]


@pytest.mark.parking
async def test_enter_parking_full(client, db_session, init_data):
    """
    Заезд: Нет свободных мест.
    """
    parking = await db_session.get(Parking, 1)
    parking.count_available_places = 0
    await db_session.commit()

    payload = {"client_id": 3, "parking_id": 1}
    resp = await client.post("/client_parkings", json=payload)

    assert resp.status_code == 400
    assert "Нет свободных мест" in resp.json()["detail"]


@pytest.mark.parking
async def test_enter_parking_duplicate(client, db_session, init_data):
    """
    Заезд: Клиент уже на парковке (повторный въезд).
    """
    payload = {"client_id": 1, "parking_id": 1}
    resp = await client.post("/client_parkings", json=payload)

    assert resp.status_code == 400
    assert "Машина уже на парковке" in resp.json()["detail"]


@pytest.mark.parking
async def test_enter_parking_auto_close_logic(client, db_session, init_data):
    """
    Проверка логики: если место осталось 1 и клиент заезжает,
    парковка должна закрыться (opened -> False).
    """
    parking = await db_session.get(Parking, 1)
    parking.count_available_places = 1
    parking.opened = True
    await db_session.commit()

    payload = {"client_id": 3, "parking_id": 1}
    resp = await client.post("/client_parkings", json=payload)
    assert resp.status_code == 201

    await db_session.refresh(parking)
    assert parking.count_available_places == 0
    assert parking.opened is False


@pytest.mark.parking
async def test_exit_parking_client_not_found(client, db_session):
    """
    Выезд: Клиент не найден.
    """
    payload = {"client_id": 999999, "parking_id": 1}
    resp = await client.request("DELETE", "/client_parkings", json=payload)
    assert resp.status_code == 404
    assert "Клиент не найден" in resp.json()["detail"]


@pytest.mark.parking
async def test_exit_parking_no_card(client, db_session, init_data):
    """
    Выезд: У клиента нет карты (Клиент 2 - Реван).
    """

    payload = {"client_id": 2, "parking_id": 1}
    resp = await client.request("DELETE", "/client_parkings", json=payload)

    assert resp.status_code == 400
    assert "не привязана карта" in resp.json()["detail"]


@pytest.mark.parking
async def test_exit_parking_record_not_found(client, db_session, init_data):
    """
    Выезд: Машина не числится на парковке (Клиент 3 - Кайл еще не заезжал).
    """
    payload = {"client_id": 3, "parking_id": 1}
    resp = await client.request("DELETE", "/client_parkings", json=payload)

    assert resp.status_code == 404
    assert "Автомобиль не найден" in resp.json()["detail"]
