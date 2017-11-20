from enum import Enum, unique
from functools import partialmethod
from collections import defaultdict, namedtuple
from unittest import mock
from urllib.parse import parse_qsl

import inspect
import json as json_mod

from aiohttp import payload
from aiohttp.client_reqrep import ClientResponse
from multidict import MultiDict, CIMultiDict
from yarl import URL


@unique
class HTTPMethods(Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'
    OPTIONS = 'OPTIONS'
    HEAD = 'HEAD'


GET = HTTPMethods.GET
POST = HTTPMethods.POST
PUT = HTTPMethods.PUT
PATCH = HTTPMethods.PATCH
DELETE = HTTPMethods.DELETE
OPTIONS = HTTPMethods.OPTIONS
HEAD = HTTPMethods.HEAD


class MockError(Exception):
    pass


class RouteNotFoundError(MockError):
    pass


class RouteNotCalledError(MockError):
    pass


AddOption = namedtuple('AddOption', ('querystring', 'match_querystring'))
AddedResponse = namedtuple('AddedResponse', ('add_options', 'response'))
CallbackResponse = namedtuple('CallbackResponse', ('cb', 'args', 'kwargs'))
Request = namedtuple('Request', ('method', 'url', 'headers', 'data', 'body'))


class RouteManager(object):
    GET = GET
    POST = POST
    PUT = PUT
    PATCH = PATCH
    DELETE = DELETE
    OPTIONS = OPTIONS
    HEAD = HEAD

    def add(self, method, url, *, data=None, json=None, text=None, content_type=None, match_querystring=False, headers=None, status=200):  # noqa
        url = URL(url)
        path = url.with_query({})
        add_options = AddOption(
            querystring=url.query_string,
            match_querystring=match_querystring,
        )

        if isinstance(method, HTTPMethods):
            method = method.name

        body = ''
        if json is not None:
            content_type = content_type or 'application/json'
            body = json_mod.dumps(json)
        elif data is not None:
            content_type = content_type or 'application/octet-stream'
            body = data
        elif text is not None:
            content_type = content_type or 'text/plain'
            body = text

        headers = CIMultiDict(headers or {})

        response = self.make_response(
            method, URL(url), body=body, status=status, content_type=content_type, headers=headers,
        )

        self.routes[(method.upper(), str(path))].append(AddedResponse(add_options, response))

    def add_callback(self, method, url, callback, *args, **kwargs):  # noqa
        callback_response = CallbackResponse(callback, args, kwargs)
        if isinstance(method, HTTPMethods):
            method = method.name
        self.routes[(method.upper(), url)].append(callback_response)

    def __enter__(self):
        self.urls_not_found = []
        self.routes = defaultdict(list)

        self.start()
        return self

    async def __aenter__(self):
        self.urls_not_found = []
        self.routes = defaultdict(list)

        self.start()

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
        self.stop()

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.stop()

    def start(self):
        async def unbound_request(session, method, url, *,
                                  params=None, data=None, json=None, headers=None, **kwargs):
            req = self.make_request(session, method, url,
                                    params=params, data=data, json=json, headers=headers, **kwargs)
            resp = await self.route(req)
            return resp

        self._patchers = []

        for method in HTTPMethods:
            func = partialmethod(unbound_request, method.name)
            patcher = mock.patch(
                'aiohttp.client.ClientSession.' + method.name.lower(), func,
            )
            patcher.start()
            self._patchers.append(patcher)

        patcher = mock.patch(
            'aiohttp.client.ClientSession._request', unbound_request,
        )
        patcher.start()
        self._patchers.append(patcher)

    def stop(self):
        [patcher.stop() for patcher in self._patchers]

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

    def find(self, method, path, query_string):
        route = self.routes.get((method, path), []).pop()
        if isinstance(route, AddedResponse):
            if route.add_options.match_querystring is True and route.add_options.querystring != query_string:
                raise IndexError
        return route

    def make_response(self, method, url, *, body='', status=200, content_type='application/octet-stream', headers=None):
        if headers is None:
            headers = {}
        headers.setdefault('Content-Type', content_type)

        resp = ClientResponse(method, url)
        resp._content = body.encode()
        resp.headers = headers
        resp.status = status
        return resp

    def make_request(self, session, method, url, *,
                     params=None, data=None, json=None, headers=None, **kwargs):
        if data is not None and json is not None:
            raise ValueError(
                'data and json parameters can not be used at the same time')
        elif json is not None:
            data = payload.JsonPayload(json, dumps=session._json_serialize)

        headers = session._prepare_headers(headers)

        return session._request_class(
            method, URL(url), loop=session._loop,
            response_class=session._response_class,
            session=session, auto_decompress=session._auto_decompress,
            params=params, data=data, headers=headers, **kwargs)

    def make_server_request(self, client_request):
        if client_request.body.content_type == 'application/x-www-form-urlencoded':
            data = MultiDict(parse_qsl(
                client_request.body._value.decode(client_request.body.encoding)
            ))
        elif client_request.body.content_type == 'application/json':
            data = json_mod.loads(client_request.body._value.decode(client_request.body.encoding))
        else:
            data = client_request.body._value

        return Request(
            client_request.method,
            client_request.url,
            client_request.headers,
            data,
            client_request.body,
        )

    async def route(self, request):
        method = request.method
        path = request.url.with_query({})
        querystring = request.url.query_string
        try:
            added_response = self.find(method, str(path), querystring)
        except IndexError:
            self.urls_not_found.append("{} {}".format(method, path))
            return self.make_response(method, request.url, status=499, content_type='unknown')

        if isinstance(added_response, AddedResponse):
            return added_response.response
        elif isinstance(added_response, CallbackResponse):
            cb, args, kwargs = added_response

            server_request = self.make_server_request(request)
            if inspect.iscoroutinefunction(cb):
                status, headers, body = await cb(server_request)
            else:
                status, headers, body = cb(server_request)
            return self.make_response(method, request.url, body=body, headers=headers, status=status)
