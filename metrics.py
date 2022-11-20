import requests
from datetime import datetime as dt


def emit_metric(type="", action="", value="", user_id="", chat_id=""):
    # Webhook to Google Sheets integration
    url = "https://flows.messagebird.com/flows/81d3595a-c360-49c2-b787-72f3a84ab38b/invoke"

    data = {
        "type": type,
        "action": action,
        "value": value,
        "user_id": user_id,
        "chat_id": chat_id,
        "timestamp": dt.utcnow().isoformat("T"),
    }
    requests.post(url, json=data)


def test():
    emit_metric("user", "subscribe")
    emit_metric("etc", "start_command")


if __name__ == "__main__":
    test()
