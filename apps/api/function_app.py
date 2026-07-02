from __future__ import annotations

import logging

import azure.functions as func

from allernav_api.menu_job_queue import parse_menu_refresh_message
from allernav_api.menu_worker import process_menu_refresh_message


app = func.FunctionApp()


@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="menu-refresh",
    connection="AZURE_SERVICE_BUS_CONNECTION_STRING",
)
def process_menu_refresh(msg: func.ServiceBusMessage) -> None:
    body = msg.get_body().decode("utf-8")
    message = parse_menu_refresh_message(body)
    attempt = int(getattr(msg, "delivery_count", 1) or 1)
    job = process_menu_refresh_message(message, attempt=attempt)
    logging.info(
        "Menu refresh worker completed job_id=%s place_id=%s status=%s item_count=%s",
        job.id,
        job.place_id,
        job.status,
        job.item_count,
    )
