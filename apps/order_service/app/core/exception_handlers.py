from fastapi import FastAPI


class OrderExceptionHandler:
    def __init__(self, app: FastAPI):
        self._app = app

    def add_handlers(self):
        pass
