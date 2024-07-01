import os

import copy
from xml.etree import ElementTree as etree
from html.parser import HTMLParser
import re

import yaml

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version("AppStream", "1.0")
gi.require_version("Flatpak", "1.0")
from gi.repository import Gtk, Adw, Gio, Flatpak, AppStream

DATA_DIR = os.path.join(os.path.dirname(__file__), "yaml_adder_data")

pool = AppStream.Pool()
pool.load()

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
        self.screenshots = self.builder.get_object("screenshots")
        self.icon = self.builder.get_object("icon")
        self.screenshot_box = self.builder.get_object("screenshot_box")

        self.flatpak_package.connect("apply", self.flatpak_id_apply)

    def flatpak_id_apply(self, _entry):
        flatpak_id = self.flatpak_package.get_text()
        component = find_appstream(flatpak_id)
        try:
            self.sadb_id.set_text(flatpak_id.split(".")[2])
        except IndexError:
            self.sadb_id.set_text(flatpak_id.replace(".", "-"))
        self.name.set_text(component.get_name())
        self.author.set_text(component.get_developer().get_name())
        self.summary.set_text(component.get_summary())
        self.primary_src.set_text("flathub")
        self.src_pkg_name.set_text(f"app/{flatpak_id}/x86_64/stable")
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
        self.homepage.set_text(component.get_url(AppStream.UrlKind.HOMEPAGE))
        self.donate.set_text(component.get_url(AppStream.UrlKind.DONATION))

        self.description.get_buffer().set_text(html_to_plain_text(component.get_description()))
        self.still_rating_notes.get_buffer().set_text("")
        self.screenshots.get_buffer().set_text("")
        self.update_icon()


    def on_activate(self, app):
        window = self.builder.get_object("application")
        window.set_application(app)
        window.present()

    def update_icon(self):
        pass

    def update_screenshots(self):
        pass

if __name__ == "__main__":
    app = Application()
    app.run(None)