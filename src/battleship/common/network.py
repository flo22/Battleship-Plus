import inspect
import asyncio.streams
from .protocol import ProtocolMessage, parse_from_stream


# Opens one connection to a server, thus internally has one reader and one writer.
# Sends protocol messages using the internal writer, listens for incoming messages and
# calls a callback for the message
class BattleshipClient:
    def __init__(self, server, port, loop, msg_callback, closed_callback):
        if not inspect.iscoroutinefunction(msg_callback):
            raise TypeError("msg_callback must be a coroutine")
        self.msg_callback = msg_callback
        self.closed_callback = closed_callback
        self.server = server
        self.port = port
        self.loop = loop
        self.reader = None
        self.writer = None
        self.receiving_task = None

    async def connect(self):
        self.reader, self.writer = await asyncio.streams.open_connection(
            self.server, self.port, loop=self.loop)
        self.receiving_task = asyncio.Task(parse_from_stream(self.reader, self.writer, self.msg_callback))
        self.receiving_task.add_done_callback(self._server_closed_connection)

    async def send(self, msg: ProtocolMessage):
        await msg.send(self.writer)

    def _server_closed_connection(self, task):
        self.closed_callback()

    def close(self):
        self.writer.close()


class BattleshipServerClient:

    next_client_id = 1

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.id = BattleshipServerClient.next_client_id
        BattleshipServerClient.next_client_id += 1

    async def send(self, msg: ProtocolMessage):
        await msg.send(self.writer)


class BattleshipServer:

    def __init__(self, ip, port, loop, client_connected_callback):
        self.ip = ip
        self.port = port
        self.loop = loop
        self.client_connected_callback = client_connected_callback
        self.server = None
        self.clients = {}

    def _accept_client(self, client_reader, client_writer):
        """
        This method accepts a new client connection and creates a Task
        to handle this client.  self.clients is updated to keep track
        of the new client.
        """

        async def internal_msg_callback(msg: ProtocolMessage):
            await external_msg_callback(msg)

        def internal_client_done(task):
            external_disconnected_callback()
            del self.clients[task]

        # start a new Task to handle this specific client connection
        task = asyncio.Task(parse_from_stream(client_reader, client_writer, internal_msg_callback))
        client_obj = BattleshipServerClient(client_reader, client_writer)
        self.clients[task] = client_obj
        external_msg_callback, external_disconnected_callback = self.client_connected_callback(client_obj)
        if not inspect.iscoroutinefunction(external_msg_callback):
            raise TypeError("msg_callback must be a coroutine")
        task.add_done_callback(internal_client_done)

    def start(self):
        """
        Starts the TCP server, so that it listens on the specified port.
        For each client that connects, the accept_client method gets
        called.  This method runs the loop until the server sockets
        are ready to accept connections.
        """
        self.server = self.loop.run_until_complete(
            asyncio.streams.start_server(self._accept_client,
                                         self.ip, self.port,
                                         loop=self.loop))

    def stop(self):
        """
        Stops the TCP server, i.e. closes the listening socket(s).
        This method runs the loop until the server sockets are closed.
        """
        if self.server is not None:
            self.server.close()
            self.loop.run_until_complete(self.server.wait_closed())
            self.server = None
