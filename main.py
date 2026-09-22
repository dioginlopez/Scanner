import os
import webbrowser

from back.app import create_app


app = create_app()


if __name__ == "__main__":
    is_render = bool(os.getenv("RENDER"))
    host = "0.0.0.0" if is_render else "127.0.0.1"
    port = int(os.getenv("PORT", "5000"))
    if not is_render:
        webbrowser.open(f"http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)
