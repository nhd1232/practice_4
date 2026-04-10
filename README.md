# Демонстрационный API-сервис для тестирования

Этот проект содержит небольшой сервис на `FastAPI`, подготовленный для доклада по автоматизации API-тестирования с использованием `Postman/Newman`, генерации отчётов и запуска в CI/CD.

## Что демонстрирует сервис

- REST-эндпоинты с базовыми CRUD-операциями для небольшого каталога товаров
- импорт тестовых данных из `JSON` и `CSV`
- сброс состояния приложения к заранее подготовленному набору данных
- сравнение текущего состояния API с эталонным выходным файлом
- воспроизводимое поведение, удобное для автоматизированного тестирования

## Структура проекта

- `app/main.py` - API-эндпоинты
- `app/store.py` - in-memory хранилище и логика сравнения с эталоном
- `data/seed_items.json` - начальный набор данных
- `data/import_items.json` - пример входного JSON-файла
- `data/import_items.csv` - пример входного CSV-файла
- `data/references/*.json` - эталонные выходные данные для проверки

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск API

```bash
uvicorn app.main:app --reload
```

После запуска открыть:

- `http://127.0.0.1:8000/docs` - Swagger UI
- `http://127.0.0.1:8000/health` - быстрая проверка доступности сервиса

## Типовой демонстрационный сценарий

1. `POST /admin/reset` - восстановить исходное состояние
2. `GET /items` - показать стартовый каталог
3. `POST /items/import/json` с файлом `data/import_items.json`
4. `POST /admin/compare/expected_after_json_import.json`
5. `POST /items/import/csv` с файлом `data/import_items.csv`
6. `POST /admin/compare/expected_after_csv_import.json`

## Коллекция Postman

Готовые к импорту файлы находятся в папке `postman/`:

- `postman/Demo_API_Testing.postman_collection.json`
- `postman/Demo_API_Testing.postman_environment.json`

### Как запускать в Postman

1. Запустить API командой `uvicorn app.main:app --reload`
2. Импортировать оба файла Postman
3. Выбрать окружение `Demo API Local Environment`
4. Запустить запросы коллекции по порядку

В коллекции уже есть проверки для:

- HTTP-статуса `200`
- размера исходного набора данных
- успешного импорта JSON
- успешного импорта CSV
- совпадения с эталонными файлами
- обработки негативных сценариев (`404`, `400`, `422`)

## Newman

Установить Node.js, затем поставить зависимости для Newman:

```bash
npm install
```

Запустить API в одном терминале, а Newman во втором:

```bash
npm run test:api
```

Эта команда запускает Postman-коллекцию из командной строки и формирует следующие отчёты:

- `reports/newman-report.html`
- `reports/newman-report.xml`

PowerShell-скрипт, который вызывается через `npm`, расположен в `scripts/run-newman.ps1`.

## CI/CD

В проекте есть workflow для GitHub Actions: `.github/workflows/api-tests.yml`.

Этот workflow автоматически:

- устанавливает Python и Node.js
- устанавливает зависимости проекта
- запускает FastAPI-сервис
- ждёт, пока станет доступен эндпоинт `/health`
- запускает коллекцию Newman
- загружает отчёты из `reports/` как build artifacts

## Примеры эндпоинтов

- `GET /items`
- `GET /items/{item_id}`
- `POST /items`
- `DELETE /items/{item_id}`
- `POST /items/import/json`
- `POST /items/import/csv`
- `POST /admin/reset`
- `GET /admin/references`
- `POST /admin/compare/{reference_name}`
