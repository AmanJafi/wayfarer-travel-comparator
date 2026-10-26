from models import Journey


# sorting returns a new list, so the collected journeys stay unchanged
def sort_by_price(journeys: list[Journey]) -> list[Journey]:
    return sorted(journeys,key=lambda x : x.price)

def sort_by_duration(journeys: list[Journey]) -> list[Journey]:
    return sorted(journeys, key=lambda x: x.duration_minutes)

def sort_by_transfers(journeys: list[Journey]) -> list[Journey]:
    # fewer stops come first; stable sorting keeps the previous order for ties
    return sorted(journeys, key=lambda x: x.transfers)
