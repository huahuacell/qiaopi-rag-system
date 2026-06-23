from __future__ import annotations

from typing import Mapping

from app.llm.style_transfer_prompts import (
    ACTIVE_STYLE_TRANSFER_PROMPT_VERSION,
    build_versioned_style_transfer_prompt,
)

INTERPRETATION_PROMPT_VERSION = "interpret-json-v2"
STYLE_TRANSFER_PROMPT_VERSION = ACTIVE_STYLE_TRANSFER_PROMPT_VERSION


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
    version: str = STYLE_TRANSFER_PROMPT_VERSION,
) -> list[dict[str, str]]:
    return build_versioned_style_transfer_prompt(
        plain_text=plain_text,
        prompt_context=prompt_context,
        evidence_references=evidence_references,
        version=version,
    )
