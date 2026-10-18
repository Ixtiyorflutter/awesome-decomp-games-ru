#!/usr/bin/env python3
"""Собирает полный русскоязычный каталог из games.json проекта
SubmitGame/awesome-decomp-games и обновляет цифры в README.

Запуск:  python3 scripts/build_catalog.py [путь_или_URL_к_games.json]
Без зависимостей, только стандартная библиотека Python 3.8+.
"""
import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime

SOURCE_URL = "https://raw.githubusercontent.com/SubmitGame/awesome-decomp-games/main/data/games.json"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")

TYPES = {
    "static-recomp": ("rekompilyacii", "⚙️ Статические рекомпиляции",
                      "Бинарники консолей и ПК, автоматически перекомпилированные в нативный код (N64Recomp, XenonRecomp, ReXGlue, рекомпиляторы PS1/PS2)."),
    "source-port": ("porty", "🔧 Порты на исходниках",
                    "Нативные порты для ПК и портативок на основе декомпиляции или официально открытого кода."),
    "engine-remake": ("remeyki-dvizhkov", "🏗 Движки-ремейки и реимплементации",
                      "Движок написан заново, графика и звук берутся из оригинальной игры."),
    "decompilation": ("dekompilyacii", "🔬 Декомпиляции",
                      "Код игры восстановлен на C/C++; многие проекты — matching (байт-в-байт с оригиналом)."),
    "disassembly": ("dizassemblirovaniya", "📜 Дизассемблирования",
                    "Читаемый ассемблер, который собирается в идентичный ROM; основа ромхаков и переводов."),
    "browser-port": ("brauzernye-porty", "🌐 Браузерные порты",
                     "Порты, работающие во вкладке браузера (WebAssembly / JavaScript)."),
    "tool": ("instrumenty", "🧰 Инструменты и лаунчеры",
             "Рекомпиляторы, лаунчеры и библиотеки для сцены."),
}
TYPE_SHORT = {
    "static-recomp": "рекомпиляция", "source-port": "порт", "engine-remake": "ремейк движка",
    "decompilation": "декомпиляция", "disassembly": "дизасм", "browser-port": "браузер", "tool": "инструмент",
}

# группа платформ: (slug, заголовок, список подстрок для сопоставления)
PLATFORMS = [
    ("n64", "Nintendo 64", ["N64"]),
    ("gamecube-wii", "GameCube и Wii", ["GameCube", "Wii"]),
    ("wiiu-3ds-switch", "Wii U, 3DS, DS и Switch", ["Wii U", "3DS", "DS", "Switch"]),
    ("nes-snes", "NES, SNES и Virtual Boy", ["NES", "SNES", "Virtual Boy"]),
    ("game-boy", "Game Boy, GBC и GBA", ["Game Boy", "GBA"]),
    ("ps1", "PlayStation 1", ["PS1"]),
    ("ps2", "PlayStation 2", ["PS2"]),
    ("ps3-ps4-psp", "PS3, PS4 и PSP", ["PS3", "PS4", "PSP"]),
    ("xbox", "Xbox", ["Xbox"]),
    ("xbox-360", "Xbox 360", ["Xbox 360"]),
    ("sega", "Sega (Genesis, Saturn, Dreamcast, 32X)", ["Genesis", "Mega Drive", "Saturn", "Dreamcast", "Sega", "32X", "Master System", "Game Gear"]),
    ("pc", "ПК (Windows, Mac)", ["PC", "Mac", "Windows"]),
    ("dos", "DOS", ["DOS"]),
    ("arcade", "Аркадные автоматы", ["Arcade"]),
    ("mobile", "Мобильные (Android, iOS)", ["Mobile", "Android", "iOS"]),
    ("retro-pc", "Ретро-компьютеры (Amiga, C64, ZX Spectrum, BBC Micro, PC-98)", ["Amiga", "Commodore", "ZX", "BBC", "Acorn", "PC-98", "Atari", "MSX", "Apple II"]),
]


def load(src):
    if src.startswith("http"):
        req = urllib.request.Request(src, headers={"User-Agent": "decomp-ru-builder"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    with open(src, encoding="utf-8") as f:
        return json.load(f)


def platform_group(p):
    """Возвращает slug группы. Точные совпадения важны: 'Xbox 360' ≠ 'Xbox', 'Wii U' ≠ 'Wii'."""
    if not p:
        return "other"
    parts = [x.strip() for x in re.split(r"[/,]", p) if x.strip()]
    first = parts[0] if parts else p
    exact = {
        "Xbox 360": "xbox-360", "Xbox": "xbox", "og xbox": "xbox", "Wii U": "wiiu-3ds-switch",
        "Wii": "gamecube-wii", "GameCube": "gamecube-wii", "DS": "wiiu-3ds-switch", "3DS": "wiiu-3ds-switch",
        "Switch": "wiiu-3ds-switch", "NES": "nes-snes", "SNES": "nes-snes", "Virtual Boy": "nes-snes",
        "GBA": "game-boy", "Game Boy": "game-boy", "Game Boy Color": "game-boy",
        "PC-98": "retro-pc", "Others": "other", "Other": "other",
    }
    if first in exact:
        return exact[first]
    low = first.lower()
    for slug, _, keys in PLATFORMS:
        for k in keys:
            if k.lower() in low:
                return slug
    return "other"


def esc(s):
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def stars(n):
    if n in (None, ""):
        return "—"
    n = int(n)
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def date(s):
    return s[:10] if s else "—"


def score(g):
    s = g.get("score")
    return f"{s:.2f}".rstrip("0").rstrip(".") if isinstance(s, (int, float)) else "—"


def link(g):
    url = g.get("url") or g.get("homepage") or g.get("play_url") or ""
    title = esc(g.get("title")) or "?"
    return f"[{title}]({url})" if url else title


def desc(g, n=150):
    d = esc(g.get("description"))
    return d if len(d) <= n else d[: n - 1].rstrip() + "…"


def sort_key(g):
    return (-(g.get("score") or 0), -(g.get("stars") or 0), (g.get("title") or "").lower())


def is_active(g):
    return not g.get("inactive") and not g.get("archived")


def table(games, with_type=False, with_platform=True):
    head = ["Игра (проект)"]
    if with_platform:
        head.append("Платформа")
    if with_type:
        head.append("Тип")
    head += ["⭐", "Score", "Коммит", "Релиз", "Описание (англ.)"]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for g in games:
        row = [link(g)]
        if with_platform:
            row.append(esc(g.get("platform")) or "—")
        if with_type:
            row.append(TYPE_SHORT.get(g.get("type"), g.get("type") or "—"))
        row += [stars(g.get("stars")), score(g), date(g.get("last_commit")),
                "✅" if g.get("release") else "—", desc(g)]
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


HEADER_NOTE = (
    "> Страница генерируется автоматически скриптом [`scripts/build_catalog.py`](../{up}scripts/build_catalog.py) "
    "из данных [SubmitGame/awesome-decomp-games](https://github.com/SubmitGame/awesome-decomp-games). "
    "Здесь только ссылки на исходный код — никаких ROM и игровых ресурсов. Данные на **{date}**.\n"
)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def build(data):
    games = data["games"]
    gen = (data.get("generated_at") or datetime.utcnow().isoformat())[:10]
    gen_ru = datetime.strptime(gen, "%Y-%m-%d").strftime("%d.%m.%Y")
    active = [g for g in games if is_active(g)]
    inactive = [g for g in games if not is_active(g)]
    nav = "[← Главная](../README.md) · [Весь каталог](README.md)"
    nav2 = "[← Главная](../../README.md) · [Весь каталог](../README.md)"

    # --- страницы по типам
    type_counts = Counter(g.get("type") for g in games)
    for t, (slug, title, about) in TYPES.items():
        act = sorted([g for g in active if g.get("type") == t], key=sort_key)
        ina = sorted([g for g in inactive if g.get("type") == t], key=sort_key)
        if not act and not ina:
            continue
        parts = [f"# {title} — полный список ({len(act) + len(ina)})", "", nav, "",
                 HEADER_NOTE.format(up="", date=gen_ru), about, ""]
        if t == "browser-port":
            playable = sorted([g for g in games if g.get("browser_playable") and g.get("play_url")], key=sort_key)
            if playable:
                parts += ["## ▶ Запускаются прямо во вкладке", "",
                          "| Игра | Платформа | Играть | Нужны свои файлы | Мультиплеер |", "|---|---|---|---|---|"]
                for g in playable:
                    parts.append(f"| {esc(g.get('title'))} | {esc(g.get('platform')) or '—'} | [▶ открыть]({g['play_url']}) | "
                                 f"{'да' if g.get('needs_assets') else '—'} | {'✅' if g.get('multiplayer') else '—'} |")
                parts += ["", "⚠️ Сайты сторонние. Никогда не устанавливай лаунчеры и расширения, которые они предлагают.", ""]
        parts += [f"## Активные проекты ({len(act)})", "", table(act), ""]
        if ina:
            parts += [f"## Неактивные и архивные ({len(ina)})", "",
                      "<details><summary>Показать</summary>", "", table(ina), "", "</details>", ""]
        parts += ["---", nav]
        write(os.path.join(CATALOG, f"{slug}.md"), "\n".join(parts))

    # --- страницы по платформам
    by_plat = defaultdict(list)
    for g in games:
        by_plat[platform_group(g.get("platform"))].append(g)
    plat_meta = [(s, t) for s, t, _ in PLATFORMS] + [("other", "Другие и мультиплатформенные")]
    plat_counts = {}
    for slug, title in plat_meta:
        lst = by_plat.get(slug, [])
        if not lst:
            continue
        act = sorted([g for g in lst if is_active(g)], key=sort_key)
        ina = sorted([g for g in lst if not is_active(g)], key=sort_key)
        plat_counts[slug] = (title, len(act), len(ina))
        best = [g for g in act if g.get("release")][:10]
        parts = [f"# {title}: декомпиляции, рекомпиляции и порты игр ({len(act) + len(ina)})", "", nav2, "",
                 HEADER_NOTE.format(up="../", date=gen_ru)]
        if best:
            parts += ["## 🏆 Во что поиграть в первую очередь", ""]
            for i, g in enumerate(best, 1):
                parts.append(f"{i}. {link(g).replace(chr(92) + '|', '|')} — {TYPE_SHORT.get(g.get('type'), '')}, ⭐ {stars(g.get('stars'))}, score {score(g)}")
            parts.append("")
        parts += [f"## Все активные проекты ({len(act)})", "", table(act, with_type=True, with_platform=True), ""]
        if ina:
            parts += [f"## Неактивные и архивные ({len(ina)})", "", "<details><summary>Показать</summary>", "",
                      table(ina, with_type=True), "", "</details>", ""]
        parts += ["---", nav2]
        write(os.path.join(CATALOG, "platformy", f"{slug}.md"), "\n".join(parts))

    # --- индекс каталога
    idx = ["# 📚 Полный каталог декомпиляций, рекомпиляций и портов игр", "", "[← Главная](../README.md)", "",
           HEADER_NOTE.format(up="", date=gen_ru),
           f"Всего **{len(games)}** проектов для **{data.get('unique_games') or len({g.get('game_key') for g in games})}** игр, "
           f"из них **{len(active)}** активных.", "", "## По типу проекта", "",
           "| Раздел | Проектов | Что это |", "|---|---|---|"]
    for t, (slug, title, about) in TYPES.items():
        if type_counts.get(t):
            idx.append(f"| [{title}]({slug}.md) | {type_counts[t]} | {about} |")
    idx += ["", "## По платформе", "", "| Платформа | Активных | Неактивных |", "|---|---|---|"]
    for slug, (title, a, i) in sorted(plat_counts.items(), key=lambda kv: -kv[1][1]):
        idx.append(f"| [{title}](platformy/{slug}.md) | {a} | {i} |")
    idx += ["", "## Как читать таблицы", "",
            "- **Score (0–5)** — рейтинг первоисточника: играбельность, полнота, активность, популярность.",
            "- **⭐** — звёзды на GitHub, **Коммит** — дата последнего коммита.",
            "- **Релиз ✅** — есть готовые сборки, компилировать не нужно.",
            "- Описания пока на английском — помоги перевести через Pull Request.", ""]
    write(os.path.join(CATALOG, "README.md"), "\n".join(idx))

    # --- блок цифр в главном README
    readme = os.path.join(ROOT, "README.md")
    if os.path.exists(readme):
        top_star = sorted(games, key=lambda g: -(g.get("stars") or 0))[:2]
        lines = ["<!-- STATS:START -->", "| Показатель | Значение |", "|---|---|",
                 f"| Проектов в каталоге | **{len(games)}** ({len(active)} активных) |",
                 f"| Уникальных игр | **{data.get('unique_games') or '—'}** |"]
        for t, (slug, title, _) in TYPES.items():
            if type_counts.get(t):
                name = re.sub(r"^\S+\s", "", title)
                lines.append(f"| [{name}](catalog/{slug}.md) | {type_counts[t]} |")
        lines.append(f"| Играбельны прямо в браузере | {sum(1 for g in games if g.get('browser_playable'))} |")
        lines.append("| Самые «звёздные» | " + ", ".join(f"{esc(g.get('title'))} — {stars(g.get('stars'))} ⭐" for g in top_star) + " |")
        lines.append(f"| Данные на | {gen_ru} (обновляются автоматически) |")
        lines.append("<!-- STATS:END -->")
        with open(readme, encoding="utf-8") as f:
            txt = f.read()
        new = re.sub(r"<!-- STATS:START -->.*?<!-- STATS:END -->", "\n".join(lines), txt, flags=re.S)
        new = re.sub(r"badge/проектов-\d+-", f"badge/проектов-{len(games)}-", new)
        if data.get("unique_games"):
            new = re.sub(r"badge/игр-\d+-", f"badge/игр-{data['unique_games']}-", new)
        new = re.sub(r"badge/данные-[\d.]+-", f"badge/данные-{gen_ru}-", new)
        if new != txt:
            with open(readme, "w", encoding="utf-8") as f:
                f.write(new)
    print(f"OK: {len(games)} проектов, данные на {gen_ru}")


if __name__ == "__main__":
    build(load(sys.argv[1] if len(sys.argv) > 1 else SOURCE_URL))
