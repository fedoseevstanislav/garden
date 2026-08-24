#!/usr/bin/env python3
"""Deterministic scorer for the garden profile questionnaire.

Usage:
    python3 score.py ANSWERS_FILE [--json]
    python3 score.py --items          # print the item table (markdown)
    python3 score.py --hand-table     # print the hand-scoring table (markdown)

ANSWERS_FILE: 40 integers 1..5 in item order, separated by spaces, commas or
newlines. Lines starting with '#' are ignored. No dependencies beyond stdlib.

Keying: '+' items are scored as given, '-' items are reversed (6 - answer).
Facet score = sum of its 5 items (5..25). Bands by raw sum:
    low  5..12  | mid 13..17 | high 18..25
Items are public-domain IPIP-NEO facet items (ipip.ori.org), translated to
Russian by the author; the translation is NOT validated.
"""
import json
import sys

FACETS = [
    # code, Russian label, IPIP-NEO source facet
    ("ORD", "Порядок", "C2 Orderliness"),
    ("SDI", "Самодисциплина", "C5 Self-Discipline"),
    ("ACH", "Стремление к результату", "C4 Achievement-Striving"),
    ("DUT", "Обязательность", "C3 Dutifulness"),
    ("DEL", "Обдуманность", "C6 Deliberation"),
    ("ACT", "Темп", "E4 Activity Level"),
    ("STR", "Стресс-реактивность", "N1 Anxiety + N6 Vulnerability (composite)"),
    ("VAR", "Потребность в новизне", "O4 Adventurousness"),
]

# Five items per facet, pattern: + + - + -  (3 direct, 2 reversed)
FACET_ITEMS = {
    "ORD": [("+", "Мой рабочий стол и файлы в порядке: всё лежит там, где должно."),
            ("+", "Кладу вещи на место сразу после использования."),
            ("-", "Оставляю свои вещи где попало."),
            ("+", "Веду списки дел и регулярно их чищу."),
            ("-", "Подолгу ищу нужные вещи или файлы.")],
    "SDI": [("+", "Берусь за рутинные дела сразу, не откладывая."),
            ("+", "Довожу свои планы до конца."),
            ("-", "Мне трудно заставить себя взяться за работу."),
            ("+", "Сразу приступаю к делу."),
            ("-", "Мне нужен толчок, чтобы начать.")],
    "ACH": [("+", "Иду прямо к цели."),
            ("+", "Ставлю себе высокую планку."),
            ("-", "Делаю ровно столько, чтобы сошло."),
            ("+", "Делаю больше, чем от меня ожидают."),
            ("-", "Не особенно стремлюсь к успеху.")],
    "DUT": [("+", "Держу свои обещания."),
            ("+", "Стараюсь следовать правилам."),
            ("-", "Нарушаю правила."),
            ("+", "Выполняю свои обязательства в срок."),
            ("-", "Перекладываю свои обязанности на других.")],
    "DEL": [("+", "Перед тем как ответить или решить, беру паузу и обдумываю."),
            ("+", "Проверяю детали, прежде чем отправить или сдать работу."),
            ("-", "Принимаю поспешные решения."),
            ("+", "Доделываю начатое, прежде чем браться за новую идею."),
            ("-", "Бросаюсь в дела, не подумав.")],
    "ACT": [("+", "Я всегда чем-то занят(а)."),
            ("+", "Много чем занимаюсь в свободное время."),
            ("-", "Люблю не торопиться."),
            ("+", "Обычно веду несколько дел одновременно."),
            ("-", "Предпочитаю спокойный, неспешный ритм жизни.")],
    "STR": [("+", "Легко поддаюсь стрессу."),
            ("+", "Часто тревожусь по разным поводам."),
            ("-", "Сохраняю спокойствие под давлением."),
            ("+", "Чувствую, что события меня захлёстывают."),
            ("-", "Большую часть времени я расслаблен(а).")],
    "VAR": [("+", "Предпочитаю разнообразие рутине."),
            ("+", "Люблю начинать новое."),
            ("-", "Не люблю перемен."),
            ("+", "Интересуюсь многими разными вещами."),
            ("-", "Я человек привычки.")],
}


def build_items():
    """Interleave facets so every batch of 8 has one item per facet and the
    reversed items are spread across batches. Returns list of dicts in
    questionnaire order (item 1..40)."""
    items = []
    codes = [f[0] for f in FACETS]
    for rnd in range(5):
        for fi, code in enumerate(codes):
            key, text = FACET_ITEMS[code][(rnd + fi) % 5]
            items.append({"n": len(items) + 1, "facet": code, "key": key, "text": text})
    return items


ITEMS = build_items()
BANDS = [(5, 12, "low"), (13, 17, "mid"), (18, 25, "high")]


def band(total):
    for lo, hi, name in BANDS:
        if lo <= total <= hi:
            return name
    raise ValueError(total)


def archetype(b):
    """Rule-ordered archetype from Orderliness (ORD) and Self-Discipline (SDI)
    bands, with Need-for-variety (VAR) as a tiebreaker for the middle cell."""
    o, s = b["ORD"], b["SDI"]
    if o == "high" and s == "high":
        return "Архитектор"
    if o == "high":                      # SDI mid/low
        return "Хранитель"
    if s == "high":                      # ORD mid/low
        return "Партизан"
    if s == "low":                       # ORD mid/low
        return "Охотник"
    # remaining: ORD mid/low and SDI mid
    return "Исследователь" if b["VAR"] == "high" else "Ремесленник"


def parse_answers(path):
    raw = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0]
            raw += line.replace(",", " ").split()
    try:
        vals = [int(x) for x in raw]
    except ValueError as e:
        sys.exit(f"error: non-integer answer: {e}")
    if len(vals) != len(ITEMS):
        sys.exit(f"error: expected {len(ITEMS)} answers, got {len(vals)}")
    bad = [i + 1 for i, v in enumerate(vals) if not 1 <= v <= 5]
    if bad:
        sys.exit(f"error: answers outside 1..5 at items {bad}")
    return vals


def score(vals):
    totals = {f[0]: 0 for f in FACETS}
    for item, v in zip(ITEMS, vals):
        totals[item["facet"]] += v if item["key"] == "+" else 6 - v
    bands = {c: band(t) for c, t in totals.items()}
    return {
        "facets": [{"code": c, "label": lbl, "source": src, "sum": totals[c],
                    "mean": round(totals[c] / 5, 1), "band": bands[c]}
                   for c, lbl, src in FACETS],
        "archetype": archetype(bands),
    }


def print_items():
    print("| № | Фасет | Ключ | Утверждение |")
    print("|---|---|---|---|")
    for it in ITEMS:
        print(f"| {it['n']} | {it['facet']} | {it['key']} | {it['text']} |")


def print_hand_table():
    print("| Фасет | Прямые пункты (балл как есть) | Обратные пункты (6 − балл) |")
    print("|---|---|---|")
    for code, lbl, _ in FACETS:
        d = [str(i["n"]) for i in ITEMS if i["facet"] == code and i["key"] == "+"]
        r = [str(i["n"]) for i in ITEMS if i["facet"] == code and i["key"] == "-"]
        print(f"| {code} {lbl} | {', '.join(d)} | {', '.join(r)} |")


def main(argv):
    if "--items" in argv:
        return print_items()
    if "--hand-table" in argv:
        return print_hand_table()
    paths = [a for a in argv if not a.startswith("--")]
    if len(paths) != 1:
        sys.exit(__doc__)
    res = score(parse_answers(paths[0]))
    if "--json" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    print("| Фасет | Сумма | Среднее | Уровень |")
    print("|---|---|---|---|")
    for f in res["facets"]:
        print(f"| {f['label']} ({f['code']}) | {f['sum']} | {f['mean']} | {f['band']} |")
    print(f"\nАрхетип: {res['archetype']}")


if __name__ == "__main__":
    main(sys.argv[1:])
