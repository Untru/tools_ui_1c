#!/usr/bin/env python3
"""
Применение переводов из .lstr файлов к XML-исходникам в формате конфигуратора.

.lstr формат:
  #Translations for: interface
  Synonym=English text
  Attribute.Name.Title=English title

XML формат (конфигуратор):
  <Synonym>
    <v8:item>
      <v8:lang>ru</v8:lang>
      <v8:content>Русский текст</v8:content>
    </v8:item>
  </Synonym>

Результат: добавляется <v8:item> с en после ru.
"""

import os
import sys
import re
from pathlib import Path


def parse_lstr(lstr_path):
    """Парсит .lstr файл, возвращает dict {key: value}."""
    translations = {}
    with open(lstr_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                if value:
                    translations[key.strip()] = value.strip()
    return translations


def add_en_to_synonym(xml_content, en_value):
    """Добавляет EN перевод в блок <Synonym> XML."""
    # Ищем блок <Synonym>...</Synonym> и добавляем en item после последнего </v8:item>
    pattern = r'(<Synonym>\s*<v8:item>\s*<v8:lang>ru</v8:lang>\s*<v8:content>[^<]*</v8:content>\s*</v8:item>)'
    replacement = r'\1\n\t\t\t\t<v8:item>\n\t\t\t\t\t<v8:lang>en</v8:lang>\n\t\t\t\t\t<v8:content>' + en_value + r'</v8:content>\n\t\t\t\t</v8:item>'
    new_content, count = re.subn(pattern, replacement, xml_content, count=1)
    return new_content, count


def add_en_to_named_block(xml_content, block_name, en_value):
    """Добавляет EN перевод в произвольный именованный блок (Title, Comment и т.д.)."""
    pattern = r'(<' + re.escape(block_name) + r'>\s*<v8:item>\s*<v8:lang>ru</v8:lang>\s*<v8:content>[^<]*</v8:content>\s*</v8:item>)'
    replacement = r'\1\n\t\t\t\t<v8:item>\n\t\t\t\t\t<v8:lang>en</v8:lang>\n\t\t\t\t\t<v8:content>' + en_value + r'</v8:content>\n\t\t\t\t</v8:item>'
    new_content, count = re.subn(pattern, replacement, xml_content)
    return new_content, count


def process_lstr_file(lstr_path, translate_dir, export_dir):
    """Обрабатывает один .lstr файл."""
    translations = parse_lstr(lstr_path)
    if not translations:
        return 0

    # Определяем путь к XML
    rel_path = os.path.relpath(lstr_path, translate_dir)
    obj_dir = os.path.dirname(rel_path)
    base_name = os.path.basename(lstr_path).replace('_en.lstr', '')

    # Находим XML файл
    xml_path = None
    if base_name == 'Form':
        # Form_en.lstr -> ../Ext/Form.xml
        xml_path = os.path.join(export_dir, obj_dir, 'Ext', 'Form.xml')
    else:
        # Obj_en.lstr -> Obj.xml (в родительской папке)
        xml_path = os.path.join(export_dir, obj_dir + '.xml')
        if not os.path.exists(xml_path):
            xml_path = os.path.join(export_dir, obj_dir, base_name + '.xml')

    if not xml_path or not os.path.exists(xml_path):
        return 0

    # Читаем XML
    with open(xml_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    applied = 0
    for key, value in translations.items():
        # Экранируем спецсимволы для XML
        value_escaped = value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

        if key == 'Synonym':
            content, count = add_en_to_synonym(content, value_escaped)
            applied += count
        elif '.' in key:
            # Составной ключ: Attribute.Name.Title -> ищем Title в контексте атрибута
            # Пока обрабатываем только простые Title
            parts = key.split('.')
            if len(parts) >= 2 and parts[-1] in ('Title', 'ToolTip'):
                content, count = add_en_to_named_block(content, parts[-1], value_escaped)
                applied += count
        else:
            # Простой ключ — ищем как блок
            content, count = add_en_to_named_block(content, key, value_escaped)
            applied += count

    if applied > 0:
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(content)

    return applied


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <translate_dir> <export_dir>")
        print(f"  translate_dir: path to translate/en/src")
        print(f"  export_dir: path to build/source/Инструменты")
        sys.exit(1)

    translate_dir = sys.argv[1]
    export_dir = sys.argv[2]

    if not os.path.isdir(translate_dir):
        print(f"ERROR: translate_dir not found: {translate_dir}")
        sys.exit(1)
    if not os.path.isdir(export_dir):
        print(f"ERROR: export_dir not found: {export_dir}")
        sys.exit(1)

    total_applied = 0
    total_files = 0

    for root, dirs, files in os.walk(translate_dir):
        for fname in files:
            if fname.endswith('_en.lstr'):
                lstr_path = os.path.join(root, fname)
                count = process_lstr_file(lstr_path, translate_dir, export_dir)
                total_applied += count
                if count > 0:
                    total_files += 1

    print(f"Translations applied: {total_applied} entries in {total_files} files")


if __name__ == '__main__':
    main()
