from __future__ import annotations

from dataclasses import asdict, dataclass

from .geometry import clamp


@dataclass
class FaceMetrics:
    jaw_width: float
    face_height: float
    nose_width: float
    nose_length: float
    lip_fullness: float
    eye_size: float
    brow_height: float


@dataclass
class Fc26Sliders:
    largura_mandibula: int
    altura_rosto: int
    largura_nariz: int
    comprimento_nariz: int
    espessura_labios: int
    tamanho_olhos: int
    altura_sobrancelha: int


BASELINES = {
    "jaw_width": 3.15,
    "face_height": 4.45,
    "nose_width": 0.95,
    "nose_length": 1.15,
    "lip_fullness": 0.32,
    "eye_size": 0.36,
    "brow_height": 0.45,
}


def metric_to_slider(value: float, baseline: float, sensitivity: float = 50.0) -> int:
    if baseline <= 0:
        return 50
    delta = (value - baseline) / baseline
    slider = round(50 + (delta * sensitivity))
    return int(clamp(slider, 0, 100))


def suggest_fc26_sliders(metrics: FaceMetrics) -> Fc26Sliders:
    return Fc26Sliders(
        largura_mandibula=metric_to_slider(metrics.jaw_width, BASELINES["jaw_width"], sensitivity=70),
        altura_rosto=metric_to_slider(metrics.face_height, BASELINES["face_height"], sensitivity=70),
        largura_nariz=metric_to_slider(metrics.nose_width, BASELINES["nose_width"], sensitivity=90),
        comprimento_nariz=metric_to_slider(metrics.nose_length, BASELINES["nose_length"], sensitivity=90),
        espessura_labios=metric_to_slider(metrics.lip_fullness, BASELINES["lip_fullness"], sensitivity=130),
        tamanho_olhos=metric_to_slider(metrics.eye_size, BASELINES["eye_size"], sensitivity=130),
        altura_sobrancelha=metric_to_slider(metrics.brow_height, BASELINES["brow_height"], sensitivity=110),
    )


def build_report_payload(metrics: FaceMetrics, sliders: Fc26Sliders, profile: dict | None = None) -> dict:
    payload = {
        "metrics_normalizadas": asdict(metrics),
        "sliders_fc26_0a100": asdict(sliders),
        "observacoes": [
            "Os valores são aproximações para ajudar no ajuste inicial do rosto no FC26.",
            "Use boa iluminação e mantenha o rosto centralizado para melhorar a precisão.",
            "Faça ajustes finos manuais no jogo para o resultado final desejado.",
        ],
    }
    if profile:
        payload["perfil_estimado"] = profile
    return payload
