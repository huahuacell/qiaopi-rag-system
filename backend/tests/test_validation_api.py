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


def test_spouse_style_transfer_passes_relationship_amount_place_and_remittance():
    response = client.post(
        "/api/validation/consistency-check",
        json={
            "task_type": "style-transfer",
            "input_text": (
                "淑兰：我到曼谷已经快半年了，住处安定，身体也好。"
                "这个月省下三十元，我托可靠的船客带回去。"
                "二十元留作家里的米钱，另外十元给孩子添衣服。"
                "夜里听雨想起你，等生意稳定便设法回去。木泉"
            ),
            "generated_text": (
                "妻淑兰：我到曼谷已近半年，住处安顿，身体亦好，勿念。"
                "本月省出三十元，托可靠船客捎回。"
                "二十元作家用米粮，十元给儿女添衣。"
                "近日夜雨想起你，待生意再稳，我必设法返乡。夫木泉"
            ),
            "evidence_references": [
                {
                    "record_id": "R1",
                    "unit_id": "U1",
                    "unit_type": "opening",
                    "title_reference": "",
                    "source_column": "evidence_opening",
                    "evidence_type": "opening",
                    "unit_text": "黄氏吾妻收知：",
                    "retrieval_sources": ["keyword"],
                    "prompt_included": True,
                }
            ],
        },
    )

    report = response.json()["validation_report"]
    assert response.status_code == 200
    assert report["is_consistent"] is True
    assert report["missing_required_facts"] == []
    checks = {item["name"]: item for item in report["checks"]}
    assert checks["recipient_consistency"]["status"] == "pass"
    assert checks["amount_consistency"]["status"] == "pass"
    assert checks["place_consistency"]["status"] == "pass"
    assert checks["remittance_expression"]["status"] == "pass"


def test_spouse_shallow_classical_aliases_keep_relationship_and_amounts_consistent():
    response = client.post(
        "/api/validation/consistency-check",
        json={
            "task_type": "style-transfer",
            "input_text": (
                "淑兰：我在曼谷平安，本月寄回三十元，"
                "二十元作家用，十元给孩子添衣。夜里想起你。木泉"
            ),
            "generated_text": (
                "【生成草稿】\n淑兰如晤：寓曼谷平安，勿念。"
                "今月寄归卅元，廿元作家用，十元为稚子添衣。"
                "夜间辄忆汝。夫木泉泐"
            ),
            "evidence_references": [
                {
                    "record_id": "R1",
                    "unit_id": "U1",
                    "unit_type": "closing",
                    "title_reference": "",
                    "source_column": "evidence_closing",
                    "evidence_type": "closing",
                    "unit_text": "夫杨木良泐",
                    "retrieval_sources": ["keyword"],
                    "prompt_included": True,
                }
            ],
        },
    )

    report = response.json()["validation_report"]
    assert response.status_code == 200
    checks = {item["name"]: item for item in report["checks"]}
    assert checks["recipient_consistency"]["status"] == "pass"
    assert checks["amount_consistency"]["status"] == "pass"
