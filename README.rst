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

``rsps.MockRoutesTestCase``
---------------------------

The ``MockRoutesTestCase`` will set up a mock application for mocking response.

The API is inspired by the ``responses`` library::

    from aiohttp.test_utils import unittest_run_loop

    from testing_aiohttp.rsps import MockRoutesTestCase


    # Create your tests here.
    class MyTestCase(MockRoutesTestCase):
        @unittest_run_loop
        async def test_response_data(self):
            with self.mock_response() as rsps:
                rsps.add('GET', '/users', data=[
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

                response = await self.client.get('/users')
                self.assertEqual(response, 200)
                users = await response.json()
                self.assertEqual(len(users), 2)

::

    from aiohttp.test_utils import unittest_run_loop

    from testing_aiohttp.rsps import MockRoutesTestCase


    async def request_callback(request):
        return (200, {}, await request.text())


    class MyTestCase(MockRoutesTestCase):

        @unittest_run_loop
        async def test_endpoint_detail_route(self):
            with self.mock_response() as rsps:
                rsps.add_callback(
                    'POST', '/users/2/notify',
                    callback=request_callback,
                    content_type='application/json',
                )

                response = await self.generic_client.users(id=2).notify(unread=3)
                self.assertEqual(await response.json(), {'unread': 3})

::

    from aiohttp.test_utils import unittest_run_loop

    from testing_aiohttp.rsps import MockRoutesTestCase


    class MyTestCase(MockRoutesTestCase):
        @unittest_run_loop
        async def test_response_match_querystring(self):
            with self.mock_response() as rsps:
                rsps.add('GET', '/users?username=user1', [
                    {
                        'id': 1,
                        'username': 'user1',
                        'group': 'watchers',
                    },
                ], match_querystring=True)

                response = await self.client.get('/users', params={'username': 'user1'})
                self.assertEqual(response.status, 200)
                users = await response.json()
                self.assertEqual(len(users), 1)

            with self.assertRaises(RouteNotFoundError):
                with self.mock_response() as rsps:
                    rsps.add('GET', '/users?username=user1', [
                        {
                            'id': 1,
                            'username': 'user1',
                            'group': 'watchers',
                        },
                    ], match_querystring=True)

                    await self.client.get('/users')


License
=======

Licensed under the MIT License.
