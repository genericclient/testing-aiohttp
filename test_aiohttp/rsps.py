from collections import defaultdict
from concurrent.futures import CancelledError
import inspect

from aiohttp.client_exceptions import ServerDisconnectedError
from aiohttp.test_utils import AioHTTPTestCase
from aiohttp import web


class MockError(Exception):
    pass


class RouteNotFoundError(CancelledError):
    pass


class RouteNotCalledError(MockError):
    pass


class RouteManager(object):

    def __init__(self, testcase, *args, **kwargs):
        self.testcase = testcase

    def add(self, method, url, data=None, *, text=None, body=None, status=200,
                  reason=None, headers=None, content_type=None):  # noqa
        if data is not None:
            response = web.json_response(data, status=status)  # noqa
        else:
            response = web.Response(text=text, body=body, status=status, reason=reason,
                    headers=headers, content_type=content_type)
        self.testcase.routes[(method.upper(), url)].append(response)

    def add_callback(self, method, url, callback, *args, **kwargs):  # noqa
        self.testcase.routes[(method.upper(), url)].append((callback, args, kwargs))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        @brief      Checks that all routes have been called.

        @param      self       The object
        @param      exc_type   The exc type
        @param      exc_value  The exc value
        @param      traceback  The traceback

        @return     None
        """
        if exc_type is ServerDisconnectedError and self.testcase.url_not_found:
            exc = self.testcase.url_not_found
            self.testcase.url_not_found = None
            raise exc

        routes = [
            route
            for route, responses in self.testcase.routes.items()
            if len(responses)
        ]
        if len(routes):
            urls = [
                "{} {}".format(method, url)
                for method, url in routes
            ]
            raise RouteNotCalledError(
                "Those url were not called:\n\t"
                "{}".format('\n\t'.join(urls))
            )


class MockRoutesTestCase(AioHTTPTestCase):
    def setUp(self):
        super(MockRoutesTestCase, self).setUp()
        self.routes = defaultdict(list)
        self.url_not_found = []

    async def route(self, request):
        method = request.method
        path = request.path
        try:
            response = self.routes.get((method, path), []).pop()
        except IndexError:
            exc = RouteNotFoundError("No url found for `{} {}`".format(method, path))
            self.url_not_found = exc
            raise exc

        if isinstance(response, web.Response):
            return response
        elif isinstance(response, tuple):
            cb, args, kwargs = response
            if inspect.iscoroutinefunction(cb):
                status, headers, body = await cb(request)
            else:
                status, headers, body = cb(request)
            return web.Response(body=body, headers=headers, status=status, *args, **kwargs)

    async def get_application(self):
        app = web.Application()
        app.router.add_route('*', '/{path_info:.*}', self.route)
        return app

    def mock_response(self, *args, **kwargs):
        return RouteManager(self, *args, **kwargs)
