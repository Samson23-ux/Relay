import httpx
from fastapi import FastAPI


class MultiTransportApp(httpx.AsyncBaseTransport):
    def __init__(self, apps: dict[str, FastAPI]):
        self._transports = {
            name: httpx.ASGITransport(app) for name, app in apps.items()
        }

    async def handle_async_request(self, request):
        app_name = request.headers["x-upstream"]
        transport = self._transports[app_name]

        return await transport.handle_async_request(request)
