# -*- coding: utf-8 -*-
"""
telegram_export.py — выгрузка постов из ОТКРЫТЫХ (@username) Telegram-каналов
проекта Lours RP в JSON для загрузки на сайт (вкладка «Импорт из Telegram»).

КАК ЭТО РАБОТАЕТ
-----------------
У каждого публичного Telegram-канала есть веб-превью без входа в аккаунт:
    https://t.me/s/<username>
Он показывает последние ~20 постов. Этого достаточно, чтобы регулярно
подтягивать свежие новости по странам без создания бота и без OAuth.

ОГРАНИЧЕНИЯ
-----------
1. Работает ТОЛЬКО для каналов с открытым @username. Ссылки вида
   https://t.me/+XXXXXXXX (приватные инвайты) через эту страницу не читаются —
   там обязателен вход живым Telegram-аккаунтом (см. блок "Приватные чаты" ниже).
2. t.me/s/ отдаёт только последние посты, а не полную историю. Для архива
   нужен Telethon с авторизацией (см. ниже).
3. Разметка t.me/s/ может измениться в будущем — если парсинг перестанет
   находить посты, проверьте актуальную структуру страницы (view-source).

УСТАНОВКА
---------
    pip install requests beautifulsoup4

ЗАПУСК
------
    python telegram_export.py
    → создаст файл lours_export.json рядом со скриптом.
    Загрузите этот файл на сайте: вкладка «Импорт из Telegram» → «Загрузить JSON-выгрузку».

АВТОМАТИЗАЦИЯ
-------------
Поставьте скрипт в cron / планировщик задач (например, раз в 6 часов), чтобы
lours_export.json обновлялся сам, и просто перезагружайте его на сайте.

ПРИВАТНЫЕ ЧАТЫ (расширение)
----------------------------
Ссылки вида t.me/+хэш — это закрытые группы/каналы. Прочитать их можно только
войдя в Telegram под своим аккаунтом. Для этого:
    1. Получите api_id и api_hash на https://my.telegram.org
    2. pip install telethon
    3. Используйте TelegramClient(...).iter_messages(chat) вместо requests —
       понадобится один раз пройти интерактивный вход (номер телефона + код).
Это отдельный скрипт, потому что требует ваших личных учётных данных — сюда
такие данные вписывать нельзя.
"""

import json
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Список открытых (@username) каналов проекта.
# channel  — то, что стоит в поле "tg" у страны на сайте (совпадает с реестром)
# label    — человекочитаемое имя, только для лога
CHANNELS = [
    {"channel": "akvilonia_lours", "label": "Республика Калзахия (Аквилония)"},
    {"channel": "askend_lours", "label": "Аскенд"},
    {"channel": "bdg_lours", "label": "Брадостанское Демократическое государство"},
    {"channel": "vrsc_lours", "label": "Вторая Республика Сан-Цара"},
    {"channel": "pf_lours", "label": "Партумская Федерация"},
    {"channel": "kk_lours", "label": "Королевство Квирсленд"},
    {"channel": "gruvia_lours", "label": "Грувийская Империя"},
    {"channel": "gms_lours", "label": "Горловой Морской Союз"},
    {"channel": "korkaria_lours", "label": "Коркария"},
    {"channel": "tatulsk_lours", "label": "Татульск"},
    {"channel": "dongbu_lours", "label": "Донгбу"},
    {"channel": "ron_lours", "label": "РОН"},
    {"channel": "vbk_lours", "label": "Винско-Боккийская конфедерация"},
    {"channel": "jeffrison_lours", "label": "Джеффрисон"},
    {"channel": "layo_lours", "label": "Лайо"},
    {"channel": "ruffise_lours", "label": "Раффайс"},
    # средние фракции
    {"channel": "BlackWhiteOcta_Lours", "label": "Black & White Octa"},
    {"channel": "PH_Lours", "label": "PH"},
    # всемирные организации / союзы с открытым username
    {"channel": "apexkosmos_lours", "label": "Apex Kosmos"},
    {"channel": "vamflours", "label": "VAMF"},
    {"channel": "gfv_lours", "label": "GFV"},
    {"channel": "lourazon_lours", "label": "Lourazon"},
    {"channel": "registry_lours", "label": "Registry"},
    {"channel": "interpol_lours", "label": "Интерпол"},
    {"channel": "LONliga", "label": "LON Liga"},
    {"channel": "SKO_lours", "label": "СКО"},
    {"channel": "ESNGRPLours", "label": "ESNGR"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LoursRPNewsBot/1.0; +https://t.me/pravila_lours)"
}


def fetch_channel_posts(username, limit=20):
    """Возвращает список постов {channel, text, date} для открытого @username."""
    url = f"https://t.me/s/{username}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [!] Не удалось получить {username}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    posts = []
    for wrap in soup.select(".tgme_widget_message_wrap"):
        text_el = wrap.select_one(".tgme_widget_message_text")
        time_el = wrap.select_one("time")
        if not text_el:
            continue
        text = text_el.get_text(separator="\n").strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        date_iso = time_el["datetime"] if time_el and time_el.has_attr("datetime") else None
        if text:
            posts.append({"channel": username, "text": text, "date": date_iso})
        if len(posts) >= limit:
            break
    return posts


def main():
    all_posts = []
    print(f"Начинаю выгрузку {len(CHANNELS)} каналов...")
    for ch in CHANNELS:
        print(f" → {ch['label']} (@{ch['channel']})")
        posts = fetch_channel_posts(ch["channel"])
        print(f"   найдено постов: {len(posts)}")
        all_posts.extend(posts)
        time.sleep(1.5)  # вежливая пауза, чтобы не долбить сервер запросами

    out_file = "lours_export.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    print(f"\nГотово: {len(all_posts)} постов сохранено в {out_file}")
    print(f"Выгрузка выполнена: {datetime.now().isoformat(timespec='seconds')}")
    print("Загрузите этот файл на сайте: вкладка «Импорт из Telegram» → «Загрузить JSON-выгрузку».")


if __name__ == "__main__":
    main()
