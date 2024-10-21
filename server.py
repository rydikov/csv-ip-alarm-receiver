# Importing necessary modules for network communication and data handling
import asyncio
import csv
import logging

from io import StringIO

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)


# Define a class to handle Contact ID protocol over TCP/IP
class ContactIDServer:
    def __init__(self, host='0.0.0.0', port=5000, callback=None):
        self.host = host  # IP address the server will listen on
        self.port = port  # Port number the server will listen on
        self.callback = callback  # Callback function to handle processed data
        # self.server_socket = None  # Socket object for the server
        # Dictionary of predefined event codes and their descriptions - Not at all compleate however covers some basics
        self.event_codes = {
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
        # Dictionary of predefined event qualifiers and their descriptions
        self.event_quals = {
            '1': 'New Event or Opening/Disarm',
            '3': 'New Restore or Closing/Arming',
            '6': 'Previously reported condition still present (status report)',
        }

    # Method to find the description for event qualifiers using their ID
    def find_event_quals(self, event_id):
        description = self.event_quals.get(event_id)
        if description:
            return f"{description} ({event_id})"
        else:
            return f"{event_id}"

    # Method to find the description for event codes using their ID
    def find_event_description(self, event_id):
        description = self.event_codes.get(event_id)
        if description:
            return f"{description} ({event_id})"
        else:
            return f"{event_id}"

    # Method to parse the Contact ID message format
    def parse_contact_id_message(self, contact_id_string):
        if len(contact_id_string) != 11:
            logger.info(f"Invalid message length: {contact_id_string}")
            return ["Invalid message length"]

        # Splitting the Contact ID message into components
        result = [
            contact_id_string[0:2],  # Message Type
            contact_id_string[2],    # Event Qualifier
            contact_id_string[3:6],  # Account Number
            contact_id_string[6:8],  # Group or Zone
            contact_id_string[8:11], # Event Code
        ]
        return result
    
    # Method to parse CSV formatted alarm data received over TCP/IP
    def parse_csv_alarm_data(self, data):
        f = StringIO(data)
        reader = csv.reader(f, delimiter=',')
        for row in reader:
            if row and len(row) >= 4:
                result = [
                    row[0],  # username
                    row[1],  # password
                    row[2],  # client code
                    row[3],  # cid
                    self.parse_contact_id_message(row[3]),  # Parsed CID data
                ]
        f.close()
        self.callback(result)
        return result

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f'Connection from {addr}')
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                decoded_message = data.decode().strip()
                self.parse_csv_alarm_data(decoded_message)  # Process decoded message
                writer.write(decoded_message.encode())
                await writer.drain()  # Ensure the data is sent
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            print(f'Connection closed for {addr}')

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
            print("Server stopped.")

#######

allowed_clients = ['AXPRO']

# Define the callback function to process received alarm data
def process_alarm(data):
    # Check if the client code is in the allowed list and the event code is not '602' (suppress polling messages)
    if data[2] in allowed_clients:
        if data[4][2] != '602':
            logger.info("Data:  " + str(data))  # Print the entire data list received from the alarm
            # logger.info("Auth User:  " + data[0]) #Print the Username used for authentication
            # logger.info("Auth Pass:  " + data[1]) #Print the Password used for authentication
            logger.info("Event Qualifier: " + server.find_event_quals(data[4][1]))  # Retrieve and print the event qualifier description
            logger.info("Event Code: " + server.find_event_description(data[4][2]))  # Retrieve and print the event code description
            logger.info("Partition: " + data[4][3])  # Print the partition where the event occurred
            logger.info("Zone / User: " + data[4][4])  # Print the zone or user associated with the event
            # logger.info("Client Code: " + data[2])  # Print the client code associated with the data
            logger.info("----------------------------")  # Print separators for clarity in output)
        else:
            logger.info("Test ok")  # Print test OK
    

# Initialize the ContactIDServer with the specified port and the callback function
server = ContactIDServer(callback=process_alarm)

# Start the server to listen for incoming alarm messages
server.start()