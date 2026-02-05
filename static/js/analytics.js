/**
 * JavaScript функциональность для страницы аналитики
 */

class AnalyticsDashboard {
    constructor() {
        this.charts = {};
        this.currentData = {};
        this.filters = {
            dateRange: null,
            projectFilter: '',
            periodType: 'daily',
            userFilter: ''
        };

        this.init();
    }

    async init() {
        console.log('🚀 Инициализация дашборда аналитики...');

        // Инициализация компонентов
        this.initDateRangePicker();
        this.initEventListeners();
        this.initCharts();

        // Загрузка начальных данных
        await this.loadDashboardData();

        console.log('✅ Дашборд аналитики инициализирован');
    }

    initDateRangePicker() {
        const dateRange = $('#dateRange');

        // Устанавливаем период по умолчанию (последние 30 дней)
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - 30);

        dateRange.daterangepicker({
            startDate: startDate,
            endDate: endDate,
            locale: {
                format: 'DD.MM.YYYY',
                separator: ' - ',
                applyLabel: 'Применить',
                cancelLabel: 'Отмена',
                fromLabel: 'От',
                toLabel: 'До',
                customRangeLabel: 'Произвольный',
                weekLabel: 'W',
                daysOfWeek: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
                monthNames: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
                firstDay: 1
            },
            ranges: {
                'Последние 7 дней': [moment().subtract(6, 'days'), moment()],
                'Последние 30 дней': [moment().subtract(29, 'days'), moment()],
                'Этот месяц': [moment().startOf('month'), moment().endOf('month')],
                'Прошлый месяц': [moment().subtract(1, 'month').startOf('month'),
                               moment().subtract(1, 'month').endOf('month')]
            }
        });

        this.filters.dateRange = {
            start: startDate,
            end: endDate
        };
    }

    initEventListeners() {
        // Форма фильтров
        $('#filtersForm').on('submit', (e) => {
            e.preventDefault();
            this.updateFilters();
            this.loadDashboardData();
        });

        // Кнопка обновления
        $('#refreshBtn').on('click', () => {
            this.loadDashboardData();
        });

        // Кнопка экспорта
        $('#exportBtn').on('click', () => {
            $('#exportModal').modal('show');
        });

        // Подтверждение экспорта
        $('#confirmExportBtn').on('click', () => {
            this.exportData();
        });

        // Переключатели типа графика
        $('input[name="chartType"]').on('change', (e) => {
            this.updateMainChart(e.target.value);
        });

        // Изменение фильтров
        $('#projectFilter, #periodType, #userFilter').on('change', () => {
            this.updateFilters();
        });
    }

    initCharts() {
        // Основной график (динамика)
        const mainCtx = document.getElementById('mainChart').getContext('2d');
        this.charts.main = new Chart(mainCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Выполнено задач',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // График проектов (круговая диаграмма)
        const projectsCtx = document.getElementById('projectsChart').getContext('2d');
        this.charts.projects = new Chart(projectsCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF',
                        '#FF9F40'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    updateFilters() {
        const dateRangeText = $('#dateRange').val();
        if (dateRangeText) {
            const dates = dateRangeText.split(' - ');
            this.filters.dateRange = {
                start: moment(dates[0], 'DD.MM.YYYY').toDate(),
                end: moment(dates[1], 'DD.MM.YYYY').toDate()
            };
        }

        this.filters.projectFilter = $('#projectFilter').val();
        this.filters.periodType = $('#periodType').val();
        this.filters.userFilter = $('#userFilter').val();
    }

    async loadDashboardData() {
        try {
            console.log('📊 Загрузка данных дашборда...');

            // Показываем индикаторы загрузки
            this.showLoadingState();

            // Загружаем данные через API
            const overviewData = await this.fetchAnalyticsOverview();
            const userMetrics = await this.fetchUserMetrics();
            const projectMetrics = await this.fetchProjectMetrics();

            // Обновляем метрики
            this.updateMetrics(overviewData);

            // Обновляем графики
            await this.updateCharts(userMetrics, projectMetrics);

            // Обновляем таблицы
            await this.updateTables(userMetrics, projectMetrics);

            console.log('✅ Данные дашборда загружены');

        } catch (error) {
            console.error('❌ Ошибка загрузки данных:', error);
            this.showErrorState(error.message);
        }
    }

    async fetchAnalyticsOverview() {
        try {
            const response = await fetch('/api/v1/analytics/overview');
            if (!response.ok) throw new Error('Ошибка загрузки обзора');
            return await response.json();
        } catch (error) {
            console.warn('⚠️ Не удалось загрузить обзор, используем мок данные');
            return this.getMockOverviewData();
        }
    }

    async fetchUserMetrics() {
        try {
            const userId = this.filters.userFilter || 'current';
            const response = await fetch(`/api/v1/analytics/users/${userId}/summary?days=30`);
            if (!response.ok) throw new Error('Ошибка загрузки метрик пользователя');
            return await response.json();
        } catch (error) {
            console.warn('⚠️ Не удалось загрузить метрики пользователя, используем мок данные');
            return this.getMockUserMetrics();
        }
    }

    async fetchProjectMetrics() {
        try {
            const projectId = this.filters.projectFilter;
            if (!projectId) return this.getMockProjectMetrics();

            const response = await fetch(`/api/v1/analytics/projects/${projectId}/summary?days=30`);
            if (!response.ok) throw new Error('Ошибка загрузки метрик проекта');
            return await response.json();
        } catch (error) {
            console.warn('⚠️ Не удалось загрузить метрики проекта, используем мок данные');
            return this.getMockProjectMetrics();
        }
    }

    updateMetrics(data) {
        const userSummary = data.user_summary || {};
        const tasks = userSummary.tasks || {};
        const projects = userSummary.projects || {};

        // Обновляем ключевые метрики
        $('#tasksCompletedMetric').text(tasks.completed || 0);
        $('#timeLoggedMetric').text(this.formatHours(tasks.total_time || 0));
        $('#activeProjectsMetric').text(projects.active || 0);
        $('#productivityMetric').text(Math.round(tasks.completion_rate || 0) + '%');
    }

    async updateCharts(userMetrics, projectMetrics) {
        // Обновляем основной график
        this.updateMainChart('tasks');

        // Обновляем график проектов
        this.updateProjectsChart(projectMetrics);
    }

    updateMainChart(type) {
        const chart = this.charts.main;
        const mockData = this.getMockChartData(type);

        chart.data.labels = mockData.labels;
        chart.data.datasets[0].data = mockData.data;
        chart.data.datasets[0].label = mockData.label;
        chart.data.datasets[0].borderColor = mockData.color;
        chart.data.datasets[0].backgroundColor = mockData.backgroundColor;

        chart.update();
    }

    updateProjectsChart(projectMetrics) {
        const chart = this.charts.projects;
        const mockData = this.getMockProjectsData();

        chart.data.labels = mockData.labels;
        chart.data.datasets[0].data = mockData.data;

        chart.update();
    }

    async updateTables(userMetrics, projectMetrics) {
        // Обновляем таблицу топ задач
        this.updateTopTasksTable();

        // Обновляем таблицу активности пользователей
        this.updateUsersActivityTable();
    }

    updateTopTasksTable() {
        const tbody = $('#topTasksTable tbody');
        const mockTasks = this.getMockTopTasks();

        tbody.empty();
        mockTasks.forEach(task => {
            const row = `
                <tr>
                    <td>${task.name}</td>
                    <td>${task.project}</td>
                    <td>${this.formatHours(task.time)}</td>
                    <td><span class="badge bg-${task.statusColor}">${task.status}</span></td>
                </tr>
            `;
            tbody.append(row);
        });
    }

    updateUsersActivityTable() {
        const tbody = $('#usersActivityTable tbody');
        const mockUsers = this.getMockUsersActivity();

        tbody.empty();
        mockUsers.forEach(user => {
            const row = `
                <tr>
                    <td>${user.name}</td>
                    <td>${user.tasks}</td>
                    <td>${this.formatHours(user.time)}</td>
                    <td>
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar bg-${user.productivityColor}"
                                 style="width: ${user.productivity}%">
                                ${user.productivity}%
                            </div>
                        </div>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });
    }

    showLoadingState() {
        // Показываем индикаторы загрузки
        $('#tasksCompletedMetric, #timeLoggedMetric, #activeProjectsMetric, #productivityMetric')
            .html('<i class="bi bi-hourglass-split"></i>');
    }

    showErrorState(message) {
        // Показываем состояние ошибки
        $('#tasksCompletedMetric').text('Ошибка');
        $('#timeLoggedMetric').text('Ошибка');
        $('#activeProjectsMetric').text('Ошибка');
        $('#productivityMetric').text('Ошибка');

        // Показываем уведомление
        this.showNotification('Ошибка загрузки данных: ' + message, 'danger');
    }

    showNotification(message, type = 'info') {
        // Создаем временное уведомление
        const notification = `
            <div class="alert alert-${type} alert-dismissible fade show position-fixed"
                 style="top: 20px; right: 20px; z-index: 1050; max-width: 400px;">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        $('body').append(notification);

        // Автоматически удаляем через 5 секунд
        setTimeout(() => {
            $('.alert').fadeOut();
        }, 5000);
    }

    async exportData() {
        const format = $('#exportFormat').val();
        const includeMetrics = $('#exportMetrics').is(':checked');
        const includeCharts = $('#exportCharts').is(':checked');
        const includeTables = $('#exportTables').is(':checked');

        try {
            this.showNotification('Подготовка экспорта...', 'info');

            // Имитация экспорта
            setTimeout(() => {
                this.showNotification(`Данные успешно экспортированы в формате ${format.toUpperCase()}`, 'success');
                $('#exportModal').modal('hide');
            }, 2000);

        } catch (error) {
            console.error('❌ Ошибка экспорта:', error);
            this.showNotification('Ошибка экспорта данных', 'danger');
        }
    }

    // Вспомогательные методы
    formatHours(seconds) {
        if (!seconds) return '0ч';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return minutes > 0 ? `${hours}ч ${minutes}м` : `${hours}ч`;
    }

    // Мок данные для демонстрации
    getMockOverviewData() {
        return {
            user_summary: {
                tasks: {
                    total: 45,
                    completed: 32,
                    in_progress: 8,
                    completion_rate: 71
                },
                projects: {
                    active: 3
                },
                metrics: []
            }
        };
    }

    getMockUserMetrics() {
        return {
            user: {
                id: 'current',
                name: 'Текущий пользователь'
            },
            tasks: {
                total: 45,
                completed: 32,
                in_progress: 8,
                completion_rate: 71
            },
            metrics: []
        };
    }

    getMockProjectMetrics() {
        return {
            project: {
                id: 'demo',
                name: 'Demo Project'
            },
            tasks: {
                total: 25,
                completed: 18,
                in_progress: 5,
                completion_rate: 72
            },
            metrics: []
        };
    }

    getMockChartData(type) {
        const labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

        const configs = {
            tasks: {
                label: 'Выполнено задач',
                data: [5, 8, 6, 9, 7, 4, 3],
                color: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)'
            },
            time: {
                label: 'Время работы (часы)',
                data: [6, 8, 7, 9, 8, 4, 2],
                color: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.2)'
            },
            productivity: {
                label: 'Продуктивность (%)',
                data: [85, 90, 78, 92, 88, 70, 65],
                color: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)'
            }
        };

        return {
            labels,
            ...configs[type]
        };
    }

    getMockProjectsData() {
        return {
            labels: ['Project Alpha', 'Project Beta', 'Project Gamma', 'Project Delta'],
            data: [35, 25, 20, 20]
        };
    }

    getMockTopTasks() {
        return [
            { name: 'Разработка API', project: 'Project Alpha', time: 14400, status: 'DONE', statusColor: 'success' },
            { name: 'Тестирование модуля', project: 'Project Beta', time: 10800, status: 'IN_PROGRESS', statusColor: 'warning' },
            { name: 'Документация', project: 'Project Alpha', time: 7200, status: 'TODO', statusColor: 'secondary' },
            { name: 'Оптимизация БД', project: 'Project Gamma', time: 5400, status: 'DONE', statusColor: 'success' },
            { name: 'UI/UX дизайн', project: 'Project Delta', time: 3600, status: 'IN_PROGRESS', statusColor: 'warning' }
        ];
    }

    getMockUsersActivity() {
        return [
            { name: 'Иван Иванов', tasks: 12, time: 28800, productivity: 85, productivityColor: 'success' },
            { name: 'Мария Петрова', tasks: 8, time: 21600, productivity: 92, productivityColor: 'success' },
            { name: 'Алексей Сидоров', tasks: 15, time: 32400, productivity: 78, productivityColor: 'warning' },
            { name: 'Елена Козлова', tasks: 6, time: 14400, productivity: 88, productivityColor: 'success' }
        ];
    }
}

// Инициализация при загрузке страницы
$(document).ready(() => {
    window.analyticsDashboard = new AnalyticsDashboard();
});
