import json
import base64
from uuid import UUID
from binascii import Error as BinasciiError


from shared.worker.tasks.log import save_log, update_log


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
    except json.JSONDecodeError, UnicodeDecodeError, BinasciiError:
        return


def get_message_meta(request_meta: dict, upstream: str) -> dict:
    message_meta: dict = {
        "trace_id": request_meta.get("trace_id"),
        "span_id": request_meta.get("span_id"),
        "parent_span_id": request_meta.get("parent_span_id"),
        "user_id": str(request_meta.get("user_id")),
    }

    message_meta["upstream"] = upstream
    return message_meta


def log_info(
    message: str,
    request_meta: dict,
    circuit: dict | None = None,
    user_id: UUID | None = None,
):
    request_meta["message"] = message

    if user_id:
        request_meta["user_id"] = str(user_id)

    if circuit:
        circuit_state = circuit.get("state")
        request_meta["circuit_open"] = True if circuit_state == "open" else False

    save_log.apply_async(priority=3, kwargs={"payload": request_meta})


def log_error(
    message: str,
    request_meta: dict,
    circuit: dict | None = None,
    user_id: UUID | None = None,
):
    request_meta["message"] = message
    request_meta["log_level"] = "error"

    if user_id:
        request_meta["user_id"] = str(user_id)

    if circuit:
        circuit_state = circuit.get("state")
        request_meta["circuit_open"] = True if circuit_state == "open" else False

    save_log.apply_async(priority=3, kwargs={"payload": request_meta})


def update_db_log(trace_id: str, span_id: str, payload: dict):
    update_log.apply_async(
        priority=3,
        kwargs={"trace_id": trace_id, "span_id": span_id, "payload": payload},
    )
