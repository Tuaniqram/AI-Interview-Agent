from datetime import date, datetime, time, timedelta


def generate_slots(
    start_date: date,
    end_date: date,
    start_time: time,
    end_time: time,
    duration_min: int,
    buffer_min: int = 0,
    existing_bookings: list[tuple[date, time, time]] | None = None,
) -> list[dict]:
    existing = existing_bookings or []
    existing_map: dict[date, list[tuple[time, time]]] = {}
    for bd, bt, et in existing:
        existing_map.setdefault(bd, []).append((bt, et))

    slots = []
    current = start_date
    delta = timedelta(minutes=duration_min + buffer_min)

    while current <= end_date:
        slot_start = datetime.combine(current, start_time)
        slot_end = datetime.combine(current, end_time)

        while slot_start + timedelta(minutes=duration_min) <= slot_end:
            slot_start_time = slot_start.time()
            slot_end_time = (slot_start + timedelta(minutes=duration_min)).time()

            conflict = False
            for book_start, book_end in existing_map.get(current, []):
                if slot_start_time < book_end and slot_end_time > book_start:
                    conflict = True
                    break

            if not conflict:
                slots.append({
                    "date": current,
                    "start_time": slot_start_time,
                    "end_time": slot_end_time,
                    "duration_min": duration_min,
                })

            slot_start += delta

        current += timedelta(days=1)

    return slots
