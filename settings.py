import logging

# Настройки логирования
logging_config = {
    "level": "INFO",  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "filename": "printer_monitoring.log",  # Файл для логирования
}

# Настройка логирования
logging.basicConfig(
    level=logging_config["level"],
    format=logging_config["format"],
    filename=logging_config["filename"],
)

snmp_cache = {} # Кэш для хранения результатов SNMP-запросов
CACHE_TTL = 300  # Время жизни кэша в секундах (5 минут)

# Настройки устройств
# devices = [
#     {
#         "ip": "192.168.88.232",
#         "community": "public",  # SNMP v2c community
#         "poll_interval": 60,    # Интервал опроса в секундах
#         "snmp_version": "2c",   # Версия SNMP (2c или 3)
#         "max_retries": 3,       # Максимальное количество попыток
#     },
#     # Добавьте другие устройства
# ]

scan_network = "192.168.88.2/24"
scan_community = "public"

# OID для мониторинга устройств Kyocera
kyocera_oids = {
    "1.3.6.1.2.1.1.3.0": "Uptime",
    '1.3.6.1.2.1.43.16.5.1.2.1.1': 'Статус устройства',
    '1.3.6.1.2.1.25.3.5.1.1.1': 'Статус принтера',
    # SYNTAX INTEGER {other(1), unknown(2), idle(3), printing(4), warmup(5)}
    '1.3.6.1.2.1.25.3.2.1.3.1': 'Модель',
    # '1.3.6.1.4.1.1347.43.5.1.1.28.1': 'Серийный номер',

    # "1.3.6.1.2.1.1.1.0": "Описание системы",  # Модель устройства
    "1.3.6.1.2.1.43.5.1.1.17.1": "Серийный номер",
    "1.3.6.1.4.1.1347.43.10.1.1.12.1.1": "page_count",
    "1.3.6.1.4.1.1347.42.3.1.3.1.1.2": "scan_count",
    "1.3.6.1.2.1.43.11.1.1.9.1.1": "toner_level",
}