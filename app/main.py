from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager

from app.routes import chat
from app.core.database import engine, get_db
from app.routes import auth
from app.routes import conversation


db_connected = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    We'll test DB connection here.
    """
    global db_connected
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db_connected = True
        print("✅ Database connected successfully.")
    except Exception as e:
        db_connected = False
        print("❌ Database connection failed:", e)

    yield

    # Shutdown logic (optional)
    await engine.dispose()


app = FastAPI(
    title="AI Form Agent",
    lifespan=lifespan
)

app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(conversation.router)


@app.get("/")
async def root():
    return {
        "message": "AI Form Agent Running",
        "database_connected": db_connected
    }
