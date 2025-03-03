import asyncio
import logging
from database import init_db, get_devices_from_db
from monitoring import monitor_device, periodic_discovery, status_updater, discover_devices
import settings

logging.basicConfig(**settings.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

async def main():
    try:
        await init_db()

        # Сначала выполняем сканирование сети, если устройств нет
        devices = await get_devices_from_db()
        if not devices:
            logger.warning("Нет устройств в базе данных. Запускаем сканирование сети.")
            print("Нет устройств в базе данных. Запускаем сканирование сети.")
            await discover_devices(settings.SCAN_NETWORK, settings.SCAN_COMMUNITY)
            devices = await get_devices_from_db()  # Повторно получаем устройства после сканирования

        logger.info(f"Найдено устройств для мониторинга: {len(devices)}")
        print(f"Найдено устройств для мониторинга: {len(devices)}")
        if not devices:
            logger.error("После сканирования сеть не содержит доступных устройств. Программа завершится.")
            print("После сканирования сеть не содержит доступных устройств. Программа завершится.")
            return

        # Создаем задачи для мониторинга
        tasks = [monitor_device(dev) for dev in devices]
        tasks.extend([periodic_discovery(), status_updater()])
        logger.info("Запуск задач мониторинга...")
        print("Запуск задач мониторинга...")
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
        print("Приложение остановлено пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())