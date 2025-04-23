# __init__.py in the project root
from server.server import DistributedServer, serve
from client.client import DistributedClient

__all__ = ['DistributedServer', 'DistributedClient', 'serve']