from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db import Base, get_db
from main import app
from models import Client, ClientParking, Parking

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)

TestingSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def init_data(db_session):
    client_with_card = Client(
        name="Энакен",
        surname="Скайуокер",
        credit_card="1111-2222-3333-4444",
        car_number="A001AA",
    )
    client_no_card = Client(name="Реван", surname="Дарт", car_number="B002BB")
    client_fresh = Client(
        name="Кайл",
        surname="Катарн",
        credit_card="5555-6666-7777-8888",
        car_number="C003CC",
    )
    db_session.add_all([client_with_card, client_no_card, client_fresh])
    await db_session.commit()

    parking = Parking(
        address="Космический порт Корусанта",
        opened=True,
        count_places=1000000,
        count_available_places=1000000,
    )
    db_session.add(parking)
    await db_session.commit()
    await db_session.refresh(parking)

    parking.count_available_places -= 1

    log_entry_enaken = ClientParking(
        client_id=client_with_card.id, parking_id=parking.id, time_in=datetime.now()
    )
    db_session.add(log_entry_enaken)
    await db_session.commit()

    return {
        "client_with_card": client_with_card,
        "client_fresh": client_fresh,
        "parking": parking,
    }
