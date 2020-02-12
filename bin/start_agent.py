"""Run the indexing agent stream processor."""
from search.agent import process_stream
from search.factory import create_ui_web_app


def start_agent() -> None:
    """Start the record processor."""
    app = create_ui_web_app()
    with app.app_context():
        process_stream()


if __name__ == "__main__":
    start_agent()
