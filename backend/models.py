from pydantic import BaseModel


class Journey(BaseModel):
    mode: str
    provider: str
    price: float
    duration_minutes: int
    transfers: int
    departure_time: str | None = None
    arrival_time: str | None = None
    source_url: str | None = None
