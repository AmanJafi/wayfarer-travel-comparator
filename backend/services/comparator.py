from models import Journey

def sort_by_price(journeys: list[Journey]) -> list[Journey]:
    return sorted(journeys,key=lambda x : x.price)

def sort_by_duration(journeys: list[Journey]) -> list[Journey]:
    return sorted(journeys, key=lambda x: x.duration_minutes)

def sort_by_transfers(journeys: list[Journey]) -> list[Journey]:
    return sorted(journeys, key=lambda x: x.transfers)
