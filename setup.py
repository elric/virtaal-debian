#!/usr/bin/env python

from distutils.core import setup, Distribution, Command
from virtaal.__version__ import ver as virtaal_version
import glob
import os
import os.path as path
import sys

try:
    import py2exe
    build_exe = py2exe.build_exe.py2exe
    Distribution = py2exe.Distribution
except ImportError:
    py2exe = None
    build_exe = Command

SOURCE_DATA_DIR = path.join('share', 'virtaal')
TARGET_DATA_DIR = path.join("share", "virtaal")

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Programming Language :: Python",
    "Topic :: Software Development :: Localization",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Operating System :: OS Independent",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: Unix"
]

options = {
    'data_files': [
        (path.join(TARGET_DATA_DIR, "autocorr"), glob.glob(path.join(SOURCE_DATA_DIR, "autocorr", "*"))),
        (TARGET_DATA_DIR, glob.glob(path.join(SOURCE_DATA_DIR, "*.*"))), 
    ],
    'scripts': [
        "bin/virtaal"
    ],
    'packages': [
        "virtaal",
        "virtaal.support",
        "virtaal.widgets"
    ],
}

#############################
# WIN 32 specifics

def get_compile_command():
    try:
        import _winreg
        compile_key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, "innosetupscriptfile\\shell\\compile\\command")
        compilecommand = _winreg.QueryValue(compile_key, "")
        compile_key.Close()

    except:
        compilecommand = "compil32.exe"
    return compilecommand

def chop(dist_dir, pathname):
    """returns the path relative to dist_dir"""
    assert pathname.startswith(dist_dir)
    return pathname[len(dist_dir):]

def create_inno_script(name, _lib_dir, dist_dir, exe_files, other_files, version = "1.0"):
    if not dist_dir.endswith(os.sep):
        dist_dir += os.sep
    exe_files = [chop(dist_dir, p) for p in exe_files]
    other_files = [chop(dist_dir, p) for p in other_files]
    pathname = path.join(dist_dir, name + os.extsep + "iss")

# See http://www.jrsoftware.org/isfaq.php for more InnoSetup config options.
    ofi = open(pathname, "w")
    print >> ofi, r'''; WARNING: This script has been created by py2exe. Changes to this script
; will be overwritten the next time py2exe is run!

[Setup]
AppName=%(name)s
AppVerName=%(name)s %(version)s
AppPublisher=Zuza Software Foundation
AppPublisherURL=http://www.translate.org.za/
AppVersion=%(version)s
AppSupportURL=http://translate.sourceforge.net/
;AppComments=
;AppCopyright=Copyright (C) 2007-2008 Zuza Software Foundation
DefaultDirName={pf}\%(name)s
DefaultGroupName=%(name)s
OutputBaseFilename=%(name)s-%(version)s-setup
ChangesAssociations=yes
SetupIconFile=%(icon_path)s

[Files]''' % {'name': name, 'version': version, 'icon_path': path.join(TARGET_DATA_DIR, "virtaal.ico")}
    for fpath in exe_files + other_files:
        print >> ofi, r'Source: "%s"; DestDir: "{app}\%s"; Flags: ignoreversion' % (fpath, os.path.dirname(fpath))
    print >> ofi, r'''
[Icons]
Name: "{group}\%(name)s Translation Editor"; Filename: "{app}\virtaal.exe";
Name: "{group}\%(name)s (uninstall)"; Filename: "{uninstallexe}"''' % {'name': name}

#    For now we don't worry about install scripts
#    if install_scripts:
#        print >> ofi, r"[Run]"
#
#        for fpath in install_scripts:
#            print >> ofi, r'Filename: "{app}\%s"; WorkingDir: "{app}"; Parameters: "-install"' % fpath
#
#        print >> ofi
#        print >> ofi, r"[UninstallRun]"
#
#        for fpath in install_scripts:
#            print >> ofi, r'Filename: "{app}\%s"; WorkingDir: "{app}"; Parameters: "-remove"' % fpath

    # File associations. Note the directive "ChangesAssociations=yes" above
    # that causes the installer to tell Explorer to refresh associations.
    # This part might cause the created installer to need administrative
    # privileges. An alternative might be to rather write to
    # HKCU\Software\Classes, but this won't be system usable then. Didn't
    # see a way to test and alter the behaviour.

    # For each file type we should have something like this:
    #
    #;File extension:
    #Root: HKCR; Subkey: ".po"; ValueType: string; ValueName: ""; ValueData: "virtaal_po"; Flags: uninsdeletevalue
    #;Description of the file type
    #Root: HKCR; Subkey: "virtaal_po"; ValueType: string; ValueName: ""; ValueData: "Gettext PO"; Flags: uninsdeletekey
    #;Icon to use in Explorer
    #Root: HKCR; Subkey: "virtaal_po\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icons\virtaal.ico"
    #;The command to open the file
    #Root: HKCR; Subkey: "virtaal_po\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\virtaal.exe"" ""%1"""

    print >> ofi, "[Registry]"
    from virtaal.formats import supported_types
    for description, extentions, _mimetypes in supported_types:
        # We skip those types where we depend on mime types, not extentions
        if not extentions:
            continue
        # Form a key from the first extention for internal only
        key = extentions[0].replace('*.', '')
        # Associate each extention with the file type
        for extention in extentions:
            extention = extention.replace('*', '')
            print >> ofi, r'Root: HKCR; Subkey: "%(extention)s"; ValueType: string; ValueName: ""; ValueData: "virtaal_%(key)s"; Flags: uninsdeletevalue' % {'extention': extention, 'key': key}
        print >> ofi, r'''Root: HKCR; Subkey: "virtaal_%(key)s"; ValueType: string; ValueName: ""; ValueData: "%(description)s"; Flags: uninsdeletekey
Root: HKCR; Subkey: "virtaal_%(key)s\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icons\virtaal.ico"
Root: HKCR; Subkey: "virtaal_%(key)s\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\virtaal.exe"" ""%%1"""''' % {'key': key, 'description': description}

    # Show a "Launch VirTaal" checkbox on the last installer screen
    print >> ofi, r'''
[Run]
Filename: "{app}\virtaal.exe"; Description: "{cm:LaunchProgram,%(name)s}"; Flags: nowait postinstall skipifsilent''' % {'name': name}
    print >> ofi
    ofi.close()
    return pathname

def compile_inno_script(script_path):
    """compiles the script using InnoSetup"""
    shell_compile_command = get_compile_command()
    compile_command = shell_compile_command.replace('"%1"', script_path)
    result = os.system(compile_command)
    if result:
        print "Error compiling iss file"
        print "Opening iss file, use InnoSetup GUI to compile manually"
        os.startfile(script_path)

class BuildWin32Installer(build_exe):
    """distutils class that first builds the exe file(s), then creates a Windows installer using InnoSetup"""
    description = "create an executable installer for MS Windows using InnoSetup and py2exe"
    user_options = getattr(build_exe, 'user_options', []) + \
        [('install-script=', None,
          "basename of installation script to be run after installation or before deinstallation")]

    def initialize_options(self):
        build_exe.initialize_options(self)

    def run(self):
        # First, let py2exe do it's work.
        build_exe.run(self)
        # create the Installer, using the files py2exe has created.
        exe_files = self.windows_exe_files + self.console_exe_files
        print "*** creating the inno setup script***"
        script_path = create_inno_script(self.distribution.metadata.name, self.lib_dir, self.dist_dir, exe_files, self.lib_files,
                                         version=self.distribution.metadata.version)
        print "*** compiling the inno setup script***"
        compile_inno_script(script_path)
        # Note: By default the final setup.exe will be in an Output subdirectory.

def find_gtk_bin_directory():
    GTK_NAME = "libgtk"
    # Look for GTK in the user's Path as well as in some familiar locations
    paths = os.environ['Path'].split(';') + [r'C:\GTK\bin', r'C:\Program Files\GTK\bin']
    for p in paths:
        files = [path.join(p, f) for f in os.listdir(p) if path.isfile(path.join(p, f)) and f.startswith(GTK_NAME)]
        if len(files) > 0:
            return p
    raise Exception("""Could not find the GTK runtime.
Please place bin directory of your GTK installation in the program path.""")

def find_gtk_files():
    def parent(dir_path):
        return path.abspath(path.join(path.abspath(dir_path), '..'))

    def strip_leading_path(leadingPath, p):
        return p[len(leadingPath) + 1:]

    data_files = []
    gtk_path = parent(find_gtk_bin_directory())
    for dir_path in [path.join(gtk_path, p) for p in ('etc', 'share', 'lib')]:
        for dir_name, _, files in os.walk(dir_path):
            files = [path.abspath(path.join(dir_name, f)) for f in files]
            if len(files) > 0:
                data_files.append((strip_leading_path(gtk_path, dir_name), files))
    return data_files

def add_win32_options(options):
    """This function is responsible for finding data files and setting options necessary
    to build executables and installers under Windows.

    @return: A 2-tuple (data_files, options), where data_files is a list of Windows
             specific data files (this would include the GTK binaries) and where
             options are the options required by py2exe."""
    if py2exe != None and ('py2exe' in sys.argv or 'innosetup' in sys.argv):
        options['data_files'].extend(find_gtk_files())

        py2exe_options = {
            "packages":   ["encodings", "virtaal"],
            "compressed": True,
            "excludes":   ["PyLucene", "Tkconstants", "Tkinter", "tcl", "translate.misc._csv"],
            "dist_dir":   "virtaal-win32",
            "includes":   ["lxml", "lxml._elementpath", "psyco", "cairo", "pango", "pangocairo", "atk", "gobject", "gtk.keysyms"],
            "optimize":   2,
        }
        innosetup_options = py2exe_options.copy()
        options.update({
            "windows": [
                {
                    'script': 'bin/virtaal',
                    'icon_resources': [(1, path.join(SOURCE_DATA_DIR, "virtaal.ico"))],
                }
            ],
            'zipfile':  "virtaal.zip",
            "options": {
                "py2exe":    py2exe_options,
                "innosetup": innosetup_options
            },
            'cmdclass':  {
                "py2exe":    build_exe,
                "innosetup": BuildWin32Installer
            }
        })
    return options

#############################
# General functions

def add_platform_specific_options(options):
    # For now, we only have win32 to worry about
    return add_win32_options(options)

def create_manifest(data_files):
    f = open('MANIFEST.in', 'w+')
    for _dest_path, data_file_list in data_files:
        f.write("include ")
        f.write(" ".join(data_file_list))
        f.write("\n")
    f.close()

def main(options):
    options = add_platform_specific_options(options)
    create_manifest(options['data_files'])
    setup(name="virtaal",
          version=virtaal_version,
          license="GNU General Public License (GPL)",
          description="A tool to create program translations.",
          long_description="""VirTaal is used to create program translations.

          It uses the Translate Toolkit to get access to translation files and therefore
          can edit a variety of files (including PO and XLIFF files).""",
          author="Translate.org.za",
          author_email="translate-devel@lists.sourceforge.net",
          url="http://translate.sourceforge.net/wiki/virtaal/index",
          download_url="http://sourceforge.net/project/showfiles.php?group_id=91920&package_id=270877",
          platforms=["any"],
          classifiers=classifiers,
          **options)

if __name__ == '__main__':
    main(options)
