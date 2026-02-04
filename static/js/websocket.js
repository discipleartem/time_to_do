/**
 * WebSocket клиент для real-time обновлений
 */

class WebSocketClient {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnected = false;
        this.connectionId = null;
        this.eventListeners = new Map();
        this.token = null;
    }

    /**
     * Установка токена аутентификации
     * @param {string} token - JWT токен
     */
    setToken(token) {
        this.token = token;
    }

    /**
     * Подключение к WebSocket
     * @param {string} url - URL WebSocket сервера
     */
    connect(url = null) {
        if (this.isConnected) {
            console.log('WebSocket уже подключен');
            return;
        }

        const wsUrl = url || `ws://localhost:8000/api/v1/ws`;
        const urlWithToken = this.token ? `${wsUrl}?token=${this.token}` : wsUrl;

        console.log('Подключение к WebSocket:', urlWithToken);

        try {
            this.ws = new WebSocket(urlWithToken);

            this.ws.onopen = (event) => {
                console.log('WebSocket подключен');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.emit('connected', event);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('WebSocket сообщение:', data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Ошибка парсинга WebSocket сообщения:', error);
                }
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket отключен:', event.code, event.reason);
                this.isConnected = false;
                this.connectionId = null;
                this.emit('disconnected', event);

                // Попытка переподключения
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.scheduleReconnect();
                }
            };

            this.ws.onerror = (event) => {
                console.error('WebSocket ошибка:', event);
                this.emit('error', event);
            };

        } catch (error) {
            console.error('Ошибка создания WebSocket:', error);
            this.emit('error', error);
        }
    }

    /**
     * Отключение от WebSocket
     */
    disconnect() {
        if (this.ws) {
            this.ws.close(1000, 'Клиент отключился');
            this.ws = null;
        }
        this.isConnected = false;
        this.connectionId = null;
        this.reconnectAttempts = this.maxReconnectAttempts; // Предотвращаем переподключение
    }

    /**
     * Планирование переподключения
     */
    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Попытка переподключения ${this.reconnectAttempts}/${this.maxReconnectAttempts} через ${delay}мс`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    /**
     * Обработка входящего сообщения
     * @param {Object} data - Данные сообщения
     */
    handleMessage(data) {
        // Установка connection_id из приветственного сообщения
        if (data.event_type === 'USER_ONLINE' || data.event_type === 'PING') {
            if (data.data.connection_id) {
                this.connectionId = data.data.connection_id;
            }
        }

        // Обработка PONG
        if (data.event_type === 'PONG') {
            this.emit('pong', data);
            return;
        }

        // Обработка ошибок
        if (data.event_type === 'ERROR') {
            this.emit('error', data);
            return;
        }

        // Обработка уведомлений
        if (data.event_type === 'NOTIFICATION') {
            this.emit('notification', data);
            return;
        }

        // Обработка событий задач
        if (data.event_type.startsWith('task_')) {
            this.emit('task', data);
            return;
        }

        // Обработка событий комментариев
        if (data.event_type.startsWith('comment_')) {
            this.emit('comment', data);
            return;
        }

        // Обработка событий проектов
        if (data.event_type.startsWith('project_')) {
            this.emit('project', data);
            return;
        }

        // Обработка событий спринтов
        if (data.event_type.startsWith('sprint_')) {
            this.emit('sprint', data);
            return;
        }

        // Обработка событий времени
        if (data.event_type.startsWith('timer_') || data.event_type.startsWith('time_')) {
            this.emit('time', data);
            return;
        }

        // Обработка событий пользователей
        if (data.event_type.startsWith('user_')) {
            this.emit('user', data);
            return;
        }

        // Общее событие
        this.emit('message', data);
    }

    /**
     * Отправка сообщения
     * @param {Object} data - Данные для отправки
     */
    send(data) {
        if (!this.isConnected || !this.ws) {
            console.error('WebSocket не подключен');
            return;
        }

        try {
            const message = JSON.stringify(data);
            this.ws.send(message);
            console.log('WebSocket отправлено:', data);
        } catch (error) {
            console.error('Ошибка отправки WebSocket сообщения:', error);
        }
    }

    /**
     * Отправка ping
     */
    ping() {
        this.send({ event_type: 'ping' });
    }

    /**
     * Присоединение к проекту
     * @param {string} projectId - ID проекта
     */
    joinProject(projectId) {
        this.send({
            event_type: 'join_project',
            project_id: projectId
        });
    }

    /**
     * Выход из проекта
     * @param {string} projectId - ID проекта
     */
    leaveProject(projectId) {
        this.send({
            event_type: 'leave_project',
            project_id: projectId
        });
    }

    /**
     * Добавление обработчика события
     * @param {string} event - Тип события
     * @param {Function} callback - Функция обратного вызова
     */
    on(event, callback) {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, []);
        }
        this.eventListeners.get(event).push(callback);
    }

    /**
     * Удаление обработчика события
     * @param {string} event - Тип события
     * @param {Function} callback - Функция обратного вызова
     */
    off(event, callback) {
        if (this.eventListeners.has(event)) {
            const listeners = this.eventListeners.get(event);
            const index = listeners.indexOf(callback);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }

    /**
     * Вызов обработчиков события
     * @param {string} event - Тип события
     * @param {*} data - Данные события
     */
    emit(event, data) {
        if (this.eventListeners.has(event)) {
            this.eventListeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Ошибка в обработчике события ${event}:`, error);
                }
            });
        }
    }

    /**
     * Получение статуса подключения
     * @returns {boolean} Статус подключения
     */
    isReady() {
        return this.isConnected && this.connectionId !== null;
    }

    /**
     * Получение информации о соединении
     * @returns {Object} Информация о соединении
     */
    getConnectionInfo() {
        return {
            isConnected: this.isConnected,
            connectionId: this.connectionId,
            reconnectAttempts: this.reconnectAttempts,
            token: !!this.token
        };
    }
}

// Создаем глобальный экземпляр
const wsClient = new WebSocketClient();

// Автоматическое подключение при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Получаем токен из localStorage
    const token = localStorage.getItem('access_token');
    if (token) {
        wsClient.setToken(token);
    }

    // Подключаемся к WebSocket
    wsClient.connect();
});

// Обработка обновления токена
window.addEventListener('storage', (e) => {
    if (e.key === 'access_token') {
        const token = e.newValue;
        if (token) {
            wsClient.setToken(token);
            if (!wsClient.isConnected) {
                wsClient.connect();
            }
        } else {
            wsClient.disconnect();
        }
    }
});

// Экспорт для использования в других скриптах
window.wsClient = wsClient;
