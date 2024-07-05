import os

import threading
import traceback
from html.parser import HTMLParser
import re
from urllib.parse import urlparse

import yaml
import requests

from PIL import Image
from io import BytesIO

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version("AppStream", "1.0")
gi.require_version("Flatpak", "1.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Soup", "3.0")
from gi.repository import Gtk, Adw, Gio, Flatpak, AppStream, Soup, GLib, Gdk

DATA_DIR = os.path.join(os.path.dirname(__file__), "yaml_adder_data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

pool = AppStream.Pool()
pool.load()

def get_image_resolution(url):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    return img.size  # Returns a tuple (width, height)


def get_highest_resolution_image(images):
    max_resolution = (0, 0)
    max_resolution_image = None
    for img in images:
        url = img.get_url()
        resolution = get_image_resolution(url)
        if resolution[0]*resolution[1] > max_resolution[0]*max_resolution[1]:  # Compare areas
            max_resolution = resolution
            max_resolution_image = url
    return max_resolution_image


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.list_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.result.append('\n')
        elif tag == 'li':
            self.result.append('- ')
            self.list_depth += 1

    def handle_endtag(self, tag):
        if tag in ('p', 'div', 'li'):
            self.result.append('\n')
        if tag in ('ul', 'ol') and self.list_depth > 0:
            self.list_depth -= 1

    def handle_data(self, data):
        if data.strip():
            self.result.append(data)


def html_to_plain_text(html):
    parser = HTMLTextExtractor()
    parser.feed(html)
    text = ''.join(parser.result)
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    return text


def download_image(url, dest_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise exception if invalid response
    # Get the file extension from the URL
    parsed_url = urlparse(url)
    file_extension = os.path.splitext(parsed_url.path)[1]
    # Append the file extension to the destination path
    dest_path += file_extension
    with open(dest_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    return dest_path


def find_appstream(flatpak_id):
    for component in pool.get_components().as_array():
        if component.get_id() == flatpak_id and component.get_origin() == "flatpak":
            return component


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.stillhq.SadbAppAdder",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(DATA_DIR, "sadb_app_adder.ui"))
        self.connect("activate", self.on_activate)

        self.flatpak_package = self.builder.get_object("flatpak_package")
        self.add_button = self.builder.get_object("add_button")
        self.sadb_id = self.builder.get_object("app_id")
        self.name = self.builder.get_object("name")
        self.author = self.builder.get_object("author")
        self.summary = self.builder.get_object("summary")
        self.primary_src = self.builder.get_object("primary_src")
        self.src_pkg_name = self.builder.get_object("src_pkg_name")
        self.categories = self.builder.get_object("categories")
        self.keywords = self.builder.get_object("keywords")
        self.mimetypes = self.builder.get_object("mimetypes")
        self.pricing = self.builder.get_object("pricing")
        self.still_rating = self.builder.get_object("rating")
        self.mobile = self.builder.get_object("mobile")
        self.icon_url = self.builder.get_object("icon_url")
        self.license = self.builder.get_object("license")
        self.homepage = self.builder.get_object("homepage")
        self.donate = self.builder.get_object("donate")
        self.demo_url = self.builder.get_object("demo_url")

        self.description = self.builder.get_object("description")
        self.still_rating_notes = self.builder.get_object("rating_notes")
        self.preview_screenshots_button = self.builder.get_object("preview_screenshots_button")
        self.screenshots = self.builder.get_object("screenshots")
        self.icon = self.builder.get_object("icon")
        self.screenshot_box = self.builder.get_object("screenshot_box")

        self.flatpak_package.connect("apply", self.flatpak_id_apply)
        self.flatpak_package.connect("changed", lambda _entry: self.flatpak_package.remove_css_class("error"))
        self.icon_url.connect("apply", lambda _button: self.update_icon())
        self.add_button.connect("clicked", self.add_to_yaml_clicked)
        self.preview_screenshots_button.connect("clicked", lambda _button: self.update_screenshots())

    def error_importing_flatpak(self, error: str):
        self.flatpak_package.set_text(error)
        self.flatpak_package.add_css_class("error")

    def flatpak_id_apply(self, _entry):
        flatpak_id = self.flatpak_package.get_text()
        pkg_name = f"app/{flatpak_id}/x86_64/stable"

        # Check for duplicate packages in the repo
        with open(os.path.join(ARTIFACTS_DIR, "repo.yaml"), 'r') as file:
            data = yaml.safe_load(file)

        for item_data in data.values():
            if 'src_pkg_name' in item_data and item_data['src_pkg_name'] == pkg_name:
                self.error_importing_flatpak(f"{pkg_name} already in repo")
                return

        try:
            component = find_appstream(flatpak_id)
            if component is None:
                component = find_appstream(flatpak_id + ".desktop")
            if component is None:
                self.error_importing_flatpak(f"Could not find data for {flatpak_id}")
                return
            try:
                self.sadb_id.set_text(flatpak_id.split(".")[-1].lower())
            except IndexError:
                self.sadb_id.set_text(flatpak_id.replace(".", "-").lower())
            self.name.set_text(component.get_name())
            try:
                self.author.set_text(component.get_developer().get_name())
            except (IndexError, TypeError):
               pass
            self.summary.set_text(component.get_summary())
            self.primary_src.set_text("flathub")
            self.src_pkg_name.set_text(pkg_name)
            self.categories.set_text(", ".join(component.get_categories()))
            # mimetypes
            if component.get_provided_for_kind(AppStream.ProvidedKind.MEDIATYPE):
                self.mimetypes.set_text(", ".join(component.get_provided_for_kind(AppStream.ProvidedKind.MEDIATYPE).get_items()))
            self.keywords.set_text(", ".join(component.get_keywords()))
            self.pricing.set_selected(1)
            self.still_rating.set_selected(0)
            self.mobile.set_selected(1)
            self.icon_url.set_text(f"https://flathub.org/repo/appstream/x86_64/icons/128x128/{flatpak_id}.png")
            self.license.set_text(component.get_project_license())

            if component.get_url(AppStream.UrlKind.HOMEPAGE):
                self.homepage.set_text(component.get_url(AppStream.UrlKind.HOMEPAGE))
            if component.get_url(AppStream.UrlKind.DONATION):
                self.donate.set_text(component.get_url(AppStream.UrlKind.DONATION))

            self.description.get_buffer().set_text(html_to_plain_text(component.get_description()))
            self.still_rating_notes.get_buffer().set_text("No notes have been provided.")

            screenshots_all = component.get_screenshots_all()
            screenshots = []
            for screenshot in screenshots_all:
                images = screenshot.get_images()
                highest_quality_image = get_highest_resolution_image(images)
                screenshots.append(highest_quality_image)
            self.screenshots.get_buffer().set_text("\n".join(screenshots))

            self.update_icon()
            try:
                self.update_screenshots()
            except GLib.Error:
                pass
        except Exception as e:
            type(traceback.format_exc())
            self.error_importing_flatpak(traceback.format_exc())

    def on_receive_bytes(self, session, result, user_data):
        message, picture = user_data
        bytes = session.send_and_read_finish(result)
        if message.get_status() != Soup.Status.OK:
            raise Exception(f"Got {message.get_status()}, {message.get_reason_phrase()}")
        texture = Gdk.Texture.new_from_bytes(bytes)
        picture.set_paintable(texture)

    def load_picture_url(self, url, picture):
        session = Soup.Session()
        message = Soup.Message(
            method="GET",
            uri=GLib.Uri.parse(url, GLib.UriFlags.NONE),
        )
        session.send_and_read_async(
            message, GLib.PRIORITY_DEFAULT, None, self.on_receive_bytes, [message, picture]
        )

    def on_activate(self, app):
        window = self.builder.get_object("application")
        window.set_application(app)
        window.present()

    def update_icon(self):
        if self.icon_url.get_text() == "":
            self.icon.set_filename(os.path.join(DATA_DIR, "icon.png"))
        self.load_picture_url(self.icon_url.get_text(), self.icon)

    def update_screenshots(self):
        # Clear screenshots
        child = self.screenshot_box.get_first_child()
        while child is not None:
            self.screenshot_box.remove(child)
            child = self.screenshot_box.get_first_child()

        buffer = self.screenshots.get_buffer()
        screenshot_urls = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).split("\n")
        for url in screenshot_urls:
            picture = Gtk.Picture()
            self.screenshot_box.append(picture)
            try:
                self.load_picture_url(url, picture)
            except GLib.Error:
                pass

    def add_to_yaml_clicked(self, button):
        thread = threading.Thread(target=self.add_to_yaml, args=(button,))
        thread.start()

    def add_to_yaml(self, button):
        yaml_container = {}
        sadb_id = self.sadb_id.get_text()

        description_buffer = self.description.get_buffer()
        still_rating_notes_buffer = self.still_rating_notes.get_buffer()
        screenshots_buffer = self.screenshots.get_buffer()

        app_yml = {
            "name": self.name.get_text(),
            "author": self.author.get_text(),
            "summary": self.summary.get_text(),
            "primary_src": self.primary_src.get_text(),
            "src_pkg_name": self.src_pkg_name.get_text(),
            "categories": self.categories.get_text().split(", "),
            "keywords": self.keywords.get_text().split(", "),
            "mimetypes": self.mimetypes.get_text().split(", "),
            "pricing": self.pricing.get_selected(),
            "still_rating": self.still_rating.get_selected(),
            "mobile": self.mobile.get_selected(),
            "icon_url": self.icon_url.get_text(),
            "license": self.license.get_text(),
            "homepage": self.homepage.get_text(),
            "donate_url": self.donate.get_text(),
            "demo_url": self.demo_url.get_text(),
            "description": description_buffer.get_text(description_buffer.get_start_iter(), description_buffer.get_end_iter(), False),
            "still_rating_notes": still_rating_notes_buffer.get_text(still_rating_notes_buffer.get_start_iter(), still_rating_notes_buffer.get_end_iter(), False),
            "screenshot_urls": screenshots_buffer.get_text(screenshots_buffer.get_start_iter(), screenshots_buffer.get_end_iter(), False).split("\n")
        }
        # Remove empty strings
        app_yml = {k: v for k, v in app_yml.items() if v != "" and v != [] and v != ['']}
        # remove ss_urls if length 1 and item is ""
        # if len(app_yml["screenshot_urls"]) == 1 and app_yml["screenshot_urls"][0] == "":
        #     app_yml.pop("screenshot_urls")
        # if len(app_yml["keywords"]) == 1 and app_yml["keywords"][0] == "":
        #     app_yml.pop("keywords")

        # Create artifact directories if they don't exist
        for dir in ["icons", "screenshots"]:
            if not os.path.exists(os.path.join(ARTIFACTS_DIR, dir)):
                os.makedirs(os.path.join(ARTIFACTS_DIR, dir))

        GLib.idle_add(lambda: self.add_button.set_label("Downloading images"))
        # Download icons and screenshots
        if "icon_url" in app_yml:
            icon_path = os.path.join(ARTIFACTS_DIR, "icons", sadb_id)
            icon_path = download_image(app_yml["icon_url"], icon_path)  # Update the path with the file extension
            app_yml[
                "icon_url"] = f"https://raw.githubusercontent.com/stillhq/saDB-repo/main/icons/{os.path.basename(icon_path)}"

        if "screenshot_urls" in app_yml:
            ss_urls = []
            for i, url in enumerate(app_yml["screenshot_urls"]):
                print(url)
                screenshot_path = os.path.join(ARTIFACTS_DIR, "screenshots", f"{sadb_id}-{i}")
                screenshot_path = download_image(url, screenshot_path)  # Update the path with the file extension
                ss_urls.append(
                    f"https://raw.githubusercontent.com/stillhq/saDB-repo/main/screenshots/{os.path.basename(screenshot_path)}")
            app_yml["screenshot_urls"] = ss_urls

        GLib.idle_add(lambda: self.add_button.set_label("Adding to yaml"))
        yaml_container = {sadb_id: app_yml}
        with open(os.path.join(ARTIFACTS_DIR, "repo.yaml"), "a") as f:
            yaml.dump(yaml_container, f)
        GLib.idle_add(lambda: self.clear())

    def clear(self):
        self.flatpak_package.set_text("")
        self.sadb_id.set_text("")
        self.name.set_text("")
        self.author.set_text("")
        self.summary.set_text("")
        self.primary_src.set_text("")
        self.src_pkg_name.set_text("")
        self.categories.set_text("")
        self.keywords.set_text("")
        self.mimetypes.set_text("")
        self.pricing.set_selected(0)
        self.still_rating.set_selected(0)
        self.mobile.set_selected(0)
        self.icon_url.set_text("")
        self.license.set_text("")
        self.homepage.set_text("")
        self.donate.set_text("")
        self.demo_url.set_text("")
        self.description.get_buffer().set_text("")
        self.still_rating_notes.get_buffer().set_text("")
        self.screenshots.get_buffer().set_text("")
        self.add_button.set_label("Add to YAML")

        try:
            self.update_icon()
        except GLib.Error:
            pass

        try:
            self.update_screenshots()
        except GLib.Error:
            pass


if __name__ == "__main__":
    app = Application()
    app.run(None)