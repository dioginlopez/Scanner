from __future__ import annotations

import threading
from dataclasses import asdict
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from flask import Flask, jsonify, render_template, request

from src.fc26_face_scanner.analyzer import _aggregate_metrics, _extract_frame_metrics, save_reports
from src.fc26_face_scanner.mapping import FaceMetrics, suggest_fc26_sliders


class ScannerSession:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.face_mesh = None
        self.samples: list[FaceMetrics] = []
        self.target = 45
        self.output_dir = "output"
        self.active = False

    def start(self, target: int, output_dir: str) -> None:
        if target < 10:
            raise ValueError("A quantidade mínima é de 10 amostras.")
        with self.lock:
            self._close_mesh()
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6,
            )
            self.samples = []
            self.target = target
            self.output_dir = output_dir or "output"
            self.active = True

    def analyze_frame(self, image_bytes: bytes) -> dict:
        with self.lock:
            if not self.active or self.face_mesh is None:
                raise RuntimeError("Nenhum escaneamento ativo.")

            image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Não foi possível ler o frame da câmera.")
            height, width = image.shape[:2]
            result = self.face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            detected = bool(result.multi_face_landmarks)
            metrics = None
            if detected:
                metrics = _extract_frame_metrics(result.multi_face_landmarks[0], width, height)
                if metrics is not None:
                    self.samples.append(metrics)

            count = len(self.samples)
            return {
                "detected": metrics is not None,
                "metrics": asdict(metrics) if metrics else None,
                "count": count,
                "target": self.target,
                "percent": round(min(100, count / self.target * 100), 1),
            }

    def finish(self) -> dict:
        with self.lock:
            threshold = max(10, self.target // 3)
            if len(self.samples) < threshold:
                raise RuntimeError("Amostras insuficientes. Melhore a iluminação e centralize o rosto.")
            metrics = _aggregate_metrics(self.samples)
            json_path, md_path = save_reports(metrics, self.output_dir)
            sliders = suggest_fc26_sliders(metrics)
            self.active = False
            self._close_mesh()
            return {
                "metrics": asdict(metrics),
                "sliders": asdict(sliders),
                "json_path": str(json_path),
                "markdown_path": str(md_path),
            }

    def stop(self) -> None:
        with self.lock:
            self.active = False
            self._close_mesh()

    def _close_mesh(self) -> None:
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None


session = ScannerSession()


def create_app() -> Flask:
    front_dir = Path(__file__).resolve().parent.parent / "front"
    app = Flask(__name__, template_folder=str(front_dir), static_folder=str(front_dir), static_url_path="/assets")

    @app.errorhandler(Exception)
    def handle_api_error(error: Exception):
        if request.path.startswith("/api/"):
            app.logger.exception("Erro na API do scanner", exc_info=error)
            return jsonify({
                "ok": False,
                "error": "Erro interno durante a análise. Verifique os logs do servidor.",
            }), 500
        raise error

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/session/start")
    def start_session():
        data = request.get_json(silent=True) or {}
        try:
            target = int(data.get("samples", 45))
            output_dir = str(data.get("output_dir", "output"))
            session.start(target, output_dir)
            return jsonify({"ok": True, "target": target})
        except (TypeError, ValueError, RuntimeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/session/frame")
    def analyze_frame():
        if "frame" not in request.files:
            return jsonify({"ok": False, "error": "Frame não enviado."}), 400
        try:
            result = session.analyze_frame(request.files["frame"].read())
            return jsonify({"ok": True, **result})
        except (ValueError, RuntimeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/session/finish")
    def finish_session():
        try:
            return jsonify({"ok": True, **session.finish()})
        except (RuntimeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/session/stop")
    def stop_session():
        session.stop()
        return jsonify({"ok": True})

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "service": "fc26-face-scanner"})

    return app
