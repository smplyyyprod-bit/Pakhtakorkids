# Руководство по развертыванию

## Требования к хост-системе

- **ОС**: Linux (Ubuntu 20.04+ рекомендуется), macOS, или Windows с WSL2
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Свободное место**: Минимум 5GB для базы данных и логов
- **Память**: Минимум 2GB RAM (4GB рекомендуется)
- **Интернет**: Для загрузки Docker образов и Telegram API

## Пошаговое развертывание

### Шаг 1: Подготовка сервера

```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установите Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Добавьте текущего пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### Шаг 2: Клонирование репозитория

```bash
cd /opt  # Или другая директория для приложений
git clone https://github.com/your-org/pakhtakorkids.git
cd pakhtakorkids
```

### Шаг 3: Получение Telegram Bot Token

1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

### Шаг 4: Конфигурация

```bash
# Создайте файл .env
cp .env.example .env

# Отредактируйте файл с использованием вашего редактора
nano .env

# Обязательные параметры:
TELEGRAM_BOT_TOKEN=<ваш_токен_от_BotFather>
TELEGRAM_ADMIN_IDS=<ваш_telegram_id>,<другие_админы>
DATABASE_URL=postgresql://coaching_user:secure_password@postgres:5432/coaching_management
```

**Как узнать свой Telegram ID:**
1. Найдите @userinfobot в Telegram
2. Отправьте любое сообщение
3. Бот ответит с вашим ID

### Шаг 5: Запуск приложения

```bash
# Запустите контейнеры
docker-compose up -d

# Проверьте статус контейнеров
docker-compose ps

# Посмотрите логи
docker-compose logs -f bot
```

### Шаг 6: Проверка

1. Откройте Telegram
2. Найдите своего бота (по имени, которое вы установили в BotFather)
3. Отправьте `/start`
4. Вы должны увидеть главное меню с вашей ролью

## Управление приложением

### Остановка приложения

```bash
docker-compose down
```

### Перезагрузка

```bash
docker-compose restart bot
```

### Просмотр логов

```bash
# Последние 100 строк логов
docker-compose logs -n 100 bot

# В режиме реального времени
docker-compose logs -f bot

# Только ошибки
docker-compose logs bot | grep ERROR
```

### Резервная копия базы данных

```bash
# Создайте резервную копию
docker-compose exec postgres pg_dump -U coaching_user coaching_management > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из резервной копии
docker-compose exec -T postgres psql -U coaching_user coaching_management < backup_файл.sql
```

### Очистка данных

```bash
# Остановите контейнеры
docker-compose down -v

# Удалит БД и Redis (ОСТОРОЖНО!)
```

## Производственное развертывание

### На облачных сервисах

#### AWS EC2

```bash
# Запустите EC2 инстанс (Ubuntu 20.04 or 22.04)
# Откройте порты 22 (SSH) и 8443 (для webhook, если нужен)

# Подключитесь и следуйте инструкциям выше
ssh -i your-key.pem ubuntu@your-instance-ip
```

#### DigitalOcean App Platform

1. Создайте новый App
2. Выберите "Docker" как источник
3. Загрузите docker-compose.yml
4. Настройте переменные окружения
5. Разверните

#### Heroku

```bash
# Установите Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Создайте приложение
heroku create your-app-name

# Добавьте переменные окружения
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set DATABASE_URL=postgresql://...
heroku config:set REDIS_URL=redis://...

# Разверните
git push heroku main
```

## Мониторинг

### Проверка здоровья

```bash
# Проверьте, что все контейнеры запущены и здоровы
docker-compose ps

# Проверьте, что бот отвечает
docker-compose exec bot python -c "from app.core.config import get_settings; print(get_settings().telegram_bot_token[:10] + '***')"
```

### Мониторинг ресурсов

```bash
# Просмотрите использование ресурсов
docker stats

# Или более детально
docker-compose stats
```

### Обновление приложения

```bash
# Получите последние изменения
git pull origin main

# Перестройте образ (если изменились зависимости)
docker-compose build --no-cache

# Перезагрузите приложение
docker-compose restart bot

# Проверьте логи
docker-compose logs -f bot
```

## Обновление базы данных

### Запуск миграций

```bash
# При первом запуске миграции запускаются автоматически
# Для ручного запуска (если нужно):
docker-compose exec bot alembic upgrade head
```

### Создание новой миграции

```bash
# Отредактируйте модели в app/domain/models/

# Создайте миграцию
docker-compose exec bot alembic revision --autogenerate -m "Описание изменений"

# Примените миграцию
docker-compose exec bot alembic upgrade head
```

## Устранение неполадок

### Контейнер не запускается

```bash
# Проверьте логи
docker-compose logs bot

# Проверьте, что файл .env существует и правильный
cat .env

# Проверьте, что PostgreSQL запущен
docker-compose ps postgres
```

### Ошибка подключения к БД

```bash
# Убедитесь, что PostgreSQL здоров
docker-compose exec postgres pg_isready -U coaching_user

# Проверьте переменные окружения
echo $DATABASE_URL

# Перезагрузите PostgreSQL
docker-compose restart postgres
```

### Бот не отвечает

```bash
# Проверьте токен в .env
grep TELEGRAM_BOT_TOKEN .env

# Убедитесь, что токен верный (спросите BotFather)
# Перезагрузите бот
docker-compose restart bot

# Проверьте логи для ошибок
docker-compose logs -f bot
```

### Высокое использование памяти

```bash
# Проверьте использование памяти каждым контейнером
docker stats

# Если Redis использует много памяти:
docker-compose exec redis redis-cli INFO memory

# Очистите кэш если нужно
docker-compose exec redis redis-cli FLUSHDB
```

## Безопасность

### Изменение пароля PostgreSQL

```bash
# Подключитесь к PostgreSQL
docker-compose exec postgres psql -U coaching_user -d coaching_management

# Внутри psql:
ALTER USER coaching_user WITH PASSWORD 'new_secure_password';
\q

# Обновите .env
nano .env
# Обновите DATABASE_URL

# Перезагрузите бот
docker-compose restart bot
```

### Включение SSL для PostgreSQL

1. Создайте сертификаты
2. Скопируйте их в контейнер PostgreSQL
3. Обновите конфигурацию PostgreSQL
4. Перезагрузите контейнер

### Резервное копирование логов

```bash
# Создайте скрипт для ежедневной архивации логов
cat > /etc/cron.daily/backup-logs << 'EOF'
#!/bin/bash
cd /opt/pakhtakorkids
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
# Удалите старые резервные копии (старше 30 дней)
find . -name "logs_backup_*.tar.gz" -mtime +30 -delete
EOF

chmod +x /etc/cron.daily/backup-logs
```

## Масштабирование

### Увеличение размера БД

```bash
# PostgreSQL автоматически растет, но вы можете заранее выделить место:
docker-compose down
# Отредактируйте docker-compose.yml, увеличив объем диска

# Или используйте внешнее хранилище (AWS EBS, GCP Persistent Disk)
```

### Горизонтальное масштабирование (несколько экземпляров бота)

В настоящее время архитектура поддерживает один экземпляр бота. Для масштабирования на несколько экземпляров потребуются изменения:
- Переместите FSM state в Redis вместо памяти
- Используйте Redis для кэширования
- Используйте очередь задач (Celery) для длительных операций

## Получение помощи

- Проверьте логи: `docker-compose logs bot`
- Посмотрите конфиг: `cat .env`
- Проверьте документацию: `README.md`
