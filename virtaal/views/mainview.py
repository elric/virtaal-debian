#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk
import os
from gtk import gdk
from gtk import glade
from translate.storage import factory

from virtaal.views import recent
from virtaal.common import pan_app, __version__
from virtaal.support import openmailto

from aboutdialog import AboutDialog
from baseview import BaseView

import pygtk
pygtk.require("2.0")

def fill_dialog(dialog, title='', message='', markup=''):
    if title:
        dialog.set_title(title)
    if markup:
        dialog.set_markup(markup)
    else:
        dialog.set_markup(message.replace('<', '&lt;'))


class EntryDialog(gtk.Dialog):
    """A simple dialog containing a dialog for user input."""

    def __init__(self, parent):
        super(EntryDialog, self).__init__(title='Input Dialog', parent=parent)
        self.set_size_request(450, 100)

        self.lbl_message = gtk.Label()
        self.vbox.pack_start(self.lbl_message)

        self.ent_input = gtk.Entry()
        self.ent_input.set_activates_default(True)
        self.vbox.pack_start(self.ent_input)

        self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.set_default_response(gtk.RESPONSE_OK)

    def run(self, title=None, message=None, keepInput=False):
        if message:
            self.set_message(message)
        if title:
            self.set_title(title)

        if not keepInput:
            self.ent_input.set_text('')

        self.show_all()
        self.ent_input.grab_focus()
        response = super(EntryDialog, self).run()

        return response, self.ent_input.get_text().decode('utf-8')

    def set_message(self, message):
        self.lbl_message.set_markup(message)

    def set_title(self, title):
        super(EntryDialog, self).set_title(title)

# TODO: Reparent dialogs with self._top_window
# XXX: This class is based on main_window.py:Virtaal from the pre-MVC days.
class MainView(BaseView):
    """The view containing the main window and menus."""

    # INITIALIZERS #
    def __init__(self, controller):
        """Constructor.
            @type  controller: virtaal.controllers.MainController
            @param controller: The controller that this view is "connected" to."""
        self.controller = controller

        if os.name == 'nt':
            # Before we do anything else, make sure that stdout and stderr are properly handled.
            import sys
            sys.stdout = open(os.path.join(pan_app.get_config_dir(), 'virtaal_log.txt'), 'ab')
            sys.stderr = sys.stdout

            # Make sure that rule-hints are shown in Windows
            rc_string = """
                style "show-rules"
                {
                    GtkTreeView::allow-rules = 1
                }
                class "GtkTreeView" style "show-rules"
                """
            gtk.rc_parse_string(rc_string)

        # Set the Glade file
        self.gladefile, self.gui = self.load_glade_file(["virtaal", "virtaal.glade"], root='MainWindow', domain="virtaal")

        # Create our events dictionary and connect it
        dic = {
                "on_mainwindow_destroy" : gtk.main_quit,
                "on_mainwindow_delete" : self._on_mainwindow_delete,
                "on_open_activate" : self._on_file_open,
                "on_save_activate" : self._on_file_save,
                "on_saveas_activate" : self._on_file_saveas,
                "on_update_activate" : self._on_file_update,
                "on_quit" : self._on_quit,
                "on_about_activate" : self._on_help_about,
                "on_localization_guide_activate" : self._on_localization_guide,
                "on_menuitem_documentation_activate" : self._on_documentation,
                "on_menuitem_report_bug_activate" : self._on_report_bug,
                }
        self.gui.signal_autoconnect(dic)

        self.status_bar = self.gui.get_widget("status_bar")
        self.statusbar_context_id = self.status_bar.get_context_id("statusbar")
        self.main_window = self.gui.get_widget("MainWindow")
        self.main_window.set_icon_from_file(pan_app.get_abs_data_filename(["icons", "virtaal.ico"]))
        self._top_window = self.main_window
        recent_files = self.gui.get_widget("recent_files")
        recent.rc.connect("item-activated", self._on_recent_file_activated)
        recent_files.set_submenu(recent.rc)

        self.controller.connect('controller-registered', self._on_controller_registered)
        self._create_dialogs()
        self._setup_key_bindings()

    def _create_dialogs(self):
        self.input_dialog = EntryDialog(self.main_window)

        self.error_dialog = gtk.MessageDialog(self.main_window, 
            gtk.DIALOG_MODAL, 
            gtk.MESSAGE_ERROR, 
            gtk.BUTTONS_OK)
        self.error_dialog.set_title(_("Error"))

        self.prompt_dialog = gtk.MessageDialog(self.main_window,
            gtk.DIALOG_MODAL,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_YES_NO,
        )
        self.prompt_dialog.set_default_response(gtk.RESPONSE_NO)

        self.info_dialog = gtk.MessageDialog(self.main_window,
            gtk.DIALOG_MODAL,
            gtk.MESSAGE_INFO,
            gtk.BUTTONS_OK,
        )

        self.open_chooser = gtk.FileChooserDialog(
            _('Choose a translation file'),
            self.main_window,
            gtk.FILE_CHOOSER_ACTION_OPEN,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        )
        self.open_chooser.set_default_response(gtk.RESPONSE_OK)
        all_supported_filter = gtk.FileFilter()
        all_supported_filter.set_name(_("All Supported Files"))
        self.open_chooser.add_filter(all_supported_filter)
        for name, extensions, mimetypes in factory.supported_files():
            #XXX: Remove when the fixed toolkit is released
            if "csv" in extensions or "qm" in extensions:
                continue
            new_filter = gtk.FileFilter()
            new_filter.set_name(_(name))
            if extensions:
                for extension in extensions:
                    new_filter.add_pattern("*." + extension)
                    all_supported_filter.add_pattern("*." + extension)
                    for compress_extension in factory.decompressclass.keys():
                        new_filter.add_pattern("*.%s.%s" % (extension, compress_extension))
                        all_supported_filter.add_pattern("*.%s.%s" % (extension, compress_extension))
            if mimetypes:
                for mimetype in mimetypes:
                    new_filter.add_mime_type(mimetype)
                    all_supported_filter.add_mime_type(mimetype)
            self.open_chooser.add_filter(new_filter)
        all_filter = gtk.FileFilter()
        all_filter.set_name(_("All Files"))
        all_filter.add_pattern("*")
        self.open_chooser.add_filter(all_filter)

        self.save_chooser = gtk.FileChooserDialog(
            _("Save"),
            self.main_window,
            gtk.FILE_CHOOSER_ACTION_SAVE,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        )
        self.save_chooser.set_do_overwrite_confirmation(True)
        self.save_chooser.set_default_response(gtk.RESPONSE_OK)

        (RESPONSE_SAVE, RESPONSE_DISCARD) = (gtk.RESPONSE_YES, gtk.RESPONSE_NO)
        self.confirm_dialog = gtk.MessageDialog(
            self.main_window,
            gtk.DIALOG_MODAL,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_NONE,
            _("The current file has been modified.\nDo you want to save your changes?")
        )
        self.confirm_dialog.add_buttons(gtk.STOCK_SAVE, RESPONSE_SAVE)
        self.confirm_dialog.add_buttons(_("_Discard"), RESPONSE_DISCARD)
        self.confirm_dialog.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.confirm_dialog.set_default_response(RESPONSE_SAVE)

    def _setup_key_bindings(self):
        self.accel_group = gtk.AccelGroup()
        self.main_window.add_accel_group(self.accel_group)
        # TODO: Move this to where it should be
        #gtk.accel_map_add_entry("<Virtaal>/Edit/Search", gtk.keysyms.F3, 0)
        #self.accel_group.connect_by_path("<Virtaal>/Edit/Search", self._on_search)


    # ACCESSORS #
    def add_accel_group(self, accel_group):
        """Add the given accelerator group to the main window.
            @type accel_group: gtk.AccelGroup()"""
        self.main_window.add_accel_group(accel_group)

    def set_saveable(self, value):
        menuitem = self.gui.get_widget("save_menuitem")
        menuitem.set_sensitive(value)
        filename = self.controller.get_store_filename()
        if filename:
            modified = ""
            if value:
                modified = "*"
            self.main_window.set_title(
                    (_('Virtaal - %(current_file)s %(modified_marker)s') %
                        {
                            "current_file": os.path.basename(filename),
                            "modified_marker": modified
                        }
                    ).rstrip()
                )
        self.modified = value

    def set_statusbar_message(self, msg):
        self.status_bar.pop(self.statusbar_context_id)
        self.status_bar.push(self.statusbar_context_id, msg)
        if msg:
            time.sleep(self.WRAP_DELAY)


    # METHODS #
    def quit(self):
        gtk.main_quit()

    def show(self):
        self.main_window.show()
        gtk.main()

    def show_input_dialog(self, title='', message=''):
        """Shows a simple dialog containing a text entry.
            @returns: The text entered into the dialog, or C{None}."""
        self.input_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.input_dialog
        response, text = self.input_dialog.run(title=title, message=message)
        self.input_dialog.hide()
        self._top_window = old_top

        if response == gtk.RESPONSE_OK:
            return text
        return None

    def show_open_dialog(self, title=''):
        """@returns: The selected file name and URI if the OK button was clicked.
            C{None} otherwise."""
        if title:
            self.open_chooser.set_title(title)

        if os.path.exists(pan_app.settings.general["lastdir"]):
            self.open_chooser.set_current_folder(pan_app.settings.general["lastdir"])

        self.open_chooser.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.open_chooser
        response = self.open_chooser.run() == gtk.RESPONSE_OK
        self.open_chooser.hide()
        self._top_window = old_top

        if response:
            return (self.open_chooser.get_filename(), self.open_chooser.get_uri())
        else:
            return ()

    def show_error_dialog(self, title='', message='', markup=''):
        fill_dialog(self.error_dialog, title, message, markup)

        self.error_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.error_dialog
        response = self.error_dialog.run()
        self.error_dialog.hide()
        self._top_window = old_top

    def show_prompt_dialog(self, title='', message='', markup=''):
        fill_dialog(self.prompt_dialog, title, message, markup)

        self.prompt_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.prompt_dialog
        response = self.prompt_dialog.run()
        self.prompt_dialog.hide()
        self._top_window = old_top

        return response == gtk.RESPONSE_YES

    def show_info_dialog(self, title='', message='', markup=''):
        """shows a simple info dialog containing a message and an OK button"""
        fill_dialog(self.info_dialog, title, message, markup)

        self.info_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.info_dialog
        response = self.info_dialog.run()
        self.info_dialog.hide()
        self._top_window = old_top

    def show_save_dialog(self, title=''):
        """@returns: C{True} if the OK button was pressed, C{False} for any
            other response."""
        if title:
            self.save_chooser.set_title(title)

        directory, filename = os.path.split(self.controller.get_store().get_filename())
        self.save_chooser.set_current_folder(directory)

        self.save_chooser.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.save_chooser
        response = self.save_chooser.run()
        self.save_chooser.hide()
        self._top_window = old_top

        return response == gtk.RESPONSE_OK

    def show_save_confirm_dialog(self):
        """@returns: One of C{'save'}, C{'discard'}, C{'cancel'} or C{''},
            depending on the button pressed."""
        self.confirm_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.confirm_dialog
        response = self.confirm_dialog.run()
        self.confirm_dialog.hide()
        self._top_window = old_top

        if response == gtk.RESPONSE_YES:
            return 'save'
        elif response == gtk.RESPONSE_NO:
            return 'discard'
        elif response == gtk.RESPONSE_CANCEL:
            return 'cancel'
        return ''


    # SIGNAL HANDLERS #
    def _on_controller_registered(self, main_controller, new_controller):
        if not main_controller.store_controller == new_controller:
            return
        if getattr(self, '_store_loaded_handler_id ', None):
            main_controller.store_controller.disconnect(self._store_loaded_handler_id)

        self._store_loaded_handler_id = new_controller.connect('store-loaded', self._on_store_loaded)

    def _on_documentation(self, _widget=None):
        openmailto.open("http://translate.sourceforge.net/wiki/virtaal/index")

    def _on_file_open(self, _widget, destroyCallback=None):
        filename_and_uri = self.show_open_dialog()
        if filename_and_uri:
            filename, uri = filename_and_uri
            self._uri = uri
            self.controller.open_file(filename, uri=uri)

    def _on_file_save(self, widget=None):
        # we force save us on potentially destructive file level
        # operations like updating to a template
        if self.controller.get_force_saveas():
            res = self._on_file_saveas(widget)
            self.controller.set_force_saveas(not res)
        else:
            self.controller.save_file()

    def _on_file_saveas(self, widget=None):
        store_filename = self.controller.get_store_filename()
        if store_filename:
            directory, filename = os.path.split(self.controller.get_store_filename())
        else:
            filename = ''
        self.save_chooser.set_current_name(filename)
        if self.show_save_dialog():
            self.controller.save_file(filename=self.save_chooser.get_filename())
            return True
        return False

    def _on_file_update(self, _widget, destroyCallback=None):
        filename_and_uri = self.show_open_dialog()
        if filename_and_uri:
            filename, uri = filename_and_uri
            self._uri = uri
            self.controller.update_file(filename, uri=uri)

    def _on_localization_guide(self, _widget=None):
        # Should be more redundent
        # If the guide is installed and no internet then open local
        # If Internet then go live, if no Internet or guide then disable
        openmailto.open("http://translate.sourceforge.net/wiki/guide/start")

    def _on_help_about(self, _widget=None):
        AboutDialog(self.main_window)

    def _on_mainwindow_delete(self, _widget, _event):
        self.controller.quit()

    def _on_quit(self, _event):
        self.controller.quit()

    def _on_recent_file_activated(self, chooser):
        item = chooser.get_current_item()
        if item.exists():
            # For now we only handle local files, and limited the recent
            # manager to only give us those anyway, so we can get the filename
            self.controller.open_file(item.get_uri_display(), uri=item.get_uri())

    def _on_report_bug(self, _widget=None):
        openmailto.open("http://bugs.locamotion.org/enter_bug.cgi?product=Virtaal&version=%s" % __version__.ver)

    def _on_store_loaded(self, store_controller):
        self.gui.get_widget('saveas_menuitem').set_sensitive(True)
        self.gui.get_widget('update_menuitem').set_sensitive(True)
        if getattr(self, '_uri', None):
            recent.rm.add_item(self._uri)
