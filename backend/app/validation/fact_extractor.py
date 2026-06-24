from __future__ import annotations

import re
from typing import Any


AMOUNT_CURRENCIES: tuple[str, ...] = (
    "洋银",
    "大洋",
    "港币",
    "国币",
    "中央币",
    "银",
)

PLACE_ALIASES: dict[str, tuple[str, ...]] = {
    "新加坡": ("新加坡", "星洲", "叻", "叻埠", "叻坡", "石叻"),
    "香港": ("香港", "港", "港地"),
    "曼谷": ("曼谷",),
    "泰国": ("泰国", "暹罗", "暹"),
    "越南": ("越南", "安南", "西贡"),
    "广东": ("广东", "潮汕", "潮州", "澄海", "海邑", "潮邑"),
}

KINSHIP_ALIASES: dict[str, tuple[str, ...]] = {
    "母亲": ("母亲", "妈妈", "阿母", "阿妈", "慈亲", "家母", "大人", "膝下"),
    "父亲": ("父亲", "爸爸", "严亲", "家父"),
    "弟弟": ("弟弟", "胞弟", "贤弟", "弟"),
    "妻子": ("妻子", "吾妻", "贤妻", "荆妻", "内妻", "内人", "爱妻", "妻"),
    "丈夫": ("丈夫", "夫君", "夫婿", "良人", "老公"),
    "孩子": ("孩子", "儿女", "儿子", "女儿", "孩儿", "稚子"),
}

REMITTANCE_TERMS: tuple[str, ...] = (
    "寄",
    "寄回",
    "寄款",
    "汇款",
    "汇回",
    "奉上",
    "付去",
    "带去",
    "带回",
    "捎回",
    "托人带回",
    "托船客",
    "查收",
    "收讫",
    "检收",
    "妥收",
    "收到钱",
)

STUDY_TERMS: tuple[str, ...] = (
    "读书",
    "学习",
    "勤学",
    "向学",
    "用功",
    "学业",
    "书",
)

SAFETY_TERMS: tuple[str, ...] = (
    "平安",
    "安好",
    "安康",
    "无恙",
    "勿念",
    "毋念",
)

DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"民国[一二三四五六七八九十廿卅\d]{1,6}年[一二三四五六七八九十廿卅\d]{1,3}月[初十廿卅一二三四五六七八九\d]{1,4}日?"),
    re.compile(r"[一二三四五六七八九十廿卅\d]{1,4}年[一二三四五六七八九十廿卅\d]{1,3}月[初十廿卅一二三四五六七八九\d]{1,4}日?"),
    re.compile(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]?[年月][初十廿卅一二三四五六七八九\d]{1,4}日?"),
)

AMOUNT_NUMERAL_PATTERN = (
    r"[零〇一二两三四五六七八九十百千万萬廿卅"
    r"壹贰弍叁肆伍陆柒捌玖拾佰仟\d]{1,10}"
)

BARE_ALLOCATION_AMOUNT_PATTERN = re.compile(
    rf"^(?:其中|其余|剩下|余下|另外|另|再|余)?\s*"
    rf"(?P<amount>{AMOUNT_NUMERAL_PATTERN})\s*"
    r"(?:用于|用作|留作|留给|作为|缴|交|给|供|作|留|备|买|购|添|"
    r"付|寄|汇|存|还|拨|充|奉)"
)

NAME_PATTERN = re.compile(
    r"(?:儿|男|女|愚|弟|兄|侄|甥)?([赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵汪祁毛禹狄米贝明臧计伏成戴宋庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣邓郁单杭洪包诸左石崔吉龚程邢裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘斜厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲台从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍却璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎连习容向古易廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公万俟司马上官欧阳夏侯诸葛闻人东方赫连皇甫尉迟公羊澹台公冶宗政濮阳淳于单于太叔申屠公孙仲孙轩辕令狐钟离宇文长孙慕容司徒司空][\u4e00-\u9fff某]{1,2})(?=谨禀|禀|顿|缄|泐|托|启|上)"
)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _amount_terms(text: str) -> list[str]:
    terms: list[str] = []
    currency_prefix = "|".join(re.escape(currency) for currency in AMOUNT_CURRENCIES)
    pattern = re.compile(
        rf"(?:{currency_prefix})?"
        rf"{AMOUNT_NUMERAL_PATTERN}元"
    )
    terms.extend(pattern.findall(text))
    for clause in re.split(r"[，,；;。！？!?\n]+", text):
        match = BARE_ALLOCATION_AMOUNT_PATTERN.match(clause.strip())
        if match:
            terms.append(match.group("amount"))
    return _dedupe(terms)


def canonical_amount(term: str) -> str | None:
    digit_match = re.search(r"(\d+)\s*元", term)
    if digit_match:
        return digit_match.group(1)
    chinese_match = re.search(
        r"([零〇一二两三四五六七八九十百千万萬廿卅壹贰弍叁肆伍陆柒捌玖拾佰仟]+)\s*元",
        term,
    )
    if chinese_match:
        value = _parse_chinese_integer(chinese_match.group(1))
        if value is not None:
            return str(value)
    bare_digit_match = re.fullmatch(r"\s*(\d+)\s*", term)
    if bare_digit_match:
        return bare_digit_match.group(1)
    bare_chinese_match = re.fullmatch(
        r"\s*([零〇一二两三四五六七八九十百千万萬廿卅壹贰弍叁肆伍陆柒捌玖拾佰仟]+)\s*",
        term,
    )
    if bare_chinese_match:
        value = _parse_chinese_integer(bare_chinese_match.group(1))
        if value is not None:
            return str(value)
    return None


def canonical_amounts(terms: list[str]) -> set[str]:
    return {canonical for term in terms if (canonical := canonical_amount(term))}


def _place_terms(text: str) -> list[str]:
    terms: list[str] = []
    for aliases in PLACE_ALIASES.values():
        terms.extend(alias for alias in aliases if alias in text)
    return _dedupe(terms)


def canonical_place(term: str) -> str | None:
    for place, aliases in PLACE_ALIASES.items():
        if term in aliases:
            return place
    return None


def canonical_places(terms: list[str]) -> set[str]:
    return {canonical for term in terms if (canonical := canonical_place(term))}


def canonical_kinship(term: str) -> str | None:
    for kinship, aliases in KINSHIP_ALIASES.items():
        if term in aliases:
            return kinship
    return None


def canonical_kinships(terms: list[str]) -> set[str]:
    return {canonical for term in terms if (canonical := canonical_kinship(term))}


def _kinship_terms(text: str) -> list[str]:
    terms: list[str] = []
    for aliases in KINSHIP_ALIASES.values():
        terms.extend(alias for alias in aliases if alias in text)
    return _dedupe(terms)


def _date_terms(text: str) -> list[str]:
    terms: list[str] = []
    for pattern in DATE_PATTERNS:
        terms.extend(pattern.findall(text))
    deduped_terms = _dedupe(terms)
    return [
        term
        for term in deduped_terms
        if not any(term != other and term in other for other in deduped_terms)
    ]


def _person_terms(text: str) -> list[str]:
    terms = [
        re.sub(r"[谨敬]$", "", match.group(1))
        for match in NAME_PATTERN.finditer(text)
    ]
    return [term for term in _dedupe(terms) if term not in {"儿谨", "男树"}]


def _recipient_salutation(text: str) -> str:
    clean_text = re.sub(
        r"^\s*【[^】]*(?:生成|草稿)[^】]*】\s*",
        "",
        text,
        count=1,
    ).lstrip()
    if not clean_text:
        return ""
    first_line = next(
        (line.strip() for line in clean_text.splitlines() if line.strip()),
        "",
    )
    if not first_line:
        return ""
    return re.split(r"[：:，,。；;！？!?]", first_line, maxsplit=1)[0].strip()[:40]


def extract_facts(text: str | None) -> dict[str, Any]:
    clean_text = text or ""
    amount_terms = _amount_terms(clean_text)
    place_terms = _place_terms(clean_text)
    return {
        "person_terms": _person_terms(clean_text),
        "place_terms": place_terms,
        "place_concepts": sorted(canonical_places(place_terms)),
        "amount_terms": amount_terms,
        "amount_values": sorted(canonical_amounts(amount_terms)),
        "date_terms": _date_terms(clean_text),
        "kinship_terms": _kinship_terms(clean_text),
        "kinship_concepts": sorted(canonical_kinships(_kinship_terms(clean_text))),
        "remittance_terms": _dedupe([term for term in REMITTANCE_TERMS if term in clean_text]),
        "study_terms": _dedupe([term for term in STUDY_TERMS if term in clean_text]),
        "safety_terms": _dedupe([term for term in SAFETY_TERMS if term in clean_text]),
    }


_CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "壹": 1,
    "二": 2,
    "两": 2,
    "贰": 2,
    "弍": 2,
    "三": 3,
    "叁": 3,
    "四": 4,
    "肆": 4,
    "五": 5,
    "伍": 5,
    "六": 6,
    "陆": 6,
    "七": 7,
    "柒": 7,
    "八": 8,
    "捌": 8,
    "九": 9,
    "玖": 9,
}
_CHINESE_SMALL_UNITS = {
    "十": 10,
    "拾": 10,
    "百": 100,
    "佰": 100,
    "千": 1000,
    "仟": 1000,
}


def _parse_chinese_integer(raw: str) -> int | None:
    if not raw:
        return None
    raw = raw.replace("廿", "二十").replace("卅", "三十")
    if all(character in _CHINESE_DIGITS for character in raw):
        digits = "".join(str(_CHINESE_DIGITS[character]) for character in raw)
        return int(digits)

    total = 0
    section = 0
    number = 0
    for character in raw:
        if character in _CHINESE_DIGITS:
            number = _CHINESE_DIGITS[character]
            continue
        if character in _CHINESE_SMALL_UNITS:
            unit = _CHINESE_SMALL_UNITS[character]
            section += (number or 1) * unit
            number = 0
            continue
        if character in {"万", "萬"}:
            section = (section + number) * 10000
            total += section
            section = 0
            number = 0
            continue
        return None
    return total + section + number


def infer_recipient_relationship(text: str | None) -> dict[str, Any]:
    clean_text = text or ""
    salutation = _recipient_salutation(clean_text)
    salutation_profiles = (
        (
            "mother",
            "亲子（写给母亲）",
            ("child_to_parent",),
            ("母亲", "妈妈", "阿母", "阿妈", "慈亲", "慈母", "娘亲"),
        ),
        (
            "father",
            "亲子（写给父亲）",
            ("child_to_parent",),
            ("父亲", "爸爸", "严亲", "严父", "爹爹"),
        ),
        (
            "wife",
            "夫妻（写给妻子）",
            ("spouse_to_spouse", "spouse"),
            ("妻子", "吾妻", "贤妻", "爱妻", "妻"),
        ),
        (
            "husband",
            "夫妻（写给丈夫）",
            ("spouse_to_spouse", "spouse"),
            ("丈夫", "夫君", "夫婿", "良人", "老公"),
        ),
        (
            "sibling",
            "手足",
            ("sibling_or_same_generation_kin",),
            (
                "阿弟",
                "弟弟",
                "胞弟",
                "贤弟",
                "吾弟",
                "兄长",
                "哥哥",
                "胞兄",
                "贤兄",
                "吾兄",
                "阿兄",
                "姐姐",
                "姊姊",
                "妹妹",
                "阿妹",
            ),
        ),
    )
    salutation_matches: list[
        tuple[int, str, str, tuple[str, ...], str]
    ] = []
    for key, label, relationship_types, aliases in salutation_profiles:
        for alias in aliases:
            position = salutation.find(alias)
            if position >= 0:
                salutation_matches.append(
                    (position, key, label, relationship_types, alias)
                )
    if salutation_matches:
        _, key, label, relationship_types, alias = min(
            salutation_matches,
            key=lambda item: item[0],
        )
        return {
            "key": key,
            "label": label,
            "relationship_types": list(relationship_types),
            "confidence": 1.0,
            "reason": f"开头收信称谓“{salutation}”明确指向{alias}关系",
        }

    facts = extract_facts(clean_text)
    concepts = set(facts["kinship_concepts"])

    explicit_profiles = (
        ("mother", "母亲", "亲子（写给母亲）", ("child_to_parent",)),
        ("father", "父亲", "亲子（写给父亲）", ("child_to_parent",)),
        ("wife", "妻子", "夫妻（写给妻子）", ("spouse_to_spouse", "spouse")),
        ("husband", "丈夫", "夫妻（写给丈夫）", ("spouse_to_spouse", "spouse")),
        ("sibling", "弟弟", "手足", ("sibling_or_same_generation_kin",)),
    )
    for key, concept, label, relationship_types in explicit_profiles:
        if concept in concepts:
            return {
                "key": key,
                "label": label,
                "relationship_types": list(relationship_types),
                "confidence": 1.0,
                "reason": f"输入中出现明确的{concept}关系称谓",
            }

    named_salutation = bool(
        re.search(
            r"(?:^|\n)\s*[\u4e00-\u9fff]{2,4}\s*[：:]",
            clean_text,
        )
    )
    shared_child_context = any(
        marker in clean_text
        for marker in (
            "孩子",
            "孩童",
            "稚子",
            "儿女",
            "给孩子",
            "带孩子",
            "孩子添衣",
            "孩子读书",
        )
    )
    spouse_context = any(
        marker in clean_text
        for marker in (
            "想起你",
            "想着你",
            "念你",
            "忆你",
            "念汝",
            "忆汝",
            "及汝",
            "与你",
            "你在身边",
            "回去一趟",
            "设法回去",
            "返乡",
            "团聚",
        )
    )
    if named_salutation and shared_child_context and spouse_context:
        return {
            "key": "wife",
            "label": "夫妻（写给妻子）",
            "relationship_types": ["spouse_to_spouse", "spouse"],
            "confidence": 0.82,
            "reason": "姓名式称谓与共同子女、思念或归家语境共同指向夫妻关系",
        }

    return {
        "key": "unknown",
        "label": "关系未明确",
        "relationship_types": [],
        "confidence": 0.0,
        "reason": "输入中没有足够稳定的收信关系线索",
    }
