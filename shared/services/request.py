import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    retry_if_exception_type,
    wait_exponential_jitter,
)


class Request:
    def __init__(self, async_client: httpx.AsyncClient = None):
        self._async_client = async_client

    RETRY_FOR = (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.WriteError,
        httpx.ReadError,
    )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(max=15, jitter=5),
        retry=retry_if_exception_type(RETRY_FOR),
    )
    async def get(
        self, url: str, params: dict = None, headers: dict = None, cookies: dict = None
    ) -> httpx.Response:
        res: httpx.Response = await self._async_client.get(
            url, params=params, headers=headers, cookies=cookies
        )
        return res

    async def post(
        self,
        url: str,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        headers: dict = None,
        cookies: dict = None,
    ) -> httpx.Response:
        res: httpx.Response = await self._async_client.post(
            url, params=params, data=data, json=json, headers=headers, cookies=cookies
        )
        return res

    async def patch(
        self,
        url: str,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        headers: dict = None,
        cookies: dict = None,
    ) -> httpx.Response:
        res: httpx.Response = await self._async_client.patch(
            url, params=params, data=data, json=json, headers=headers, cookies=cookies
        )
        return res

    async def delete(
        self,
        url: str,
        params: dict = None,
        headers: dict = None,
        cookies: dict = None,
    ) -> httpx.Response:
        res: httpx.Response = await self._async_client.delete(
            url, params=params, headers=headers, cookies=cookies
        )
        return res
