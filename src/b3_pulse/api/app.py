import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response

from b3_pulse.api import schemas, service
from b3_pulse.config import settings
from b3_pulse.logging_config import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info(
        "b3-pulse API starting (default ticker=%s, mlflow=%s)",
        settings.ticker,
        settings.mlflow_tracking_uri,
    )
    yield
    logger.info("b3-pulse API shutting down")


app = FastAPI(title="b3-pulse API", lifespan=lifespan)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("%s %s failed", request.method, request.url.path)
        raise
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.0f ms)", request.method, request.url.path, response.status_code, elapsed_ms
    )
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest", response_model=schemas.IngestResponse)
def ingest(request: schemas.IngestRequest) -> schemas.IngestResponse:
    result = service.run_ingestion_pipeline(request.ticker, request.start_date, request.end_date)
    return schemas.IngestResponse(**result)


@app.get("/quotes", response_model=list[schemas.Quote])
def quotes(ticker: str = settings.ticker, limit: int = 90) -> list[schemas.Quote]:
    df = service.get_recent_quotes(ticker, limit)
    return [
        schemas.Quote(
            trade_date=str(row.trade_date),
            closing_price=float(row.closing_price),
            trade_volume=float(row.trade_volume),
        )
        for row in df.itertuples()
    ]


@app.get("/predict", response_model=schemas.PredictionResponse)
def predict(ticker: str = settings.ticker) -> schemas.PredictionResponse:
    try:
        result = service.predict_next_close(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return schemas.PredictionResponse(**result)


@app.get("/model/metrics", response_model=schemas.ModelMetrics)
def model_metrics(ticker: str = settings.ticker) -> schemas.ModelMetrics:
    try:
        result = service.get_latest_metrics(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return schemas.ModelMetrics(**result)


def serve() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
