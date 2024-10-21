import asyncio
import csv
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

SERVICE_TEST_REPORT_CODE = '602'
CONTACT_ID_LENGTH = 11
MIN_MESSAGE_LENGTH = 4

EVENT_CODES = {
    '100': 'Medical Emergency',
    '101': 'Fire Alarm',
    '130': 'Burglary',
    '137': 'Tamper',
    '570': 'Bypass',
    '110': 'Power Outage',
    '120': 'Panic Alarm',
    '602': 'Service Test Report',
    '407': 'Remote Arming/Disarming',
    '401': 'Open/Close by User',
    '441': 'Stay Arming'
}

EVENT_QUALS = {
    '1': 'New event or opening',
    '3': 'New restore or closing',
    '6': 'Previous event',
}


class InvalidEventException(Exception):
    pass

class Event:
    """
    Data example: ,,AXPRO,18340101501
    """
    def __init__(self, data):

        message = data.split(',')

        if len(message) < MIN_MESSAGE_LENGTH:
            raise InvalidEventException("Invalid message size")
        
        self.raw = data
        
        self.username = message[0]
        self.password = message[1]
        self.client_code = message[2]
        self.cid = message[3]

        if len(self.cid) != CONTACT_ID_LENGTH:
            raise InvalidEventException("Invalid CID lenght")
        
        self.message_type = self.cid[0:2]
        self.event_qualifier = self.cid[2]
        self.event_code = self.cid[3:6]
        self.group = self.cid[6:8]
        self.sensor_or_user = self.cid[8:11]

    def is_test(self):
        return self.event_code == SERVICE_TEST_REPORT_CODE

    @property
    def event_description(self):
        description = EVENT_CODES.get(self.event_code)
        if description:
            return f"{description} ({self.event_code})"
        else:
            return f"{self.event_code}"

    @property        
    def event_quals(self):
        qualifier = EVENT_QUALS.get(self.event_qualifier)
        if qualifier:
            return f"{qualifier} ({self.event_qualifier})"
        else:
            return f"{self.event_qualifier}"


class ContactIDServer:
    def __init__(self, host='0.0.0.0', port=5001, callback=None):
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
                decoded_message = data.decode().strip()

                try:
                    event = Event(decoded_message)
                except InvalidEventException as e:
                    logger.error(f"Invalid event: {decoded_message} Error: {e}")
                else:
                    self.callback(event)
                
                writer.write(decoded_message.encode())
                await writer.drain()  # Ensure the data is sent
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f'Connection closed for {addr}')

    async def run_server(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = server.sockets[0].getsockname()
        logger.info(f'Serving on {addr}')

        async with server:
            await server.serve_forever()

    def start(self):
        try:
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            logger.info("Server stopped.")

#######

allowed_clients = ['AXPRO']

# Define the callback function to process received alarm data
def process_alarm(event):
    # Check if the client code is in the allowed list and the event code is not '602' (suppress polling messages)
    if event.client_code in allowed_clients:
        if not event.is_test():
            logger.info(f"Data received: {event.raw}")
            logger.info(f"Qualifier: {event.event_quals}. Event: {event.event_description} on partition: {event.group}. Zone/User: {event.sensor_or_user}")
            logger.info("---------------------------")
        else:
            logger.info("Test ok")
    

# Initialize the ContactIDServer with the specified port and the callback function
server = ContactIDServer(callback=process_alarm)

# Start the server to listen for incoming alarm messages
server.start()