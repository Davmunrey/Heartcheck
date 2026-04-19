from heartscan_ml.labels import parse_scp_codes, ptbxl_to_screening_class


def test_parse_scp():
    d = parse_scp_codes("{'NORM': 100.0, 'AFIB': 0.0}")
    assert d["NORM"] == 100.0


def test_normal_vs_abnormal():
    assert ptbxl_to_screening_class({"NORM": 100.0}) == 0
    assert ptbxl_to_screening_class({"NORM": 0.0, "STTC": 50.0}) == 1
