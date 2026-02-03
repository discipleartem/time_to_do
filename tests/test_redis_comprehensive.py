"""
Комплексные тесты для Redis модуля
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from redis.asyncio import Redis

from app.core.redis import RedisService, close_redis, get_redis, init_redis


class TestRedisService:
    """Тесты для RedisService"""

    @pytest.fixture
    def mock_redis(self):
        """Мок Redis клиента"""
        mock = AsyncMock(spec=Redis)
        # Настраиваем все методы как корутины с правильными возвращаемыми значениями
        mock.set = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.expire = AsyncMock(return_value=1)
        mock.incr = AsyncMock(return_value=5)
        mock.lpush = AsyncMock(return_value=3)
        mock.rpop = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def redis_service(self, mock_redis):
        """Создание RedisService с мок Redis"""
        return RedisService(mock_redis)

    # Тесты базовых операций
    @pytest.mark.asyncio
    async def test_set_success(self, redis_service, mock_redis):
        """Тест успешного сохранения значения"""
        mock_redis.set.return_value = True

        result = await redis_service.set("test_key", {"value": "test"})

        assert result is True
        mock_redis.set.assert_called_once_with(
            "test_key", json.dumps({"value": "test"}, default=str), ex=None
        )

    @pytest.mark.asyncio
    async def test_set_with_expire(self, redis_service, mock_redis):
        """Тест сохранения значения с временем жизни"""
        mock_redis.set.return_value = True

        result = await redis_service.set("test_key", "test_value", expire=60)

        assert result is True
        mock_redis.set.assert_called_once_with(
            "test_key", json.dumps("test_value", default=str), ex=60
        )

    @pytest.mark.asyncio
    async def test_set_error(self, redis_service, mock_redis):
        """Тест сохранения значения с ошибкой"""
        mock_redis.set.side_effect = Exception("Redis error")

        result = await redis_service.set("test_key", "test_value")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_success(self, redis_service, mock_redis):
        """Тест успешного получения значения"""
        mock_redis.get.return_value = json.dumps({"value": "test"})

        result = await redis_service.get("test_key")

        assert result == {"value": "test"}
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_not_found(self, redis_service, mock_redis):
        """Тест получения несуществующего значения"""
        mock_redis.get.return_value = None

        result = await redis_service.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_error(self, redis_service, mock_redis):
        """Тест получения значения с ошибкой"""
        mock_redis.get.side_effect = Exception("Redis error")

        result = await redis_service.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_success(self, redis_service, mock_redis):
        """Тест успешного удаления ключа"""
        mock_redis.delete.return_value = 1

        result = await redis_service.delete("test_key")

        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_not_found(self, redis_service, mock_redis):
        """Тест удаления несуществующего ключа"""
        mock_redis.delete.return_value = 0

        result = await redis_service.delete("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_error(self, redis_service, mock_redis):
        """Тест удаления с ошибкой"""
        mock_redis.delete.side_effect = Exception("Redis error")

        result = await redis_service.delete("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, redis_service, mock_redis):
        """Тест проверки существования ключа - существует"""
        mock_redis.exists.return_value = 1

        result = await redis_service.exists("test_key")

        assert result is True
        mock_redis.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_false(self, redis_service, mock_redis):
        """Тест проверки существования ключа - не существует"""
        mock_redis.exists.return_value = 0

        result = await redis_service.exists("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_error(self, redis_service, mock_redis):
        """Тест проверки существования с ошибкой"""
        mock_redis.exists.side_effect = Exception("Redis error")

        result = await redis_service.exists("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_expire_success(self, redis_service, mock_redis):
        """Тест успешной установки времени жизни"""
        mock_redis.expire.return_value = 1

        result = await redis_service.expire("test_key", 60)

        assert result is True
        mock_redis.expire.assert_called_once_with("test_key", 60)

    @pytest.mark.asyncio
    async def test_expire_not_found(self, redis_service, mock_redis):
        """Тест установки времени жизни для несуществующего ключа"""
        mock_redis.expire.return_value = 0

        result = await redis_service.expire("test_key", 60)

        assert result is False

    @pytest.mark.asyncio
    async def test_expire_error(self, redis_service, mock_redis):
        """Тест установки времени жизни с ошибкой"""
        mock_redis.expire.side_effect = Exception("Redis error")

        result = await redis_service.expire("test_key", 60)

        assert result is False

    @pytest.mark.asyncio
    async def test_incr_success(self, redis_service, mock_redis):
        """Тест успешного инкремента счетчика"""
        mock_redis.incr.return_value = 5

        result = await redis_service.incr("counter")

        assert result == 5
        mock_redis.incr.assert_called_once_with("counter")

    @pytest.mark.asyncio
    async def test_incr_error(self, redis_service, mock_redis):
        """Тест инкремента счетчика с ошибкой"""
        mock_redis.incr.side_effect = Exception("Redis error")

        result = await redis_service.incr("counter")

        assert result is None

    @pytest.mark.asyncio
    async def test_lpush_success(self, redis_service, mock_redis):
        """Тест успешного добавления в список"""
        mock_redis.lpush.return_value = 3

        result = await redis_service.lpush("mylist", "item1", "item2", {"data": "test"})

        assert result == 3
        mock_redis.lpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_lpush_error(self, redis_service, mock_redis):
        """Тест добавления в список с ошибкой"""
        mock_redis.lpush.side_effect = Exception("Redis error")

        result = await redis_service.lpush("mylist", "item1")

        assert result is None

    @pytest.mark.asyncio
    async def test_rpop_success(self, redis_service, mock_redis):
        """Тест успешного получения из списка"""
        mock_redis.rpop.return_value = json.dumps({"data": "test"})

        result = await redis_service.rpop("mylist")

        assert result == {"data": "test"}
        mock_redis.rpop.assert_called_once_with("mylist")

    @pytest.mark.asyncio
    async def test_rpop_empty(self, redis_service, mock_redis):
        """Тест получения из пустого списка"""
        mock_redis.rpop.return_value = None

        result = await redis_service.rpop("mylist")

        assert result is None

    @pytest.mark.asyncio
    async def test_rpop_error(self, redis_service, mock_redis):
        """Тест получения из списка с ошибкой"""
        mock_redis.rpop.side_effect = Exception("Redis error")

        result = await redis_service.rpop("mylist")

        assert result is None

    # Тесты сериализации/десериализации
    @pytest.mark.asyncio
    async def test_set_complex_object(self, redis_service, mock_redis):
        """Тест сохранения сложного объекта"""
        complex_data = {
            "user": {"id": 123, "name": "Test"},
            "items": [1, 2, 3],
            "nested": {"key": "value"},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        mock_redis.set.return_value = True

        result = await redis_service.set("complex_key", complex_data)

        assert result is True
        # Проверяем, что данные были сериализованы
        call_args = mock_redis.set.call_args
        serialized_data = call_args[0][1]
        parsed_data = json.loads(serialized_data)
        assert parsed_data == complex_data

    @pytest.mark.asyncio
    async def test_get_complex_object(self, redis_service, mock_redis):
        """Тест получения сложного объекта"""
        complex_data = {
            "user": {"id": 123, "name": "Test"},
            "items": [1, 2, 3],
        }
        mock_redis.get.return_value = json.dumps(complex_data)

        result = await redis_service.get("complex_key")

        assert result == complex_data

    @pytest.mark.asyncio
    async def test_set_none_value(self, redis_service, mock_redis):
        """Тест сохранения None значения"""
        mock_redis.set.return_value = True

        result = await redis_service.set("null_key", None)

        assert result is True
        call_args = mock_redis.set.call_args
        serialized_data = call_args[0][1]
        assert serialized_data == "null"

    @pytest.mark.asyncio
    async def test_get_none_value(self, redis_service, mock_redis):
        """Тест получения None значения"""
        mock_redis.get.return_value = "null"

        result = await redis_service.get("null_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_unserializable_object(self, redis_service, mock_redis):
        """Тест сохранения объекта, который нельзя сериализовать"""

        class UnserializableObject:
            def __str__(self):
                return "unserializable"

        obj = UnserializableObject()
        mock_redis.set.return_value = True

        result = await redis_service.set("obj_key", obj)

        assert result is True
        call_args = mock_redis.set.call_args
        serialized_data = call_args[0][1]
        # Объект должен быть преобразован в строку через default=str
        assert serialized_data == '"unserializable"'

    # Тесты списков
    @pytest.mark.asyncio
    async def test_list_operations(self, redis_service, mock_redis):
        """Тест операций со списками"""
        # Добавляем элементы
        mock_redis.lpush.return_value = 2
        await redis_service.lpush("mylist", "first", "second")

        # Получаем элементы
        mock_redis.rpop.return_value = json.dumps("first")
        result = await redis_service.rpop("mylist")

        assert result == "first"

    @pytest.mark.asyncio
    async def test_list_with_complex_objects(self, redis_service, mock_redis):
        """Тест списков со сложными объектами"""
        items = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        mock_redis.lpush.return_value = 2

        result = await redis_service.lpush("items_list", *items)

        assert result == 2
        # Проверяем, что элементы были сериализованы
        call_args = mock_redis.lpush.call_args
        serialized_items = call_args[0][1:]  # Пропускаем ключ
        assert len(serialized_items) == 2
        assert (
            json.loads(serialized_items[0]) == items[0]
        )  # Первый элемент в списке аргументов
        assert json.loads(serialized_items[1]) == items[1]

    # Тесты счетчиков
    @pytest.mark.asyncio
    async def test_counter_operations(self, redis_service, mock_redis):
        """Тест операций со счетчиками"""
        mock_redis.incr.side_effect = [1, 2, 3]

        # Первый инкремент
        result1 = await redis_service.incr("counter")
        assert result1 == 1

        # Второй инкремент
        result2 = await redis_service.incr("counter")
        assert result2 == 2

        # Третий инкремент
        result3 = await redis_service.incr("counter")
        assert result3 == 3

    # Тесты обработки ошибок
    @pytest.mark.asyncio
    async def test_json_serialization_error(self, redis_service, mock_redis):
        """Тест ошибки сериализации JSON"""

        # Создаем объект, который вызовет ошибку при сериализации
        class BadObject:
            def __str__(self):
                raise ValueError("Cannot serialize")

        mock_redis.set.return_value = True

        result = await redis_service.set("bad_key", BadObject())

        assert result is False

    @pytest.mark.asyncio
    async def test_json_deserialization_error(self, redis_service, mock_redis):
        """Тест ошибки десериализации JSON"""
        mock_redis.get.return_value = "invalid json"

        result = await redis_service.get("bad_key")

        assert result is None

    # Тесты граничных случаев
    @pytest.mark.asyncio
    async def test_empty_key(self, redis_service, mock_redis):
        """Тест операций с пустым ключом"""
        mock_redis.get.return_value = None

        result = await redis_service.get("")

        assert result is None
        mock_redis.get.assert_called_once_with("")

    @pytest.mark.asyncio
    async def test_very_large_value(self, redis_service, mock_redis):
        """Тест сохранения очень большого значения"""
        large_value = "x" * 1000000  # 1MB строка
        mock_redis.set.return_value = True

        result = await redis_service.set("large_key", large_value)

        assert result is True

    @pytest.mark.asyncio
    async def test_unicode_values(self, redis_service, mock_redis):
        """Тест сохранения Unicode значений"""
        unicode_value = {"message": "Привет мир! 🌍", "emoji": "🚀🎉"}
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps(unicode_value)

        # Сохранение
        set_result = await redis_service.set("unicode_key", unicode_value)
        assert set_result is True

        # Получение
        get_result = await redis_service.get("unicode_key")
        assert get_result == unicode_value

    @pytest.mark.asyncio
    async def test_numeric_values(self, redis_service, mock_redis):
        """Тест сохранения числовых значений"""
        numeric_values = [42, 3.14, -1, 0]
        mock_redis.set.return_value = True

        for value in numeric_values:
            key = f"num_{type(value).__name__}"
            # Сохранение
            set_result = await redis_service.set(key, value)
            assert set_result is True

            # Получение
            mock_redis.get.return_value = json.dumps(value)
            get_result = await redis_service.get(key)
            assert get_result == value

    @pytest.mark.asyncio
    async def test_boolean_values(self, redis_service, mock_redis):
        """Тест сохранения булевых значений"""
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps(True)

        # Сохранение True
        set_result = await redis_service.set("bool_true", True)
        assert set_result is True

        # Получение True
        get_result = await redis_service.get("bool_true")
        assert get_result is True


class TestRedisModule:
    """Тесты для модуля Redis"""

    @pytest.mark.asyncio
    async def test_get_redis(self):
        """Тест получения Redis клиента"""
        with patch("app.core.redis.redis_client") as mock_client:
            result = await get_redis()
            assert result == mock_client

    @pytest.mark.asyncio
    async def test_init_redis_success(self):
        """Тест успешной инициализации Redis"""
        with patch("app.core.redis.redis_client") as mock_client:
            mock_client.ping.return_value = True

            # Перехватываем print
            with patch("builtins.print") as mock_print:
                await init_redis()

            mock_client.ping.assert_called_once()
            mock_print.assert_called_once_with("✅ Redis подключен успешно")

    @pytest.mark.asyncio
    async def test_init_redis_error(self):
        """Тест ошибки инициализации Redis"""
        with patch("app.core.redis.redis_client") as mock_client:
            mock_client.ping.side_effect = Exception("Connection failed")

            with patch("builtins.print") as mock_print:
                await init_redis()

            mock_client.ping.assert_called_once()
            mock_print.assert_called_once()
            # Проверяем, что в сообщении об ошибке есть текст
            error_message = mock_print.call_args[0][0]
            assert "❌ Ошибка подключения к Redis" in error_message

    @pytest.mark.asyncio
    async def test_close_redis(self):
        """Тест закрытия соединения с Redis"""
        with patch("app.core.redis.redis_client") as mock_client:
            await close_redis()
            mock_client.close.assert_called_once()


class TestRedisIntegration:
    """Интеграционные тесты для Redis (с моками)"""

    @pytest.fixture
    def mock_redis(self):
        """Мок Redis клиента для интеграционных тестов"""
        mock = AsyncMock(spec=Redis)
        mock.set = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.expire = AsyncMock(return_value=1)
        mock.incr = AsyncMock(return_value=1)
        mock.lpush = AsyncMock(return_value=1)
        mock.rpop = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def redis_service(self, mock_redis):
        """Создание RedisService с мок Redis"""
        return RedisService(mock_redis)

    @pytest.mark.asyncio
    async def test_cache_workflow(self, redis_service, mock_redis):
        """Тест рабочего процесса кэширования"""
        # Настройка моков
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None  # Изначально нет в кэше

        # Попытка получить из кэша (промах)
        cached_data = await redis_service.get("user:123")
        assert cached_data is None

        # Сохранение в кэш
        user_data = {"id": 123, "name": "Test User", "email": "test@example.com"}
        await redis_service.set("user:123", user_data, expire=300)

        # Повторное получение из кэша
        mock_redis.get.return_value = json.dumps(user_data)
        cached_data = await redis_service.get("user:123")

        assert cached_data == user_data

    @pytest.mark.asyncio
    async def test_rate_limiting_workflow(self, redis_service, mock_redis):
        """Тест рабочего процесса rate limiting"""
        # Настройка моков
        mock_redis.incr.side_effect = [1, 2, 3, 4, 5, 6]  # 6 запросов
        mock_redis.expire.return_value = True

        # Симулируем 6 запросов
        for _i in range(6):
            count = await redis_service.incr("rate_limit:user:123")
            if count == 1:
                # Устанавливаем время жизни для первого запроса
                await redis_service.expire("rate_limit:user:123", 3600)

        # Проверяем счетчик
        assert count == 6

    @pytest.mark.asyncio
    async def test_session_workflow(self, redis_service, mock_redis):
        """Тест рабочего процесса сессий"""
        # Настройка моков
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps({"user_id": 123, "active": True})
        mock_redis.exists.return_value = 1
        mock_redis.delete.return_value = 1

        # Создание сессии
        session_data = {
            "user_id": 123,
            "active": True,
            "created_at": "2024-01-01T00:00:00Z",
        }
        await redis_service.set("session:abc123", session_data, expire=7200)

        # Проверка сессии
        session_exists = await redis_service.exists("session:abc123")
        assert session_exists is True

        # Получение данных сессии
        session = await redis_service.get("session:abc123")
        assert session["user_id"] == 123

        # Удаление сессии
        deleted = await redis_service.delete("session:abc123")
        assert deleted is True

    @pytest.mark.asyncio
    async def test_queue_workflow(self, redis_service, mock_redis):
        """Тест рабочего процесса очереди"""
        # Настройка моков
        mock_redis.lpush.return_value = 1
        mock_redis.rpop.side_effect = [
            json.dumps({"task": "send_email", "data": {"to": "user@example.com"}}),
            json.dumps({"task": "process_image", "data": {"image_id": 123}}),
            None,  # Очередь пуста
        ]

        # Добавление задач в очередь
        task1 = {"task": "send_email", "data": {"to": "user@example.com"}}
        task2 = {"task": "process_image", "data": {"image_id": 123}}

        await redis_service.lpush("task_queue", task1, task2)

        # Обработка задач
        processed_tasks = []
        while True:
            task = await redis_service.rpop("task_queue")
            if task is None:
                break
            processed_tasks.append(task)

        assert len(processed_tasks) == 2
        assert processed_tasks[0]["task"] == "send_email"
        assert processed_tasks[1]["task"] == "process_image"

    @pytest.mark.asyncio
    async def test_error_recovery(self, redis_service, mock_redis):
        """Тест восстановления после ошибок"""
        # Настройка моков - сначала ошибка, потом успех
        mock_redis.get.side_effect = [
            Exception("Redis down"),
            json.dumps({"data": "recovered"}),
        ]

        # Первая попытка - ошибка
        result1 = await redis_service.get("test_key")
        assert result1 is None

        # Вторая попытка - успех
        result2 = await redis_service.get("test_key")
        assert result2 == {"data": "recovered"}

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, redis_service, mock_redis):
        """Тест одновременных операций"""
        import asyncio

        # Настройка моков
        mock_redis.set.return_value = True

        # Для get возвращаем разные значения в зависимости от ключа
        def get_side_effect(key):
            # Извлекаем worker_id и item_id из ключа
            parts = key.split("_")
            worker_id = int(parts[1])
            item_id = int(parts[3])
            return json.dumps({"worker": worker_id, "item": item_id})

        mock_redis.get.side_effect = get_side_effect

        async def worker(worker_id: int):
            # Каждый воркер выполняет несколько операций
            for i in range(5):
                await redis_service.set(
                    f"worker_{worker_id}_item_{i}", {"worker": worker_id, "item": i}
                )
                result = await redis_service.get(f"worker_{worker_id}_item_{i}")
                assert result["worker"] == worker_id
                assert result["item"] == i

        # Запускаем несколько воркеров одновременно
        tasks = [worker(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Проверяем, что все операции были выполнены
        total_calls = mock_redis.set.call_count + mock_redis.get.call_count
        assert total_calls == 30  # 3 воркера * 5 операций * 2 (set + get)
