from pydantic import BaseModel


class Journey(BaseModel):
    # both scrapers use this shape so the rest of the app can treat results alike
    mode: str
    provider: str
    price: float
    duration_minutes: int
    transfers: int
    # some source pages do not provide times or a link for every result
    departure_time: str | None = None
    arrival_time: str | None = None
    source_url: str | None = None
