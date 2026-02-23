<div align="center">

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/) [![Poetry](https://img.shields.io/badge/poetry-package%20manager-purple)](https://python-poetry.org/) [![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff) [![Type checked: mypy](https://img.shields.io/badge/types-mypy-blue)](https://github.com/python/mypy) [![Docker](https://img.shields.io/badge/docker-ready-2496ED)](https://www.docker.com/) [![Pydantic](https://img.shields.io/badge/pydantic-v2-red)](https://docs.pydantic.dev/) [![SQLAlchemy](https://img.shields.io/badge/sqlalchemy-2.0-orange)](https://www.sqlalchemy.org/) [![Pandas](https://img.shields.io/badge/pandas-2.0-darkblue)](https://pandas.pydata.org/) [![Plotly](https://img.shields.io/badge/plotly-6.0-blueviolet)](https://plotly.com/) [![Matplotlib](https://img.shields.io/badge/matplotlib-3.8-blue)](https://matplotlib.org/) [![Seaborn](https://img.shields.io/badge/seaborn-0.13-lightblue)](https://seaborn.pydata.org/) [![Scikit-learn](https://img.shields.io/badge/scikit--learn-1.3-orange)](https://scikit-learn.org/) [![Structlog](https://img.shields.io/badge/structlog-24.0-lightgrey)](https://www.structlog.org/) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen)](https://pre-commit.com/) [![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)

</div>

<div align="center">
  <a href="#english">🇬🇧 English</a> | <a href="#russian">🇷🇺 Русский</a>
</div>
<br>

---

<a id="english"></a>
<div align="center">

# 💰 Financial Data Analysis Pipeline

A production-ready ETL and analysis pipeline for financial transaction data. Built with clean architecture, type safety, and testability in mind.
</div>

---

## 📋 Table of Contents
- [Features](#features-english)
- [Quick Start](#quick-start-english)
- [Project Structure](#project-structure-english)
- [Configuration](#configuration-english)
- [Usage](#usage-english)
- [Output Structure](#output-structure-english)
- [Development](#development-english)
- [License](#license-english)

---

<a id="features-english"></a>
## ✨ Features

- **ETL Pipeline**: Extract from Excel/JSON, clean, validate, and load into SQLite
- **Data Cleaning**: Automatic validation and cleaning of:
  - Transaction IDs, dates, amounts
  - Client data (age, net worth, gender)
  - Handling of missing/invalid values
- **Analysis Suite**:
  - Top 5 services by order count
  - Revenue analysis by city, service, payment method
  - Client segmentation by net worth
  - Monthly trends and forecasting
- **Visualization**:
  - Static plots (Matplotlib/Seaborn)
  - Interactive HTML reports (Plotly)
  - Auto-generated Markdown summaries
  - [Visualization example REPORT.md](https://github.com/script-logic/etl-and-analysis-financial-data/blob/main/finance_analisys_report_example.pdf)
- **Reporting**:
  - Timestamped folders with complete report packages
- **Production Ready**:
  - Full type hints with mypy --strict
  - Comprehensive logging with structlog
  - Docker support




---

<a id="quick-start-english"></a>
## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Poetry
- Your data files (place them in data/):
  - `transactions_data.xlsx`
  - `clients_data.json`

### Installation

```bash
# Clone the repository
git clone https://github.com/script-logic/etl-and-analysis-financial-data.git
cd etl-and-analysis-financial-data

# Create .env file from example
cp .env.example .env

# Install with poetry
poetry install

```

### Run the pipeline

```bash
# Basic run
poetry run python run_pipeline.py

# With options
poetry run python run_pipeline.py --no-plots --forecast-months 3

# Using Docker
docker-compose up

# Using Makefile
make run
```

---

<a id="project-structure-english"></a>
## 📁 Project Structure

```
├── app/                                # Main application package
│   ├── application/                    # Use cases (business logic)
│   │   └── use_cases/
│   │       ├── analysis.py             # Analysis orchestration
│   │       └── warehouse.py            # ETL orchestration
│   ├── config/                         # Configuration
│   │   └── config.py                   # Pydantic settings
│   ├── domain/                         # Domain models
│   │   ├── entities/                   # Business entities
│   │   └── value_objects/              # Value objects
│   ├── infrastructure/                 # External concerns
│   │   ├── analysis/                   # Analysis & viz
│   │   ├── data_cleaning/              # Validation rules
│   │   ├── data_loading/               # Excel/JSON loaders
│   │   ├── database/                   # SQLAlchemy models
│   │   └── logger/                     # Structured logging
│   └── utils/                          # Helpers
├── reports/                            # Generated reports
├── data/                               # Data dir to place Excel/Json files
├── .env.example                        # Example environment
├── docker-compose.yml                  # Docker setup
├── pyproject.toml                      # Project metadata
└── run_pipeline.py                     # Entry point
```

---

<a id="configuration-english"></a>
## ⚙️ Configuration

Configure via `.env` file (copy from `.env.example`):

```env
# Data paths
DATA_PATHS__TRANSACTIONS_FILE=data/transactions_data.xlsx
DATA_PATHS__CLIENTS_FILE=data/clients_data.json
DATA_PATHS__DATABASE_FILE=warehouse.db
DATA_PATHS__REPORTS_DIR=reports

# Analysis parameters
ANALYSIS__TOP_SERVICES_LIMIT=5
ANALYSIS__FORECAST_MONTHS=1
ANALYSIS__MIN_MONTHS_FOR_FORECAST=3

# Logging
LOGGER__DEBUG=true
LOGGER__LOG_LEVEL=INFO
```

---

<a id="usage-english"></a>
## 🎯 Usage

### Command Line Options

```bash
python run_pipeline.py [OPTIONS]

Options:
  --no-plots              Skip generating visualizations
  --no-clear              Don't clear database (keep existing data)
  --clear-db              Clear database before loading
  --transactions PATH     Path to transactions Excel file
  --clients PATH          Path to clients JSON file
  --db PATH               Path to SQLite database
  --forecast-months N     Number of months to forecast (1-12)
  --min-months-forecast N Minimum months required for forecast
  --help                  Show this message
```

### Examples

```bash
# Full analysis with default settings
python run_pipeline.py

# Quick analysis without plots
python run_pipeline.py --no-plots

# Forecast for 3 months
python run_pipeline.py --forecast-months 3

# Force reload data
python run_pipeline.py --clear-db

# Custom file locations
python run_pipeline.py \
  --transactions ./my_data/transactions.xlsx \
  --clients ./my_data/clients.json \
  --db ./my_data/warehouse.db
```

---

<a id="output-structure-english"></a>
## 📊 Output Structure

Each run creates a timestamped report folder:

```
reports/
├── report_20260223_010453/
│   ├── REPORT.md                                  # Self-contained markdown report
│   └── report_metadata/
│       ├── analysis_results_20260223_010453.json  # Raw data
│       ├── analysis_report.html                   # Interactive Plotly report
│       ├── monthly_trend.png
│       ├── revenue_by_age.png
│       ├── revenue_by_service.png
│       └── transaction_distribution.png
└── report_20260223_020115/                        # Next run
    └── ...
```

### Report Contents

- **REPORT.md**: Complete analysis with embedded plots
- **JSON**: Raw numerical results for further processing
- **PNG**: Static visualizations
- **HTML**: Interactive dashboard

---

<a id="development-english"></a>
## 🛠 Development

### Setup

```bash
# Install dev dependencies
poetry install --with dev

# Install pre-commit hooks
pre-commit install

# Run linting
make lint
```

### Code Quality

- **Ruff**: Fast Python linter
- **mypy**: Strict type checking
- **pre-commit**: Automated checks

### Docker

```bash
# Build and run
docker-compose up

# Rebuild
docker-compose build --no-cache
```

---

<a id="license-english"></a>
## 📝 License

MIT License - feel free to use and modify.

---

<br>
<hr>
<br>

<a id="russian"></a>

<div align="center">
  <a href="#english">🇬🇧 English</a> | <a href="#russian">🇷🇺 Русский</a>
</div>
<div align="center">

# 💰 Конвейер анализа финансовых данных

ETL и аналитический конвейер для данных финансовых транзакций.
Разработан с  применением принйипов чистой архитектуры и типобезопасностью.

</div>

---

## 📋 Содержание
- [Возможности](#возможности-russian)
- [Быстрый старт](#быстрый-старт-russian)
- [Структура проекта](#структура-проекта-russian)
- [Конфигурация](#конфигурация-russian)
- [Использование](#использование-russian)
- [Структура отчётов](#структура-отчётов-russian)
- [Разработка](#разработка-russian)
- [Лицензия](#лицензия-russian)

---

<a id="возможности-russian"></a>
## ✨ Возможности

- **ETL конвейер**: Загрузка из Excel/JSON, очистка, валидация и сохранение в SQLite
- **Очистка данных**: Автоматическая валидация:
  - ID транзакций, даты, суммы
  - Данные клиентов (возраст, капитал, пол)
  - Обработка пропусков и ошибок
- **Аналитика**:
  - Топ-5 услуг по количеству заказов
  - Анализ выручки по городам, услугам, способам оплаты
  - Сегментация клиентов по уровню капитала
  - Месячные тренды и прогнозирование
- **Визуализация**:
  - Статические графики (Matplotlib/Seaborn)
  - Интерактивные HTML-отчёты (Plotly)
  - Авто-генерируемые Markdown сводки
  - [Пример визуализации REPORT.md](https://github.com/script-logic/etl-and-analysis-financial-data/blob/main/finance_analisys_report_example.pdf)
- **Отчётность**:
  - Папки с временными метками и полным комплектом отчётов
- **Готов к продакшену**:
  - Полная типизация (mypy --strict)
  - Структурированное логирование (structlog)
  - Поддержка Docker

---

<a id="быстрый-старт-russian"></a>
## 🚀 Быстрый старт

### Требования
- Python 3.11+
- Poetry
- Ваши файлы с данными (поместите в папку data/):
  - `transactions_data.xlsx`
  - `clients_data.json`

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/script-logic/etl-and-analysis-financial-data.git
cd etl-and-analysis-financial-data

# Создайте .env файл из .env.example
cp .env.example .env

# Установка с poetry
poetry install
```

### Запуск конвейера

```bash
# Базовый запуск
poetry run python run_pipeline.py

# С опциями
poetry run python run_pipeline.py --no-plots --forecast-months 3

# Через Docker
docker-compose up

# Через Makefile
make run
```

---

<a id="структура-проекта-russian"></a>
## 📁 Структура проекта

```
├── app/                                # Основной пакет приложения
│   ├── application/                    # Use cases (бизнес-логика)
│   │   └── use_cases/
│   │       ├── analysis.py             # Оркестрация анализа
│   │       └── warehouse.py            # Оркестрация ETL
│   ├── config/                         # Конфигурация
│   │   └── config.py                   # Pydantic настройки
│   ├── domain/                         # Доменные модели
│   │   ├── entities/                   # Бизнес-сущности
│   │   └── value_objects/              # Value objects
│   ├── infrastructure/                 # Внешние зависимости
│   │   ├── analysis/                   # Анализ и визуализация
│   │   ├── data_cleaning/              # Правила валидации
│   │   ├── data_loading/               # Загрузчики Excel/JSON
│   │   ├── database/                   # SQLAlchemy модели
│   │   └── logger/                     # Структурированное логирование
│   └── utils/                          # Вспомогательные утилиты
├── reports/                            # Сгенерированные отчёты
├── data/                               # Папка для размещения Excel/Json файлов
├── .env.example                        # Пример .env файла
├── docker-compose.yml                  # Docker настройки
├── pyproject.toml                      # Метаданные проекта
└── run_pipeline.py                     # Точка входа
```

---

<a id="конфигурация-russian"></a>
## ⚙️ Конфигурация

Настройка через `.env` файл (скопируйте из `.env.example`):

```env
# Пути к данным
DATA_PATHS__TRANSACTIONS_FILE=data/transactions_data.xlsx
DATA_PATHS__CLIENTS_FILE=data/clients_data.json
DATA_PATHS__DATABASE_FILE=warehouse.db
DATA_PATHS__REPORTS_DIR=reports

# Параметры анализа
ANALYSIS__TOP_SERVICES_LIMIT=5
ANALYSIS__FORECAST_MONTHS=1
ANALYSIS__MIN_MONTHS_FOR_FORECAST=3

# Логирование
LOGGER__DEBUG=true
LOGGER__LOG_LEVEL=INFO
```

---

<a id="использование-russian"></a>
## 🎯 Использование

### Опции командной строки

```bash
python run_pipeline.py [ОПЦИИ]

Опции:
  --no-plots              Не генерировать визуализации
  --no-clear              Не очищать БД (сохранить существующие данные)
  --clear-db              Очистить БД перед загрузкой
  --transactions PATH     Путь к Excel файлу с транзакциями
  --clients PATH          Путь к JSON файлу с клиентами
  --db PATH               Путь к SQLite базе данных
  --forecast-months N     Количество месяцев для прогноза (1-12)
  --min-months-forecast N Минимум месяцев данных для прогноза
  --help                  Показать справку
```

### Примеры

```bash
# Полный анализ с настройками по умолчанию
python run_pipeline.py

# Быстрый анализ без графиков
python run_pipeline.py --no-plots

# Прогноз на 3 месяца
python run_pipeline.py --forecast-months 3

# Принудительная перезагрузка данных
python run_pipeline.py --clear-db

# Свои пути к файлам
python run_pipeline.py \
  --transactions ./my_data/transactions.xlsx \
  --clients ./my_data/clients.json \
  --db ./my_data/warehouse.db
```

---

<a id="структура-отчётов-russian"></a>
## 📊 Структура отчётов

Каждый запуск создаёт папку с временной меткой:

```
reports/
├── report_20260223_010453/
│   ├── REPORT.md                                  # Самодостаточный Markdown отчёт
│   └── report_metadata/
│       ├── analysis_results_20260223_010453.json  # Сырые данные
│       ├── analysis_report.html                   # Интерактивный Plotly отчёт
│       ├── monthly_trend.png
│       ├── revenue_by_age.png
│       ├── revenue_by_service.png
│       └── transaction_distribution.png
└── report_20260223_020115/                        # Следующий запуск
    └── ...
```

### Содержимое отчёта

- **REPORT.md**: Полный анализ со встроенными графиками
- **JSON**: Числовые результаты для дальнейшей обработки
- **PNG**: Статические визуализации
- **HTML**: Интерактивная панель управления

---

<a id="разработка-russian"></a>
## 🛠 Разработка

### Настройка

```bash
# Установка dev зависимостей
poetry install --with dev

# Установка pre-commit хуков
pre-commit install

# Запуск линтинга
make lint
```

### Качество кода

- **Ruff**: Быстрый линтер Python
- **mypy**: Строгая проверка типов
- **pre-commit**: Автоматические проверки

### Docker

```bash
# Сборка и запуск
docker-compose up

# Пересборка
docker-compose build --no-cache
```

---

<a id="лицензия-russian"></a>
## 📝 Лицензия

MIT License - свободно используйте и модифицируйте.

---
