"""Textual TUI for reviewing Voice of the World candidate lines."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, Markdown, Static

from supergene.voice_review import (
    ReviewAction,
    ReviewCandidate,
    ReviewDecision,
    append_accepted_seed,
    default_decisions_path,
    load_pending_candidates,
    record_decision,
)


class VoiceReviewApp(App[None]):
    """Interactive Textual app for reviewing Voice of the World candidates."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #summary {
        dock: top;
        height: 3;
        padding: 0 1;
        background: $surface;
    }

    #body {
        height: 1fr;
        padding: 1 2;
    }

    #candidate {
        height: auto;
        min-height: 9;
        border: solid $primary;
        padding: 1 2;
    }

    #metadata {
        height: auto;
        min-height: 5;
        margin-top: 1;
    }

    #context {
        height: auto;
        min-height: 5;
        margin-top: 1;
        border: round $panel;
        padding: 1 2;
    }

    #editor {
        display: none;
        margin-top: 1;
    }

    #status {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $surface;
    }

    .score {
        width: 1fr;
    }
    """

    BINDINGS = [
        Binding("a", "accept", "Accept"),
        Binding("e", "edit", "Edit"),
        Binding("r", "reject", "Reject"),
        Binding("s", "skip", "Skip"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        review_path: Path,
        seed_path: Path,
        decisions_path: Path | None = None,
    ) -> None:
        """Initialize the review app.

        Args:
            review_path: CSV file containing review-needed candidates.
            seed_path: Seed file to append accepted candidate lines to.
            decisions_path: Optional JSONL file for persisted decisions.
        """

        super().__init__()
        self.review_path = review_path
        self.seed_path = seed_path
        self.decisions_path = decisions_path or default_decisions_path(review_path)
        self.candidates: list[ReviewCandidate] = []
        self.index = 0
        self.accepted_count = 0
        self.rejected_count = 0
        self.skipped_count = 0
        self.edited_text_by_id: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        """Create the app layout."""

        yield Header(show_clock=True)
        yield Static("", id="summary")
        with Vertical(id="body"):
            yield Markdown("", id="candidate")
            with Horizontal(id="metadata"):
                yield Static("", id="score-final", classes="score")
                yield Static("", id="score-tfidf", classes="score")
                yield Static("", id="score-fuzzy", classes="score")
                yield Static("", id="score-keyword", classes="score")
            yield Markdown("", id="context")
            yield Input(placeholder="Edit current candidate, then press Enter", id="editor", disabled=True)
        yield Label("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Load candidates and render the first item when the app starts."""

        self.candidates = load_pending_candidates(self.review_path, self.decisions_path)
        self._render_current()

    def action_accept(self) -> None:
        """Accept the current candidate and append it to the seed file."""

        candidate = self._current_candidate()
        if candidate is None:
            return
        reviewed_text = self._candidate_text(candidate)
        appended = append_accepted_seed(self.seed_path, reviewed_text)
        self._record(candidate, ReviewAction.ACCEPT)
        self.accepted_count += 1
        suffix = "appended to seeds" if appended else "already in seeds"
        self._advance(f"Accepted: {suffix}.")

    def action_edit(self) -> None:
        """Edit the current candidate text before deciding."""

        candidate = self._current_candidate()
        if candidate is None:
            return
        editor = self.query_one("#editor", Input)
        editor.value = self._candidate_text(candidate)
        editor.disabled = False
        editor.display = True
        editor.focus()
        self.query_one("#status", Label).update("Editing candidate. Press Enter to apply.")

    def action_reject(self) -> None:
        """Reject the current candidate."""

        candidate = self._current_candidate()
        if candidate is None:
            return
        self._record(candidate, ReviewAction.REJECT)
        self.rejected_count += 1
        self._advance("Rejected.")

    def action_skip(self) -> None:
        """Skip the current candidate for this review session."""

        candidate = self._current_candidate()
        if candidate is None:
            return
        self.skipped_count += 1
        self.index += 1
        self._render_current("Skipped for now.")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Apply edited candidate text when the editor is submitted.

        Args:
            event: Textual input submission event.
        """

        if event.input.id != "editor":
            return
        candidate = self._current_candidate()
        if candidate is None:
            return
        edited_text = event.value.strip()
        if edited_text:
            self.edited_text_by_id[candidate.candidate_id] = edited_text
        event.input.disabled = True
        event.input.display = False
        self._render_current("Edited candidate text applied.")

    def _record(self, candidate: ReviewCandidate, action: ReviewAction) -> None:
        """Persist a decision for a candidate.

        Args:
            candidate: Candidate being reviewed.
            action: Selected review action.
        """

        record_decision(
            self.decisions_path,
            ReviewDecision(
                candidate_id=candidate.candidate_id,
                action=action,
                raw_text=self._candidate_text(candidate),
                chapter_file=candidate.chapter_file,
                line_number=candidate.line_number,
            ),
        )

    def _advance(self, message: str) -> None:
        """Move to the next candidate and update the UI.

        Args:
            message: Status message to display after advancing.
        """

        self.index += 1
        self._render_current(message)

    def _current_candidate(self) -> ReviewCandidate | None:
        """Return the candidate currently displayed."""

        if self.index >= len(self.candidates):
            return None
        return self.candidates[self.index]

    def _candidate_text(self, candidate: ReviewCandidate) -> str:
        """Return the edited text for a candidate, falling back to raw text.

        Args:
            candidate: Candidate being displayed or decided.

        Returns:
            Edited candidate text when available.
        """

        return self.edited_text_by_id.get(candidate.candidate_id, candidate.raw_text)

    def _render_current(self, status: str = "") -> None:
        """Render the active candidate and review progress.

        Args:
            status: Optional status message for the bottom bar.
        """

        remaining = max(0, len(self.candidates) - self.index)
        self.query_one("#summary", Static).update(
            " | ".join(
                [
                    f"Review file: {self.review_path}",
                    f"Seed file: {self.seed_path}",
                    f"Remaining: {remaining}",
                    f"Accepted: {self.accepted_count}",
                    f"Rejected: {self.rejected_count}",
                    f"Skipped: {self.skipped_count}",
                ]
            )
        )

        candidate = self._current_candidate()
        if candidate is None:
            self.query_one("#candidate", Markdown).update(
                "# Review Complete\n\nNo pending review candidates remain."
            )
            self.query_one("#context", Markdown).update("")
            self.query_one("#editor", Input).display = False
            self.query_one("#status", Label).update(status or "Press q to quit.")
            for widget_id in ("#score-final", "#score-tfidf", "#score-fuzzy", "#score-keyword"):
                self.query_one(widget_id, Static).update("")
            return

        position = self.index + 1
        title = candidate.title or "Untitled chapter"
        candidate_text = self._candidate_text(candidate)
        edited_marker = " *(edited)*" if candidate_text != candidate.raw_text else ""
        self.query_one("#candidate", Markdown).update(
            "\n\n".join(
                [
                    f"## {position} / {len(self.candidates)} - {title}",
                    f"`{candidate.chapter_file}:{candidate.line_number}`",
                    f"**Category:** `{candidate.category}`",
                    f"### Candidate{edited_marker}",
                    f"> {candidate_text}",
                    "### Closest Seed",
                    f"> {candidate.matched_seed or '(none)'}",
                ]
            )
        )
        self.query_one("#score-final", Static).update(f"Final: {candidate.final_score:.3f}")
        self.query_one("#score-tfidf", Static).update(f"TF-IDF: {candidate.tfidf_similarity:.3f}")
        self.query_one("#score-fuzzy", Static).update(f"Fuzzy: {candidate.fuzzy_similarity:.3f}")
        self.query_one("#score-keyword", Static).update(f"Keyword: {candidate.keyword_score:.3f}")
        self.query_one("#context", Markdown).update(
            "\n\n".join(
                [
                    "### Context",
                    f"Before: {candidate.context_before or '(none)'}",
                    f"After: {candidate.context_after or '(none)'}",
                ]
            )
        )
        self.query_one("#status", Label).update(status or "a accept | r reject | s skip | q quit")


def run_voice_review_tui(
    review_path: Path,
    seed_path: Path,
    decisions_path: Path | None = None,
) -> None:
    """Run the Textual Voice of the World review app.

    Args:
        review_path: CSV file containing review-needed candidates.
        seed_path: Seed file to append accepted candidates to.
        decisions_path: Optional JSONL file for saved decisions.
    """

    VoiceReviewApp(review_path, seed_path, decisions_path).run()
