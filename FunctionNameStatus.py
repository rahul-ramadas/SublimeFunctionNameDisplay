import sublime
import sublime_plugin
import re
import sys
from time import time

# Ideas taken from C0D312, nizur & tito in http://www.sublimetext.com/forum/viewtopic.php?f=2&t=4589
# Also, from https://github.com/SublimeText/WordHighlight/blob/master/word_highlight.py

def plugin_loaded():
    global Pref

    class Pref:
        def load(self):
            Pref.display_file      = settings.get('display_file', False)
            Pref.display_class     = settings.get('display_class', False)
            Pref.display_function  = settings.get('display_function', True)
            Pref.display_arguments = settings.get('display_arguments', False)
            Pref.wait_time         = settings.get('update_delay', 0.50)
            Pref.time              = time()

    settings = sublime.load_settings('Function Name Display.sublime-settings')
    Pref = Pref()
    Pref.load()
    settings.add_on_change('reload', lambda:Pref.load())

clean_name = re.compile('^\s*(public\s+|private\s+|protected\s+|static\s+|function\s+|def\s+)+', re.I)

class FunctionNameStatusEventHandler(sublime_plugin.EventListener):

    def __init__(self):
        self.pending_deferred_task = False

    # on_activated_async seems to not fire on startup
    def on_activated(self, view):
        Pref.time = time()
        view.settings().set('function_name_status_row', -1)
        self.display_current_class_and_function(view, 'activated')

    def on_selection_modified_async(self, view):
        Pref.time = time()
        if not self.pending_deferred_task:
            self.pending_deferred_task = True
            sublime.set_timeout_async(lambda:self.display_current_class_and_function_delayed(view),
                                      int(1000 * Pref.wait_time))

    def display_current_class_and_function_delayed(self, view):
        last_time = Pref.time
        now = time()
        remaining_time = int(1000 * (Pref.wait_time - (now - last_time)))
        epsilon = 100
        if (remaining_time < 100):
            self.pending_deferred_task = False
            self.display_current_class_and_function(view, 'selection_modified:delayed')
        else:
            sublime.set_timeout_async(lambda:self.display_current_class_and_function_delayed(view),
                                      remaining_time)

    # display the current class and function name
    def display_current_class_and_function(self, view, where):
        # print("display_current_class_and_function running from " + where)
        view_settings = view.settings()
        if view_settings.get('is_widget'):
            return

        for region in view.sel():
            region_row, region_col = view.rowcol(region.begin())

            if region_row != view_settings.get('function_name_status_row', -1):
                view_settings.set('function_name_status_row', region_row)
            else:
                return

            s = ""
            found = False

            fname = view.file_name()
            if Pref.display_file and None != fname:
                 s = fname + " "

            # Look for any classes
            if Pref.display_class:
                class_regions = view.find_by_selector('entity.name.type.class')
                for r in reversed(class_regions):
                    row, col = view.rowcol(r.begin())
                    if row <= region_row:
                        s += view.substr(r)
                        found = True
                        break;

            # Look for any functions
            if Pref.display_function:
                function_regions = view.find_by_selector('meta.function')
                if function_regions:
                    for r in reversed(function_regions):
                        row, col = view.rowcol(r.begin())
                        if row <= region_row:
                            if Pref.display_class and s:
                                s += "::"
                            lines = view.substr(r).splitlines()
                            name = clean_name.sub('', lines[0])
                            if Pref.display_arguments:
                                s += name.strip()
                            else:
                                if 'C++' in view.settings().get('syntax'):
                                    if Pref.display_class or len(name.split('(')[0].split('::'))<2:
                                        s += name.split('(')[0].strip()
                                    else:
                                        s += name.split('(')[0].split('::')[1].strip()
                                else:
                                    s += name.split('(')[0].split(':')[0].strip()
                            found = True
                            break

            if not found:
                view.erase_status('function')
                fname = view.file_name()
                if Pref.display_file and None != fname:
                    view.set_status('function', fname)
            else:
                view.set_status('function', s)

            return

        view.erase_status('function')
