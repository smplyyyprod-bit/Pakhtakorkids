# Архитектура системы

## 🏗️ Общее описание

Система построена на **Clean Architecture** с использованием следующих слоев:

```
┌─────────────────────────────────────────────────────────┐
│         Presentation Layer (Telegram Bot)               │
│  ├─ Handlers (обработчики команд)                       │
│  ├─ Keyboards (UI элементы)                             │
│  └─ Utils (FSM, форматирование текста)                 │
├─────────────────────────────────────────────────────────┤
│         Application Layer (Use Cases & DTO)             │
│  └─ Бизнес-логика высокого уровня                      │
├─────────────────────────────────────────────────────────┤
│         Domain Layer (Business Logic & Entities)        │
│  ├─ Models (SQLAlchemy ORM)                            │
│  └─ Value Objects                                       │
├─────────────────────────────────────────────────────────┤
│      Infrastructure Layer (Implementation Details)      │
│  ├─ Repositories (доступ к данным)                      │
│  ├─ Services (бизнес-операции)                          │
│  ├─ Database (конфигурация БД)                          │
│  └─ Scheduler (планировщик задач)                       │
├─────────────────────────────────────────────────────────┤
│           Core Layer (Configuration)                    │
│  ├─ Config (переменные окружения)                       │
│  ├─ Logger (логирование)                                │
│  └─ Constants                                           │
└─────────────────────────────────────────────────────────┘
```

## 📦 Компоненты системы

### 1. Telegram Bot (Presentation Layer)

**Файлы:**
- `app/presentation/telegram/bot.py` - Основное приложение бота
- `app/presentation/telegram/handlers/` - Обработчики команд

**Обработчики:**
- **StartHandler** - Инициализация и главное меню
- **AdminHandler** - Функции администратора
- **ManagerHandler** - Функции менеджера
- **ReportHandler** - Заполнение ежедневных отчетов

**Клавиатуры:**
- Inline кнопки для всех операций
- Pagination для больших списков
- Быстрые селекторы времени

### 2. Сервисный слой (Services)

**UserService**
```python
- get_or_create_user(telegram_id, full_name, role)
- get_user(telegram_id)
- get_admin_users()
- get_manager_users()
- update_user_branch(user_id, branch_id)
- deactivate_user(user_id)
- activate_user(user_id)
```

**BranchService**
```python
- create_branch(name, description, address)
- get_branch(branch_id)
- get_all_branches()
- update_branch(branch_id, ...)
- deactivate_branch(branch_id)
```

**CoachService**
```python
- create_coach(unique_id, full_name, position, team, branch_id)
- get_coach(coach_id)
- get_branch_coaches(branch_id)
- update_coach(coach_id, ...)
- deactivate_coach(coach_id)
- move_coach_to_branch(coach_id, branch_id)
```

**DailyReportService**
```python
- create_or_update_report(coach_id, branch_id, report_date, **kwargs)
- calculate_worked_hours(start_time, end_time)
- get_report(coach_id, report_date)
- auto_create_daily_reports(branch_id, report_date)
- get_completion_stats(branch_id, report_date)
- get_monthly_stats(coach_id, year, month)
```

**StatisticsService**
```python
- get_company_overview()
- get_coach_rankings(year, month)
- get_attendance_trends(year, month)
```

**ExportService**
```python
- export_to_excel(coach_id, year, month)
- export_to_pdf(coach_id, year, month)
```

### 3. Слой доступа к данным (Repository Pattern)

**BaseRepository** - Базовый класс для всех репозиториев
```python
- create(obj)
- get_by_id(id)
- get_all(skip, limit)
- update(obj)
- delete(id)
- count()
```

**Специализированные репозитории:**
- UserRepository
- BranchRepository
- CoachRepository
- DailyReportRepository
- EvaluationCriteriaRepository

### 4. Модели домена (Domain Models)

```
User
├── id
├── telegram_id (уникальный)
├── full_name
├── role (ADMIN, MANAGER, COACH)
├── is_active
└── branch_id (FK)

Branch
├── id
├── name (уникальный)
├── description
├── address
└── is_active

Coach
├── id
├── unique_id (уникальный)
├── full_name
├── position
├── team
├── branch_id (FK)
└── is_active

DailyReport
├── id
├── coach_id (FK)
├── branch_id (FK)
├── report_date
├── upper_uniform (YES, NO, NO_DATA)
├── lower_uniform (YES, NO, NO_DATA)
├── start_time
├── end_time
├── worked_hours
├── attendance (PRESENT, SICK, VACATION, ABSENT, NOT_FILLED)
├── late_arrival_minutes
├── early_departure_minutes
├── notes
├── admin_comments
├── is_completed
├── completed_by_user_id
├── created_at
└── updated_at

EvaluationCriteria
├── id
├── name (уникальный)
├── description
├── field_type (text, number, select, boolean)
├── is_active
└── order

CriterionValue
├── id
├── criterion_id (FK)
├── value
├── label
└── order

AuditLog
├── id
├── user_id
├── action
├── entity_type
├── entity_id
├── changes (JSON)
└── created_at
```

## 🔄 Потоки данных

### Ежедневный рабочий процесс администратора

```
1. Администратор отправляет /start
   ↓
2. Система создает или находит пользователя (User)
   ↓
3. Администратор выбирает отделение (Branch)
   ↓
4. Система показывает список активных тренеров (Coach)
   ↓
5. Администратор выбирает тренера
   ↓
6. Система получает или создает DailyReport для сегодня
   ↓
7. Администратор заполняет форму (FSM с состояниями)
   ↓
8. Система проверяет и сохраняет данные
   ↓
9. Система показывает следующего тренера
   ↓
10. Повторить для всех тренеров в отделении
```

### Автоматическое создание отчетов

```
Каждый вечер (23:30 по умолчанию):
   ↓
APScheduler запускает job
   ↓
Получить все отделения
   ↓
Для каждого отделения:
   ├─ Получить всех активных тренеров
   └─ Создать DailyReport с default значениями
   ↓
Логировать количество созданных отчетов
```

### Расчет статистики

```
Менеджер запрашивает месячный отчет для тренера
   ↓
Получить все DailyReport за месяц
   ↓
Итерировать по отчетам и рассчитать:
   ├─ Отработано часов (сумма)
   ├─ Отработано дней (count where worked_hours > 0)
   ├─ Опозданий (count где late_arrival_minutes > 0)
   ├─ Всего минут опоздания (sum late_arrival_minutes)
   ├─ Дни болезни (count где attendance == SICK)
   ├─ Дни отпуска (count где attendance == VACATION)
   ├─ Нарушения формы (count где uniform != YES)
   └─ Отсутствия без объяснения (count где attendance == ABSENT)
   ↓
Вернуть статистику
```

## 🗄️ Модель базы данных

### ERD (Entity Relationship Diagram)

```
┌─────────────────┐         ┌──────────────────┐
│      User       │         │     Branch       │
├─────────────────┤         ├──────────────────┤
│ id (PK)         │         │ id (PK)          │
│ telegram_id (U) │────┐    │ name (U)         │
│ full_name       │    │    │ description      │
│ role            │    │    │ address          │
│ is_active       │    │    │ is_active        │
│ branch_id (FK)  │────┼────├─ (back_populates │
│ created_at      │    │    │  users)          │
│ updated_at      │    │    │ created_at       │
└─────────────────┘    │    │ updated_at       │
                       │    └──────────────────┘
                       │            ▲
                       │            │
                       │       ┌────┴─────────┐
                       │       │              │
                    ┌──┴──────────┐    ┌──────┴────────┐
                    │    Coach    │    │  DailyReport  │
                    ├─────────────┤    ├───────────────┤
                    │ id (PK)     │    │ id (PK)       │
                    │ unique_id(U)│    │ coach_id (FK) │
                    │ full_name   │────┤ branch_id(FK) │
                    │ position    │    │ report_date   │
                    │ team        │    │ upper_uniform │
                    │ branch_id(FK)    │ lower_uniform │
                    │ is_active   │    │ start_time    │
                    │ created_at  │    │ end_time      │
                    │ updated_at  │    │ worked_hours  │
                    └─────────────┘    │ attendance    │
                                       │ late_arrival  │
                                       │ early_depart  │
                                       │ notes         │
                                       │ admin_comm.   │
                                       │ is_completed  │
                                       │ completed_by  │
                                       │ created_at    │
                                       │ updated_at    │
                                       └───────────────┘

┌──────────────────────┐
│ EvaluationCriteria   │
├──────────────────────┤
│ id (PK)              │
│ name (U)             │
│ description          │
│ field_type           │
│ is_active            │
│ order                │
│ created_at           │
│ updated_at           │
└──────────────────────┘
         ▲
         │ (has)
         │
┌────────┴────────────┐
│  CriterionValue     │
├─────────────────────┤
│ id (PK)             │
│ criterion_id (FK)   │
│ value               │
│ label               │
│ order               │
│ created_at          │
│ updated_at          │
└─────────────────────┘

┌──────────────────────┐
│    AuditLog          │
├──────────────────────┤
│ id (PK)              │
│ user_id              │
│ action               │
│ entity_type          │
│ entity_id            │
│ changes (JSON)       │
│ created_at           │
└──────────────────────┘
```

## 🔐 Управление доступом (RBAC)

### Роли и разрешения

```
ADMIN
├─ Заполнение ежедневных отчетов
├─ Редактирование своих отчетов
├─ Просмотр отчетов в своем отделении
└─ (Без доступа к аналитике компании)

MANAGER
├─ Просмотр всех тренеров
├─ Просмотр месячных отчетов для всех
├─ Просмотр панели управления
├─ Просмотр рейтингов
├─ Экспорт отчетов
├─ Добавление/редактирование/удаление тренеров
├─ Добавление/редактирование отделений
└─ Управление критериями оценки

COACH
└─ Просмотр только своего профиля
```

## 🔄 Конечные автоматы (FSM)

### ReportFormStates (Заполнение отчета)

```
┌─────────────────┐
│  selecting_     │
│   branch        │
└────────┬────────┘
         │ (branch selected)
         ↓
┌─────────────────┐
│  selecting_     │
│   coach         │
└────────┬────────┘
         │ (coach selected)
         ↓
┌─────────────────┐
│ filling_        │
│ attendance      │
└────────┬────────┘
         │ (attendance selected)
         ↓
┌─────────────────────┐
│ filling_upper_      │
│ uniform             │
└────────┬────────────┘
         │ (uniform selected)
         ↓
┌─────────────────────┐
│ filling_lower_      │
│ uniform             │
└────────┬────────────┘
         │ (uniform selected)
         ↓
┌─────────────────────┐
│ filling_start_time  │
└────────┬────────────┘
         │ (time selected)
         ↓
┌─────────────────────┐
│ filling_end_time    │
└────────┬────────────┘
         │ (time selected)
         ↓
┌─────────────────────┐
│ filling_late_       │
│ minutes             │
└────────┬────────────┘
         │ (minutes entered)
         ↓
┌──────────────────────┐
│ filling_early_       │
│ minutes              │
└────────┬─────────────┘
         │ (minutes entered)
         ↓
┌──────────────────────┐
│ filling_notes        │
└────────┬─────────────┘
         │ (notes entered)
         ↓
┌──────────────────────┐
│ reviewing_report     │
└────────┬─────────────┘
    ┌────┴────┬─────────┐
    ↓         ↓         ↓
[Save]   [Edit]   [Cancel]
    │         │         │
    │         │         └─────────────────┐
    │         │                           │
    └─────────┼───────────────────────────┘
              │
         [next coach]
```

## 📊 Диаграмма последовательности (Заполнение отчета)

```
Admin      Bot        Database    Service
  │         │             │           │
  ├─ start ─→│             │           │
  │         │─ check user ─→│          │
  │         │←─ user found ─│          │
  │         │─ show menu   →│
  │         │←──────────────│
  │
  ├─ select branch ─→│
  │         │─ get branches ──→│
  │         │←─ branches list  │
  │         │─ show coaches   →│
  │
  ├─ select coach ─→│
  │         │─ get/create report ─→│
  │         │←─ report created     │
  │         │─ show form          →│
  │
  ├─ fill attendance ─→│
  │         │─ update state ──→│
  │         │─ show next field →│
  │
  ├─ fill uniform ─→│
  │         │(similar flow)
  │
  ├─ fill times ─→│
  │         │─ calculate hours ──→│
  │         │←─ hours calculated  │
  │
  ├─ save report ─→│
  │         │─ save to DB ──→│
  │         │←─ saved ────────│
  │         │─ show confirmation →│
  │
  ├─ show next ─→│
  │         │─ get next coach ──→│
  │         │←─ coach found      │
  │         │─ show form        →│
```

## 🚀 Масштабируемость

### Текущая архитектура
- ✅ Поддерживает 50-500 тренеров
- ✅ Поддерживает 1-10 отделений
- ✅ Один экземпляр бота

### Для масштабирования на тысячи тренеров

1. **Использовать Redis для FSM вместо памяти**
   ```python
   # Вместо MemoryStorage
   from aiogram.fsm.storage.redis import RedisStorage
   storage = RedisStorage(redis=redis_client)
   ```

2. **Кэширование часто используемых данных**
   ```python
   # Кэшировать список тренеров, критерии оценки
   cache.set('coaches:branch:1', coaches, ttl=3600)
   ```

3. **Очереди задач для длительных операций**
   ```python
   # Используйте Celery для асинхронных операций
   @shared_task
   def export_reports_task(coach_id, year, month):
       # Длительный экспорт
       pass
   ```

4. **Горизонтальное масштабирование бота**
   ```yaml
   # docker-compose.yml
   services:
     bot:
       deploy:
         replicas: 3  # 3 экземпляра бота
       # Используйте webhook вместо polling
   ```

## 🔄 Интеграции будущего

### REST API (Планируется)
```python
# FastAPI приложение
app/presentation/api/
├── endpoints/
│   ├── coaches.py
│   ├── reports.py
│   ├── statistics.py
│   └── users.py
├── middlewares/
│   └── auth.py
└── schemas/
    ├── coach.py
    ├── report.py
    └── user.py
```

### Веб-панель (Планируется)
```
frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── stores/
└── public/
```

### Мобильное приложение (Планируется)
- Flutter приложение для iOS/Android
- Доступ к API через REST

---

**Версия архитектуры:** 1.0.0  
**Последнее обновление:** 2026-08-04
