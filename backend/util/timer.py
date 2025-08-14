import time


class Timer:
    def __init__(self, precision: int = 3) -> None:
        self.start_time = time.time()
        self.precision = precision

    def reset(self) -> None:
        self.start_time = time.time()

    def duration(self) -> float:
        return round(time.time() - self.start_time, self.precision)
