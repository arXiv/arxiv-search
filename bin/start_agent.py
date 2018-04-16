"""Run the indexing agent stream processor."""
from search.agent import process_stream


def start_agent() -> None:
    """Start the record processor."""
    process_stream()


if __name__ == '__main__':
    start_agent()
