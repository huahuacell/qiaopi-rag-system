from __future__ import annotations

from typing import Mapping


INTERPRETATION_PROMPT_VERSION = "interpret-json-v2"
STYLE_TRANSFER_PROMPT_VERSION = "style-transfer-json-v2"


def _evidence_reference_lines(evidence_references: list[Mapping[str, str]]) -> str:
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


def build_interpretation_prompt(
    *,
    query: str,
    prompt_context: str,
    evidence_references: list[Mapping[str, str]],
) -> list[dict[str, str]]:
    system_prompt = (
        "你是侨批历史文献解读助手。必须只依据提供的证据回答，"
        "不得编造证据中没有的人名、金额、日期、地点或情节。"
        "只输出一个合法 JSON 对象，不要输出 Markdown 代码围栏。"
    )
    user_prompt = f"""请根据以下侨批证据，生成一段现代中文解释。

要求：
1. 用现代中文解释侨批内容。
2. 说明谁写给谁。
3. 说明是否有批款、金额、用途。
4. 说明主要情感和嘱托。
5. 不要编造证据中没有的信息。
6. 如果证据不足，要明确说“不确定”。
7. 明确标注这是“生成解读”，不是历史原文。

用户问题：
{query}

证据上下文：
{prompt_context}

参考证据：
{_evidence_reference_lines(evidence_references)}

请严格输出以下 JSON 结构：
{{
  "generated_text": "完整的现代中文生成解读",
  "summary": ["结构化摘要要点"],
  "style_notes": [],
  "warnings": ["证据不足或不确定之处"]
}}
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_style_transfer_prompt(
    *,
    plain_text: str,
    prompt_context: str,
    evidence_references: list[Mapping[str, str]],
) -> list[dict[str, str]]:
    system_prompt = (
        "你是侨批文体改写助手。你可以参考真实侨批样例的措辞和结构，"
        "但不得把生成内容声称为历史原文，也不得新增用户未提供的事实。"
        "只输出一个合法 JSON 对象，不要输出 Markdown 代码围栏。"
    )
    user_prompt = f"""请把用户白话内容改写为侨批体草稿。

要求：
1. 根据用户白话内容写成侨批体。
2. 参考真实侨批样例，但不要逐字抄袭过长片段。
3. 保留用户给出的事实：人物、地点、金额、嘱托。
4. 不要新增用户没有提供的金额、日期、姓名。
5. 输出结构包括：
   - 侨批体正文
   - 风格依据说明
   - 参考证据列表
6. 明确标注这是“生成草稿”，不是历史原文。

用户白话内容：
{plain_text}

风格与证据上下文：
{prompt_context}

参考证据：
{_evidence_reference_lines(evidence_references)}

请严格输出以下 JSON 结构：
{{
  "generated_text": "完整的侨批体生成草稿",
  "summary": ["保留的事实要点"],
  "style_notes": ["采用的侨批文体特征"],
  "warnings": ["无法确定或需要复核的内容"]
}}
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
