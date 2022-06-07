import sublime
import sublime_plugin
import os

class FileContents:

  project_folder_path = "[project]"

  def __init__(self, file_name, short_name, folder_name):
    self.file_name = file_name
    self.short_name = short_name
    self.folder_name = folder_name

  def folder_path(self):
    if self.folder_name is None:
      return None
    else:
      # Path without folder name
      base_path = self.removeprefix(self.file_name, self.folder_name)
      # Path without file name
      relative_base_path = self.removesuffix(base_path, self.short_name)
      # Path without starting and ending path separator
      with_leading_ending_path_sep = self.strip_path_sep(relative_base_path)
      if with_leading_ending_path_sep:
        return with_leading_ending_path_sep
      else:
        # with_leading_ending_path_sep is empty, the file is in the project dir
        return self.project_folder_path

  def strip_path_sep(self, original):
    return self.strip_char(original, os.path.sep)

  def strip_char(self, original, char):
    return self.removesuffix(self.removeprefix(original, char), char)

  # removeprefix is added in Python 3.9+
  def removeprefix(self, original, prefix):
    if original.startswith(prefix):
      return original[len(prefix):]
    else:
      return original

  # removesuffix is added in Python 3.9+
  def removesuffix(self, original, prefix):
    if original.endswith(prefix):
      return original[:-len(prefix)]
    else:
      return original

  """
    Returns a truncated path should the path length exceed
    a certain maximum value.
  """
  def truncated_path(self, settings):
    folder_path = self.folder_path()
    if folder_path == self.project_folder_path:
      return ""
    else:
      if len(folder_path) > settings.truncation_line_length:
        return "...{}".format(folder_path[-settings.truncation_preview_length:])
      else:
        return ""

  def __str__(self):
    return "FileContents(file_name={0}, short_name={1}, folder_name={2})".format(self.file_name, self.short_name, self.folder_name)

  def __repr__(self):
    return self.__str__()

class BufferContents:
  def __init__(self, tab_name):
    self.tab_name = tab_name

  def __str__(self):
    return "BufferContents(tab_name={0})".format(self.tab_name)

  def __repr__(self):
    return self.__str__()

class OpenTabSettings:

  def __init__(self, truncation_line_length, truncation_preview_length):
    self.truncation_line_length = truncation_line_length
    self.truncation_preview_length = truncation_preview_length

  def __str__(self):
    return "OpenTabSettings(truncation_line_length={0}, truncation_preview_length={1})".format(self.truncation_line_length, self.truncation_preview_length)

  def __repr__(self):
    return self.__str__()

class OpenTabsCommand(sublime_plugin.WindowCommand):

  def load_open_tab_settings(self):
    settings = sublime.load_settings("OpenTabs.sublime-settings")
    if settings.has('truncation_line_length') and settings.has('truncation_preview_length'):
      return OpenTabSettings(settings.get('truncation_line_length'), settings.get('truncation_preview_length'))
    else:
      print(
        """
        Could not find 'truncation_line_length' and 'truncation_preview_length' settings.
         Defaulting truncation_line_length: 30 and truncation_preview_length:15
         Update OpenTabs.sublime-settings to change the above values.
        """
      )

      return OpenTabSettings(30, 15)

  def run(self):
    window = self.window
    self.views = window.views()
    self.tracked_views = []
    self.selected_index = -1
    self.index = -1

    self.settings = self.load_open_tab_settings()

    folder_name = self.get_folder_name()

    for view in self.views:
      self.index += 1 #start at 0
      active_view = self.window.active_view()
      if active_view and active_view == view:
        self.selected_index = self.index

      file_name = view.file_name()
      if file_name:
        short_name = os.path.basename(file_name)
        contents = FileContents(file_name, short_name, folder_name)
        self.tracked_views.append(contents)
      else:
        if view.name():
          contents = BufferContents(view.name())
          self.tracked_views.append(contents)

    if self.tracked_views:
      panel_items = self.create_panel_items()
      window.show_quick_panel(
        items = panel_items,
        on_select = self.when_file_selected,
        placeholder = "OpenTabs: {}".format(len(panel_items)),
        on_highlight = self.when_file_selected
      )

  def get_folder_name(self):
    window = self.window
    if window:
      variables = window.extract_variables()
      if variables:
        return variables.get('folder') # could be None

  def create_panel_items(self):
    return list(map(lambda content: self.create_file_panel_item(content), self.tracked_views))

  def create_file_panel_item(self, some_content):
    if type(some_content) == FileContents:
      file_content = some_content
      return sublime.QuickPanelItem(file_content.short_name, "<u>{}</u>".format(file_content.folder_path()), file_content.truncated_path(self.settings), sublime.KIND_VARIABLE)
    else:
      buffer_content = some_content
      return sublime.QuickPanelItem(buffer_content.tab_name, "", "unsaved", sublime.KIND_NAVIGATION)

  def when_file_selected(self, index):
    user_selection = self.selected_index if index == -1 else index
    if user_selection != -1 and self.tracked_views and len(self.tracked_views) > user_selection:
      some_content = self.tracked_views[user_selection]
      if type(some_content) == FileContents:
        self.find_tab_by_filename(some_content)
      else:
        self.find_tab_by_name(some_content)


  def find_tab_by_filename(self, file_content):
    window = self.window
    view = window.find_open_file(file_content.file_name)
    if view:
      window.focus_view(view)

  def find_tab_by_name(self, tab_content):
    window = self.window
    view = self.find_view_by_tab_name(tab_content.tab_name)
    if view:
      window.focus_view(view)


  def find_view_by_tab_name(self, tab_name):
    for view in self.views:
      if not view.file_name() and view.name() == tab_name:
        return view

    return None

  def is_enabled(self):
    views = self.window.views()
    return views is not None and len(views) != 0

  def is_visible(self):
    views = self.window.views()
    return views is not None and len(views) != 0
