from __future__ import annotations

import re
from dataclasses import dataclass


NORMALIZATION_VERSION = "qiaopi-text-normalizer-1.0.0"
_INLINE_SPACE_RE = re.compile(r"[ \t]+")


@dataclass(frozen=True)
class NormalizedText:
    original_text: str
    normalized_text: str
    normalized_to_original: tuple[int, ...]
    version: str = NORMALIZATION_VERSION

    def original_span(self, normalized_start: int, normalized_end: int) -> tuple[int, int]:
        if normalized_start < 0 or normalized_end < normalized_start:
            raise ValueError("Invalid normalized span")
        if normalized_start == normalized_end:
            if normalized_start >= len(self.normalized_to_original):
                return len(self.original_text), len(self.original_text)
            offset = self.normalized_to_original[normalized_start]
            return offset, offset
        if normalized_end > len(self.normalized_to_original):
            raise ValueError("Normalized span exceeds normalized text")
        return (
            self.normalized_to_original[normalized_start],
            self.normalized_to_original[normalized_end - 1] + 1,
        )


def normalize_newlines(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


def normalize_qiaopi_text(text: str) -> str:
    return normalize_qiaopi_text_with_mapping(text).normalized_text


def normalize_qiaopi_text_with_mapping(text: str) -> NormalizedText:
    original = str(text or "")
    newline_text, newline_map = _normalize_newlines_with_mapping(original)
    prepared_text = newline_text.replace("\u3000", " ")

    output_chars: list[str] = []
    output_map: list[int] = []
    compact_lines: list[tuple[list[str], list[int]]] = []
    blank_seen = False

    cursor = 0
    for line in prepared_text.split("\n"):
        line_map = newline_map[cursor : cursor + len(line)]
        compact_chars, compact_map = _compact_line(line, line_map)
        cursor += len(line) + 1

        if not compact_chars:
            if compact_lines and not blank_seen:
                compact_lines.append(([], []))
            blank_seen = True
            continue
        compact_lines.append((compact_chars, compact_map))
        blank_seen = False

    while compact_lines and not compact_lines[-1][0]:
        compact_lines.pop()

    for index, (line_chars, line_map) in enumerate(compact_lines):
        if index:
            previous_line_map = compact_lines[index - 1][1]
            next_line_map = line_map
            if previous_line_map:
                newline_source = min(previous_line_map[-1] + 1, len(original))
            elif next_line_map:
                newline_source = max(0, next_line_map[0] - 1)
            else:
                newline_source = len(original)
            output_chars.append("\n")
            output_map.append(newline_source)
        output_chars.extend(line_chars)
        output_map.extend(line_map)

    return NormalizedText(
        original_text=original,
        normalized_text="".join(output_chars),
        normalized_to_original=tuple(output_map),
    )


def _normalize_newlines_with_mapping(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    mapping: list[int] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\r":
            chars.append("\n")
            mapping.append(index)
            if index + 1 < len(text) and text[index + 1] == "\n":
                index += 2
            else:
                index += 1
            continue
        chars.append(char)
        mapping.append(index)
        index += 1
    return "".join(chars), mapping


def _compact_line(line: str, mapping: list[int]) -> tuple[list[str], list[int]]:
    if not line:
        return [], []
    first = 0
    while first < len(line) and line[first] in {" ", "\t"}:
        first += 1
    last = len(line)
    while last > first and line[last - 1] in {" ", "\t"}:
        last -= 1

    chars: list[str] = []
    char_map: list[int] = []
    index = first
    while index < last:
        if line[index] in {" ", "\t"}:
            match = _INLINE_SPACE_RE.match(line, index, last)
            chars.append(" ")
            char_map.append(mapping[index])
            index = match.end() if match else index + 1
            continue
        chars.append(line[index])
        char_map.append(mapping[index])
        index += 1
    return chars, char_map
