from pysnmp.hlapi.v3arch.asyncio import *
import logging
from settings import STATUS_OID, SNMP_TIMEOUT, SNMP_RETRIES

logger = logging.getLogger(__name__)

async def get_snmp_data(device, oid, retries=3):
    snmp_engine = SnmpEngine()  # Локальный экземпляр
    for attempt in range(retries):
        try:
            auth_data = CommunityData(device["community"], mpModel=0)
            transport = await UdpTransportTarget.create(
                (device['ip'], 161),
                timeout=SNMP_TIMEOUT,
                retries=SNMP_RETRIES
            )
            iterator = get_cmd(snmp_engine, auth_data, transport, ContextData(), ObjectType(ObjectIdentity(oid)))
            errorIndication, errorStatus, errorIndex, varBinds = await iterator
            if errorIndication:
                logger.warning(f"{device['ip']}: Ошибка SNMP (попытка {attempt + 1}): {errorIndication}")
                print(f"{device['ip']}: Ошибка SNMP (попытка {attempt + 1}): {errorIndication}")
                continue
            for varBind in varBinds:
                value = decode_snmp_value(varBind[1])
                logger.debug(f"Получено значение для {device['ip']} OID {oid}: {value}")
                return value
        except Exception as e:
            logger.error(f"Ошибка SNMP-запроса к {device['ip']}: {e}")
            print(f"Ошибка SNMP-запроса к {device['ip']}: {e}")
        finally:
            snmp_engine.close_dispatcher()
    return None

def decode_snmp_value(value):
    try:
        if isinstance(value, OctetString):
            return value.asOctets().decode('utf-8', errors='ignore').strip()
        return int(value) if value.isValue else str(value)
    except Exception as e:
        logger.error(f"Ошибка декодирования: {e}")
        print(f"Ошибка декодирования: {e}")
        return None

async def is_device_available(device):
    return await get_snmp_data(device, STATUS_OID) is not None