import os
import re
import sys
from pathlib import Path

MSGID_PATTERN = re.compile(r'(?:_|wxTRANSLATE)\(\s*"((?:[^"\\]|\\.)*)"\s*\)')


def escape_po_string(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def extract_strings_from_file(filepath):
    """Извлекает все msgid из одного файла."""
    strings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        strings.extend(MSGID_PATTERN.findall(content))
    except (IOError, UnicodeDecodeError) as e:
        print(f"Ошибка при обработке {filepath}: {e}", file=sys.stderr)
    return strings


def save_as_pot(strings, output_file):
    """Сохраняет уникальные строки в .pot файл."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('msgid ""\n')
        f.write('msgstr ""\n')
        f.write('"Content-Type: text/plain; charset=UTF-8\\n"\n')
        f.write('"Content-Transfer-Encoding: 8bit\\n"\n\n')

        for s in strings:
            f.write(f'msgid "{escape_po_string(s)}"\n')
            f.write('msgstr ""\n\n')

    print(f"Создан шаблон .pot с {len(strings)} записями: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("Использование: python localizertextpot.py <путь_к_исходникам> [выходной_файл]")
        sys.exit(1)

    root_dir = Path(sys.argv[1])
    if not root_dir.is_dir():
        print(f"Ошибка: папка '{root_dir}' не найдена.")
        sys.exit(1)

    output_file = sys.argv[2] if len(sys.argv) > 2 else 'messages.pot'

    # Расширения файлов для поиска
    extensions = ('.cpp', '.h', '.hpp', '.cxx', '.hxx', '.cc', '.hh')

    all_strings = []
    print(f"Поиск в папке: {root_dir}")

    for filepath in root_dir.rglob('*'):
        if filepath.suffix.lower() in extensions:
            strings = extract_strings_from_file(filepath)
            if strings:
                print(f"{filepath}: найдено {len(strings)} строк")
                all_strings.extend(strings)

    # Удаляем дубликаты с сохранением порядка
    unique_strings = list(dict.fromkeys(all_strings))

    print(f"\nСтатистика:")
    print(f"Всего уникальных строк: {len(unique_strings)}")
    print(f"Всего строк с дубликатами: {len(all_strings)}")

    if unique_strings:
        save_as_pot(unique_strings, output_file)
    else:
        print("Не найдено ни одной строки для перевода.")


if __name__ == "__main__":
    main()