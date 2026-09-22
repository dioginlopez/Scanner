from src.fc26_face_scanner.mapping import FaceMetrics, metric_to_slider, suggest_fc26_sliders


def test_metric_to_slider_midpoint():
    assert metric_to_slider(1.0, 1.0) == 50


def test_metric_to_slider_clamps_range():
    assert metric_to_slider(999.0, 1.0) == 100
    assert metric_to_slider(-999.0, 1.0) == 0


def test_suggest_fc26_sliders_return_valid_ranges():
    metrics = FaceMetrics(
        jaw_width=3.2,
        face_height=4.4,
        nose_width=1.0,
        nose_length=1.1,
        lip_fullness=0.35,
        eye_size=0.4,
        brow_height=0.5,
    )
    sliders = suggest_fc26_sliders(metrics)
    for value in sliders.__dict__.values():
        assert 0 <= value <= 100
