from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from backend.business_logic import session, ollama_manager, pause, resume, get_settings, update_settings

FRONT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app(session):
    app = Flask(__name__)
    CORS(app)
    app.config['SESSION'] = session

    @app.route('/')
    def index():
        return send_from_directory(FRONT_DIR, 'front.html', mimetype='text/html')

    @app.route('/front_css.css')
    def serve_css():
        return send_from_directory(FRONT_DIR, 'front_css.css', mimetype='text/css')

    @app.route('/front_js.js')
    def serve_js():
        return send_from_directory(FRONT_DIR, 'front_js.js', mimetype='application/javascript')

    @app.route('/<path:filename>')
    def static_files(filename):
        return send_from_directory(FRONT_DIR, filename)

    @app.route("/api/devices")
    def get_devices():
        return jsonify(app.config['SESSION'].get_available_devices())

    @app.route("/api/devices/set", methods=["POST"])
    def set_device():
        s = app.config['SESSION']
        data = request.get_json() or {}
        kind = data.get("kind")
        dev_id = str(data.get("id"))
        label = ""
        group = "inputs" if kind == "input" else "outputs"
        for d in s.get_available_devices().get(group, []):
            if d["id"] == dev_id:
                label = d["label"]
        ok, msg = s.set_device(kind, dev_id, label)
        return jsonify({"ok": ok, "message": msg})

    @app.route("/api/presets", methods=["GET"])
    def get_presets():
        return jsonify(app.config['SESSION'].get_available_presets())

    @app.route("/api/presets", methods=["POST"])
    def create_preset():
        s = app.config['SESSION']
        data = request.get_json() or {}
        new_id = s.create_preset(data.get("name", ""), data.get("prompt", ""))
        return jsonify({"ok": True, "id": new_id})

    @app.route("/api/presets/<preset_id>", methods=["PUT"])
    def update_preset(preset_id):
        s = app.config['SESSION']
        data = request.get_json() or {}
        ok = s.update_preset(preset_id, data.get("name", ""), data.get("prompt", ""))
        return jsonify({"ok": ok})

    @app.route("/api/presets/<preset_id>", methods=["DELETE"])
    def delete_preset(preset_id):
        s = app.config['SESSION']
        ok = s.delete_preset(preset_id)
        return jsonify({"ok": ok})

    @app.route("/api/presets/select", methods=["POST"])
    def select_preset():
        s = app.config['SESSION']
        data = request.get_json() or {}
        ok, msg = s.set_preset(data.get("id"))
        return jsonify({"ok": ok, "message": msg})

    @app.route("/api/settings", methods=["GET"])
    def settings_get():
        return jsonify(get_settings())

    @app.route("/api/settings", methods=["POST"])
    def settings_post():
        data = request.get_json() or {}
        return jsonify(update_settings(data))

    @app.route("/api/command", methods=["POST"])
    def command():
        s = app.config['SESSION']
        data = request.get_json() or {}
        cmd = data.get("cmd")

        if cmd == "start":
            ok, msg = s.start()
        elif cmd == "stop":
            ok, msg = s.stop()
        elif cmd == "pause":
            ok, msg = pause()
        elif cmd == "resume":
            ok, msg = resume()
        elif cmd == "set_sensitivity":
            ok, msg = s.set_sensitivity(float(data.get("value", 0.01)))
        elif cmd == "set_rate":
            ok, msg = s.set_rate(float(data.get("value", 1.0)))
        elif cmd == "start_recording":
            ok, msg = s.start_recording()
        elif cmd == "stop_recording":
            ok, msg = s.stop_recording()
        elif cmd == "start_recording":
            ok, msg = s.start_recording()
        elif cmd == "stop_recording":
            ok, msg = s.stop_recording()
        elif cmd == "set_volume":
            ok, msg = s.set_volume(float(data.get("value", 1.0)))
        else:
            return jsonify({"ok": False, "error": "unknown command"}), 400

        return jsonify({"ok": ok, "message": msg})

    @app.route("/api/state")
    def state():
        return jsonify(app.config['SESSION'].get_state())

    @app.route("/api/logs")
    def logs():
        since = int(request.args.get("since", 0))
        return jsonify(app.config['SESSION'].get_logs(since))

    # ------------------- OLLAMA ROUTES -------------------
    @app.route("/api/ollama/status")
    def ollama_status():
        return jsonify(ollama_manager.check_status())

    @app.route("/api/ollama/install", methods=["POST"])
    def ollama_install():
        ok = ollama_manager.download_and_install()
        return jsonify({"ok": ok})

    @app.route("/api/ollama/models")
    def ollama_models():
        available = ollama_manager.get_available_models()
        installed = ollama_manager.get_installed_models()
        installed_ids = {m.get("name") for m in installed}
        result = []
        for model in available:
            model_copy = model.copy()
            model_copy["installed"] = model["id"] in installed_ids
            result.append(model_copy)
        return jsonify(result)

    @app.route("/api/ollama/models/download", methods=["POST"])
    def ollama_download_model():
        data = request.get_json() or {}
        model_id = data.get("id")
        if not model_id:
            return jsonify({"ok": False, "message": "Не указан id модели"}), 400
        result = ollama_manager.download_model(model_id)
        return jsonify(result)

    return app


if __name__ == "__main__":
    app = create_app(session)
    app.run(host="127.0.0.1", port=5000, debug=False)