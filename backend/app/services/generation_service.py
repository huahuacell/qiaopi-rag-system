from app.generation.qwen_client import QwenClient
from app.schemas import PlainInterpretationRequest, StyleTransferRequest


def _common_evidence() -> list:
    return [
        {
            "source_field": "original_text",
            "source_text": "今托水客附上银八元",
            "reason": "支持汇款金额",
            "similarity_score": 0.95,
        },
        {
            "source_field": "original_text",
            "source_text": "望收讫后置办米粮并药费",
            "reason": "支持家用用途解读",
            "similarity_score": 0.9,
        },
    ]


def generate_plain_interpretation(request: PlainInterpretationRequest) -> dict:
    QwenClient().generate("plain-interpretation-placeholder")
    return {
        "record_id": request.record_id or "CSQP-SFHC-TEXT-001",
        "generated_text": "这封侨批的意思是：寄信人在新加坡平安，托人带回八元钱，请母亲收到后用于购买米粮和药品。",
        "summary": [
            "寄信人在新加坡报平安。",
            "寄信人汇给母亲八元。",
            "汇款用于米粮和药费。",
        ],
        "slots": {
            "sender": "陈生",
            "recipient": "母亲",
            "origin_place": "新加坡",
            "destination_place": "广东潮州",
            "money": "八元",
            "purpose": "米粮和药费",
        },
        "evidence": _common_evidence(),
        "evidence_mapping": [
            {
                "target_span": "托人带回八元钱",
                "source_field": "original_text",
                "source_text": "今托水客附上银八元",
                "reason": "生成片段由汇款证据支撑",
                "similarity_score": 0.95,
            },
            {
                "target_span": "用于购买米粮和药品",
                "source_field": "original_text",
                "source_text": "置办米粮并药费",
                "reason": "生成用途与原文一致",
                "similarity_score": 0.9,
            },
        ],
        "consistency_check": {
            "status": "passed",
            "warnings": [],
            "passed_rules": [
                "money_supported_by_evidence",
                "recipient_supported_by_evidence",
                "purpose_supported_by_evidence",
            ],
            "failed_rules": [],
        },
    }


def generate_style_transfer(request: StyleTransferRequest) -> dict:
    QwenClient().generate("style-transfer-placeholder")
    plain_text = request.plain_text.strip()
    return {
        "generated_text": "慈母大人膝下敬禀者：男在星洲平安，勿以为念。今托水客奉上银八元，伏乞查收，以备家中米粮药费之用。谨此禀安。",
        "summary": [
            "将白话家书转换为更接近侨批的敬禀语气。",
            "保留报平安、亲属称谓、汇款金额和家用目的。",
        ],
        "slots": {
            "recipient": request.slots.get("recipient", "母亲"),
            "origin_place": request.slots.get("origin_place", "新加坡"),
            "money": request.slots.get("money", "八元"),
            "purpose": request.slots.get("purpose", "家用"),
            "input_preview": plain_text[:80],
        },
        "evidence": _common_evidence(),
        "evidence_mapping": [
            {
                "target_span": "慈母大人膝下敬禀者",
                "source_field": "style_pattern",
                "source_text": "慈母大人膝下",
                "reason": "使用侨批常见的尊敬亲属开头",
                "similarity_score": 0.88,
            },
            {
                "target_span": "奉上银八元",
                "source_field": "original_text",
                "source_text": "附上银八元",
                "reason": "保留汇款金额",
                "similarity_score": 0.94,
            },
        ],
        "consistency_check": {
            "status": "passed",
            "warnings": [],
            "passed_rules": [
                "money_preserved",
                "recipient_preserved",
                "no_real_api_call",
            ],
            "failed_rules": [],
        },
    }
