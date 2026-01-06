"""
live_text_check.py
Threaded live spelling + grammar checking for PyQt6 QTextEdit using LanguageTool.

- Red wavy underline = spelling
- Blue wavy underline = grammar
- Right-click on/near an issue to get suggestions + actions

Dependencies:
    pip install language-tool-python

Optional (RECOMMENDED for local grammar):
    Install Java (JRE/JDK 17+) and provide java_path or ensure JAVA_HOME/PATH.

Why local:
    Public API is rate-limited and will break live checking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set
import os
import shutil

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot


@dataclass
class SpellIssue:
    start: int
    length: int
    word: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class GrammarIssue:
    start: int
    length: int
    message: str
    replacements: List[str] = field(default_factory=list)


@dataclass
class CheckResult:
    spell: List[SpellIssue] = field(default_factory=list)
    grammar: List[GrammarIssue] = field(default_factory=list)
    error: Optional[str] = None


class _LTWorker(QObject):
    result_ready = pyqtSignal(object)  # CheckResult
    debug = pyqtSignal(str)

    def __init__(
        self,
        language: str = "en-US",
        do_spell: bool = True,
        do_grammar: bool = True,
        java_path: Optional[str] = None,
    ):
        super().__init__()
        self.language = language
        self.do_spell = do_spell
        self.do_grammar = do_grammar
        self.java_path = java_path  # optional explicit java.exe path

        self._tool = None
        self._using_public_api = False
        self._ignore_words: Set[str] = set()
        self._custom_words: Set[str] = set()

    def set_ignore_words(self, words: Set[str]):
        self._ignore_words = set(words)

    def set_custom_words(self, words: Set[str]):
        self._custom_words = set(words)

    def _ensure_java_visible(self):
        """
        Make sure the worker process can find Java.
        This matters if running under PyCharm/venv where PATH differs from CMD.
        """
        if self.java_path:
            # If java_path points to java.exe, ensure its folder is on PATH
            java_dir = os.path.dirname(self.java_path)
            os.environ["PATH"] = java_dir + ";" + os.environ.get("PATH", "")
            os.environ["JAVA_HOME"] = os.path.dirname(java_dir)  # parent of /bin
            return

        # Otherwise, see if java is discoverable
        if shutil.which("java"):
            return

        # If not, emit debug; tool creation will fail, but message is clearer
        self.debug.emit("[LiveTextChecker] Java not found in this process PATH. "
                        "Set java_path explicitly when creating LiveTextChecker.")

    def _ensure_tool(self):
        if self._tool is not None:
            return

        try:
            import language_tool_python  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "language_tool_python is not installed. Run: pip install language-tool-python"
            ) from e

        # Ensure java is visible before creating tool
        self._ensure_java_visible()

        try:
            # ✅ LOCAL tool (no rate limits)
            # language_tool_python supports java_path in newer versions; if yours doesn’t,
            # our PATH/JAVA_HOME injection above still solves it.
            try:
                if self.java_path:
                    self._tool = language_tool_python.LanguageTool(
                        self.language,
                        java_path=self.java_path
                    )
                else:
                    self._tool = language_tool_python.LanguageTool(self.language)
            except TypeError:
                # Older language_tool_python without java_path kwarg
                self._tool = language_tool_python.LanguageTool(self.language)
            self._using_public_api = False
            self.debug.emit("[LiveTextChecker] LanguageTool initialized (local).")
        except Exception as e:
            self.debug.emit(f"[LiveTextChecker] Local LanguageTool init failed: {e}. "
                            "Falling back to public API.")
            try:
                self._tool = language_tool_python.LanguageToolPublicAPI(self.language)
                self._using_public_api = True
                self.debug.emit("[LiveTextChecker] LanguageTool initialized (public API).")
            except Exception as api_error:
                raise RuntimeError(f"Failed to initialize LanguageTool: {api_error}") from api_error

    @pyqtSlot(str)
    def check_text(self, text: str):
        try:
            if not text or not text.strip():
                self.result_ready.emit(CheckResult(spell=[], grammar=[]))
                return

            # Tool needed if either spelling or grammar is enabled
            if self.do_spell or self.do_grammar:
                self._ensure_tool()

            matches = self._tool.check(text) if self._tool else []

            spell: List[SpellIssue] = []
            grammar: List[GrammarIssue] = []

            for m in matches:
                start = int(getattr(m, "offset", 0))
                length = int(getattr(m, "errorLength", 0))
                if length <= 0:
                    continue

                frag = text[start:start + length].strip()
                low = frag.lower()

                if low in self._ignore_words or low in self._custom_words:
                    continue

                issue_type = str(getattr(m, "ruleIssueType", "")).lower()
                replacements = list(getattr(m, "replacements", []) or [])[:8]

                if self.do_spell and issue_type == "misspelling":
                    spell.append(SpellIssue(start=start, length=length, word=frag, suggestions=replacements))
                else:
                    if self.do_grammar:
                        grammar.append(
                            GrammarIssue(
                                start=start,
                                length=length,
                                message=str(getattr(m, "message", "Possible issue")),
                                replacements=replacements,
                            )
                        )

            self.result_ready.emit(CheckResult(spell=spell, grammar=grammar))

        except Exception as e:
            if not self._using_public_api:
                try:
                    self._tool = None
                    self._ensure_tool()
                    matches = self._tool.check(text) if self._tool else []
                    spell: List[SpellIssue] = []
                    grammar: List[GrammarIssue] = []
                    for m in matches:
                        start = int(getattr(m, "offset", 0))
                        length = int(getattr(m, "errorLength", 0))
                        if length <= 0:
                            continue
                        frag = text[start:start + length].strip()
                        low = frag.lower()
                        if low in self._ignore_words or low in self._custom_words:
                            continue
                        issue_type = str(getattr(m, "ruleIssueType", "")).lower()
                        replacements = list(getattr(m, "replacements", []) or [])[:8]
                        if self.do_spell and issue_type == "misspelling":
                            spell.append(SpellIssue(start=start, length=length, word=frag, suggestions=replacements))
                        else:
                            if self.do_grammar:
                                grammar.append(
                                    GrammarIssue(
                                        start=start,
                                        length=length,
                                        message=str(getattr(m, "message", "Possible issue")),
                                        replacements=replacements,
                                    )
                                )
                    self.result_ready.emit(CheckResult(spell=spell, grammar=grammar))
                    return
                except Exception as retry_error:
                    self.result_ready.emit(CheckResult(spell=[], grammar=[], error=str(retry_error)))
                    return
            self.result_ready.emit(CheckResult(spell=[], grammar=[], error=str(e)))


class LiveTextChecker(QObject):
    result_ready = pyqtSignal(object)  # CheckResult
    debug = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QObject] = None,
        language: str = "en_US",
        debounce_ms: int = 900,  # ✅ bump debounce for local LT stability
        do_spell: bool = True,
        do_grammar: bool = True,
        java_path: Optional[str] = None,  # ✅ allow explicit java.exe path
    ):
        super().__init__(parent)

        lt_lang = "en-US" if language.lower().startswith("en") else language

        self._debounce_ms = debounce_ms
        self._pending_text: str = ""
        self._ignore_words_session: Set[str] = set()
        self._custom_words: Set[str] = set()

        self._thread = QThread(self)
        self._worker = _LTWorker(
            language=lt_lang,
            do_spell=do_spell,
            do_grammar=do_grammar,
            java_path=java_path
        )
        self._worker.moveToThread(self._thread)

        self._worker.result_ready.connect(self._on_result)
        self._worker.debug.connect(self.debug)

        self._thread.start()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire_check)

    def stop(self):
        try:
            self._thread.quit()
            self._thread.wait(1500)
        except Exception:
            pass

    def ignore_word_session(self, word: str):
        if word:
            self._ignore_words_session.add(word.lower())
            self._worker.set_ignore_words(self._ignore_words_session)

    def add_custom_word(self, word: str):
        if word:
            self._custom_words.add(word.lower())
            self._worker.set_custom_words(self._custom_words)

    def schedule(self, text: str):
        self._pending_text = text or ""
        self._timer.start(self._debounce_ms)

    def _fire_check(self):
        self._worker.set_ignore_words(self._ignore_words_session)
        self._worker.set_custom_words(self._custom_words)
        QTimer.singleShot(0, lambda: self._worker.check_text(self._pending_text))

    @pyqtSlot(object)
    def _on_result(self, result: CheckResult):
        if getattr(result, "error", None):
            self.debug.emit(f"[LiveTextChecker] Error: {result.error}")
        self.result_ready.emit(result)
