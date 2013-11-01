# -*- coding: utf-8 -*-
u"""
:author: Joseph Martinot-Lagarde

Created on Sat Jan 19 14:57:57 2013
"""
from __future__ import (
    print_function, unicode_literals, absolute_import, division)

try:
    import autopep8
    is_autopep8_installed = True

    # Check version
    try:
        autopep8.fix_string
        has_autopep8_fix_string = True

        FIX_LIST = {}  # Should be an ordereddict
        for code, description in autopep8.supported_fixes():
            code = code.strip()
            description = description.strip()
            if description not in FIX_LIST:
                FIX_LIST[description] = [code]
            else:
                FIX_LIST[description].append(code)
        DEFAULT_IGNORE = set(("E711", "E712", "W6"))
    except AttributeError:
        has_autopep8_fix_string = False
except ImportError:
    is_autopep8_installed = False

from spyderlib.qt.QtGui import (
    QWidget, QTextCursor, QVBoxLayout, QGroupBox, QScrollArea, QLabel,
    QCheckBox)

# Local imports
from spyderlib.baseconfig import get_translation
_ = get_translation("p_autopep8", dirname="spyderplugins")
from spyderlib.utils.qthelpers import get_icon, create_action
from spyderlib.py3compat import to_text_string

from spyderlib.plugins import SpyderPluginMixin, PluginConfigPage


class AutoPEP8ConfigPage(PluginConfigPage):
    """Widget with configuration options for line profiler
    """
    def setup_page(self):

        options_group = QGroupBox(_("Options"))
        passes_spin = self.create_spinbox(
            _("Additional pep8 passes: "), _("(-1 is infinite)"), 'passes',
            default=-1, min_=-1, max_=1000000, step=10)
        aggressive_spin = self.create_spinbox(
            _("Level of aggressivity: "), None, 'aggressive',
            default=0, min_=0, max_=2, step=1)

        fix_layout = QVBoxLayout()
        indent = QCheckBox(" ").sizeHint().width()
        print(indent)
        for description in sorted(FIX_LIST, key=lambda k: FIX_LIST[k]):
            codes = FIX_LIST[description]
            if not DEFAULT_IGNORE.intersection(codes):
                option = self.create_checkbox(
                    ", ".join(codes), ",".join(codes), default=True)
            else:
                option = self.create_checkbox(
                    "{codes} - ({warning})".format(
                        codes=", ".join(codes), warning=_("UNSAFE")),
                    ",".join(codes), default=False)
            fix_layout.addWidget(option)
            label = QLabel(_(description))
            label.setWordWrap(True)
            label.setIndent(indent)
            font = label.font()
            font.setPointSizeF(font.pointSize() * 0.9)
            label.setFont(font)
            fix_layout.addWidget(label)

        options_layout = QVBoxLayout()
        options_layout.addWidget(passes_spin)
        options_layout.addWidget(aggressive_spin)
        options_group.setLayout(options_layout)

        widget_scroll = QWidget()
        widget_scroll.setLayout(fix_layout)
        fix_scroll = QScrollArea()
        fix_scroll.setWidget(widget_scroll)
        fix_scroll.setWidgetResizable(True)
        fig_out_layout = QVBoxLayout()
        fig_out_layout.addWidget(fix_scroll, 1)
        fix_group = QGroupBox(_("Errors/warnings to fix"))
        fix_group.setLayout(fig_out_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(options_group)
        vlayout.addWidget(fix_group, 1)
        self.setLayout(vlayout)


class AutoPEP8(QWidget, SpyderPluginMixin):  # pylint: disable=R0904
    """Python source code automatic formatting based on autopep8.

    QObject is needed to register the action.
    """
    CONF_SECTION = "autopep8"
    CONFIGWIDGET_CLASS = AutoPEP8ConfigPage

    def __init__(self, parent=None):
        QWidget.__init__(self, parent=parent)
        SpyderPluginMixin.__init__(self, parent)

    #------ SpyderPluginMixin API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Autopep8")

    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('profiler.png')

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        pass

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        autopep8_act = create_action(
            self, _("Run autopep8 code autoformatting"),
            triggered=self.run_autopep8)
        autopep8_act.setEnabled(is_autopep8_installed
                                and has_autopep8_fix_string)
        self.register_shortcut(autopep8_act, context="Editor",
                               name="Run autoformatting", default="Shift+F8")

        self.main.source_menu_actions += [None, autopep8_act]
        self.main.editor.pythonfile_dependent_actions += [autopep8_act]

    def refresh_plugin(self):
        """Refresh autopep8 widget"""
        pass

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        pass

    #------ Public API --------------------------------------------------------
    def run_autopep8(self):
        """Format code with autopep8"""
        if not is_autopep8_installed:
            self.main.statusBar().showMessage(
                _("Unable to run: the 'autopep8' python module is not"
                  " installed."))
            return
        if not has_autopep8_fix_string:
            self.main.statusBar().showMessage(
                _("Unable to run: the the minimum version of 'autopep8' python"
                  " module is 0.8.6, please upgrade."))
            return

        # Retrieve active fixes
        ignore = []
        for description in FIX_LIST:
            codes = ",".join(FIX_LIST[description])
            if not self.get_option(codes):
                ignore.append(codes)

        # Retrieve text of current opened file
        editorstack = self.main.editor.get_current_editorstack()
        index = editorstack.get_stack_index()
        finfo = editorstack.data[index]
        editor = finfo.editor
        cursor = editor.textCursor()
        cursor.beginEditBlock()  # Start cancel block
        options = [""]
        if not cursor.hasSelection():
            position_start = 0
            cursor.select(QTextCursor.Document)  # Select all
        else:
            # Select whole lines
            position_end = cursor.selectionEnd()
            cursor.setPosition(cursor.selectionStart())
            cursor.movePosition(QTextCursor.StartOfLine)
            position_start = cursor.position()
            cursor.setPosition(position_end, QTextCursor.KeepAnchor)
            cursor.movePosition(QTextCursor.StartOfLine,
                                QTextCursor.KeepAnchor)
            position_lastline_start = cursor.position()
            if not position_end == position_lastline_start:
                cursor.movePosition(QTextCursor.EndOfLine,
                                    QTextCursor.KeepAnchor)
                # Select EOL if not on a new line
                if not position_lastline_start == cursor.position():
                    cursor.movePosition(QTextCursor.Right,
                                        QTextCursor.KeepAnchor)

            # Disable checks of newlines at end of file
            if not cursor.atEnd():
                ignore.append("W391")

        # replace(): See qt doc for QTextCursor.selectedText()
        text_before = to_text_string(
            cursor.selectedText().replace("\u2029", "\n"))

        # Run autopep8
        options = ["", "--ignore", ",".join(ignore),
                   "--pep8-passes", str(self.get_option("passes")),
                   "--max-line-length",
                   str(self.window().editor.get_option("edge_line_column"))]
        for aggressive in range(self.get_option("aggressive")):
            options.append("--aggressive")
        options = autopep8.parse_args(options)[0]
        text_after = autopep8.fix_string(text_before, options)

        # Apply new text if needed
        if text_before != text_after:
            cursor.insertText(text_after)  # Change text

        cursor.endEditBlock()  # End cancel block

        # Select changed text
        position_end = cursor.position()
        cursor.setPosition(position_start, QTextCursor.MoveAnchor)
        cursor.setPosition(position_end, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)

        self.main.statusBar().showMessage(
            _("Autopep8 finished !"))


#==============================================================================
# The following statements are required to register this 3rd party plugin:
#==============================================================================
PLUGIN_CLASS = AutoPEP8  # pylint: disable=C0103
