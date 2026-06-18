from __future__ import annotations

import re
from typing import Any


AMOUNT_NUMBER_ALIASES: dict[str, tuple[str, ...]] = {
    "1": ("一元", "壹元"),
    "2": ("二元", "贰元", "弍元"),
    "3": ("三元", "叁元"),
    "4": ("四元", "肆元"),
    "5": ("五元", "伍元"),
    "6": ("六元", "陆元"),
    "7": ("七元", "柒元"),
    "8": ("八元", "捌元"),
    "9": ("九元", "玖元"),
    "10": ("十元", "拾元"),
}

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
    "泰国": ("泰国", "暹罗", "暹"),
    "越南": ("越南", "安南", "西贡"),
    "广东": ("广东", "潮汕", "潮州", "澄海", "海邑", "潮邑"),
}

KINSHIP_ALIASES: dict[str, tuple[str, ...]] = {
    "母亲": ("母亲", "妈妈", "阿母", "阿妈", "慈亲", "家母", "大人", "膝下"),
    "父亲": ("父亲", "爸爸", "严亲", "家父"),
    "弟弟": ("弟弟", "胞弟", "贤弟", "弟"),
}

REMITTANCE_TERMS: tuple[str, ...] = (
    "寄",
    "寄款",
    "汇款",
    "奉上",
    "付去",
    "带去",
    "查收",
    "收讫",
    "检收",
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
    amount_suffix = "|".join(
        re.escape(alias)
        for aliases in AMOUNT_NUMBER_ALIASES.values()
        for alias in aliases
    )
    pattern = re.compile(rf"(?:{currency_prefix})?[零一二三四五六七八九十壹贰弍叁肆伍陆柒捌玖拾\d]{{1,6}}元")
    terms.extend(pattern.findall(text))
    terms.extend(alias for aliases in AMOUNT_NUMBER_ALIASES.values() for alias in aliases if alias in text)
    return _dedupe(terms)


def canonical_amount(term: str) -> str | None:
    for number, aliases in AMOUNT_NUMBER_ALIASES.items():
        if any(alias in term for alias in aliases):
            return number
    digit_match = re.search(r"(\d+)\s*元", term)
    if digit_match:
        return digit_match.group(1)
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
        "remittance_terms": _dedupe([term for term in REMITTANCE_TERMS if term in clean_text]),
        "study_terms": _dedupe([term for term in STUDY_TERMS if term in clean_text]),
        "safety_terms": _dedupe([term for term in SAFETY_TERMS if term in clean_text]),
    }
