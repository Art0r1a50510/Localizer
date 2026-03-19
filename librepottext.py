#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import argparse
import requests
from pathlib import Path


class LibreTranslator:
    """Клиент для LibreTranslate API."""

    def __init__(self, server_url="http://localhost:5000", source_lang="en", target_lang="ru", delay=0.5):
        self.server_url = server_url.rstrip('/')
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.delay = delay
        self.translate_url = f"{self.server_url}/translate"
        self.languages_url = f"{self.server_url}/languages"
        self._check_server()

    def _check_server(self):
        """Проверяет доступность сервера и поддерживаемые языки."""
        try:
            resp = requests.get(self.languages_url, timeout=5)
            if resp.status_code == 200:
                languages = resp.json()
                lang_codes = [lang['code'] for lang in languages]
                if self.target_lang not in lang_codes:
                    print(f"Внимание: целевой язык '{self.target_lang}' может не поддерживаться.")
                    print(f"Поддерживаемые языки: {', '.join(lang_codes[:10])}...")
                print(f"Сервер LibreTranslate доступен ({self.server_url})")
                return True
            else:
                print(f"Сервер вернул ошибку {resp.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"Не удалось подключиться к {self.server_url}")
            print("   Убедитесь, что LibreTranslate запущен.")
            sys.exit(1)
        except Exception as e:
            print(f"Ошибка при проверке сервера: {e}")
            sys.exit(1)

    def translate(self, text):
        if not text or not text.strip():
            return ""

        payload = {
            "q": text,
            "source": self.source_lang,
            "target": self.target_lang,
            "format": "text"
        }

        try:
            response = requests.post(self.translate_url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get("translatedText", "")
            else:
                print(f"Ошибка API {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"Ошибка при переводе '{text[:30]}...': {e}")
            return None

    def translate_batch(self, texts):
        """Переводит список текстов с задержкой между запросами."""
        results = []
        for i, text in enumerate(texts, 1):
            print(f"  [{i}/{len(texts)}] Перевод: {text[:50]}{'...' if len(text) > 50 else ''}")
            translated = self.translate(text)
            results.append(translated if translated is not None else "")
            if self.delay > 0 and i < len(texts):
                time.sleep(self.delay)
        return results


def escape_po_string(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def parse_pot_file(filepath):
    entries = []
    current_entry = {"msgid": None, "msgstr": None, "comments": []}
    in_msgid = False
    in_msgstr = False

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.rstrip('\n')
        # Комментарии (кроме fuzzy)
        if line.startswith('#') and not line.startswith('#,'):
            if current_entry["msgid"] is None:
                current_entry["comments"].append(line)
        elif line.startswith('msgid '):
            in_msgid, in_msgstr = True, False
            # Сохраняем предыдущую запись
            if current_entry["msgid"] is not None:
                entries.append(current_entry)
                current_entry = {"msgid": None, "msgstr": None, "comments": []}
            content = line[6:].strip()
            if content.startswith('"') and content.endswith('"'):
                current_entry["msgid"] = content[1:-1]
            else:
                current_entry["msgid"] = content
        elif line.startswith('msgstr '):
            in_msgid, in_msgstr = False, True
            content = line[7:].strip()
            if content.startswith('"') and content.endswith('"'):
                current_entry["msgstr"] = content[1:-1]
            else:
                current_entry["msgstr"] = content
        elif line.startswith('"') and in_msgid:
            # Продолжение многострочного msgid
            content = line.strip()
            if content.startswith('"') and content.endswith('"'):
                current_entry["msgid"] += content[1:-1]
        elif line.startswith('"') and in_msgstr:
            # Продолжение многострочного msgstr
            content = line.strip()
            if content.startswith('"') and content.endswith('"'):
                current_entry["msgstr"] += content[1:-1]
        elif line.strip() == "" and current_entry["msgid"] is not None:
            # Пустая строка — конец записи
            entries.append(current_entry)
            current_entry = {"msgid": None, "msgstr": None, "comments": []}
            in_msgid = in_msgstr = False

    # Добавляем последнюю запись
    if current_entry["msgid"] is not None:
        entries.append(current_entry)

    # Убираем записи с пустым msgid (заголовок) — он обрабатывается отдельно
    return [e for e in entries if e["msgid"] is not None and e["msgid"] != ""]


def write_po_file(entries, output_file, target_lang):
    """
    Записывает переведённые записи в .po файл.
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        # Заголовок
        f.write('msgid ""\n')
        f.write('msgstr ""\n')
        f.write(f'"Language: {target_lang}\\n"\n')
        f.write('"Content-Type: text/plain; charset=UTF-8\\n"\n')
        f.write('"Content-Transfer-Encoding: 8bit\\n"\n')
        f.write('\n')

        for entry in entries:
            # Комментарии
            for comment in entry.get("comments", []):
                f.write(comment + '\n')

            # msgid
            msgid = entry["msgid"]
            if '\n' in msgid:
                f.write('msgid ""\n')
                for line in msgid.split('\n'):
                    f.write(f'"{escape_po_string(line)}\\n"\n')
            else:
                f.write(f'msgid "{escape_po_string(msgid)}"\n')

            # msgstr
            msgstr = entry.get("msgstr", "")
            if msgstr:
                if '\n' in msgstr:
                    f.write('msgstr ""\n')
                    for line in msgstr.split('\n'):
                        f.write(f'"{escape_po_string(line)}\\n"\n')
                else:
                    f.write(f'msgstr "{escape_po_string(msgstr)}"\n')
            else:
                f.write('msgstr ""\n')

            f.write('\n')


def main():
    parser = argparse.ArgumentParser(description='Перевод .pot файла через LibreTranslate')
    parser.add_argument('input_pot', help='Входной .pot файл')
    parser.add_argument('-o', '--output', help='Выходной .po файл (по умолчанию: <язык>.po в папке исходника)')
    parser.add_argument('-t', '--target', default='ru', help='Целевой язык (код, например ru, de, fr)')
    parser.add_argument('-s', '--source', default='en', help='Исходный язык (по умолчанию en)')
    parser.add_argument('-u', '--url', default='http://localhost:5000', help='URL сервера LibreTranslate')
    parser.add_argument('-d', '--delay', type=float, default=0.5, help='Задержка между запросами (сек)')

    args = parser.parse_args()

    # Проверка входного файла
    if not os.path.isfile(args.input_pot):
        print(f"Файл {args.input_pot} не найден.")
        sys.exit(1)

    # Определяем выходной файл
    if args.output:
        output_file = args.output
    else:
        input_path = Path(args.input_pot)
        output_file = input_path.parent / f"{args.target}.po"

    # Создаём переводчик
    translator = LibreTranslator(
        server_url=args.url,
        source_lang=args.source,
        target_lang=args.target,
        delay=args.delay
    )

    # Парсим .pot файл
    print(f"Чтение файла: {args.input_pot}")
    entries = parse_pot_file(args.input_pot)
    print(f"Найдено записей для перевода: {len(entries)}")

    if not entries:
        print("Нет записей для перевода.")
        sys.exit(0)

    # Извлекаем все msgid для перевода
    texts_to_translate = [e["msgid"] for e in entries]

    # Переводим
    print(f"Перевод на {args.target}...")
    translations = translator.translate_batch(texts_to_translate)

    # Заполняем msgstr
    for entry, trans in zip(entries, translations):
        entry["msgstr"] = trans

    # Записываем результат
    write_po_file(entries, output_file, args.target)
    print(f"Готово! Результат сохранён в {output_file}")


if __name__ == "__main__":
    main()