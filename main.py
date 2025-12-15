import re
import random
import os
import sys
from pathlib import Path
from typing import List, Tuple, Set, Optional

AUDIO_EXTENSIONS = {'mp3', 'flac', 'wav', 'aac', 'ogg', 'wma'}
MIN_NUMBER = 1
MAX_NUMBER = 99999

PATTERN_WITH_DASH = re.compile(
    r'^(\d{1,3})\s+(.+?)\s*-\s*(.+?\.[^.]+)$',
    re.IGNORECASE
)

PATTERN_SIMPLE = re.compile(
    r'^(\d{1,3})\s+(.+?)$',
    re.IGNORECASE
)

PATTERN_ALREADY_RENAMED = re.compile(
    r'^(\d{4,})\s+(.+?)\s*-\s*(.+?\.[^.]+)$',
    re.IGNORECASE
)

PATTERN_WITH_DASH_ANY_NUMBER = re.compile(
    r'^(\d+)\s+(.+?)\s*-\s*(.+?\.[^.]+)$',
    re.IGNORECASE
)


def _extract_audio_info(filename: str) -> Optional[Tuple[str, str]]:
    match = PATTERN_WITH_DASH.match(filename)
    if match:
        return match.group(2), match.group(3)

    match = PATTERN_ALREADY_RENAMED.match(filename)
    if match:
        return match.group(2), match.group(3)

    match = PATTERN_WITH_DASH_ANY_NUMBER.match(filename)
    if match:
        return match.group(2), match.group(3)

    match = PATTERN_SIMPLE.match(filename)
    if match:
        artist_and_title = match.group(2)
        if '.' in artist_and_title:
            ext = artist_and_title.rsplit('.', 1)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                artist = artist_and_title.rsplit('.', 1)[0]
                return artist, artist_and_title
        return artist_and_title, artist_and_title

    return None


def _generate_unique_numbers(
        count: int,
        existing_numbers: Set[int],
        forbidden_per_file: List[Optional[int]]
) -> List[int]:
    base_available = set(range(MIN_NUMBER, MAX_NUMBER + 1)) - existing_numbers
    if len(base_available) < count:
        raise ValueError(
            f"Недостаточно доступных номеров. "
            f"Нужно: {count}, доступно: {len(base_available)}"
        )
    unique_numbers = []
    used_numbers = set()

    for i, forbidden_number in enumerate(forbidden_per_file):
        available_for_this = base_available - used_numbers
        if forbidden_number is not None:
            available_for_this.discard(forbidden_number)
        if not available_for_this:
            raise ValueError(
                f"Недостаточно доступных номеров для файла {i + 1}. "
                f"Запрещен номер: {forbidden_number}"
            )
        chosen = random.choice(list(available_for_this))
        unique_numbers.append(chosen)
        used_numbers.add(chosen)
    assert len(unique_numbers) == len(set(unique_numbers)), "Обнаружены дубликаты в сгенерированных номерах!"

    return unique_numbers


def _extract_current_number(filename: str) -> Optional[int]:
    match = re.match(r'^(\d+)', filename)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


def _get_existing_numbers(folder: Path, exclude_files: List[Path] = None) -> Set[int]:
    exclude_set = set(exclude_files) if exclude_files else set()
    existing_numbers = set()
    for item in folder.iterdir():
        if item.is_file() and item not in exclude_set:
            number = _extract_current_number(item.name)
            if number is not None:
                existing_numbers.add(number)
    return existing_numbers


def rename_tracks_uniquely(folder_path: str = None):
    if folder_path:
        current_folder = Path(folder_path)
    else:
        if getattr(sys, 'frozen', False):
            current_folder = Path(sys.executable).parent
        else:
            current_folder = Path(__file__).parent
    print(f"Работаю в папке: {current_folder}")

    if not current_folder.exists():
        print(f"❌ Папка не существует: {current_folder}")
        return

    if not current_folder.is_dir():
        print(f"❌ Указанный путь не является папкой: {current_folder}")
        return

    files_to_rename: List[Tuple[Path, str, str, Optional[int]]] = []

    for item in current_folder.iterdir():
        if item.is_file():
            audio_info = _extract_audio_info(item.name)
            if audio_info:
                artist, title_with_ext = audio_info
                current_number = _extract_current_number(item.name)
                files_to_rename.append((item, artist, title_with_ext, current_number))

    if not files_to_rename:
        print("❌ Нет файлов, подходящих под шаблон.")
        print('Ожидаемые форматы:')
        print('  1. "01 Исполнитель - Название.mp3"')
        print('  2. "02 7Б Осень Минус"')
        print('  3. "71896 Исполнитель - Название.mp3" (уже переименованные)')
        return

    print(f"✅ Найдено подходящих файлов: {len(files_to_rename)}")

    files_to_rename_paths = [f[0] for f in files_to_rename]
    existing_numbers = _get_existing_numbers(current_folder, exclude_files=files_to_rename_paths)

    if existing_numbers:
        print(f"ℹ️  Исключено {len(existing_numbers)} существующих номеров других файлов")

    forbidden_per_file = [f[3] for f in files_to_rename]

    try:
        unique_numbers = _generate_unique_numbers(
            len(files_to_rename),
            existing_numbers,
            forbidden_per_file
        )
    except ValueError as e:
        print(f"❌ Ошибка генерации номеров: {e}")
        return

    if len(unique_numbers) != len(set(unique_numbers)):
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Обнаружены дубликаты в сгенерированных номерах!")
        return

    for (file, artist, title_with_ext, old_number), new_number in zip(files_to_rename, unique_numbers):
        if old_number is not None and old_number == new_number:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Файл {file.name} получил тот же номер {new_number}!")
            return

    renamed_count = 0
    failed_files = []
    for (file, artist, title_with_ext, old_number), new_number in zip(files_to_rename, unique_numbers):
        new_name = f"{new_number} {artist} - {title_with_ext}"
        new_path = current_folder / new_name

        if new_path.exists() and new_path != file:
            print(f"⚠️  Пропущен {file.name}: файл {new_name} уже существует")
            failed_files.append(file.name)
            continue

        try:
            file.rename(new_path)
            old_info = f" (было: {old_number})" if old_number is not None else ""
            print(f"→ {file.name} → {new_name}{old_info}")
            renamed_count += 1
        except Exception as e:
            print(f"❌ Ошибка с {file.name}: {type(e).__name__}: {e}")
            failed_files.append(file.name)

    total_tracks = len(files_to_rename)
    errors_count = len(failed_files)

    print("\n===== Отчет =====")
    print(f"Всего треков в папке (по шаблону): {total_tracks}")
    print(f"Успешно переименовано: {renamed_count}")
    print(f"Ошибок при переименовании: {errors_count}")

    if failed_files:
        print("Файлы с ошибками:")
        for name in failed_files:
            print(f"  - {name}")


if __name__ == "__main__":
    try:
        rename_tracks_uniquely("")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 50)
    print("Нажмите Enter, чтобы закрыть окно...")

    if sys.platform == "win32":
        os.system("pause")
    else:
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass