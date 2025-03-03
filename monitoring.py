import asyncio
from ipaddress import IPv4Network
import logging
import settings
import aiosqlite
from snmp_utils import get_snmp_data, is_device_available
from database import update_device_data, update_device_status, log_status_change, get_devices_from_db

logger = logging.getLogger(__name__)

async def discover_devices(network: str, community: str):
    logger.info(f"Начало сканирования сети {network}")
    print(f"Начало сканирования сети {network}")
    net = IPv4Network(network, strict=False)
    semaphore = asyncio.Semaphore(settings.SCAN_SEMAPHORE_LIMIT)
    devices_to_add = []

    async def check_ip(ip):
        async with semaphore:
            device = {"ip": str(ip), "community": community}
            if await is_device_available(device):
                model = await get_snmp_data(device, settings.MODEL_OID)
                serial = await get_snmp_data(device, settings.SERIAL_OID)
                if model and serial:
                    devices_to_add.append((str(ip), community, model, serial))
                    logger.info(f"Обнаружено устройство: {ip} - {model}")
                    print(f"Обнаружено устройство: {ip} - {model}")

    tasks = [check_ip(ip) for ip in net.hosts()]
    await asyncio.gather(*tasks)

    if devices_to_add:
        async with aiosqlite.connect('pm_data.db') as conn:
            await conn.executemany(
                'INSERT OR IGNORE INTO devices (ip_address, community, model, serial) VALUES (?, ?, ?, ?)',
                devices_to_add
            )
            await conn.commit()
            logger.info(f"Добавлено {len(devices_to_add)} новых устройств")
            print(f"Добавлено {len(devices_to_add)} новых устройств")
    else:
        logger.warning(f"Не обнаружено новых устройств в сети {network}")
        print(f"Не обнаружено новых устройств в сети {network}")

async def monitor_device(device):
    prev_status = None
    while True:
        try:
            if not await is_device_available(device):
                logger.warning(f"Устройство {device['ip_address']} недоступно")
                print(f"Устройство {device['ip_address']} недоступно")
                await asyncio.sleep(settings.RETRY_INTERVAL)
                continue
            data = {name: await get_snmp_data(device, oid) for oid, name in settings.KYOCERA_OIDS.items()}
            current_status = data.get('Статус устройства')
            if prev_status and current_status != prev_status:
                await log_status_change(device['id'], 'status_change', f"Статус изменился: {prev_status} → {current_status}")
            prev_status = current_status
            await update_device_data(device, data)
            await update_device_status(device['id'], current_status)
            await asyncio.sleep(settings.MONITOR_INTERVAL)
        except Exception as e:
            logger.error(f"Ошибка мониторинга {device['ip_address']}: {e}")
            print(f"Ошибка мониторинга {device['ip_address']}: {e}")
            await asyncio.sleep(settings.RETRY_INTERVAL)

async def periodic_discovery():
    while True:
        await discover_devices(settings.SCAN_NETWORK, settings.SCAN_COMMUNITY)
        await asyncio.sleep(3600)  # Каждые час

async def status_updater():
    while True:
        try:
            devices = await get_devices_from_db()
            if not devices:
                logger.warning("Нет устройств для обновления статуса")
                print("Нет устройств для обновления статуса")
                await asyncio.sleep(60)
                continue
            tasks = [
                update_device_status(
                    dev['id'],
                    await get_snmp_data({'ip': dev['ip_address'], 'community': dev['community']}, settings.STATUS_OID)
                )
                for dev in devices
            ]
            await asyncio.gather(*tasks)
            logger.info("Статус всех устройств обновлен")
            print("Статус всех устройств обновлен")
        except Exception as e:
            logger.error(f"Ошибка в status_updater: {e}")
            print(f"Ошибка в status_updater: {e}")
        finally:
            await asyncio.sleep(60)  # Каждую минуту