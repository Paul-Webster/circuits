from circuits import Component
from circuits.net.sockets import Write

class Server(Component):

    channel = "server"

    def __init__(self):
        super(Server, self).__init__()

        self.data = ""
        self.host = None
        self.port = None
        self.client = None
        self.ready = False
        self.closed = False
        self.connected = False
        self.disconnected = False

    def ready(self, component):
        self.ready = True
        self.host, self.port = component._sock.getsockname()[:2]

    def closed(self):
        self.closed = True

    def connect(self, sock, *args):
        self.connected = True
        self.client = args
        self.fire(Write(sock, b"Ready"))

    def disconnect(self, sock):
        self.client = None
        self.disconnected = True

    def read(self, sock, data):
        self.data = data
        return data
