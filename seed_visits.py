"""Add 25 sample visits to today's local 08:00–18:00 interval."""
import random
from datetime import datetime, time, timedelta
import storage

if __name__ == "__main__":
    storage.init()
    start = datetime.combine(datetime.now().date(), time(8))
    for seconds in sorted(random.randint(0, 10 * 3600) for _ in range(25)):
        storage.add_visit((start + timedelta(seconds=seconds)).astimezone().isoformat(timespec="seconds"))
    print("Added 25 sample visits for today.")
