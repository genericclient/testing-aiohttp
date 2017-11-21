_version = "0.0.7"
__version__ = VERSION = tuple(map(int, _version.split('.')))


from .rsps import RouteManager, RouteNotCalledError, RouteNotFoundError  # noqa
