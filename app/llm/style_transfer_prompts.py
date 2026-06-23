from __future__ import annotations

from typing import Any, Mapping


STYLE_TRANSFER_V1 = "style-transfer-json-v1"
STYLE_TRANSFER_V2 = "style-transfer-concise-json-v2"
STYLE_TRANSFER_V3 = "style-transfer-concise-json-v3"
STYLE_TRANSFER_V4 = "style-transfer-concise-json-v4"
STYLE_TRANSFER_V5 = "style-transfer-vernacular-json-v5"
ACTIVE_STYLE_TRANSFER_PROMPT_VERSION = STYLE_TRANSFER_V4


STYLE_TRANSFER_PROMPT_PROFILES: dict[str, dict[str, str]] = {
    STYLE_TRANSFER_V1: {
        "system": (
            "你是侨批文体改写助手。你可以参考真实侨批样例的措辞和结构，"
            "但不得把生成内容声称为历史原文，也不得新增用户未提供的事实。"
            "只输出一个合法 JSON 对象，不要输出 Markdown 代码围栏。"
        ),
        "instruction": "请把用户白话内容改写为侨批体草稿。",
        "requirements": """1. 根据用户白话内容写成侨批体。
2. 参考真实侨批样例，但不要逐字抄袭过长片段。
3. 保留用户给出的事实：人物、地点、金额、嘱托。
4. 不要新增用户没有提供的金额、日期、姓名。
5. 输出结构包括：
   - 侨批体正文
   - 风格依据说明
   - 参考证据列表
6. 明确标注这是“生成草稿”，不是历史原文。""",
        "method_guide": "",
        "generated_text_schema": "完整的侨批体生成草稿",
        "legacy_output": "",
    },
    STYLE_TRANSFER_V2: {
        "system": (
            "你是侨批家书文体改写助手。目标文风是简洁、真挚、自然的浅近文言，"
            "不是公文、奏折、骈文或刻意艰深的古文。只借鉴真实侨批的少量措辞，"
            "不得堆叠套语、冒充历史原文或新增用户未提供的事实。"
            "只输出一个合法 JSON 对象，不要输出 Markdown 代码围栏。"
        ),
        "instruction": "请把用户白话内容改写为简洁的浅近文言侨批家书草稿。",
        "requirements": """1. 完整保留用户给出的事实，包括人物、关系、地点、金额、事件、情感和嘱托。
2. 不得新增或改变用户给出的事实，不得补写输入中没有的用途、礼仪或生活情节。
3. 使用现代读者无需注释也能读懂的浅近文言，宁简勿繁。
4. 正文目标长度为原白话内容汉字数的 60%—80%，同一事实或情感只表达一次。
5. 使用一处称谓、一组结尾，不得为了形式增加内容。
6. 真实侨批样例只用于选择少量表达，不得把多个样例的套语拼接进正文。
7. generated_text 第一行只写“【生成草稿】”，文体说明放入 style_notes。""",
        "method_guide": "",
        "generated_text_schema": "【生成草稿】\\n完整、简洁的浅近文言侨批家书正文",
        "legacy_output": "",
    },
    STYLE_TRANSFER_V3: {
        "system": (
            "你是侨批家书文体改写助手。目标文风是简洁、真挚、自然的浅近文言。"
            "内容忠实高于古雅程度，不得堆叠套语，不得新增事实。"
            "只输出一个合法 JSON 对象，不要输出 Markdown 代码围栏。"
        ),
        "instruction": "请把用户白话内容改写为紧凑的浅近文言侨批家书草稿。",
        "requirements": """1. 完整保留输入中的事实、情感和嘱托，不得新增、替换或改变。
2. 正文目标长度为原白话内容汉字数的 55%—70%，优先接近 65%。
3. 不逐段机械翻译；合并同义信息，同一事实、情感或安慰只表达一次。
4. 全文采用一处称谓问候、一至两个正文段落和一处结尾署名。
5. 称谓与问候只允许一套，署名只能出现一次。
6. 避免公文化、骈文化和过度雕饰的表达。
7. 完稿前删除重复问候、重复安慰、重复结语和重复署名。
8. generated_text 第一行只写“【生成草稿】”，文体说明放入 style_notes。""",
        "method_guide": "",
        "generated_text_schema": "【生成草稿】\\n完整、紧凑的浅近文言侨批家书正文",
        "legacy_output": "",
    },
    STYLE_TRANSFER_V4: {
        "system": (
            "你是侨批家书文体改写助手。目标文风是简洁、自然、易读的浅近文言。"
            "提示词只规定方法，不预设具体人物、地点、物品、事件或答案。"
            "不得新增事实，只输出合法 JSON 对象。"
        ),
        "instruction": "请根据本次用户输入，生成内容中立、简洁的侨批家书草稿。",
        "requirements": """1. 用户输入是生成事实的唯一来源；检索样例只提供文体依据。
2. 不得新增、替换、扩大或缩小输入中的数量、时间、人物、地点、物品、动作和关系。
3. 正文目标长度为原白话内容汉字数的 55%—70%，不逐段机械翻译。
4. 同一功能的称谓、问候、安慰、祝颂和结语各最多保留一套。
5. 署名只能出现一次，不得同时使用两种落款结构。
6. 不使用固定范文套写所有输入，也不从检索样例借入事实。
7. 完稿前检查事实覆盖、表达压缩、段落数量和署名次数。
8. generated_text 第一行只写“【生成草稿】”，文体说明放入 style_notes。""",
        "method_guide": """【改写方法】
先提取事实、情感和嘱托，再合并语义相近的信息；依据人物关系选择称谓，
只借鉴与当前输入相符的少量文体表达，最后检查事实覆盖和重复内容。""",
        "generated_text_schema": "【生成草稿】\\n完整、内容中立的侨批家书正文",
        "legacy_output": "",
    },
    STYLE_TRANSFER_V5: {
        "system": (
            "你是侨批家书文体改写助手。目标文风是以自然白话为主体、以少量传统"
            "家书措辞点缀的侨批体，而不是文言文仿写。现代读者应当能够顺畅直读，"
            "无需解释古语。你可以参考真实侨批样例，但内容忠实和自然可读始终高于"
            "古雅程度；不得堆叠套语，不得把生成内容声称为历史原文，也不得新增"
            "用户未提供的事实。只输出一个合法 JSON 对象，不要输出 Markdown 代码围栏。"
        ),
        "instruction": "请把用户白话内容改写为简洁、自然、白话底色的侨批家书草稿。",
        "requirements": """1. 完整保留用户给出的事实，包括人物、关系、地点、金额、事件、情感和嘱托。
2. 不得新增、替换、扩大或缩小用户给出的事实；数量、时间、姓名、地点、物品、动作、因果和人物关系均须与输入一致。
3. 保持现代汉语的基本语序和常用词，以白话表达为主，只在称谓、问候、寄递、祝颂或结尾处适量使用传统家书措辞。不得把每个句子都改造成文言句。
4. 正文目标长度为原白话内容汉字数的 55%—70%，优先接近 65%。在不丢失事实的前提下压缩句子，同一事实、情感或安慰只表达一次，不逐段对应翻译，不重复解释。
5. 全文采用“一处称谓问候 + 一至两个正文段落 + 一处结尾署名”的紧凑结构。
6. 每个句子至多出现一个明显的传统书面表达；传统措辞应像点缀，不能成为全文主体。
7. 避免公文化、奏折化、骈文化或过度雕饰的表达。
8. 不得自行增加寄递方式、币种称谓、身份礼称或时代背景；不得主动添加输入中没有的比喻、典故、夸饰和古典意象。
9. 真实侨批样例仅用于选择少量自然措辞，不得整句照搬或借入样例事实。
10. 称谓与问候只允许一套；署名只能出现一次。
11. 将冗长口语压缩为语义等价的自然家书表达，不得改变语气强度、事实范围或确定程度。
12. 完稿前进行白话可读性检查，随后删除重复问候、重复安慰、重复结语和重复署名。
13. generated_text 第一行只写“【生成草稿】”，文体说明放入 style_notes。
14. summary 只列保留的关键事实；warnings 只列确实无法确定或需要人工复核的内容。""",
        "method_guide": """【改写方法】
1. 先在内部提取输入中的事实单元、情感单元和嘱托单元。
2. 合并语义相近的单元，删除仅为口语衔接而重复出现的信息。
3. 依据人物关系选择一种称谓结构，依据内容选择必要的正文表达。
4. 只从检索样例中借鉴与当前输入相符的少量句法和用词，不借入样例事实。
5. 完稿后检查事实覆盖、表达压缩、段落数量和署名次数，再输出最终结果。

【禁止过拟合】
- 不预设用户会输入哪一种人物、地点、物品、事件、景象、活动或情感。
- 不因提示词中的示范内容而生成用户没有提供的信息。
- 不使用固定范文套写所有输入；每次只根据本次输入决定内容和称谓。
- 检索样例只提供文体依据，用户输入才是生成事实的唯一来源。""",
        "generated_text_schema": "【生成草稿】\\n完整、简洁、白话底色的侨批家书正文",
        "legacy_output": "",
    },
}


def available_style_transfer_prompt_versions() -> tuple[str, ...]:
    return tuple(STYLE_TRANSFER_PROMPT_PROFILES)


def build_versioned_style_transfer_prompt(
    *,
    plain_text: str,
    prompt_context: str,
    evidence_references: list[Mapping[str, Any]],
    version: str = ACTIVE_STYLE_TRANSFER_PROMPT_VERSION,
) -> list[dict[str, str]]:
    try:
        profile = STYLE_TRANSFER_PROMPT_PROFILES[version]
    except KeyError as exc:
        available = ", ".join(available_style_transfer_prompt_versions())
        raise ValueError(f"Unknown style-transfer prompt version: {version}. Available: {available}") from exc

    method_guide = profile["method_guide"].strip()
    method_section = f"\n\n{method_guide}" if method_guide else ""
    prompt_body = f"""{profile["instruction"]}

要求：
{profile["requirements"]}{method_section}

用户白话内容：
{plain_text}

风格与证据上下文：
{prompt_context}

参考证据：
{_evidence_reference_lines(evidence_references)}
"""
    legacy_output = profile["legacy_output"].strip()
    if legacy_output:
        user_prompt = f"""{prompt_body}

{legacy_output}
"""
    else:
        user_prompt = f"""{prompt_body}

请严格输出以下 JSON 结构：
{{
  "generated_text": "{profile["generated_text_schema"]}",
  "summary": ["保留的事实要点"],
  "style_notes": ["采用的侨批文体特征"],
  "warnings": ["无法确定或需要复核的内容"]
}}
"""
    return [
        {"role": "system", "content": profile["system"]},
        {"role": "user", "content": user_prompt},
    ]


def _evidence_reference_lines(evidence_references: list[Mapping[str, Any]]) -> str:
    if not evidence_references:
        return "暂无可引用证据。"
    lines: list[str] = []
    for index, reference in enumerate(evidence_references, start=1):
        lines.append(
            (
                f"{index}. record_id={reference.get('record_id', '')}; "
                f"unit_id={reference.get('unit_id', '')}; "
                f"unit_type={reference.get('unit_type', '')}; "
                f"source_column={reference.get('source_column', '')}; "
                f"evidence_type={reference.get('evidence_type', '')}"
            )
        )
    return "\n".join(lines)
