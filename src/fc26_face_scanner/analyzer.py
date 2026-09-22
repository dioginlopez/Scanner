from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import cv2
import mediapipe as mp

from .geometry import distance, median
from .mapping import FaceMetrics, build_report_payload, suggest_fc26_sliders


@dataclass(frozen=True)
class CaptureResult:
    metrics: FaceMetrics
    report_json_path: Path
    report_markdown_path: Path


LANDMARKS = {
    "jaw_left": 234,
    "jaw_right": 454,
    "forehead": 10,
    "chin": 152,
    "nose_left": 98,
    "nose_right": 327,
    "nose_bridge": 168,
    "nose_tip": 1,
    "lip_upper": 13,
    "lip_lower": 14,
    "eye_left_outer": 33,
    "eye_right_outer": 263,
    "eye_left_top": 159,
    "eye_left_bottom": 145,
    "eye_right_top": 386,
    "eye_right_bottom": 374,
    "brow_left": 105,
    "brow_right": 334,
}


def _landmark_to_px(landmark, frame_width: int, frame_height: int) -> tuple[float, float]:
    return landmark.x * frame_width, landmark.y * frame_height


def _extract_frame_metrics(face_landmarks, frame_width: int, frame_height: int) -> FaceMetrics | None:
    points: Dict[str, tuple[float, float]] = {}
    landmarks = getattr(face_landmarks, "landmark", face_landmarks)
    for name, index in LANDMARKS.items():
        lm = landmarks[index]
        points[name] = _landmark_to_px(lm, frame_width, frame_height)

    interocular = distance(points["eye_left_outer"], points["eye_right_outer"])
    if interocular <= 1e-6:
        return None

    jaw_width = distance(points["jaw_left"], points["jaw_right"]) / interocular
    face_height = distance(points["forehead"], points["chin"]) / interocular
    nose_width = distance(points["nose_left"], points["nose_right"]) / interocular
    nose_length = distance(points["nose_bridge"], points["nose_tip"]) / interocular
    lip_fullness = distance(points["lip_upper"], points["lip_lower"]) / interocular
    eye_size = (
        distance(points["eye_left_top"], points["eye_left_bottom"])
        + distance(points["eye_right_top"], points["eye_right_bottom"])
    ) / (2 * interocular)
    brow_height = (
        distance(points["brow_left"], points["eye_left_top"])
        + distance(points["brow_right"], points["eye_right_top"])
    ) / (2 * interocular)

    return FaceMetrics(
        jaw_width=jaw_width,
        face_height=face_height,
        nose_width=nose_width,
        nose_length=nose_length,
        lip_fullness=lip_fullness,
        eye_size=eye_size,
        brow_height=brow_height,
    )


def _aggregate_metrics(samples: List[FaceMetrics]) -> FaceMetrics:
    return FaceMetrics(
        jaw_width=median([sample.jaw_width for sample in samples]),
        face_height=median([sample.face_height for sample in samples]),
        nose_width=median([sample.nose_width for sample in samples]),
        nose_length=median([sample.nose_length for sample in samples]),
        lip_fullness=median([sample.lip_fullness for sample in samples]),
        eye_size=median([sample.eye_size for sample in samples]),
        brow_height=median([sample.brow_height for sample in samples]),
    )


def _build_markdown(payload: dict) -> str:
    lines = [
        "# Relatório facial para FC26",
        "",
        "## Sliders sugeridos (0-100)",
    ]
    for key, value in payload["sliders_fc26_0a100"].items():
        lines.append(f"- **{key}**: {value}")

    lines.extend([
        "",
        "## Métricas normalizadas",
    ])
    for key, value in payload["metrics_normalizadas"].items():
        lines.append(f"- **{key}**: {value:.4f}")

    lines.extend([
        "",
        "## Observações",
    ])
    for note in payload["observacoes"]:
        lines.append(f"- {note}")

    return "\n".join(lines)


def save_reports(metrics: FaceMetrics, output_dir: str = "output") -> tuple[Path, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    sliders = suggest_fc26_sliders(metrics)
    payload = build_report_payload(metrics, sliders)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_path / f"fc26_face_report_{timestamp}.json"
    md_path = output_path / f"fc26_face_report_{timestamp}.md"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_markdown(payload), encoding="utf-8")
    return json_path, md_path


def run_live_capture(
    camera_index: int = 0,
    sample_count: int = 45,
    output_dir: str = "output",
    show_preview: bool = True,
) -> CaptureResult:
    if camera_index < 0:
        raise ValueError("O índice da câmera deve ser maior ou igual a zero.")
    if sample_count < 10:
        raise ValueError("A quantidade de amostras deve ser de pelo menos 10.")

    mp_face_mesh = mp.solutions.face_mesh
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Não foi possível abrir a câmera. Verifique permissões e índice.")

    samples: List[FaceMetrics] = []

    try:
        with mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        ) as face_mesh:
            while len(samples) < sample_count:
                success, frame = cap.read()
                if not success:
                    continue

                frame = cv2.flip(frame, 1)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(frame_rgb)

                if results.multi_face_landmarks:
                    landmark_data = results.multi_face_landmarks[0]
                    height, width = frame.shape[:2]
                    metrics = _extract_frame_metrics(landmark_data, width, height)
                    if metrics is not None:
                        samples.append(metrics)

                if show_preview:
                    text = f"Amostras: {len(samples)}/{sample_count} | Q para cancelar"
                    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (40, 230, 40), 2)
                    cv2.imshow("FC26 Face Scanner", frame)
                    key = cv2.waitKey(1)
                    if key & 0xFF == ord("q"):
                        break
    finally:
        cap.release()
        if show_preview:
            cv2.destroyAllWindows()

    if len(samples) < max(10, sample_count // 3):
        raise RuntimeError(
            "Amostras insuficientes. Tente novamente com melhor iluminação e rosto centralizado."
        )

    consolidated = _aggregate_metrics(samples)
    json_path, md_path = save_reports(consolidated, output_dir)

    return CaptureResult(metrics=consolidated, report_json_path=json_path, report_markdown_path=md_path)
