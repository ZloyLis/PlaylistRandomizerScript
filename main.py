import re
import random
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Optional, Tuple

AUDIO_EXTENSIONS = {'mp3', 'flac', 'wav', 'aac', 'ogg', 'wma'}
MIN_NUMBER = 1
MAX_NUMBER = 99999

PATTERN_WITH_DASH = re.compile(
    r'^(\d{1,3})\s+(.+?)\s*-\s*(.+?\.[^.]+)$',
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

PATTERN_SIMPLE = re.compile(
    r'^(\d{1,3})\s+(.+?)$',
    re.IGNORECASE
)

PATTERN_NUMBER_PREFIX = re.compile(r'^(\d+)')


@dataclass
class AudioFileInfo:
    path: Path
    artist: str
    title_with_ext: str
    current_number: Optional[int] = None


def _extract_audio_info(filename: str) -> Optional[Tuple[str, str]]:
    for pattern in (PATTERN_WITH_DASH, PATTERN_ALREADY_RENAMED, PATTERN_WITH_DASH_ANY_NUMBER):
        match = pattern.match(filename)
        if match:
            return match.group(2), match.group(3)

    match = PATTERN_SIMPLE.match(filename)
    if match:
        artist_and_title = match.group(2)
        if '.' in artist_and_title:
            parts = artist_and_title.rsplit('.', 1)
            if len(parts) == 2:
                ext = parts[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    return parts[0], artist_and_title
        return artist_and_title, artist_and_title

    return None


def _generate_unique_numbers(
        count: int,
        existing_numbers: Set[int],
        forbidden_per_file: List[Optional[int]]
) -> List[int]:
    total_range = MAX_NUMBER - MIN_NUMBER + 1
    available_count = total_range - len(existing_numbers)

    if available_count < count:
        raise ValueError(
            f"Недостаточно доступных номеров. "
            f"Нужно: {count}, доступно: {available_count}"
        )

    all_forbidden = existing_numbers.copy()
    for forbidden in forbidden_per_file:
        if forbidden is not None:
            all_forbidden.add(forbidden)

    unique_numbers = []
    used_numbers = set()
    max_attempts = available_count * 2

    for i, forbidden_number in enumerate(forbidden_per_file):
        attempts = 0
        while attempts < max_attempts:
            candidate = random.randint(MIN_NUMBER, MAX_NUMBER)

            if (candidate not in all_forbidden and
                    candidate not in used_numbers and
                    candidate != forbidden_number):
                unique_numbers.append(candidate)
                used_numbers.add(candidate)
                break
            attempts += 1
        else:
            raise ValueError(
                f"Недостаточно доступных номеров для файла {i + 1}. "
                f"Запрещен номер: {forbidden_number}"
            )

    return unique_numbers


def _extract_current_number(filename: str) -> Optional[int]:
    match = PATTERN_NUMBER_PREFIX.match(filename)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, OverflowError):
            pass
    return None


def _get_existing_numbers(folder: Path, exclude_files: Optional[List[Path]] = None) -> Set[int]:
    exclude_set = set(exclude_files) if exclude_files else set()
    existing_numbers = set()

    for item in folder.iterdir():
        if item.is_file() and item not in exclude_set:
            number = _extract_current_number(item.name)
            if number is not None:
                existing_numbers.add(number)

    return existing_numbers


def rename_tracks_uniquely(folder_path: Optional[str] = None) -> None:
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

    files_to_rename: List[AudioFileInfo] = []

    for item in current_folder.iterdir():
        if item.is_file():
            audio_info = _extract_audio_info(item.name)
            if audio_info:
                artist, title_with_ext = audio_info
                current_number = _extract_current_number(item.name)
                files_to_rename.append(
                    AudioFileInfo(item, artist, title_with_ext, current_number)
                )

    if not files_to_rename:
        print("❌ Нет файлов, подходящих под шаблон.")
        print('Ожидаемые форматы:')
        print('  1. "01 Исполнитель - Название.mp3"')
        print('  2. "02 7Б Осень Минус"')
        print('  3. "71896 Исполнитель - Название.mp3" (уже переименованные)')
        return

    print(f"✅ Найдено подходящих файлов: {len(files_to_rename)}")

    files_to_rename_paths = [f.path for f in files_to_rename]
    existing_numbers = _get_existing_numbers(current_folder, exclude_files=files_to_rename_paths)

    if existing_numbers:
        print(f"ℹ️  Исключено {len(existing_numbers)} существующих номеров других файлов")

    forbidden_per_file = [f.current_number for f in files_to_rename]

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

    for file_info, new_number in zip(files_to_rename, unique_numbers):
        if file_info.current_number is not None and file_info.current_number == new_number:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Файл {file_info.path.name} получил тот же номер {new_number}!")
            return

    renamed_count = 0
    failed_files: List[str] = []

    for file_info, new_number in zip(files_to_rename, unique_numbers):
        new_name = f"{new_number} {file_info.artist} - {file_info.title_with_ext}"
        new_path = current_folder / new_name

        if new_path.exists() and new_path != file_info.path:
            print(f"⚠️  Пропущен {file_info.path.name}: файл {new_name} уже существует")
            failed_files.append(file_info.path.name)
            continue

        try:
            file_info.path.rename(new_path)
            old_info = f" (было: {file_info.current_number})" if file_info.current_number is not None else ""
            print(f"→ {file_info.path.name} → {new_name}{old_info}")
            renamed_count += 1
        except OSError as e:
            print(f"❌ Ошибка с {file_info.path.name}: {type(e).__name__}: {e}")
            failed_files.append(file_info.path.name)
        except Exception as e:
            print(f"❌ Неожиданная ошибка с {file_info.path.name}: {type(e).__name__}: {e}")
            failed_files.append(file_info.path.name)

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