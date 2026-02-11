import logging
from collections import deque


class MemoryLogHandler(logging.Handler):
    """將 log 存在記憶體中的 handler，保留最近 N 筆"""

    def __init__(self, max_records=500):
        super().__init__()
        self.records = deque(maxlen=max_records)

    def emit(self, record):
        self.records.append(self.format(record))

    def get_logs(self) -> list[str]:
        return list(self.records)

    def clear(self):
        self.records.clear()


# 全域 singleton
memory_handler = MemoryLogHandler(max_records=500)
memory_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
