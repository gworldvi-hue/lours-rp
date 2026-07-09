# -*- coding: utf-8 -*-
"""
telegram_export_public.py — выгрузка ВСЕХ постов из открытых каналов Lours RP
в JSON, без входа в личный Telegram-аккаунт.

Использует публичную веб-версию каналов (t.me/s/<username>), доступную без
авторизации. Проходит историю канала постранично (параметр before=), пока
не дойдёт до начала канала или до лимита MAX_POSTS_PER_CHANNEL.

Из закрытых чатов по инвайт-ссылке ничего не берёт — у них нет публичной
веб-страницы. Никакие секреты для этого скрипта не нужны.
"""

import json
import re
import time
import urllib.request
from html import unescape

PUBLIC_CHANNELS = [
    "akvilonia_lours", "askend_lours", "bdg_lours", "vrsc_lours", "pf_lours",
    "kk_lours", "gruvia_lours", "gms_lours", "korkaria_lours", "tatulsk_lours",
    "dongbu_lours", "ron_lours", "vbk_lours", "jeffrison_lours", "layo_lours",
    "ruffise_lours",
    "BlackWhiteOcta_Lours", "PH_Lours",
    "apexkosmos_lours", "vamflours", "gfv_lours", "lourazon_lours",
    "registry_lours", "interpol_lours",
    "LONliga", "SKO_lours", "ESNGRPLours",
    "MEME_LOURS_RP", "pravila_lours",
]

# Верхний предел постов на канал, чтобы не уйти в бесконечный цикл на очень
# старых/активных каналах и не словить лишний рейт-лимит от Telegram.
# Поставьте None, если действительно нужна вся история без ограничений
# (тогда учитывайте, что для активных каналов это может быть долго).
MAX_POSTS_PER_CHANNEL = 2000

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

MSG_ROW_RE = re.compile(
    r'<div class="tgme_widget_message[^"]*"[^>]*data-post="[^/]+/(\d+)"(.*?)'
    r'(?=<div class="tgme_widget_message[^"]*"[^>]*data-post=|\Z)',
    re.DOTALL,
)
TEXT_RE = re.compile(
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL,
)
DATE_RE = re.compile(r'<time[^>]*datetime="([^"]+)"')
TAG_RE = re.compile(r"<[^>]+>")


def clean_text(raw_html):
    text = raw_html.replace("<br>", "\n").replace("<br/>", "\n")
    text = TAG_RE.sub("", text)
    return unescape(text).strip()


def fetch_page(username, before=None):
    url = f"https://t.me/s/{username}"
    if before:
        url += f"?before={before}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def fetch_channel(username):
    posts = []
    seen_ids = set()
    before = None

    while True:
        try:
            html = fetch_page(username, before)
        except Exception as e:
            print(f"   [!] не удалось загрузить страницу: {e}")
            break

        rows = MSG_ROW_RE.findall(html)
        if not rows:
            break

        page_ids = []
        added_this_page = 0
        for msg_id, block in rows:
            msg_id = int(msg_id)
            page_ids.append(msg_id)
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)

            text_match = TEXT_RE.search(block)
            if not text_match:
                continue
            text = clean_text(text_match.group(1))
            if not text:
                continue
            date_match = DATE_RE.search(block)
            date = date_match.group(1) if date_match else None

            posts.append({"channel": username, "text": text, "date": date})
            added_this_page += 1

        if not page_ids:
            break

        # Идём назад по истории: следующая страница — это посты СТАРШЕ
        # самого младшего id, который мы уже видели.
        oldest_on_page = min(page_ids)
        if before is not None and oldest_on_page >= before:
            # страница не сдвинулась назад — дальше листать некуда
            break
        before = oldest_on_page

        if MAX_POSTS_PER_CHANNEL is not None and len(posts) >= MAX_POSTS_PER_CHANNEL:
            print(f"   [i] достигнут лимит {MAX_POSTS_PER_CHANNEL} постов, останавливаюсь")
            break

        if added_this_page == 0:
            # вся страница уже была видена раньше — конец истории
            break

        time.sleep(0.5)

    return posts


def main():
    all_posts = []
    print(f"Публичные каналы: {len(PUBLIC_CHANNELS)}")
    for username in PUBLIC_CHANNELS:
        print(f" → @{username}")
        posts = fetch_channel(username)
        print(f"   постов: {len(posts)}")
        all_posts.extend(posts)
        time.sleep(1)

    out_file = "lours_export.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)
    print(f"\nГотово: {len(all_posts)} постов сохранено в {out_file}")


if __name__ == "__main__":
    main()