import os
import shutil

import requests
from urllib.parse import urlparse

import yaml


def download_image(url, dest_path):
    print("downloading: " + url)
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise exception if invalid response
    # Get the file extension from the URL
    parsed_url = urlparse(url)
    file_extension = os.path.splitext(parsed_url.path)[1]
    # Append the file extension to the destination path
    dest_path += file_extension
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest_path


ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

for dir in ["icons", "screenshots"]:
    if os.path.exists(os.path.join(ARTIFACTS_DIR, dir)):
        shutil.rmtree(os.path.join(ARTIFACTS_DIR, dir))
        os.makedirs(os.path.join(ARTIFACTS_DIR, dir))

with open(os.path.join(ARTIFACTS_DIR, "repo.yaml"), 'r') as file:
    data = yaml.safe_load(file)

for item_name, item_data in data.items():
    print(f"Downloading images {item_name}...")

    if 'icon_url' in item_data:
        icon_path = os.path.join(ARTIFACTS_DIR, "icons", item_name)
        icon_path = download_image(item_data["icon_url"], icon_path)  # Update the path with the file extension

    if 'screenshot_urls' in item_data:
        for i, url in enumerate(item_data["screenshot_urls"]):
            screenshot_path = os.path.join(ARTIFACTS_DIR, "screenshots", f"{item_name}-{i}")
            screenshot_path = download_image(url, screenshot_path)  # Update the path with the file extension