/**
 * Time to DO - Основной JavaScript файл
 */

// Глобальные переменные
let currentUser = null;
let websocket = null;
let theme = localStorage.getItem('theme') || 'light';

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function () {
    initializeTheme();
    initializeWebSocket();
    initializeEventListeners();
    initializeTooltips();
    initializeModals();
});

// Инициализация темы
function initializeTheme() {
    document.documentElement.setAttribute('data-bs-theme', theme);
    updateThemeIcon();
}

// Переключение темы
function toggleTheme() {
    theme = theme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-bs-theme', theme);
    localStorage.setItem('theme', theme);
    updateThemeIcon();
}

// Обновление иконки темы
function updateThemeIcon() {
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.className = theme === 'light' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
    }
}

// Инициализация WebSocket
function initializeWebSocket() {
    if (typeof WebSocket !== 'undefined') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        websocket = new WebSocket(wsUrl);

        websocket.onopen = function () {
            console.log('WebSocket соединение установлено');
        };

        websocket.onmessage = function (event) {
            handleWebSocketMessage(JSON.parse(event.data));
        };

        websocket.onclose = function () {
            console.log('WebSocket соединение закрыто');
            // Попытка переподключения через 5 секунд
            setTimeout(initializeWebSocket, 5000);
        };

        websocket.onerror = function (error) {
            console.error('WebSocket ошибка:', error);
        };
    }
}

// Обработка WebSocket сообщений
function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'task_updated':
            updateTaskInUI(message.data);
            break;
        case 'task_created':
            addTaskToUI(message.data);
            break;
        case 'comment_added':
            addCommentToUI(message.data);
            break;
        case 'user_online':
            updateUserOnlineStatus(message.data);
            break;
        case 'notification':
            showNotification(message.data);
            break;
        default:
            console.log('Неизвестный тип сообщения:', message.type);
    }
}

// Инициализация обработчиков событий
function initializeEventListeners() {
    // Переключатель темы
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Drag and drop для Kanban доски
    initializeDragAndDrop();

    // Формы с HTMX
    if (typeof htmx !== 'undefined') {
        htmx.on('htmx:afterRequest', function (evt) {
            handleHtmxResponse(evt);
        });
    }

    // Таймеры
    initializeTimers();

    // Автосохранение форм
    initializeAutoSave();
}

// Инициализация Drag and Drop
function initializeDragAndDrop() {
    const tasks = document.querySelectorAll('.kanban-task');
    const columns = document.querySelectorAll('.kanban-column');

    tasks.forEach(task => {
        task.addEventListener('dragstart', handleDragStart);
        task.addEventListener('dragend', handleDragEnd);
    });

    columns.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
        column.addEventListener('dragleave', handleDragLeave);
    });
}

// Drag and Drop обработчики
let draggedElement = null;

function handleDragStart(e) {
    draggedElement = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
}

function handleDragEnd(e) {
    this.classList.remove('dragging');

    const columns = document.querySelectorAll('.kanban-column');
    columns.forEach(column => {
        column.classList.remove('drag-over');
    });
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }

    e.dataTransfer.dropEffect = 'move';
    this.classList.add('drag-over');

    return false;
}

function handleDragLeave(e) {
    this.classList.remove('drag-over');
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }

    this.classList.remove('drag-over');

    if (draggedElement && draggedElement !== this) {
        const taskId = draggedElement.dataset.taskId;
        const newStatus = this.dataset.status;
        const projectId = this.dataset.projectId;

        // Отправка запроса на сервер
        moveTask(taskId, newStatus, projectId);

        // Обновление UI
        this.appendChild(draggedElement);
    }

    return false;
}

// Перемещение задачи
async function moveTask(taskId, newStatus, projectId) {
    try {
        const response = await fetch(`/api/v1/tasks/${taskId}/move`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                status: newStatus,
                project_id: projectId
            })
        });

        if (!response.ok) {
            throw new Error('Ошибка при перемещении задачи');
        }

        showNotification({
            type: 'success',
            text: 'Задача успешно перемещена'
        });

    } catch (error) {
        console.error('Ошибка:', error);
        showNotification({
            type: 'error',
            text: 'Не удалось переместить задачу'
        });
    }
}

// Инициализация таймеров
function initializeTimers() {
    const timerDisplays = document.querySelectorAll('.timer-display');

    timerDisplays.forEach(display => {
        const taskId = display.dataset.taskId;
        if (taskId) {
            startTimerUpdate(taskId, display);
        }
    });
}

// Обновление таймера
function startTimerUpdate(taskId, display) {
    setInterval(async () => {
        try {
            const response = await fetch(`/api/v1/time/entries/active/${taskId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.duration) {
                    display.textContent = formatDuration(data.duration);
                }
            }
        } catch (error) {
            console.error('Ошибка обновления таймера:', error);
        }
    }, 1000);
}

// Форматирование длительности
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Инициализация автосохранения
function initializeAutoSave() {
    const forms = document.querySelectorAll('[data-auto-save]');

    forms.forEach(form => {
        let saveTimeout;

        form.addEventListener('input', function () {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => {
                autoSaveForm(form);
            }, 2000);
        });
    });
}

// Автосохранение формы
async function autoSaveForm(form) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch(form.dataset.autoSave, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showAutoSaveIndicator(form, true);
        } else {
            showAutoSaveIndicator(form, false);
        }
    } catch (error) {
        showAutoSaveIndicator(form, false);
    }
}

// Индикатор автосохранения
function showAutoSaveIndicator(form, success) {
    const indicator = form.querySelector('.auto-save-indicator');
    if (indicator) {
        indicator.className = `auto-save-indicator text-${success ? 'success' : 'danger'}`;
        indicator.textContent = success ? 'Сохранено' : 'Ошибка сохранения';

        setTimeout(() => {
            indicator.textContent = '';
        }, 3000);
    }
}

// Инициализация тултипов
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Инициализация модальных окон
function initializeModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('show.bs.modal', function () {
            // Предзагрузка данных при открытии модального окна
            const url = this.dataset.preloadUrl;
            if (url) {
                loadModalData(this, url);
            }
        });
    });
}

// Загрузка данных для модального окна
async function loadModalData(modal, url) {
    try {
        const response = await fetch(url);
        const data = await response.json();

        // Заполнение формы данными
        const form = modal.querySelector('form');
        if (form) {
            Object.keys(data).forEach(key => {
                const field = form.querySelector(`[name="${key}"]`);
                if (field) {
                    field.value = data[key];
                }
            });
        }
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
    }
}

// Обработка HTMX ответов
function handleHtmxResponse(evt) {
    if (evt.detail.successful) {
        // Показать уведомление об успехе
        const response = evt.detail.xhr.response;
        if (response.includes('alert-success')) {
            showNotification({
                type: 'success',
                text: 'Операция выполнена успешно'
            });
        }
    } else {
        // Показать уведомление об ошибке
        showNotification({
            type: 'error',
            text: 'Произошла ошибка'
        });
    }
}

// Показать уведомление
function showNotification(data) {
    const toast = document.createElement('div');
    toast.className = `toast notification-toast align-items-center text-white bg-${data.type === 'error' ? 'danger' : 'success'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${data.text}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    const container = document.querySelector('.toast-container') || createToastContainer();
    container.appendChild(toast);

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Удаление элемента после скрытия
    toast.addEventListener('hidden.bs.toast', function () {
        toast.remove();
    });
}

// Создать контейнер для уведомлений
function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1050';
    document.body.appendChild(container);
    return container;
}

// Обновление задачи в UI
function updateTaskInUI(taskData) {
    const taskElement = document.querySelector(`[data-task-id="${taskData.id}"]`);
    if (taskElement) {
        // Обновление данных задачи
        taskElement.dataset.status = taskData.status;
        taskElement.dataset.priority = taskData.priority;

        // Обновление отображения
        const titleElement = taskElement.querySelector('.task-title');
        if (titleElement) {
            titleElement.textContent = taskData.title;
        }

        // Обновление класса приоритета
        taskElement.className = taskElement.className.replace(/priority-\w+/, `priority-${taskData.priority}`);

        // Анимация обновления
        taskElement.classList.add('fade-in');
        setTimeout(() => {
            taskElement.classList.remove('fade-in');
        }, 300);
    }
}

// Добавление задачи в UI
function addTaskToUI(taskData) {
    const column = document.querySelector(`[data-status="${taskData.status}"]`);
    if (column) {
        const taskElement = createTaskElement(taskData);
        column.appendChild(taskElement);

        // Анимация появления
        taskElement.classList.add('fade-in');
    }
}

// Создание элемента задачи
function createTaskElement(taskData) {
    const div = document.createElement('div');
    div.className = `card kanban-task priority-${taskData.priority}`;
    div.dataset.taskId = taskData.id;
    div.draggable = true;

    div.innerHTML = `
        <div class="card-body p-3">
            <h6 class="card-title task-title">${taskData.title}</h6>
            <p class="card-text text-muted small text-truncate-2">${taskData.description || ''}</p>
            <div class="d-flex justify-content-between align-items-center">
                <span class="badge bg-${getStatusColor(taskData.status)}">${getStatusText(taskData.status)}</span>
                <div class="d-flex align-items-center">
                    ${taskData.assignee ? `<img src="${taskData.assignee.avatar}" class="avatar-sm me-1" alt="${taskData.assignee.name}">` : ''}
                    <small class="text-muted">#${taskData.id}</small>
                </div>
            </div>
        </div>
    `;

    // Добавление обработчиков drag and drop
    div.addEventListener('dragstart', handleDragStart);
    div.addEventListener('dragend', handleDragEnd);

    return div;
}

// Получение цвета статуса
function getStatusColor(status) {
    const colors = {
        'todo': 'secondary',
        'in_progress': 'primary',
        'review': 'warning',
        'done': 'success'
    };
    return colors[status] || 'secondary';
}

// Получение текста статуса
function getStatusText(status) {
    const texts = {
        'todo': 'К выполнению',
        'in_progress': 'В работе',
        'review': 'На проверке',
        'done': 'Выполнено'
    };
    return texts[status] || status;
}

// Обновление онлайн статуса пользователя
function updateUserOnlineStatus(userData) {
    const statusElement = document.querySelector(`[data-user-id="${userData.id}"] .online-status`);
    if (statusElement) {
        statusElement.className = `online-status ${userData.online ? 'online' : 'offline'}`;
        statusElement.title = userData.online ? 'Онлайн' : 'Офлайн';
    }
}

// Добавление комментария в UI
function addCommentToUI(commentData) {
    const commentsContainer = document.querySelector(`[data-task-id="${commentData.task_id}"] .comments-container`);
    if (commentsContainer) {
        const commentElement = createCommentElement(commentData);
        commentsContainer.appendChild(commentElement);

        // Анимация появления
        commentElement.classList.add('fade-in');
    }
}

// Создание элемента комментария
function createCommentElement(commentData) {
    const div = document.createElement('div');
    div.className = 'comment mb-3';
    div.innerHTML = `
        <div class="d-flex">
            <img src="${commentData.author.avatar}" class="avatar me-2" alt="${commentData.author.name}">
            <div class="flex-grow-1">
                <div class="d-flex justify-content-between">
                    <strong>${commentData.author.name}</strong>
                    <small class="text-muted">${formatDate(commentData.created_at)}</small>
                </div>
                <p class="mb-0">${commentData.content}</p>
            </div>
        </div>
    `;
    return div;
}

// Форматирование даты
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) {
        return 'только что';
    } else if (diff < 3600000) {
        return `${Math.floor(diff / 60000)} мин. назад`;
    } else if (diff < 86400000) {
        return `${Math.floor(diff / 3600000)} ч. назад`;
    } else {
        return date.toLocaleDateString('ru-RU');
    }
}

// Экспорт глобальных функций
window.TimeToDO = {
    toggleTheme,
    moveTask,
    showNotification,
    formatDuration,
    formatDate
};
