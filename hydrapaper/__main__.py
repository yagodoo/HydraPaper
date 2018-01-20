# __main__.py
#
# Copyright (C) 2017 GabMus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import pathlib

import argparse
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf

from . import monitor_parser as MonitorParser
from . import wallpaper_merger as WallpaperMerger

import hashlib # for pseudo-random wallpaper name generation

HOME = os.environ.get('HOME')

IMAGE_EXTENSIONS = [
    '.jpg',
    '.jpeg',
    '.png',
    '.tiff',
    '.svg'
]

class Application(Gtk.Application):
    def __init__(self, **kwargs):
        self.builder = Gtk.Builder.new_from_resource(
            '/org/gabmus/hydrapaper/ui/ui.glade'
        )
        super().__init__(
            application_id='org.gabmus.hydrapaper',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs
        )
        self.RESOURCE_PATH = '/org/gabmus/hydrapaper/'

        self.builder.connect_signals(self)

        settings = Gtk.Settings.get_default()
        # settings.set_property("gtk-application-prefer-dark-theme", True)

        self.window = self.builder.get_object('window')

        self.mainBox = self.builder.get_object('mainBox')
        self.apply_button = self.builder.get_object('applyButton')

        self.monitors_flowbox = self.builder.get_object('monitorsFlowbox')
        self.wallpapers_flowbox = self.builder.get_object('wallpapersFlowbox')

        # This is a list of Monitor objects
        self.monitors = MonitorParser.build_monitors_from_dict()

        self.wallpapers_paths = [
            '{0}/Pictures'.format(HOME)
        ]
        self.wallpapers_list = []

    def set_monitor_wallpaper_preview(self, wp_path):
        monitor_widgets = self.monitors_flowbox.get_selected_children()[0].get_children()[0].get_children()
        for w in monitor_widgets:
            if type(w) == Gtk.Image:
                m_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(wp_path, 64, 64, True)
                w.set_from_pixbuf(m_pixbuf)
            elif type(w) == Gtk.Label:
                current_m_name = w.get_text()
                for m in self.monitors:
                    if m.name == current_m_name:
                        m.wallpaper = wp_path

    def make_monitors_flowbox_item(self, monitor):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        label = Gtk.Label()
        label.set_text(monitor.name)
        image = Gtk.Image()
        image.set_from_icon_name('image-missing', Gtk.IconSize.DIALOG)
        box.pack_start(image, False, False, 0)
        box.pack_start(label, False, False, 0)
        box.set_margin_left(24)
        box.set_margin_right(24)
        return box

    def make_wallpapers_flowbox_item(self, wp_path):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        wp_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(wp_path, 250, 250, True)
        image = Gtk.Image.new_from_pixbuf(wp_pixbuf)
        box.pack_start(image, False, False, 0)
        box.set_margin_left(12)
        box.set_margin_right(12)
        box.wallpaper_path = wp_path
        return box

    def fill_monitors_flowbox(self):
        for m in self.monitors:
            self.monitors_flowbox.insert(
                self.make_monitors_flowbox_item(m),
            -1) # -1 appends to the end

    def fill_wallpapers_flowbox(self):
        for w in self.wallpapers_list:
            self.wallpapers_flowbox.insert(
                self.make_wallpapers_flowbox_item(w),
            -1) # -1 appends to the end

    def get_wallpapers_list(self):
        for path in self.wallpapers_paths:
            pictures = os.listdir('{0}'.format(path))
            for pic in pictures:
                if pathlib.Path(pic).suffix.lower() not in IMAGE_EXTENSIONS:
                    pictures.pop(pictures.index(pic))
            self.wallpapers_list.extend(['{0}/'.format(path) + pic for pic in pictures])

    def do_activate(self):
        self.add_window(self.window)
        self.window.set_wmclass('HydraPaper', 'HydraPaper')
        self.window.set_title('HydraPaper')

        appMenu = Gio.Menu()
        appMenu.append("About", "app.about")
        appMenu.append("Quit", "app.quit")
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_activate)
        self.builder.get_object("aboutdialog").connect(
            "delete-event", lambda *_:
                self.builder.get_object("aboutdialog").hide() or True
        )
        self.add_action(about_action)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit_activate)
        self.add_action(quit_action)
        self.set_app_menu(appMenu)

        self.fill_monitors_flowbox()

        self.get_wallpapers_list()
        self.fill_wallpapers_flowbox() # TODO: do this in a separate thread, it takes too long

        self.window.show_all()

    def do_command_line(self, args):
        """
        GTK.Application command line handler
        called if Gio.ApplicationFlags.HANDLES_COMMAND_LINE is set.
        must call the self.do_activate() to get the application up and running.
        """
        Gtk.Application.do_command_line(self, args)  # call the default commandline handler
        # make a command line parser
        parser = argparse.ArgumentParser(prog='gui')
        # add a -c/--color option
        parser.add_argument('-q', '--quit-after-init', dest='quit_after_init', action='store_true', help='initialize application (e.g. for macros initialization on system startup) and quit')
        # parse the command line stored in args, but skip the first element (the filename)
        self.args = parser.parse_args(args.get_arguments()[1:])
        # call the main program do_activate() to start up the app
        self.do_activate()
        return 0

    def on_about_activate(self, *args):
        self.builder.get_object("aboutdialog").show()

    def on_quit_activate(self, *args):
        self.quit()

    def onDeleteWindow(self, *args):
        self.quit()

    # Handler functions START

    def on_aboutdialog_close(self, *args):
        self.builder.get_object("aboutdialog").hide()

    def on_wallpapersFlowbox_child_activated(self, flowbox, selected_item):
        self.set_monitor_wallpaper_preview(
            selected_item.get_child().wallpaper_path
        )

    def on_applyButton_clicked(self, btn):
        if len(self.monitors)!=2:
            print('Configurations different from 2 monitors are not supported for now :(')
            exit(1)
        if not (self.monitors[0].wallpaper and self.monitors[1].wallpaper):
            print('Set both wallpapers before applying')
            return
        if not os.path.isdir('{0}/Pictures/HydraPaper'.format(HOME)):
            os.mkdir('{0}/Pictures/HydraPaper'.format(HOME))
        saved_wp_path = '{0}/Pictures/HydraPaper/{1}.png'.format(HOME, hashlib.sha256(
            'HydraPaper{0}{1}'.format(self.monitors[0].wallpaper, self.monitors[1].wallpaper).encode()
        ).hexdigest())
        WallpaperMerger.multi_setup_standalone(
            self.monitors[0].width,
            self.monitors[0].height,
            self.monitors[1].width,
            self.monitors[1].height,
            self.monitors[0].wallpaper,
            self.monitors[1].wallpaper,
            self.monitors[0].offset_x,
            self.monitors[0].offset_y,
            self.monitors[1].offset_x,
            self.monitors[1].offset_y,
            saved_wp_path
        )
        WallpaperMerger.set_wallpaper(saved_wp_path)

    # Handler functions END


def main():
    application = Application()

    try:
        ret = application.run(sys.argv)
    except SystemExit as e:
        ret = e.code

    sys.exit(ret)


if __name__ == '__main__':
    main()