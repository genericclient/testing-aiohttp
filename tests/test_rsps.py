import json

from aiohttp import ClientSession
from asynctest import TestCase

from test_aiohttp import RouteManager, RouteNotCalledError, RouteNotFoundError


async def request_callback(request):
    return (200, {'Content-Type': 'text/plain'}, json.dumps(request.data))


# Create your tests here.
class RSPSTestCase(TestCase):
    BASE_URL = 'http://example.org'

    def setUp(self):
        super().setUp()
        self.session = ClientSession(loop=self.loop)

    async def test_response_data(self):
        with RouteManager() as rsps:
            async with self.session as client:
                rsps.add(rsps.GET, self.BASE_URL + '/users', json=[
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

                response = await client.get(self.BASE_URL + '/users')
                self.assertEqual(response.status, 200)
                users = await response.json()
                self.assertEqual(len(users), 2)

    async def test_response_status_code(self):
        with RouteManager() as rsps:
            rsps.add(rsps.GET, self.BASE_URL + '/users', json={'details': 'Not found'}, status=404)
            async with self.session as client:
                response = await client.get(self.BASE_URL + '/users')
                self.assertEqual(response.status, 404)

        with RouteManager() as rsps:
            rsps.add(rsps.POST, self.BASE_URL + '/users', json={'details': 'Success'}, status=201)
            async with self.session as client:
                response = await client.post(self.BASE_URL + '/users')
                self.assertEqual(response.status, 201)

    async def test_response_match_querystring(self):
        with RouteManager() as rsps:
            rsps.add(rsps.GET, self.BASE_URL + '/users?username=user1', json=[
                {
                    'id': 1,
                    'username': 'user1',
                    'group': 'watchers',
                },
            ], match_querystring=True)

            async with self.session as client:
                response = await client.get(self.BASE_URL + '/users', params={'username': 'user1'})
                self.assertEqual(response.status, 200)
                users = await response.json()
                self.assertEqual(len(users), 1)

        with self.assertRaises(RouteNotFoundError):
            with RouteManager() as rsps:
                rsps.add(rsps.GET, self.BASE_URL + '/users?username=user1', json=[
                    {
                        'id': 1,
                        'username': 'user1',
                        'group': 'watchers',
                    },
                ], match_querystring=True)

                async with self.session as client:
                    await client.get(self.BASE_URL + '/users')

    async def test_must_match_all(self):
        with self.assertRaises(RouteNotCalledError):
            with RouteManager() as rsps:
                rsps.add(rsps.GET, self.BASE_URL + '/users', json=[
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
                rsps.add(rsps.GET, self.BASE_URL + '/users/1', json=[
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

                async with self.session as client:
                    await client.get(self.BASE_URL + '/users/1')

    async def test_route_not_found(self):
        with self.assertRaises(RouteNotFoundError):
            with RouteManager():
                async with self.session as client:
                    await client.get(self.BASE_URL + '/users')

    async def test_response_text(self):
        with RouteManager() as rsps:
            rsps.add(rsps.GET, self.BASE_URL + '/users', text='ok')

            async with self.session as client:
                response = await client.get(self.BASE_URL + '/users')
        self.assertEqual(response.content_type, 'text/plain')
        text = await response.text()
        self.assertEqual(text, 'ok')

    async def test_response_content_type(self):
        with RouteManager() as rsps:
            rsps.add(rsps.GET, self.BASE_URL + '/users', text='<h1>ok</h1>', content_type='text/html')

            async with self.session as client:
                response = await client.get(self.BASE_URL + '/users')
                self.assertEqual(response.content_type, 'text/html')

    async def test_response_callback(self):
        with RouteManager() as rsps:
            rsps.add_callback(rsps.POST, self.BASE_URL + '/users', callback=request_callback)

            async with self.session as client:
                response = await client.post(self.BASE_URL + '/users', json={'some': {'nested': 'payload'}})
                self.assertEqual(response.content_type, 'text/plain')
