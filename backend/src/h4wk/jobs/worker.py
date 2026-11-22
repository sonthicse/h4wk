"""Chạy worker hàng đợi default với số luồng tính theo watchlist (xem lanes.worker_threads).

uv run python -m h4wk.jobs.worker

Số luồng tính lúc khởi động: thêm kênh hoặc tăng số luồng mỗi kênh vượt quá số này thì khởi
động lại worker để có thêm luồng; trong lúc đó các kênh vẫn chạy, chỉ chia nhau ít luồng hơn.
"""

import sys

from huey.bin.huey_consumer import consumer_main

from h4wk.jobs.lanes import worker_threads


def main() -> None:
    sys.argv = [sys.argv[0], "h4wk.jobs.queue.huey", "-w", str(worker_threads())]
    consumer_main()


if __name__ == "__main__":
    main()
