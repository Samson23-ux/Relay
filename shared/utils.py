import json
import base64
from binascii import Error as BinasciiError


async def encode_data(payload: dict) -> str:
    payload_string: str = json.dumps(payload)
    return base64.b64encode(payload_string.encode()).decode()


async def decode_string(cursor_string: str, curr_order: str) -> dict:
    try:
        if not cursor_string:
            return

        cursor_string = base64.b64decode(cursor_string)
        cursor_payload = json.loads(cursor_string)

        if cursor_payload["order"] != curr_order.lower():
            return
        return cursor_payload
    except (json.JSONDecodeError, UnicodeDecodeError, BinasciiError):
        return
