# -*- coding: utf-8 -*-
"""
telegram_export_full.py — выгрузка постов ИЗ ВСЕХ каналов и чатов проекта
Lours RP (открытых @username И закрытых по +инвайт-ссылке) в JSON.

В отличие от telegram_export_public.py, этот скрипт входит под вашим личным
Telegram-аккаунтом (через Telethon) — поэтому видит всё, что видите вы,
включая закрытые ООС-чаты и приватные организации. Именно поэтому для него
нужны личные учётные данные (api_id/api_hash) и один раз — код входа.

ЭТОТ СКРИПТ НЕ ЗАПУСКАЕТСЯ ВРУЧНУЮ КАЖДЫЙ РАЗ — он предназначен для
автоматического запуска через GitHub Actions по расписанию
(см. .github/workflows/telegram-export.yml). Настройка — один раз,
дальше всё работает само.

------------------------------------------------------------------------
КАК НАСТРОИТЬ (всё делается с телефона, через браузер)
------------------------------------------------------------------------

ШАГ 1. Получить api_id и api_hash
  1. Откройте https://my.telegram.org в браузере телефона
  2. Войдите под своим номером
  3. API development tools → создайте приложение (любое название)
  4. Скопируйте api_id (число) и api_hash (строка)

ШАГ 2. Получить сессионную строку (одноразовый вход)
  1. Откройте https://colab.research.google.com в браузере телефона
  2. Создайте новый блокнот (New notebook)
  3. В первой ячейке выполните:
         !pip install telethon
  4. Во второй ячейке вставьте содержимое файла generate_session.py
     (он идёт вместе с этим архивом) и запустите ячейку
  5. Введите api_id, api_hash, номер телефона, код из Telegram
     (и пароль 2FA, если он у вас включён)
  6. Скопируйте выведенную длинную строку — это TELEGRAM_SESSION

ШАГ 3. Добавить секреты в репозиторий
  В репозитории на GitHub (можно с телефона, через браузер, не приложение):
  Settings → Secrets and variables → Actions → New repository secret
  Добавьте три секрета:
    TELEGRAM_API_ID     — число из шага 1
    TELEGRAM_API_HASH   — строка из шага 1
    TELEGRAM_SESSION    — строка из шага 2

ШАГ 4. Включить Actions
  Вкладка Actions в репозитории → включить workflow, если попросит.
  Дальше он будет запускаться сам по расписанию (см. workflow-файл),
  либо вручную: Actions → Telegram Export → Run workflow.

Сессионная строка даёт полный доступ к вашему аккаунту — храните её
только в Secrets (они не видны в коде и в логах), никогда не публикуйте.
------------------------------------------------------------------------
"""

import json
import os
import time

from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
from telethon.tl.types import ChatInviteAlready, ChatInvite
from telethon.errors import FloodWaitError, UserAlreadyParticipantError

# ==== Учётные данные берутся из переменных окружения (GitHub Secrets) ====
API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION = os.environ["TELEGRAM_SESSION"]

# Если True — скрипт САМ ВСТУПИТ в закрытые чаты по инвайт-ссылке, если вы
# ещё не состоите в них. Это реальное действие с вашим аккаунтом.
# Если вы уже состоите во всех чатах ниже — можно оставить False.
AUTO_JOIN_PRIVATE = True

# Публичные каналы (username без @)
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

# Закрытые чаты — только хэш-часть ссылки после "t.me/+"
PRIVATE_INVITE_HASHES = [
    "Sivtq18nROBiZmMy",
    "aDPd40fwlJ44ZmYy",
    "enU-nU8wp5I0ZGI6",
    "63JXyTXIj_9jZDNi",
    "UXpmkI63Hgk1MDhi",
    "UhMkJIYpCTA4MDQy",
    "eakV4xThNlBjYThi",
    "ub4sSLvElJQ2Mzky",
]

LIMIT_PER_CHAT = 30


def dump_messages(client, entity, source_label):
    posts = []
    try:
        for msg in client.iter_messages(entity, limit=LIMIT_PER_CHAT):
            if msg.text:
                posts.append({
                    "channel": source_label,
                    "text": msg.text,
                    "date": msg.date.isoformat() if msg.date else None,
                })
    except FloodWaitError as e:
        print(f"  [!] FloodWait {e.seconds}s на {source_label}, пропускаю остаток")
    except Exception as e:
        print(f"  [!] Ошибка чтения {source_label}: {e}")
    return posts


def main():
    all_posts = []
    with TelegramClient(StringSession(SESSION), API_ID, API_HASH) as client:

        print(f"Публичные каналы: {len(PUBLIC_CHANNELS)}")
        for username in PUBLIC_CHANNELS:
            print(f" → @{username}")
            try:
                entity = client.get_entity(username)
                posts = dump_messages(client, entity, username)
                print(f"   постов: {len(posts)}")
                all_posts.extend(posts)
            except Exception as e:
                print(f"   [!] не удалось: {e}")
            time.sleep(1)

        print(f"\nЗакрытые чаты по инвайтам: {len(PRIVATE_INVITE_HASHES)}")
        for h in PRIVATE_INVITE_HASHES:
            label = f"invite:{h[:8]}"
            print(f" → {label}")
            try:
                check = client(CheckChatInviteRequest(h))
                if isinstance(check, ChatInviteAlready):
                    entity = check.chat
                elif isinstance(check, ChatInvite):
                    if not AUTO_JOIN_PRIVATE:
                        print("   [i] Вы не состоите в чате, AUTO_JOIN_PRIVATE=False — пропуск")
                        continue
                    try:
                        result = client(ImportChatInviteRequest(h))
                        entity = result.chats[0]
                    except UserAlreadyParticipantError:
                        entity = client(CheckChatInviteRequest(h)).chat
                else:
                    print("   [!] Неизвестный тип приглашения, пропуск")
                    continue
                posts = dump_messages(client, entity, label)
                print(f"   постов: {len(posts)}")
                all_posts.extend(posts)
            except FloodWaitError as e:
                print(f"   [!] FloodWait {e.seconds}s, пропуск")
            except Exception as e:
                print(f"   [!] не удалось: {e}")
            time.sleep(2)

    out_file = "lours_export.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)
    print(f"\nГотово: {len(all_posts)} постов сохранено в {out_file}")


if __name__ == "__main__":
    main()
