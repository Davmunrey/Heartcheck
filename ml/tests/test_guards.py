from heartscan_ml.guards import apply_guards


def test_implausible_bpm_abstains():
    r = apply_guards(
        raw_bpm=450.0,
        model_confidence=0.99,
        extraction_quality=3,
        predicted_class="arrhythmia",
    )
    assert r.reportable is False
    assert r.non_reportable_reason == "IMPLAUSIBLE_BPM"


def test_low_quality():
    r = apply_guards(
        raw_bpm=72.0,
        model_confidence=0.99,
        extraction_quality=1,
        predicted_class="normal",
    )
    assert r.reportable is False
