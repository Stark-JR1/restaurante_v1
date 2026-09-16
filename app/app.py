from flask import Flask

from app.routes import bp


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder="../static",
        static_url_path="/static",
    )
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.json.ensure_ascii = False
    app.register_blueprint(bp)
    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=False, use_reloader=False)
