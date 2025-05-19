import logging

import requests

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["WEBHOOK"])


def post_webhook(name: str, url: str, message: str, event_data: dict) -> bool:
    try:
        log.debug(f"post_webhook: {url}, {message}, {event_data}")
        payload = {}

        # Slack and Google Chat Webhooks
        if "https://hooks.slack.com" in url:
            payload["text"] = message
        else:
            payload = {**event_data}

        log.debug(f"payload: {payload}")
        r = requests.post(url, json=payload)
        r.raise_for_status()
        log.debug(f"r.text: {r.text}")
        return True
    except Exception as e:
        log.exception(e)
        return False
