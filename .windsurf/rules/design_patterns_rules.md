---
trigger: glob
---
# Паттерны проектирования (Gang of Four)

## ПРАВИЛО ПРИМЕНЕНИЯ

При написании кода, рефакторинга, редактировании кода, обновлении/удалении кода смотри на возможность применения одного из этих паттернов.

---

## ПОРОЖДАЮЩИЕ ПАТТЕРНЫ (Creational Patterns)

Паттерны, которые управляют процессом создания объектов.

---

### Abstract Factory / Абстрактная Фабрика

**Описание:**
Абстрактная фабрика задаёт интерфейс создания всех доступных типов продуктов, а каждая конкретная реализация фабрики порождает продукты одной из вариаций. Клиентский код вызывает методы фабрики для получения продуктов, вместо самостоятельного создания с помощью оператора `new`. При этом фабрика сама следит за тем, чтобы создать продукт нужной вариации.

**Популярность:** ⭐⭐⭐  
**Сложность:** ⭐⭐⭐

**Когда применять:**
- Система не должна зависеть от способа создания и компоновки объектов
- Нужно создавать семейства взаимосвязанных объектов
- Необходимо обеспечить использование объектов только из одного семейства

**Пример на Python:**
```python
# Абстрактная фабрика для создания UI элементов
from abc import ABC, abstractmethod

class Button(ABC):
    @abstractmethod
    def paint(self): pass

class Checkbox(ABC):
    @abstractmethod
    def paint(self): pass

# Конкретные продукты Windows
class WindowsButton(Button):
    def paint(self):
        return "Render a button in Windows style"

class WindowsCheckbox(Checkbox):
    def paint(self):
        return "Render a checkbox in Windows style"

# Конкретные продукты MacOS
class MacButton(Button):
    def paint(self):
        return "Render a button in MacOS style"

class MacCheckbox(Checkbox):
    def paint(self):
        return "Render a checkbox in MacOS style"

# Абстрактная фабрика
class GUIFactory(ABC):
    @abstractmethod
    def create_button(self) -> Button: pass
    
    @abstractmethod
    def create_checkbox(self) -> Checkbox: pass

# Конкретные фабрики
class WindowsFactory(GUIFactory):
    def create_button(self) -> Button:
        return WindowsButton()
    
    def create_checkbox(self) -> Checkbox:
        return WindowsCheckbox()

class MacFactory(GUIFactory):
    def create_button(self) -> Button:
        return MacButton()
    
    def create_checkbox(self) -> Checkbox:
        return MacCheckbox()

# Использование
def create_ui(factory: GUIFactory):
    button = factory.create_button()
    checkbox = factory.create_checkbox()
    print(button.paint())
    print(checkbox.paint())

# Клиентский код
factory = WindowsFactory()  # Или MacFactory()
create_ui(factory)
```

---

### Builder / Строитель

**Описание:**
Строитель отделяет конструирование сложного объекта от его представления, позволяя использовать один и тот же процесс конструирования для создания различных представлений. Паттерн позволяет создавать объект пошагово, вызывая только те шаги, которые вам нужны.

**Популярность:** ⭐⭐⭐  
**Сложность:** ⭐⭐

**Когда применять:**
- Необходимо создавать сложные объекты с множеством параметров
- Процесс создания объекта должен быть независим от частей объекта
- Нужны разные представления создаваемого объекта

**Пример на Python:**
```python
# Строитель для создания сложных объектов (например, дом)
class House:
    def __init__(self):
        self.walls = None
        self.doors = None
        self.windows = None
        self.roof = None
        self.garage = None
    
    def __str__(self):
        return f"House: {self.walls} walls, {self.doors} doors, {self.windows} windows, {self.roof} roof, garage: {self.garage}"

class HouseBuilder:
    def __init__(self):
        self.house = House()
    
    def build_walls(self, walls):
        self.house.walls = walls
        return self
    
    def build_doors(self, doors):
        self.house.doors = doors
        return self
    
    def build_windows(self, windows):
        self.house.windows = windows
        return self
    
    def build_roof(self, roof):
        self.house.roof = roof
        return self
    
    def build_garage(self, garage):
        self.house.garage = garage
        return self
    
    def get_house(self):
        return self.house

# Использование
custom = (HouseBuilder()
          .build_walls(5)
          .build_doors(2)
          .build_windows(6)
          .build_roof("dome")
          .get_house())
print(custom)
```

---

### Factory Method / Фабричный Метод

**Описание:**
Фабричный метод определяет общий интерфейс для создания объектов в суперклассе, позволяя подклассам изменять тип создаваемых объектов. Вместо прямого вызова конструктора объекта (`new`), вызывается специальный фабричный метод.

**Популярность:** ⭐⭐⭐  
**Сложность:** ⭐

**Когда применять:**
- Заранее неизвестны типы и зависимости объектов
- Нужна возможность расширения создания объектов в библиотеке или фреймворке
- Хотите экономить системные ресурсы, повторно используя уже созданные объекты

**Пример на Python:**
```python
# Фабричный метод для создания транспорта
from abc import ABC, abstractmethod

class Transport(ABC):
    @abstractmethod
    def deliver(self): pass

class Truck(Transport):
    def deliver(self):
        return "Delivery by land in a box"

class Ship(Transport):
    def deliver(self):
        return "Delivery by sea in a container"

# Абстрактный создатель
class Logistics(ABC):
    @abstractmethod
    def create_transport(self) -> Transport:
        pass
    
    def plan_delivery(self):
        transport = self.create_transport()
        return f"Logistics: {transport.deliver()}"

# Конкретные создатели
class RoadLogistics(Logistics):
    def create_transport(self) -> Transport:
        return Truck()

class SeaLogistics(Logistics):
    def create_transport(self) -> Transport:
        return Ship()

# Использование
client_code(RoadLogistics())
client_code(SeaLogistics())
```

---

### Singleton / Одиночка

**Описание:**
Одиночка гарантирует, что у класса есть только один экземпляр, и предоставляет к нему глобальную точку доступа. Паттерн решает две проблемы одновременно: обеспечение единственного экземпляра класса и предоставление глобальной точки доступа к этому экземпляру.

**Популярность:** ⭐⭐  
**Сложность:** ⭐

**Когда применять:**
- Должен быть ровно один экземпляр класса (подключение к БД, логгер)
- Нужна глобальная точка доступа к этому экземпляру
- Экземпляр должен расширяться путём наследования

**Пример на Python:**
```python
# Одиночка через метакласс (самый надёжный)
class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    def __init__(self):
        self.connection = "Database connection"
    
    def query(self, sql):
        return f"Executing: {sql}"

# Использование
db1 = Database()
db2 = Database()
print(db1 is db2)  # True - один и тот же объект
```

---

## СТРУКТУРНЫЕ ПАТТЕРНЫ (Structural Patterns)

Паттерны, которые показывают способы компоновки объектов и классов в более крупные структуры.

---

### Adapter / Адаптер

**Описание:**
Адаптер позволяет объектам с несовместимыми интерфейсами работать вместе. Он оборачивает несовместимый объект и делает его совместимым с другим объектом, преобразуя интерфейс одного объекта в интерфейс, ожидаемый клиентом.

**Популярность:** ⭐⭐⭐  
**Сложность:** ⭐

**Когда применять:**
- Нужно использовать класс, интерфейс которого не соответствует вашим потребностям
- Необходима совместная работа классов с несовместимыми интерфейсами
- Требуется повторное использование существующих классов без изменения их кода

**Пример на Python:**
```python
# Адаптер для работы с несовместимыми интерфейсами
class EuropeanSocket:
    def voltage(self):
        return 230

class USASocket:
    def voltage(self):
        return 120

# Адаптер
class SocketAdapter:
    def __init__(self, socket):
        self.socket = socket
    
    def voltage(self):
        return self.socket.voltage() // 2

# Использование
euro_socket = EuropeanSocket()
adapted_socket = SocketAdapter(euro_socket)
print(adapted_socket.voltage())  # 115V
```

---

### Decorator / Декоратор

**Описание:**
Декоратор позволяет динамически добавлять объектам новую функциональность, оборачивая их в полезные "обёртки". Декоратор предоставляет альтернативу наследованию для расширения функциональности, позволяя надевать обязанности на объекты, а не на классы.

**Популярность:** ⭐⭐  
**Сложность:** ⭐⭐

**Когда применять:**
- Нужно динамически добавлять объектам новые обязанности
- Невозможно расширить функциональность через наследование
- Требуется возможность комбинировать несколько дополнительных функций

**Пример на Python:**
```python
# Декоратор для динамического добавления функциональности
class DataSource:
    def write_data(self, data):
        pass

class FileDataSource(DataSource):
    def write_data(self, data):
        return f"Writing to file: {data}"

class EncryptionDecorator(DataSourceDecorator):
    def write_data(self, data):
        encrypted = self._encrypt(data)
        return f"[Encrypted] {self._source.write_data(encrypted)}"
```

---

## ПОВЕДЕНЧЕСКИЕ ПАТТЕРНЫ (Behavioral Patterns)

Паттерны, которые отвечают за эффективное и безопасное взаимодействие между объектами.

---

### Observer / Наблюдатель

**Описание:**
Наблюдатель определяет зависимость типа "один ко многим" между объектами так, что при изменении состояния одного объекта все зависящие от него оповещаются об этом событии.

**Популярность:** ⭐⭐⭐  
**Сложность:** ⭐⭐

**Когда применять:**
- При изменении состояния одного объекта требуется изменять состояние других объектов
- Необходимо чтобы один объект мог оповещать множество других объектов
- Наблюдаемая система не должна знать о том, кто и как использует её состояние

**Пример на Python:**
```python
# Наблюдатель для оповещения об изменениях
from abc import ABC, abstractmethod

class Observer(ABC):
    @abstractmethod
    def update(self, message): pass

class Subject(ABC):
    @abstractmethod
    def attach(self, observer: Observer): pass
    
    @abstractmethod
    def detach(self, observer: Observer): pass
    
    @abstractmethod
    def notify(self): pass

class NewsAgency(Subject):
    def __init__(self):
        self._observers = []
        self._latest_news = ""
    
    def attach(self, observer: Observer):
        self._observers.append(observer)
    
    def detach(self, observer: Observer):
        self._observers.remove(observer)
    
    def notify(self):
        for observer in self._observers:
            observer.update(self._latest_news)
    
    def add_news(self, news):
        self._latest_news = news
        self.notify()

class NewsSubscriber(Observer):
    def __init__(self, name):
        self.name = name
    
    def update(self, message):
        print(f"{self.name} received news: {message}")

# Использование
agency = NewsAgency()
subscriber1 = NewsSubscriber("Alice")
subscriber2 = NewsSubscriber("Bob")

agency.attach(subscriber1)
agency.attach(subscriber2)
agency.add_news("Breaking: New Python release!")
```

---

### Strategy / Стратегия

**Описание:**
Стратегия определяет семейство алгоритмов, инкапсулирует каждый из них и делает их взаимозаменяемыми. Стратегия позволяет изменять алгоритмы независимо от клиентов, которые ими пользуются.

**Популярность:** ⭐⭐⭐  
**Сложность:** ⭐⭐

**Когда применять:**
- Нужно использовать разные вариации алгоритма внутри одного объекта
- Необходимо иметь возможность менять алгоритмы во время выполнения
- Алгоритм использует данные, о которых клиенты не должны знать

**Пример на Python:**
```python
# Стратегия для выбора алгоритма сортировки
from abc import ABC, abstractmethod

class SortStrategy(ABC):
    @abstractmethod
    def sort(self, data): pass

class BubbleSort(SortStrategy):
    def sort(self, data):
        # Реализация пузырьковой сортировки
        return sorted(data)

class QuickSort(SortStrategy):
    def sort(self, data):
        # Реализация быстрой сортировки
        return sorted(data, reverse=True)

class SortContext:
    def __init__(self, strategy: SortStrategy):
        self._strategy = strategy
    
    def set_strategy(self, strategy: SortStrategy):
        self._strategy = strategy
    
    def sort_data(self, data):
        return self._strategy.sort(data)

# Использование
context = SortContext(BubbleSort())
result1 = context.sort_data([3, 1, 4, 1, 5])

context.set_strategy(QuickSort())
result2 = context.sort_data([3, 1, 4, 1, 5])
```

---

*Это руководство по паттернам проектирования должно применяться при разработке для создания качественного, масштабируемого и поддерживаемого кода.*
