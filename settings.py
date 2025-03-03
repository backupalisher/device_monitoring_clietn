import logging
import os

LOGGING_CONFIG = {
    "level": logging.INFO,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "filename": os.path.join(os.path.dirname(__file__), "printer_monitoring.log"),
    "filemode": "a",
    "encoding": "utf-8",
}

SNMP_TIMEOUT = 1.5
SNMP_RETRIES = 2
SCAN_SEMAPHORE_LIMIT = 50
MAX_RETRIES = 3
RETRY_INTERVAL = 300  # 5 минут
MONITOR_INTERVAL = 300  # 5 минут
SCAN_NETWORK = "192.168.88.2/24"
SCAN_COMMUNITY = "public"

KYOCERA_OIDS = {
    "1.3.6.1.2.1.1.3.0": "Uptime",
    "1.3.6.1.2.1.43.16.5.1.2.1.1": "Статус устройства",
    "1.3.6.1.2.1.25.3.5.1.1.1": "Статус принтера",
    "1.3.6.1.2.1.25.3.2.1.3.1": "Модель",
    "1.3.6.1.2.1.43.5.1.1.17.1": "Серийный номер",
    "1.3.6.1.4.1.1347.43.10.1.1.12.1.1": "page_count",
    "1.3.6.1.4.1.1347.42.3.1.3.1.1.2": "scan_count",
    "1.3.6.1.2.1.43.11.1.1.9.1.1": "toner_level",
}

MODEL_OID = "1.3.6.1.2.1.25.3.2.1.3.1"
SERIAL_OID = "1.3.6.1.2.1.43.5.1.1.17.1"
STATUS_OID = "1.3.6.1.2.1.43.16.5.1.2.1.1"