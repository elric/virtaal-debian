#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
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

import gtk
import locale
import os
import sys
import logging
from gtk import gdk

from virtaal.views import recent, theme
from virtaal.common import pan_app

from baseview import BaseView

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

# XXX: This class is based on main_window.py:Virtaal from the pre-MVC days (Virtaal 0.2).
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
        self.main_window = self.gui.get_widget("MainWindow")

        if sys.platform == 'darwin':
            try:
                gtk.rc_parse(pan_app.get_abs_data_filename(["OSX_Leopard_theme", "gtkrc"]))
            except:
                logging.exception("Couldn't find OSX_Leopard_theme")
            # Sometimes we have two resize grips: one from GTK, one from Aqua. We
            # might want to disable the GTK one:
            #self.gui.get_widget('status_bar').set_property("has-resize-grip", False)
            try:
                # FIXME: Rename the separators that were automatically named by Glade
                import igemacintegration
                # Move the menu bar to the mac menu
                menubar = self.gui.get_widget('menubar')
                igemacintegration.ige_mac_menu_set_menu_bar(menubar)
                menubar.hide()
                igemacintegration.ige_mac_menu_connect_window_key_handler(self.main_window)
                # Move the quit menu item
                mnu_quit = self.gui.get_widget("mnu_quit")
                igemacintegration.ige_mac_menu_set_quit_menu_item(mnu_quit)
                mnu_quit.hide()
                self.gui.get_widget("separatormenuitem2").hide()
                # Move the about menu item
                mnu_about = self.gui.get_widget("mnu_about")
                group = igemacintegration.ige_mac_menu_add_app_menu_group()
                igemacintegration.ige_mac_menu_add_app_menu_item(group, mnu_about, None)
                self.gui.get_widget("separator1").hide()
                # Move the preferences menu item
                mnu_about = self.gui.get_widget("mnu_prefs")
                group = igemacintegration.ige_mac_menu_add_app_menu_group()
                igemacintegration.ige_mac_menu_add_app_menu_item(group, mnu_about, None)
                self.gui.get_widget("menuitem5").hide()
            except ImportError, e:

                logging.debug("igemacintegration module not found. Expect zero integration with the mac desktop.")

        self.main_window.connect('destroy', self._on_quit)
        self.main_window.connect('delete-event', self._on_quit)
        # File menu signals
        self.gui.get_widget('mnu_open').connect('activate', self._on_file_open)
        self.gui.get_widget('mnu_save').connect('activate', self._on_file_save)
        self.gui.get_widget('mnu_saveas').connect('activate', self._on_file_saveas)
        self.gui.get_widget('mnu_close').connect('activate', self._on_file_close)
        self.gui.get_widget('mnu_update').connect('activate', self._on_file_update)
        self.gui.get_widget('mnu_revert').connect('activate', self._on_file_revert)
        self.gui.get_widget('mnu_quit').connect('activate', self._on_quit)
        # View menu signals
        self.gui.get_widget('mnu_fullscreen').connect('activate', self._on_fullscreen)
        # Help menu signals
        self.gui.get_widget('mnu_documentation').connect('activate', self._on_documentation)
        self.gui.get_widget('mnu_tutorial').connect('activate', self._on_tutorial)
        self.gui.get_widget('mnu_localization_guide').connect('activate', self._on_localization_guide)
        self.gui.get_widget('mnu_report_bug').connect('activate', self._on_report_bug)
        self.gui.get_widget('mnu_about').connect('activate', self._on_help_about)

        # The classic menu bar:
        self.menubar = self.gui.get_widget('menubar')
        # The menu structure, regardless of where it is shown (initially the menubar):
        self.menu_structure = self.menubar
        self.status_bar = self.gui.get_widget("status_bar")
        self.status_bar.set_sensitive(False)
        self.statusbar_context_id = self.status_bar.get_context_id("statusbar")
        #Only used in full screen, initialised as needed
        self.btn_app = None
        self.app_menu = None

        self.main_window.set_icon_from_file(pan_app.get_abs_data_filename(["icons", "virtaal.ico"]))
        self.main_window.resize(
            int(pan_app.settings.general['windowwidth']),
            int(pan_app.settings.general['windowheight'])
        )
        self._top_window = self.main_window

        self.main_window.connect('window-state-event', self._on_window_state_event)

        recent_files = self.gui.get_widget("mnu_recent_files")
        recent.rc.connect("item-activated", self._on_recent_file_activated)
        recent_files.set_submenu(recent.rc)

        self.controller.connect('controller-registered', self._on_controller_registered)
        self._create_dialogs()
        self._setup_key_bindings()
        self._track_window_state()
        self.main_window.connect('style-set', self._on_style_set)

    def _create_dialogs(self):
        self._input_dialog = None
        self._error_dialog = None
        self._prompt_dialog = None
        self._info_dialog = None
        self._save_chooser = None
        self._open_chooser = None
        self._confirm_dialog = None

    @property
    def input_dialog(self):
        # Generic input dialog
        if not self._input_dialog:
            self._input_dialog = EntryDialog(self.main_window)
        return self._input_dialog

    @property
    def error_dialog(self):
        if not self._error_dialog:
        # Error dialog
            self._error_dialog = gtk.MessageDialog(self.main_window,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_ERROR,
                gtk.BUTTONS_OK)
            self._error_dialog.set_title(_("Error"))
        return self._error_dialog

    @property
    def prompt_dialog(self):
        # Yes/No prompt dialog
        if not self._prompt_dialog:
            self._prompt_dialog = gtk.MessageDialog(self.main_window,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_QUESTION,
                gtk.BUTTONS_YES_NO,
            )
            self._prompt_dialog.set_default_response(gtk.RESPONSE_NO)
        return self._prompt_dialog

    @property
    def info_dialog(self):
        # Informational dialog
        if not self._info_dialog:
            self._info_dialog = gtk.MessageDialog(self.main_window,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_INFO,
                gtk.BUTTONS_OK,
            )
        return self._info_dialog

    @property
    def open_chooser(self):
        # Open (file chooser) dialog
        if not self._open_chooser:
            self._open_chooser = gtk.FileChooserDialog(
                _('Choose a Translation File'),
                self.main_window,
                gtk.FILE_CHOOSER_ACTION_OPEN,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
            )
            self._open_chooser.set_default_response(gtk.RESPONSE_OK)
            all_supported_filter = gtk.FileFilter()
            all_supported_filter.set_name(_("All Supported Files"))
            self._open_chooser.add_filter(all_supported_filter)
            from translate.storage import factory as storage_factory
            supported_files_dict = dict([ (_(name), (extensions, mimetypes)) for name, extensions, mimetypes in storage_factory.supported_files() ])
            supported_file_names = supported_files_dict.keys()
            supported_file_names.sort(cmp=locale.strcoll)
            for name in supported_file_names:
                extensions, mimetypes = supported_files_dict[name]
                #XXX: we can't open generic .csv formats, so listing it is probably
                # more harmful than good.
                if "csv" in extensions:
                    continue
                new_filter = gtk.FileFilter()
                new_filter.set_name(name)
                if extensions:
                    for extension in extensions:
                        new_filter.add_pattern("*." + extension)
                        all_supported_filter.add_pattern("*." + extension)
                        for compress_extension in storage_factory.decompressclass.keys():
                            new_filter.add_pattern("*.%s.%s" % (extension, compress_extension))
                            all_supported_filter.add_pattern("*.%s.%s" % (extension, compress_extension))
                if mimetypes:
                    for mimetype in mimetypes:
                        new_filter.add_mime_type(mimetype)
                        all_supported_filter.add_mime_type(mimetype)
                self._open_chooser.add_filter(new_filter)

            #doc_filter = gtk.FileFilter()
            #doc_filter.set_name(_('Translatable documents'))
            #from translate.convert import factory as convert_factory
            #for extension in convert_factory.converters.keys():
            #    if isinstance(extension, tuple):
            #        continue # Skip extensions that need templates
            #    doc_filter.add_pattern('*.' + extension)
            #    all_supported_filter.add_pattern('*.' + extension)
            #self._open_chooser.add_filter(doc_filter)

            #proj_filter = gtk.FileFilter()
            #proj_filter.set_name(_('Translate project bundles'))
            #proj_filter.add_pattern('*.zip')
            #all_supported_filter.add_pattern('*.zip')
            #self._open_chooser.add_filter(proj_filter)

            all_filter = gtk.FileFilter()
            all_filter.set_name(_("All Files"))
            all_filter.add_pattern("*")
            self._open_chooser.add_filter(all_filter)

        return self._open_chooser

    @property
    def save_chooser(self):
        # Save (file chooser) dialog
        if not self._save_chooser:
            self._save_chooser = gtk.FileChooserDialog(
                _("Save"),
                self.main_window,
                gtk.FILE_CHOOSER_ACTION_SAVE,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK)
            )
            self._save_chooser.set_do_overwrite_confirmation(True)
            self._save_chooser.set_default_response(gtk.RESPONSE_OK)
        return self._save_chooser

    @property
    def confirm_dialog(self):
        # Save confirmation dialog (Save/Discard/Cancel buttons)
        if not self._confirm_dialog:
            (RESPONSE_SAVE, RESPONSE_DISCARD) = (gtk.RESPONSE_YES, gtk.RESPONSE_NO)
            self._confirm_dialog = gtk.MessageDialog(
                self.main_window,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_QUESTION,
                gtk.BUTTONS_NONE,
                _("The current file has been modified.\nDo you want to save your changes?")
            )
            self._confirm_dialog.__save_button = self._confirm_dialog.add_button(gtk.STOCK_SAVE, RESPONSE_SAVE)
            self._confirm_dialog.add_button(_("_Discard"), RESPONSE_DISCARD)
            self._confirm_dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            self._confirm_dialog.set_default_response(RESPONSE_SAVE)
        return self._confirm_dialog

    def _setup_key_bindings(self):
        self.accel_group = gtk.AccelGroup()
        self.main_window.add_accel_group(self.accel_group)

    def _track_window_state(self):
        self._window_is_maximized = False

        def on_state_event(widget, event):
            self._window_is_maximized = bool(event.new_window_state & gtk.gdk.WINDOW_STATE_MAXIMIZED)
        self.main_window.connect('window-state-event', on_state_event)

    def _on_style_set(self, widget, prev_style):
        theme.update_style(widget)


    # ACCESSORS #
    def add_accel_group(self, accel_group):
        """Add the given accelerator group to the main window.
            @type accel_group: gtk.AccelGroup"""
        self.main_window.add_accel_group(accel_group)

    def set_saveable(self, value):
        menuitem = self.gui.get_widget("mnu_save")
        menuitem.set_sensitive(value)
        menuitem = self.gui.get_widget("mnu_revert")
        menuitem.set_sensitive(value)
        filename = self.controller.get_store_filename()
        if filename:
            modified = ""
            if value:
                modified = "*"
            self.main_window.set_title(
                    #l10n: This is the title of the main window of Virtaal
                    #%(modified_marker)s is a star that is displayed if the file is modified, and should be at the start of the window title
                    #%(current_file)s is the file name of the current file
                    #most languages will not need to change this
                    (_('%(modified_marker)s%(current_file)s - Virtaal') %
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
    def ask_plural_info(self):
        """Ask the user to provide plural information.
            @returns: A 2-tuple containing the number of plurals as the first
                element and the plural equation as the second element."""
        # Adapted from Virtaal 0.2's document.py:compute_nplurals
        def ask_for_number_of_plurals():
            while True:
                try:
                    nplurals = self.show_input_dialog(message=_("Please enter the number of noun forms (plurals) to use"))
                    return int(nplurals)
                except ValueError, _e:
                    pass

        def ask_for_plurals_equation():
            return self.show_input_dialog(message=_("Please enter the plural equation to use"))

        from translate.lang import factory as langfactory
        lang     = langfactory.getlanguage(self.controller.lang_controller.target_lang.code)
        nplurals = lang.nplurals or ask_for_number_of_plurals()
        if nplurals > 1 and lang.pluralequation == "0":
            return nplurals, ask_for_plurals_equation()
        else:
            # Note that if nplurals == 1, the default equation "0" is correct
            return nplurals, lang.pluralequation

    def append_menu(self, name):
        """Add a menu with the given name to the menu bar."""
        menu = gtk.Menu()
        menuitem = gtk.MenuItem(name)
        menuitem.set_submenu(menu)
        self.menu_structure.append(menuitem)
        self.menu_structure.show_all()
        return menuitem

    def append_menu_item(self, name, menu, after=None):
        """Add a new menu item with the given name to the menu with the given
            name (C{menu})."""
        if isinstance(after, (str, unicode)):
            after = self.find_menu(after)

        parent_item = None
        if isinstance(menu, gtk.MenuItem):
            parent_item = menu
        else:
            parent_item = self.find_menu(menu)
        if parent_item is None:
            return None

        parent_menu = parent_item.get_submenu()
        menuitem = gtk.MenuItem(name)
        if after is None:
            parent_menu.add(menuitem)
        else:
            after_index = parent_menu.get_children().index(after) + 1
            parent_menu.insert(menuitem, after_index)
        self.menu_structure.show_all()
        return menuitem

    def find_menu(self, label):
        """Find the menu with the given label on the menu bar."""
        for menuitem in self.menu_structure.get_children():
            if menuitem.get_child() and menuitem.get_child().get_text() == label:
                return menuitem

        if '_' in label:
            return self.find_menu(label.replace('_', ''))

        return None

    def find_menu_item(self, label, menu=None):
        """Find the menu item with the given label and in the menu with the
            given name (if it exists).

            @param label: The label of the menu item to find.
            @param menu: The (optional) (name of the) menu to search in."""
        if not isinstance(menu, gtk.MenuItem):
            menu = self.find_menu(label)
        if menu is not None:
            menus = [menu]
        else:
            menus = [mi for mi in self.menu_structure.get_children()]

        for menuitem in menus:
            for item in menuitem.get_submenu().get_children():
                if item.get_child() and item.get_child().get_text() == label:
                    return item, menuitem

        if '_' in label:
            return self.find_menu_item(label.replace('_', ''), menu)

        return None, None

    def open_file(self):
        filename_and_uri = self.show_open_dialog()
        if filename_and_uri:
            filename, uri = filename_and_uri
            self._uri = uri
            return self.controller.open_file(filename, uri=uri)
        return False

    def quit(self):
        if self._window_is_maximized:
            pan_app.settings.general['maximized'] = 1
        else:
            width, height = self.main_window.get_size()
            pan_app.settings.general['windowwidth'] = width
            pan_app.settings.general['windowheight'] = height
            pan_app.settings.general['maximized'] = ''
        pan_app.settings.write()
        gtk.main_quit()

    def show(self):
        if pan_app.settings.general['maximized']:
            self.main_window.maximize()
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
        last_path = (pan_app.settings.general["lastdir"] or "").decode(sys.getdefaultencoding())

        from virtaal.support import native_widgets
        if native_widgets.dialog_to_use == 'kdialog':
            return native_widgets.kdialog_open_dialog(self.main_window, title, last_path)
        elif native_widgets.dialog_to_use == 'win32':
            return native_widgets.win32_open_dialog(title, last_path)

        # otherwise we always fall back to the default code
        if title:
            self.open_chooser.set_title(title)

        if os.path.exists(last_path):
            self.open_chooser.set_current_folder(last_path)

        self.open_chooser.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.open_chooser
        response = self.open_chooser.run() == gtk.RESPONSE_OK
        self.open_chooser.hide()
        self._top_window = old_top

        if response:
            filename = self.open_chooser.get_filename().decode('utf-8')
            pan_app.settings.general["lastdir"] = os.path.dirname(filename)
            return (filename, self.open_chooser.get_uri().decode('utf-8'))
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

    def show_save_dialog(self, title='', current_filename=None):
        """@returns: C{True} if the OK button was pressed, C{False} for any
            other response."""
        if not current_filename:
            current_filename = self.controller.get_store().get_filename()

        from virtaal.support import native_widgets
        if native_widgets.dialog_to_use == 'kdialog':
            return native_widgets.kdialog_save_dialog(self.main_window, title, current_filename)
        elif native_widgets.dialog_to_use == 'win32':
            return native_widgets.win32_save_dialog(title, current_filename)

        # otherwise we always fall back to the default code
        if title:
            self.save_chooser.set_title(title)

        directory, filename = os.path.split(current_filename)

        if os.access(directory, os.F_OK | os.R_OK | os.X_OK | os.W_OK):
            self.save_chooser.set_current_folder(directory)
        self.save_chooser.set_current_name(filename)

        self.save_chooser.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.save_chooser
        response = self.save_chooser.run()
        self.save_chooser.hide()
        self._top_window = old_top

        if response == gtk.RESPONSE_OK:
            filename = self.save_chooser.get_filename().decode('utf-8')
            #FIXME: do we need uri here?
            return filename

    def show_save_confirm_dialog(self):
        """@returns: One of C{'save'}, C{'discard'}, or C{'cancel'},
            depending on the button pressed."""
        self.confirm_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.confirm_dialog
        self.confirm_dialog.__save_button.grab_focus()
        response = self.confirm_dialog.run()
        self.confirm_dialog.hide()
        self._top_window = old_top

        if response == gtk.RESPONSE_YES:
            return 'save'
        elif response == gtk.RESPONSE_NO:
            return 'discard'
        return 'cancel'

    def show_app_icon(self):
        if not self.btn_app:
            self.btn_app = self.gui.get_widget('btn_app')
            image = self.gui.get_widget('img_app')
            image.set_from_file(pan_app.get_abs_data_filename(['icons', 'hicolor', '24x24', 'mimetypes', 'x-translation.png']))
            self.app_menu = gtk.Menu()
            self.btn_app.connect('pressed', self._on_app_pressed)
            self.btn_app.show()
        for child in self.menu_structure:
            child.reparent(self.app_menu)
        self.menu_structure = self.app_menu
        self.btn_app.show()

    def hide_app_icon(self):
        self.btn_app.hide()
        for child in self.app_menu:
            child.reparent(self.menubar)
        self.menu_structure = self.menubar

    # SIGNAL HANDLERS #
    def _on_controller_registered(self, main_controller, new_controller):
        if not main_controller.store_controller == new_controller:
            return
        if getattr(self, '_store_loaded_handler_id ', None):
            main_controller.store_controller.disconnect(self._store_loaded_handler_id)

        self._store_closed_handler_id = new_controller.connect('store-closed', self._on_store_closed)
        self._store_loaded_handler_id = new_controller.connect('store-loaded', self._on_store_loaded)

    def _on_documentation(self, _widget=None):
        from virtaal.support import openmailto
        openmailto.open("http://translate.sourceforge.net/wiki/virtaal/index")

    def _on_file_open(self, _widget):
        self.open_file()

    def _on_file_save(self, widget=None):
        self.controller.save_file()

    def _on_file_saveas(self, widget=None):
        self.controller.save_file(force_saveas=True)

    def _on_file_close(self, widget=None):
        self.controller.close_file()

    def _on_file_update(self, _widget):
        filename_and_uri = self.show_open_dialog()
        if filename_and_uri:
            filename, uri = filename_and_uri
            self._uri = uri
            self.controller.update_file(filename, uri=uri)

    def _on_file_revert(self, widget=None):
        self.controller.revert_file()

    def _on_fullscreen(self, widget=None):
        if widget.get_active():
            self.main_window.fullscreen()
            self.status_bar.hide()
            self.show_app_icon()
            self.menubar.hide()
        else:
            self.main_window.unfullscreen()
            self.status_bar.show()
            self.hide_app_icon()
            self.menubar.show()

    def _on_tutorial(self, widget=None):
        self.controller.open_tutorial()

    def _on_localization_guide(self, _widget=None):
        # Should be more redundent
        # If the guide is installed and no internet then open local
        # If Internet then go live, if no Internet or guide then disable
        from virtaal.support import openmailto
        openmailto.open("http://translate.sourceforge.net/wiki/guide/start")

    def _on_help_about(self, _widget=None):
        from widgets.aboutdialog import AboutDialog
        AboutDialog(self.main_window)

    def _on_quit(self, *args):
        self.controller.quit()
        return True

    def _on_recent_file_activated(self, chooser):
        item = chooser.get_current_item()
        if item.exists():
            # For now we only handle local files, and limited the recent
            # manager to only give us those anyway, so we can get the filename
            self._uri = item.get_uri()
            self.controller.open_file(item.get_uri_display().decode('utf-8'), uri=item.get_uri().decode('utf-8'))

    def _on_report_bug(self, _widget=None):
        from virtaal.support import openmailto
        from virtaal import __version__
        openmailto.open("http://bugs.locamotion.org/enter_bug.cgi?product=Virtaal&version=%s" % __version__.ver)

    def _on_store_closed(self, store_controller):
        for widget_name in ('mnu_saveas', 'mnu_close', 'mnu_update', 'mnu_properties'):
            self.gui.get_widget(widget_name).set_sensitive(False)
        self.status_bar.set_sensitive(False)
        self.main_window.set_title(_('Virtaal'))

    def _on_store_loaded(self, store_controller):
        self.gui.get_widget('mnu_saveas').set_sensitive(True)
        self.gui.get_widget('mnu_close').set_sensitive(True)
        self.gui.get_widget('mnu_update').set_sensitive(True)
        self.gui.get_widget('mnu_properties').set_sensitive(True)
        self.status_bar.set_sensitive(True)
        if store_controller.project:
            if not store_controller._archivetemp:
                recent.rm.add_item('file://' + store_controller.get_bundle_filename())
        else:
            if getattr(self, '_uri', None):
                recent.rm.add_item(self._uri)
            else:
                recent.rm.add_item('file://' + os.path.abspath(store_controller.store.filename))

    def _on_window_state_event(self, widget, event):
        mnu_fullscreen = self.gui.get_widget('mnu_fullscreen')
        mnu_fullscreen.set_active(event.new_window_state & gdk.WINDOW_STATE_FULLSCREEN)

    def _on_app_pressed(self, btn):
        self.app_menu.popup(None, None, None, 0, 0)
