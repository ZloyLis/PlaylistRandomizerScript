import re
import random
from pathlib import Path


def rename_tracks_uniquely(folder_path: str = None):
    current_folder = Path(folder_path) if folder_path else Path(__file__).parent
    print(f"Работаю в папке: {current_folder}")

    if not current_folder.exists():
        print(f"❌ Папка не существует: {current_folder}")
        return

    pattern1 = re.compile(
        r'^(\d{1,3})\s+(.+?)\s*-\s*(.+?\.[^.]+)$',
        re.IGNORECASE
    )

    pattern2 = re.compile(
        r'^(\d{1,3})\s+(.+?)$',
        re.IGNORECASE
    )

    pattern3 = re.compile(
        r'^(\d{4,})\s+(.+?)\s*-\s*(.+?\.[^.]+)$',
        re.IGNORECASE
    )

    files_to_rename = []

    for item in current_folder.iterdir():
        if item.is_file():
            name = item.name
            match1 = pattern1.match(name)
            match2 = pattern2.match(name)
            match3 = pattern3.match(name)

            if match1:
                artist = match1.group(2)
                title_with_ext = match1.group(3)
                files_to_rename.append((item, artist, title_with_ext))
            elif match2:
                artist_and_title = match2.group(2)
                if '.' in artist_and_title and artist_and_title.rsplit('.', 1)[1].lower() in ['mp3', 'flac', 'wav', 'aac', 'ogg', 'wma']:
                    artist = artist_and_title.rsplit('.', 1)[0]
                    title_with_ext = artist_and_title
                else:
                    artist = artist_and_title
                    title_with_ext = artist_and_title
                files_to_rename.append((item, artist, title_with_ext))
            elif match3:
                artist = match3.group(2)
                title_with_ext = match3.group(3)
                files_to_rename.append((item, artist, title_with_ext))

    if not files_to_rename:
        print("❌ Нет файлов, подходящих под шаблон.")
        print('Ожидаемые форматы:')
        print('  1. "01 Исполнитель - Название.mp3"')
        print('  2. "02 7Б Осень Минус"')
        print('  3. "71896 Исполнитель - Название.mp3" (уже переименованные)')
        return

    print(f"✅ Найдено подходящих файлов: {len(files_to_rename)}")

    unique_numbers = random.sample(range(1, 100000), len(files_to_rename))

    renamed_count = 0
    for i, (file, artist, title_with_ext) in enumerate(files_to_rename):
        new_number = unique_numbers[i]
        new_name = f"{new_number} {artist} - {title_with_ext}"
        new_path = current_folder / new_name

        try:
            file.rename(new_path)
            print(f"→ {file.name} → {new_name}")
            renamed_count += 1
        except Exception as e:
            print(f"❌ Ошибка с {file.name}: {type(e).__name__}: {e}")

    print(f"\n✅ Итого: переименовано {renamed_count} из {len(files_to_rename)} файлов")


if __name__ == "__main__":
    rename_tracks_uniquely("")  # или None, если хочешь использовать папку со скриптом