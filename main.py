"""Runs arxiv-search in debug mode.

Run as `python main.py`"""
from search.factory import create_ui_web_app

if __name__ == "__main__":
    app = create_ui_web_app()
    app.config['FLASK_DEBUG']=1
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, port=8080)
