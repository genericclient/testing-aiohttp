===============
testing-aiohttp
===============

.. image:: https://travis-ci.org/genericclient/testing-aiohttp.svg?branch=master
    :target: https://travis-ci.org/genericclient/testing-aiohttp

Testing utilities for `aiohttp`. Python 3.5+ only.


Installation
============

::

    $ pip install testing-aiohttp

Usage
=====

``AioLoopTestCase``
-------------------

A ``TestCase`` subclass to provides an asyncio loop, so that it can be used in conjuction with ``aiohttp.test_utils.unittest_run_loop``::

    from aiohttp.test_utils import unittest_run_loop

    from test_aiohttp import AioLoopTestCase

    async def add(a, b):
        return a + b

    # Create your tests here.
    class MyTestCase(AioLoopTestCase):
        @unittest_run_loop
        async def test_something_async(self):
            my_result = await add(1, 2)
            self.assertEqual(my_result, 3)

For convenience, it also provides ``setUpAsync`` and a ``tearDownAsync`` methods.

``RouteManager``
---------------------------

``RouteManager`` will mock up responses for `aiohttp.Client``.

The API is inspired by the ``responses`` library::

    from aiohttp import ClientSession
    from aiohttp.test_utils import unittest_run_loop

    from testing_aiohttp import AioLoopTestCase, RouteManager


    # Create your tests here.
    class MyTestCase(AioLoopTestCase):
        @unittest_run_loop
        async def test_response_data(self):
            with RouteManager() as rsps:
                rsps.add('GET', 'http://example.org/users', json=[
                    {
                        'id': 1,
                        'username': 'user1',
                        'group': 'watchers',
                    },
                    {
                        'id': 2,
                        'username': 'user2',
                        'group': 'watchers',
                    },
                ])

                async with ClientSession() as session:
                    response = await session.get('http://example.org/users')
                self.assertEqual(response, 200)
                users = await response.json()
                self.assertEqual(len(users), 2)

::

    from aiohttp import ClientSession
    from aiohttp.test_utils import unittest_run_loop

    from testing_aiohttp import AioLoopTestCase, RouteManager


    async def request_callback(request):
        return (200, {}, 'ok')


    class MyTestCase(AioLoopTestCase):

        @unittest_run_loop
        async def test_endpoint_detail_route(self):
            with RouteManager() as rsps:
                rsps.add_callback(
                    'POST', 'http://example.org/users/2/notify',
                    callback=request_callback,
                    content_type='application/json',
                )

                async with ClientSession() as session:
                    response = await session.post('http://example.org/users/2/notify')
                self.assertEqual(await response.text(), 'ok')

::
    from aiohttp import ClientSession
    from aiohttp.test_utils import unittest_run_loop

    from testing_aiohttp.rsps import AioLoopTestCase, RouteManager, RouteNotFoundError


    class MyTestCase(AioLoopTestCase):
        @unittest_run_loop
        async def test_response_match_querystring(self):
            with RouteManager() as rsps:
                rsps.add('GET', 'http://example.org/users?username=user1', json=[
                    {
                        'id': 1,
                        'username': 'user1',
                        'group': 'watchers',
                    },
                ], match_querystring=True)

                with ClientSession() as session:
                    response = await session.get('http://example.org/users', params={'username': 'user1'})
                self.assertEqual(response.status, 200)
                users = await response.json()
                self.assertEqual(len(users), 1)

            with self.assertRaises(RouteNotFoundError):
                with RouteManager() as rsps:
                    rsps.add('GET', 'http://example.org/users?username=user1', json=[
                        {
                            'id': 1,
                            'username': 'user1',
                            'group': 'watchers',
                        },
                    ], match_querystring=True)

                    with ClientSession() as session:
                        await session.get('http://example.org/users')


License
=======

Licensed under the MIT License.
