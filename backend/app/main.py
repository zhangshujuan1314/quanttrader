from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import strategy, backtest, trade, data, auth
from app.infrastructure.persistence.database import create_database, dispose


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await create_database()
    yield
    await dispose()

app = FastAPI(title="量化智投", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(data.router, prefix="/api/data")
app.include_router(strategy.router, prefix="/api/strategy")
app.include_router(backtest.router, prefix="/api/backtest")
app.include_router(trade.router, prefix="/api/trade")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
