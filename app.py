from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

from backend.business_logic import session

FRONT_DIR = os.path.dirname(os.path.abspath(__file__))

def create_app(session):
    app = Flask(__name__)
    CORS(app)
    app.config['SESSION'] = session

    @app.route('/')
    def index():
        return send_from_directory(FRONT_DIR, 'front.html')

    @app.route('/<path:filename>')
    def static_files(filename):
        return send_from_directory(FRONT_DIR, filename)

    @app.route("/api/devices")
    def get_devices():
        return jsonify({
            "inputs": [
                {"id": "mic-0", "label": "Микрофон (VB-Cable)"},
                {"id": "mic-1", "label": "Микрофон (Встроенный)"}
            ],
            "outputs": [
                {"id": "out-0", "label": "Динамики (Realtek)"},
                {"id": "out-1", "label": "Наушники (USB)"}
            ]
        })

    @app.route("/api/presets")
    def get_presets():
        return jsonify([
            {"id": "p1", "name": "Ассистент", "prompt": "Ты – полезный голосовой ассистент."},
            {"id": "p2", "name": "Переводчик", "prompt": "Ты переводишь речь с русского на английский."},
            {"id": "p3", "name": "Собеседник", "prompt": "Ты – дружелюбный собеседник."}
        ])

    @app.route("/api/command", methods=["POST"])
    def handle_command():
        s = app.config['SESSION']
        data = request.get_json()
        cmd = data.get("cmd")

        if cmd == "start":
            ok, msg = s.start()
        elif cmd == "stop":
            ok, msg = s.stop()
        elif cmd == "pause":
            ok, msg = s.pause()
        elif cmd == "resume":
            ok, msg = s.resume()
        elif cmd == "set_rate":
            ok, msg = s.set_rate(data.get("value", 1.0))
        elif cmd == "set_volume":
            ok, msg = s.set_volume(data.get("value", 1.0))
        else:
            return jsonify({"ok": False, "error": f"unknown command: {cmd}"}), 400

        return jsonify({"ok": ok, "message": msg})

    @app.route("/api/logs")
    def get_logs():
        s = app.config['SESSION']
        since = request.args.get("since", default=0, type=int)
        return jsonify(s.get_logs(since))

    @app.route("/api/state")
    def get_state():
        s = app.config['SESSION']
        return jsonify(s.get_state())

    return app


if __name__ == "__main__":
    app = create_app(session)
    app.run(host="0.0.0.0", port=5000, debug=True)