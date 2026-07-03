import requests


def send_screenshot(gas_url, name, image_data):
    """Send a base64-encoded screenshot to the Google Apps Script endpoint."""
    payload = {"name": name, "image_data": image_data}
    response = requests.post(gas_url, json=payload)
    return response.text
