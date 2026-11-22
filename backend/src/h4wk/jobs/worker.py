import sys

from huey.bin.huey_consumer import consumer_main

from h4wk.jobs.lanes import worker_threads


def main() -> None:
    sys.argv = [sys.argv[0], "h4wk.jobs.queue.huey", "-w", str(worker_threads())]
    consumer_main()


if __name__ == "__main__":
    main()
