from collections import defaultdict, namedtuple
from urllib.parse import urlparse

import inspect

from aiohttp.test_utils import AioHTTPTestCase
from aiohttp import web


class MockError(Exception):
    pass


class RouteNotFoundError(MockError):
    pass


class RouteNotCalledError(MockError):
    pass


AddedResponse = namedtuple('AddedResponse', ('add_options', 'response'))
AddOption = namedtuple('AddOption', ('url', 'match_querystring'))


class RouteManager(object):
    def find(self, method, path, path_qs):
        route = self.routes.get((method, path), []).pop()
        if isinstance(route, AddedResponse):
            if route.add_options.match_querystring is True and route.add_options.url != path_qs:
                raise IndexError
        return route

    def add(self, method, url, data=None, *, text=None, body=None, match_querystring=False, **kwargs):  # noqa
        add_options = AddOption(
            url=url,
            match_querystring=match_querystring,
        )

        path = urlparse(url).path

        if data is not None:
            response = web.json_response(data, **kwargs)  # noqa
        else:
            response = web.Response(text=text, body=body, **kwargs)
        self.routes[(method.upper(), path)].append(AddedResponse(add_options, response))

    def add_callback(self, method, url, callback, *args, **kwargs):  # noqa
        self.routes[(method.upper(), url)].append((callback, args, kwargs))

    def __enter__(self):
        self.urls_not_found = []
        self.routes = defaultdict(list)
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
        if self.urls_not_found:
            urls = self.urls_not_found[:]
            self.urls_not_found = []
            raise RouteNotFoundError(
                "Those url were not found:\n\t"
                "{}".format('\n\t'.join(urls))
            )

        routes = [
            route
            for route, responses in self.routes.items()
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

    async def route(self, request):
        method = request.method
        path = request.path
        path_qs = request.path_qs
        try:
            added_response = self.find(method, path, path_qs)
        except IndexError:
            self.urls_not_found.append("{} {}".format(method, path))
            return web.Response(status=499, content_type='unknown')

        if isinstance(added_response, AddedResponse):
            return added_response.response
        elif isinstance(added_response, tuple):
            cb, args, kwargs = added_response
            if inspect.iscoroutinefunction(cb):
                status, headers, body = await cb(request)
            else:
                status, headers, body = cb(request)
            return web.Response(body=body, headers=headers, status=status, *args, **kwargs)


class MockRoutesTestCase(AioHTTPTestCase):
    async def get_application(self):
        app = web.Application()
        self.route_manager = RouteManager()
        app.router.add_route('*', '/{path_info:.*}', self.route_manager.route)
        return app

    def mock_response(self, *args, **kwargs):
        return self.route_manager
