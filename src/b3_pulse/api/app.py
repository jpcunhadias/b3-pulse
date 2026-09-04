from fastapi import FastAPI, HTTPException

from b3_pulse.api import schemas, service
from b3_pulse.config import settings

app = FastAPI(title="b3-pulse API")


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
