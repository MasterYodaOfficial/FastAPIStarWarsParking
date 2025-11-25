from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import Base, engine
from routers import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Yoda Parking API", version="2.0", lifespan=lifespan)

app.include_router(router)
