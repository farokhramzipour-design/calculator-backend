from __future__ import annotations

import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.routers import auth, calculation, invoices, rates, shipments, taric

settings = get_settings()

configure_logging()
logger = get_logger()

app = FastAPI(
    title=settings.app_name,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://veritariffai.co"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(shipments.router, prefix=settings.api_prefix)
app.include_router(rates.router, prefix=settings.api_prefix)
app.include_router(calculation.router, prefix=settings.api_prefix)
app.include_router(taric.router, prefix=settings.api_prefix)
app.include_router(taric.admin_router, prefix=settings.api_prefix)
app.include_router(invoices.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {"service": settings.app_name}


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    logger.info("request", path=str(request.url.path), method=request.method, request_id=request_id)
    response.headers["X-Request-ID"] = request_id
    return response
