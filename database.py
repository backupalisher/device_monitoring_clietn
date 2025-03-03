import aiosqlite
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect('pm_data.db') as conn:
        await conn.executescript('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE,
                community TEXT,
                model TEXT,
                serial TEXT,
                page_count INTEGER DEFAULT 0,
                toner_level INTEGER DEFAULT 0,
                scan_count INTEGER DEFAULT 0,
                uptime INTEGER DEFAULT 0,
                last_updated DATETIME
            );
            CREATE TABLE IF NOT EXISTS device_status (
                device_id INTEGER PRIMARY KEY,
                status TEXT,
                last_checked DATETIME,
                FOREIGN KEY(device_id) REFERENCES devices(id)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER,
                type TEXT,
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(device_id) REFERENCES devices(id)
            );
        ''')
        await conn.commit()
        logger.info("База данных инициализирована")
        print("База данных инициализирована")

async def get_devices_from_db():
    async with aiosqlite.connect('pm_data.db') as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM devices") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def update_device_data(device, data):
    try:
        async with aiosqlite.connect('pm_data.db') as conn:
            await conn.execute('''
                UPDATE devices SET
                    page_count = ?,
                    toner_level = ?,
                    scan_count = ?,
                    uptime = ?,
                    last_updated = ?
                WHERE id = ?
            ''', (
                int(data.get('page_count', 0)) if data.get('page_count') else 0,
                int(data.get('toner_level', 0)) if data.get('toner_level') else 0,
                int(data.get('scan_count', 0)) if data.get('scan_count') else 0,
                int(data.get('Uptime', 0)) if data.get('Uptime') else 0,
                datetime.now().isoformat(),
                device['id']
            ))
            await conn.commit()
            logger.info(f"Данные {device['ip_address']} обновлены")
            print(f"Данные {device['ip_address']} обновлены")
    except Exception as e:
        logger.error(f"Ошибка обновления {device['ip_address']}: {e}")
        print(f"Ошибка обновления {device['ip_address']}: {e}")

async def update_device_status(device_id, status):
    try:
        async with aiosqlite.connect('pm_data.db') as conn:
            await conn.execute('''
                INSERT OR REPLACE INTO device_status (device_id, status, last_checked)
                VALUES (?, ?, ?)
            ''', (device_id, status, datetime.now().isoformat()))
            await conn.commit()
            logger.info(f"Статус устройства {device_id} обновлен: {status}")
            print(f"Статус устройства {device_id} обновлен: {status}")
    except Exception as e:
        logger.error(f"Ошибка обновления статуса устройства {device_id}: {e}")
        print(f"Ошибка обновления статуса устройства {device_id}: {e}")

async def log_status_change(device_id, event_type, message):
    try:
        async with aiosqlite.connect('pm_data.db') as conn:
            await conn.execute('''
                INSERT INTO events (device_id, type, message)
                VALUES (?, ?, ?)
            ''', (device_id, event_type, message))
            await conn.commit()
            logger.info(f"Событие для устройства {device_id}: {event_type} - {message}")
            print(f"Событие для устройства {device_id}: {event_type} - {message}")
    except Exception as e:
        logger.error(f"Ошибка записи события для устройства {device_id}: {e}")
        print(f"Ошибка записи события для устройства {device_id}: {e}")