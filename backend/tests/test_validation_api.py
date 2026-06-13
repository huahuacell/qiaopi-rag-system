from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_style_transfer_consistency_passes_when_amount_is_preserved_as_formal_chinese():
    response = client.post(
        "/api/validation/consistency-check",
        json={
            "task_type": "style-transfer",
            "input_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
            "generated_text": "慈亲大人膝下：儿客居叻埠平安，兹奉上大洋银捌元，祈查收。另望胞弟勤学向上。儿谨禀。",
            "evidence_references": [],
        },
    )

    payload = response.json()
    report = payload["validation_report"]
    assert response.status_code == 200
    assert report["risk_level"] in {"low", "medium"}
    assert not report["missing_required_facts"]
    assert not report["unsupported_new_facts"]
    assert any(
        check["name"] == "amount_consistency" and check["status"] == "pass"
        for check in report["checks"]
    )
    assert any(
        check["name"] == "place_consistency" and check["status"] == "pass"
        for check in report["checks"]
    )
    assert any(
        check["name"] == "study_instruction_consistency" and check["status"] == "pass"
        for check in report["checks"]
    )


def test_style_transfer_consistency_warns_when_amount_changes():
    response = client.post(
        "/api/validation/consistency-check",
        json={
            "task_type": "style-transfer",
            "input_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
            "generated_text": "慈亲大人膝下：儿客居叻埠平安，兹奉上大洋银拾元，祈查收。另望胞弟勤学向上。儿谨禀。",
            "evidence_references": [],
        },
    )

    report = response.json()["validation_report"]
    assert response.status_code == 200
    assert report["risk_level"] == "high"
    assert any("金额" in fact for fact in report["unsupported_new_facts"])
    assert any(
        check["name"] == "amount_consistency" and check["status"] == "fail"
        for check in report["checks"]
    )


def test_style_transfer_consistency_warns_when_date_and_name_are_invented():
    response = client.post(
        "/api/validation/consistency-check",
        json={
            "task_type": "style-transfer",
            "input_text": "母亲您好，我在新加坡平安，寄八元回家，请弟弟好好读书。",
            "generated_text": "慈亲大人膝下：儿在香港平安，奉上大洋银拾元，并于民国二十年五月初三寄回。儿陈某谨禀。",
            "evidence_references": [],
        },
    )

    report = response.json()["validation_report"]
    assert response.status_code == 200
    assert report["risk_level"] == "high"
    assert any("地点" in fact for fact in report["unsupported_new_facts"])
    assert any("日期" in fact for fact in report["unsupported_new_facts"])
    assert any("姓名" in fact for fact in report["unsupported_new_facts"])


def test_interpretation_validation_loads_real_record_id():
    response = client.post(
        "/api/validation/consistency-check",
        json={
            "task_type": "interpret",
            "input_text": "这封侨批主要说了什么？",
            "generated_text": "生成解读：这封侨批提到寄款查收，并嘱家中照用。",
            "evidence_references": [],
            "record_id": "CSQP-SFHC-TEXT-017",
        },
    )

    report = response.json()["validation_report"]
    assert response.status_code == 200
    assert report["checks"]
    assert any(check["name"] == "amount_support_check" for check in report["checks"])
    assert "evidence_coverage" in report
