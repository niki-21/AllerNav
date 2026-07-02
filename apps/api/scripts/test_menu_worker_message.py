from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from allernav_api.menu_job_queue import parse_menu_refresh_message
from allernav_api.menu_worker import process_menu_refresh_message


def sample_payload() -> str:
    return json.dumps(
        {
            "version": 1,
            "job_id": str(uuid4()),
            "place_id": "local-menu-worker-test",
            "restaurant_name": "AllerNav Menu Worker Test",
            "website_url": os.getenv(
                "MENU_WORKER_TEST_WEBSITE_URL",
                "https://allernav.vercel.app/demo/allernav_arabic_menu_ocr_test.pdf",
            ),
            "document_urls": [],
            "menu_version": "local-test",
        }
    )


def read_payload(value: str | None) -> str:
    if not value:
        return sample_payload()
    if value.lstrip().startswith(("{", "[")):
        return value
    path = Path(value)
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else value
    except OSError:
        return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an AllerNav menu refresh message directly without Azure Service Bus."
    )
    parser.add_argument(
        "payload",
        nargs="?",
        help="Inline JSON or a path to a JSON file. A sample payload is generated when omitted.",
    )
    parser.add_argument("--attempt", type=int, default=1, help="Delivery attempt passed to the worker.")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    message = parse_menu_refresh_message(read_payload(args.payload))
    job = process_menu_refresh_message(message, attempt=max(1, args.attempt))
    print(job.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
