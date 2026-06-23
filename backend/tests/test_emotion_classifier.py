from app.analysis.emotion_classifier import classify_segment, split_qiaopi_segments


def _prediction_keys(result: dict) -> set[str]:
    return {prediction["key"] for prediction in result["predictions"]}


def test_emotion_classifier_supports_multiple_labels_and_traceable_terms():
    result = classify_segment("母亲病故，闻之悲痛，望节哀珍重。")

    assert {"grief_sorrow", "care_instruction"}.issubset(_prediction_keys(result))
    grief = next(
        prediction
        for prediction in result["predictions"]
        if prediction["key"] == "grief_sorrow"
    )
    assert "悲痛" in grief["trigger_terms"]
    assert result["valence"] == "negative"
    assert result["engine"] in {"pytorch", "python_compatible_fallback"}


def test_emotion_classifier_respects_negated_worry_expression():
    result = classify_segment("两地平安，甚慰，切勿挂怀。")

    assert "reassurance_relief" in _prediction_keys(result)
    assert "worry_pressure" not in _prediction_keys(result)
    assert result["valence"] == "positive"


def test_emotion_classifier_keeps_practical_content_neutral():
    result = classify_segment("兹逢轮便，奉上大洋捌元，到祈查收。")

    assert _prediction_keys(result) == {"practical_neutral"}
    assert result["valence"] == "neutral"


def test_long_ocr_paragraph_is_split_into_bounded_segments():
    text = "家中诸事祈回音示知，" * 30
    segments = split_qiaopi_segments(text)

    assert len(segments) > 1
    assert all(0 < len(segment) <= 180 for segment in segments)

