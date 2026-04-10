from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Annotated, Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.store import ItemStore


app = FastAPI(
    title="Демонстрационный API для автоматизированного тестирования",
    description=(
        "Небольшой REST API, созданный для демонстрации API-тестирования "
        "с помощью Postman/Newman, генерации отчётов и запуска в CI/CD."
    ),
    version="1.0.0",
)

store = ItemStore()


class ItemIn(BaseModel):
    id: int | None = Field(default=None, description="Идентификатор товара. Генерируется автоматически, если не указан.")
    name: str = Field(..., min_length=1, description="Название товара.")
    category: str = Field(..., min_length=1, description="Категория товара.")
    price: float = Field(..., ge=0, description="Цена товара в условных единицах.")
    quantity: int = Field(..., ge=0, description="Доступное количество товара.")


class ImportResult(BaseModel):
    source_format: str
    items_loaded: int
    replace_existing: bool
    current_total: int
    file_name: str


@app.on_event("startup")
def load_seed_data() -> None:
    # При старте сервиса поднимаем предсказуемое исходное состояние для demo-сценариев
    store.reset_from_seed()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Демонстрационный API-сервис запущен.",
        "docs": "/docs",
        "purpose": "Используйте этот сервис для демонстрации автоматизированного API-тестирования с Postman/Newman.",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items")
def list_items() -> dict[str, Any]:
    items = store.list_items()
    return {"count": len(items), "items": items}


@app.get("/items/{item_id}")
def get_item(item_id: int) -> dict[str, Any]:
    item = store.get_item(item_id)

    if item is None:
        raise HTTPException(status_code=404, detail=f"Товар с id={item_id} не найден.")

    return item


@app.post("/items", status_code=201)
def create_item(item: ItemIn) -> dict[str, Any]:
    try:
        created_item = store.create_item(item.model_dump())
    except ValueError as error:
        # Ошибки валидации бизнес-правил переводим в HTTP-ответ, удобный для API-тестов
        raise HTTPException(status_code=400, detail=str(error)) from error

    return created_item


@app.delete("/items/{item_id}")
def delete_item(item_id: int) -> dict[str, Any]:
    deleted_item = store.delete_item(item_id)

    if deleted_item is None:
        raise HTTPException(status_code=404, detail=f"Товар с id={item_id} не найден.")

    return {
        "message": "Товар успешно удалён.",
        "deleted_item": deleted_item,
    }


@app.post("/items/import/json", response_model=ImportResult)
async def import_items_from_json(
    file: Annotated[UploadFile, File(...)],
    replace_existing: bool = False,
) -> ImportResult:
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Пожалуйста, загрузите файл в формате JSON.")

    try:
        payload = json.loads((await file.read()).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail=f"Некорректный JSON-файл: {error}") from error

    # Поддерживаем оба варианта: список записей напрямую и объект с полем "items"
    records = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    if not isinstance(records, list):
        raise HTTPException(status_code=400, detail="JSON должен содержать список товаров.")

    try:
        loaded = store.replace_with_records(records) if replace_existing else store.append_records(records)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=f"Некорректные данные товара: {error}") from error

    return ImportResult(
        source_format="json",
        items_loaded=loaded,
        replace_existing=replace_existing,
        current_total=len(store.list_items()),
        file_name=file.filename,
    )


@app.post("/items/import/csv", response_model=ImportResult)
async def import_items_from_csv(
    file: Annotated[UploadFile, File(...)],
    replace_existing: bool = False,
) -> ImportResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Пожалуйста, загрузите файл в формате CSV.")

    try:
        content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail=f"Некорректная кодировка CSV-файла: {error}") from error

    # DictReader сразу приводит CSV к словарям, совместимым с нормализацией в ItemStore
    reader = csv.DictReader(StringIO(content))
    records = list(reader)
    if not records:
        raise HTTPException(status_code=400, detail="CSV-файл пуст.")

    try:
        loaded = store.replace_with_records(records) if replace_existing else store.append_records(records)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=f"Некорректные данные товара: {error}") from error

    return ImportResult(
        source_format="csv",
        items_loaded=loaded,
        replace_existing=replace_existing,
        current_total=len(store.list_items()),
        file_name=file.filename,
    )


@app.post("/admin/reset")
def reset_to_seed() -> dict[str, Any]:
    # Административный маршрут нужен для повторяемых прогонов: перед тестом возвращаем сервис к эталону
    return store.reset_from_seed()


@app.get("/admin/references")
def list_references() -> dict[str, list[str]]:
    # Отдельная точка просмотра упрощает проверку того, какие эталоны доступны для сравнения
    return {"reference_files": store.list_reference_files()}


@app.post("/admin/compare/{reference_name}")
def compare_with_reference(reference_name: str) -> dict[str, Any]:
    try:
        return store.compare_with_reference(reference_name)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"Эталонный файл '{reference_name}' не найден.") from error
    except ValueError as error:
        # Сюда попадают ошибки формата эталона или структуры данных, а не ошибки транспортного уровня
        raise HTTPException(status_code=400, detail=str(error)) from error
