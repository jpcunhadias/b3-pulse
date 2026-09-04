from pydantic import BaseModel


class IngestRequest(BaseModel):
    ticker: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class IngestResponse(BaseModel):
    ticker: str
    bronze_partitions: int
    feature_rows: int


class Quote(BaseModel):
    trade_date: str
    closing_price: float
    trade_volume: float


class PredictionResponse(BaseModel):
    ticker: str
    as_of_date: str
    last_close: float
    predicted_next_close: float
    model_version: str


class ModelMetrics(BaseModel):
    run_id: str
    mae: float
    rmse: float
    mape: float
