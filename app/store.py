from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REFERENCES_DIR = DATA_DIR / "references"


class ItemStore:
    def __init__(self) -> None:
        # in-memory хранилище:
        self._items: dict[int, dict[str, Any]] = {}

    def reset_from_seed(self, filename: str = "seed_items.json") -> dict[str, Any]:
        # Seed-файл задаёт базовое состояние, от которого стартуют позитивные сценарии и сравнение с эталоном
        records = self._read_json_file(DATA_DIR / filename)
        imported = self.replace_with_records(records)
        return {
            "message": "Исходные данные успешно загружены.",
            "source_file": filename,
            "items_loaded": imported,
        }

    def list_items(self) -> list[dict[str, Any]]:
        return [deepcopy(self._items[item_id]) for item_id in sorted(self._items)]

    def get_item(self, item_id: int) -> dict[str, Any] | None:
        item = self._items.get(item_id)
        return deepcopy(item) if item else None

    def create_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = self._normalize_item(payload)

        if item["id"] in self._items:
            raise ValueError(f"Товар с id={item['id']} уже существует.")

        self._items[item["id"]] = item
        return deepcopy(item)

    def delete_item(self, item_id: int) -> dict[str, Any] | None:
        item = self._items.pop(item_id, None)
        return deepcopy(item) if item else None

    def append_records(self, records: list[dict[str, Any]]) -> int:
        imported = 0

        for record in records:
            item = self._normalize_item(record)
            # При пакетном импорте запись с тем же id переопределяется последним значением из входных данных
            self._items[item["id"]] = item
            imported += 1

        return imported

    def replace_with_records(self, records: list[dict[str, Any]]) -> int:
        self._items.clear()
        return self.append_records(records)

    def compare_with_reference(self, reference_name: str) -> dict[str, Any]:
        reference_path = REFERENCES_DIR / reference_name
        expected_items = self._read_json_file(reference_path)
        actual_items = self.list_items()

        matches = actual_items == expected_items
        differences: list[dict[str, Any]] = []

        # Сначала фиксируем точечные расхождения по позициям, затем отдельно проверяем размер наборов
        for index, (actual, expected) in enumerate(zip(actual_items, expected_items), start=1):
            if actual != expected:
                differences.append(
                    {
                        "position": index,
                        "expected": expected,
                        "actual": actual,
                    }
                )

        if len(actual_items) != len(expected_items):
            differences.append(
                {
                    "position": "size",
                    "expected_count": len(expected_items),
                    "actual_count": len(actual_items),
                }
            )

        return {
            "reference_file": reference_name,
            "matches": matches,
            "actual_count": len(actual_items),
            "expected_count": len(expected_items),
            "differences": differences,
        }

    def list_reference_files(self) -> list[str]:
        return sorted(path.name for path in REFERENCES_DIR.glob("*.json"))

    def _normalize_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        item_id = payload.get("id")
        if item_id in (None, ""):
            # Если id отсутствует, генерируем его на стороне сервиса для ручного создания записи
            item_id = self._next_id()

        # Приводим данные из JSON и CSV к единому внутреннему формату перед сохранением и сравнением
        item = {
            "id": int(item_id),
            "name": str(payload["name"]).strip(),
            "category": str(payload["category"]).strip(),
            "price": float(payload["price"]),
            "quantity": int(payload["quantity"]),
        }

        if item["price"] < 0:
            raise ValueError("Цена не может быть отрицательной.")

        if item["quantity"] < 0:
            raise ValueError("Количество не может быть отрицательным.")

        return item

    def _next_id(self) -> int:
        # Новый id всегда больше максимального уже загруженного значения
        return max(self._items, default=0) + 1

    @staticmethod
    def _read_json_file(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        # Разрешаем хранить данные либо как список, либо как объект-обёртку с полем "items"
        if isinstance(payload, dict) and "items" in payload:
            payload = payload["items"]

        if not isinstance(payload, list):
            raise ValueError("JSON-файл должен содержать список товаров или поле 'items'.")

        return payload
