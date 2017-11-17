from aiohttp.test_utils import unittest_run_loop

from test_aiohttp.rsps import MockRoutesTestCase, RouteNotCalledError, RouteNotFoundError


async def request_callback(request):
    return (200, {}, await request.text())


# Create your tests here.
class RSPSTestCase(MockRoutesTestCase):

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
            self.assertEqual(response.status, 200)
            users = await response.json()
            self.assertEqual(len(users), 2)

    @unittest_run_loop
    async def test_response_status_code(self):
        with self.mock_response() as rsps:
            rsps.add('GET', '/users', data={'details': 'Not found'}, status=404)

            response = await self.client.get('/users')
            self.assertEqual(response.status, 404)
    
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

    @unittest_run_loop
    async def test_must_match_all(self):
        with self.assertRaises(RouteNotCalledError):
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
                rsps.add('GET', '/users/1', data=[
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

                await self.client.get('/users/1')

    @unittest_run_loop
    async def test_route_not_found(self):
        with self.assertRaises(RouteNotFoundError):
            with self.mock_response():
                await self.client.get('/users')

    @unittest_run_loop
    async def test_response_text(self):
        with self.mock_response() as rsps:
            rsps.add('GET', '/users', text='ok')

            response = await self.client.get('/users')
            self.assertEqual(response.content_type, 'text/plain')
            text = await response.text()
            self.assertEqual(text, 'ok')

    @unittest_run_loop
    async def test_response_content_type(self):
        with self.mock_response() as rsps:
            rsps.add('GET', '/users', text='<h1>ok</h1>', content_type='text/html')

            response = await self.client.get('/users')
            self.assertEqual(response.content_type, 'text/html')
