from fastapi import FastAPI
from src.auth.routes import auth_router
from src.board.routes import board_router
from .middleware import register_middleware
from contextlib import asynccontextmanager
import structlog
from src.config import Config
from src.db.main import init_db
from src.errors import register_all_errors

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app.starting", domain=Config.DOMAIN)
    await init_db()
    logger.info("app.ready")

    yield

    logger.info("app.shutting_down")

version = "v1"

version_prefix = f"/api/{version}"

app = FastAPI(
    version=version,
    title="Board App",
    description="A simple board app",
    lifespan=lifespan
)

# register errors / middleware

register_middleware(app)
register_all_errors(app)

# include all routers

app.include_router(auth_router, prefix=f"/api/{version}/users", tags=["Auth / Users"])
app.include_router(board_router, prefix=f"/api/{version}/board", tags=["Board"])