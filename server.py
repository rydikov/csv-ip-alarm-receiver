import asyncio
import logging

from dataclasses import dataclass

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

logger = logging.getLogger(__name__)

SERVICE_TEST_REPORT_CODE = 602
CONTACT_ID_LENGTH = 11
MIN_MESSAGE_LENGTH = 4

EVENT_CODES = {
    100: 'Medical Emergency',
    101: 'Fire Alarm',
    130: 'Burglary',
    137: 'Tamper',
    570: 'Bypass',
    110: 'Power Outage',
    120: 'Panic Alarm',
    602: 'Service Test Report',
    407: 'Remote Arming/Disarming',
    401: 'Open/Close by User',
    441: 'Stay Arming'
}

EVENT_QUALS = {
    1: 'New event or opening',
    3: 'New restore or closing',
    6: 'Previous event',
}


class InvalidEventException(Exception):
    pass


@dataclass
class Event:
    """
    Data example: user,password,AXPRO,18340101501
    """

    raw: str
    username: str
    password: str
    client_code: str
    cid: str

    message_type: int
    event_qualifier: int
    event_code: int
    group: int
    sensor_or_user: int

    @classmethod
    def from_data(cls, data):

        message = data.split(',')

        if len(message) < MIN_MESSAGE_LENGTH:
            raise InvalidEventException("Invalid message size")

        raw = data
        username, password, client_code, cid = message[:MIN_MESSAGE_LENGTH]

        if len(cid) != CONTACT_ID_LENGTH:
            raise InvalidEventException("Invalid CID length")

        try:
            message_type = int(cid[0:2])
            event_qualifier = int(cid[2])
            event_code = int(cid[3:6])
            group = int(cid[6:8])
            sensor_or_user = int(cid[8:11])
        except ValueError as e:
            raise InvalidEventException(f"Invalid CID format {e}")

        return cls(
            raw,
            username,
            password,
            client_code,
            cid,
            message_type,
            event_qualifier,
            event_code,
            group,
            sensor_or_user
        )

    def is_test(self):
        return self.event_code == SERVICE_TEST_REPORT_CODE

    @property
    def description(self):
        if description := EVENT_CODES.get(self.event_code):
            return f"{description} ({self.event_code})"
        else:
            return f"{self.event_code}"

    @property
    def qualifier(self):
        if qualifier := EVENT_QUALS.get(self.event_qualifier):
            return f"{qualifier} ({self.event_qualifier})"
        else:
            return f"{self.event_qualifier}"


class ContactIDServer:
    def __init__(self, host='0.0.0.0', port=5000, callback=None):
        self.host = host
        self.port = port
        self.callback = callback

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f'Connection from {addr}')
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                try:
                    decoded_data = data.decode().strip()
                except UnicodeDecodeError as e:
                    logger.error(f"Decode error: {e}")
                    break
                try:
                    event = Event.from_data(decoded_data)
                except InvalidEventException as e:
                    logger.error(f"Invalid event: {decoded_data} Error: {e}")
                    break
                else:
                    self.callback(event)

                writer.write(decoded_data.encode())
                await writer.drain()  # Ensure the data is sent
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f'Connection closed for {addr}')

    async def run_server(self):
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        addr = server.sockets[0].getsockname()
        logger.info(f'Serving on {addr}')

        async with server:
            await server.serve_forever()

    def start(self):
        try:
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            logger.info("Server stopped.")


allowed_clients = ['AXPRO']


# Define the callback function to process received alarm data
def process_alarm(event):
    """
    Check if the client code is in the allowed list
    and the event code is not '602' (suppress polling messages)
    """
    if event.client_code in allowed_clients:
        if not event.is_test():
            logger.info(f"Qualifier: {event.qualifier}. Event: {event.description} on partition: {event.group}. Zone/User: {event.sensor_or_user}. Message: {event.raw}")
        else:
            logger.info("Test ok")


server = ContactIDServer(callback=process_alarm)

# Start the server to listen for incoming alarm messages
server.start()
