import time
import structlog

logger = structlog.get_logger(__name__)

class DataConverterContextManager:
    def __init__(self, data_conversion_type: str, data_length: int = 0):
        self.data_conversion_type = data_conversion_type
        self.data_length = data_length
        self.start_time: float | None = None
        self.end_time: float | None = None

    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        time_taken = self.end_time - self.start_time
        if time_taken > 0.1:
            logger.warning(f"{self.data_conversion_type} took {time_taken} seconds for a length of {self.data_length}")

    def set_data_length(self, data_length: int):
        self.data_length = data_length