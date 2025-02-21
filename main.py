# Клиент
from datetime import datetime
import sqlite3
import asyncio
import logging

from ipaddress import IPv4Network
import itertools

from pysnmp.hlapi.v3arch.asyncio import *

import settings
from settings import kyocera_oids, logging_config

# Настройка логирования
logging.basicConfig(
    level=logging_config["level"],
    format=logging_config["format"],
    filename=logging_config["filename"],
)


async def discover_devices(network: str, community: str):
    """Сканирует сеть и добавляет новые устройства в БД."""
    net = IPv4Network(network, strict=False)
    semaphore = asyncio.Semaphore(100)  # Ограничение одновременных запросов

    async def check_ip(ip):
        async with semaphore:
            device = {"ip": str(ip), "community": community}
            if await is_device_available(device):
                keys = [key for key in kyocera_oids if kyocera_oids[key] == "Модель"]
                model = await get_snmp_data(device, keys)
                keys = [key for key in kyocera_oids if kyocera_oids[key] == "Серийный номер"]
                serial = await get_snmp_data(device, keys)
                print(device)
                if model and serial:
                    with sqlite3.connect('pm_data.db') as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT OR IGNORE INTO devices (ip_address, community, model, serial)
                            VALUES (?, ?, ?, ?)
                        ''', (str(ip), community, model, serial))
                        conn.commit()

    # Генерация всех IP в сети и асинхронная проверка
    ips = (net.network_address + i for i in itertools.islice(itertools.count(), 1, net.num_addresses))
    await asyncio.gather(*[check_ip(ip) for ip in ips])

def log_event(device_id: int, event_type: str, message: str):
    print('log_event', device_id, event_type, message)
    with sqlite3.connect('pm_data.db') as conn:
        conn.execute('''
            INSERT INTO events (device_id, type, message)
            VALUES (?, ?, ?)
        ''', (device_id, event_type, message))
        conn.commit()


async def get_snmp_data(device, oid, description=None):
    """Выполняет SNMP-запрос с обработкой ошибок."""
    snmpEngine = SnmpEngine()
    try:
        auth_data = CommunityData(device["community"], mpModel=0)
        # print(device['ip'], oid)
        iterator = get_cmd(
            snmpEngine,
            auth_data,
            await UdpTransportTarget.create((device['ip'], 161), timeout=1, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )

        errorIndication, errorStatus, errorIndex, varBinds = await iterator

        if errorIndication:
            logging.warning(f"Устройство {device['ip']}: Ошибка SNMP (OID {oid}): {errorIndication}")
            return None
        elif errorStatus:
            logging.warning(f"Устройство {device['ip']}: Ошибка статуса: {errorStatus.prettyPrint()}")
            return None

        for varBind in varBinds:
            oid, value = varBind
            try:
                decoded_value = bytes(value).decode('utf-8') if isinstance(value, OctetString) else value
                return str(decoded_value)
            except Exception as e:
                logging.error(f"Ошибка декодирования: {e}")
                return None
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        return None
    finally:
        snmpEngine.close_dispatcher()


async def is_device_available(device):
    """Проверяет доступность устройства через SNMP."""
    snmpEngine = SnmpEngine()
    try:
        iterator = get_cmd(
            snmpEngine,
            CommunityData(device["community"], mpModel=0),
            await UdpTransportTarget.create((device["ip"], 161), timeout=1, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.3.0")),  # sysUpTime
        )

        errorIndication, errorStatus, errorIndex, varBinds = await iterator

        return not (errorIndication or errorStatus)
    except Exception as e:
        logging.error(f"Ошибка при проверке устройства {device['ip']} (SNMP): {e}")
        return False
    finally:
        snmpEngine.close_dispatcher()


async def monitor_device(device):
    """Мониторинг устройства и обновление данных в БД."""
    prev_status = None
    while True:
        if await is_device_available(device):
            logging.info(f"Начало опроса {device['ip']}")
            tasks = [get_snmp_data(device, oid, desc) for oid, desc in kyocera_oids.items()]
            results = await asyncio.gather(*tasks)

            current_status = await get_snmp_data(device, "1.3.6.1.2.1.43.16.5.1.2.1.1")
            if prev_status and current_status != prev_status:
                log_event(device['id'], 'status_change', f"Статус изменился: {prev_status} → {current_status}")
            prev_status = current_status

            data = {desc: results[i] for i, (_, desc) in enumerate(kyocera_oids.items())}
            print(data['Модель'], data['Статус устройства'], data['page_count'], data['scan_count'], data['toner_level'])
            try:
                page_count = int(data['page_count']) if data['page_count'] else None
                scan_count = int(data['scan_count']) if data['scan_count'] else None
                toner_level = int(data['toner_level']) if data['toner_level'] else None
                uptime = int(data['Uptime']) if data['Uptime'] else None
            except (ValueError, TypeError) as e:
                logging.error(f"Ошибка преобразования данных для {device['ip']}: {e}")
                page_count = scan_count = toner_level = None

            try:
                with sqlite3.connect('pm_data.db') as conn:
                    conn.execute('''
                        UPDATE devices 
                        SET page_count = ?, toner_level = ?, scan_count = ?, uptime = ?
                        WHERE id = ?
                    ''', (page_count, toner_level, scan_count, uptime, device['id']))
                    conn.commit()
            except sqlite3.Error as e:
                logging.error(f"Ошибка БД при обновлении {device['ip']}: {e}")
        else:
            logging.warning(f"Устройство {device['ip']} недоступно")

        await asyncio.sleep(60)


async def get_devices_from_db():
    """Возвращает список устройств из базы данных."""
    devices = []
    try:
        with sqlite3.connect('pm_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, ip_address, community FROM devices")
            for row in cursor.fetchall():
                devices.append({
                    'id': row[0],
                    'name': row[1],
                    'ip': row[2],
                    'community': row[3]
                })
    except Exception as e:
        logging.error(f"Ошибка при загрузке устройств: {e}")
    return devices


async def update_device_status():
    """Обновляет статус устройств в таблице device_status."""
    try:
        with sqlite3.connect('pm_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, ip_address, community FROM devices")
            for device_id, ip, community in cursor.fetchall():
                status = await get_snmp_data(
                    {'ip': ip, 'community': community},
                    # "1.3.6.1.2.1.1.3.0",
                    "1.3.6.1.2.1.43.16.5.1.2.1.1",
                    "Статус устройства"
                )
                time_format = "%Y-%m-%d %H:%M:%S"
                now = datetime.now().strftime(time_format)
                if status is not None:
                    cursor.execute('''
                        INSERT OR REPLACE INTO device_status 
                        (device_id, status, last_checked)
                        VALUES (?, ?, ?)
                    ''', (device_id, status, now))
            conn.commit()
    except Exception as e:
        logging.error(f"Ошибка при обновлении статусов: {e}")


async def status_updater():
    """Периодически обновляет статусы устройств."""
    while True:
        await update_device_status()
        await asyncio.sleep(30)


async def main():
    """Основная функция приложения."""
    # Запуск сканирования при старте
    await discover_devices(settings.scan_network, settings.scan_community)

    # Периодическое сканирование каждые 24 часа
    async def periodic_discovery():
        while True:
            await discover_devices(settings.scan_network, settings.scan_community)
            await asyncio.sleep(86400)

    devices = await get_devices_from_db()
    if not devices:
        logging.warning("Нет устройств для мониторинга.")
        return

    monitoring_tasks = [asyncio.create_task(monitor_device(dev)) for dev in devices]
    await asyncio.gather(*monitoring_tasks, status_updater(), periodic_discovery())


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Приложение остановлено.")