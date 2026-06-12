#!/usr/bin/env python3
"""
find_voice_lines.py

Search a directory of Markdown chapters for lines similar to known
"Voice of the World" announcement lines.

Pipeline:
1. Load seed examples from voice_of_the_world.txt
2. Extract candidate lines from .md files
3. Prefilter candidates using Voice-like keywords/patterns
4. Score candidates against seed examples using TF-IDF cosine similarity
5. Add rule-based boosts for strong Voice-of-the-World markers
6. Export likely matches and review-needed matches

Install:
    uv add rich loguru pandas scikit-learn rapidfuzz

Run:
    uv run python find_voice_lines.py \
        --chapters ./chapters \
        --seeds ./voice_of_the_world.txt \
        --out ./output

Optional:
    uv run python find_voice_lines.py \
        --chapters ./chapters \
        --seeds ./voice_of_the_world.txt \
        --out ./output \
        --likely-threshold 0.65 \
        --review-threshold 0.45
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from loguru import logger
from rapidfuzz import fuzz
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


console = Console()


VOICE_KEYWORDS = [
    "killed",
    "hunted",
    "beast soul",
    "no beast soul",
    "beast soul gained",
    "beast soul obtained",
    "geno point",
    "geno points",
    "life essence",
    "life geno essence",
    "flesh eaten",
    "meat eaten",
    "flesh consumed",
    "meat consumed",
    "consumed",
    "gained",
    "obtained",
    "evolution successful",
    "status of evolver",
    "status of surpasser",
    "gene found",
    "xenogeneic",
    "gene +1",
    "identifying beast soul",
    "super body",
    "gene lock",
    "absorbed",
    "life span",
]

# These markers define the high-recall prefilter. They are intentionally broad
# because the later hybrid scorer is responsible for demoting prose/dialogue.
STRONG_MARKERS = [
    "beast soul",
    "geno point",
    "geno points",
    "life essence",
    "life geno essence",
    "killed",
    "hunted",
    "eaten",
    "consumed",
    "obtained",
    "gained",
    "xenogeneic",
    "identifying beast soul",
    "evolution successful",
]

DIALOGUE_MARKERS = [
    " said ",
    " asked ",
    " replied ",
    " shouted ",
    " cried ",
    " thought ",
    " murmured ",
    " whispered ",
    " exclaimed ",
]

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("kill_announcement", ["killed"]),
    ("hunted_announcement", ["hunted"]),
    ("beast_soul_result", ["beast soul"]),
    ("geno_point_gain", ["geno point", "geno points", "gene +1"]),
    ("life_essence", ["life essence", "life geno essence", "essence absorbed"]),
    ("eaten_or_consumed", ["eaten", "consumed", "flesh", "meat"]),
    ("evolution_status", ["evolution successful", "status of evolver", "status of surpasser"]),
    ("gene_lock", ["gene lock"]),
    ("xenogeneic_gene", ["xenogeneic"]),
    ("system_notice", ["announcement:", "identifying beast soul", "super body exhausted"]),
]


@dataclass
class Candidate:
    """A candidate line for the Voice of the World."""
    chapter_file: str
    chapter_index: int | None
    title: str | None
    line_number: int
    raw_text: str
    normalized_text: str
    context_before: str
    context_after: str
    keyword_score: float
    tfidf_similarity: float = 0.0
    fuzzy_similarity: float = 0.0
    final_score: float = 0.0
    matched_seed: str = ""
    category: str = "unknown_voice"
    decision: str = "unscored"


@dataclass(frozen=True)
class VoiceLineSearchSummary:
    """Summary counts from a Voice of the World line search."""

    total_candidates: int
    likely_count: int
    review_count: int


def normalize_text(text: str) -> str:
    """Normalize text for matching while preserving meaning."""
    logger.trace("Entering normalize_text")
    replacements = {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "—": " ",
        "–": " ",
        "…": "...",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(pattern=r"<!--.*?-->", repl=" ", string=text)
    text = re.sub(pattern=r"[*_`>#\-\[\]\(\)]", repl=" ", string=text)
    text = re.sub(pattern=r"\s+", repl=" ", string=text)
    return text.strip().lower()


def clean_display_text(text: str) -> str:
    """Clean markdown wrappers but keep readable original casing."""
    logger.trace("Entering clean_display_text")
    text = text.strip()
    text = re.sub(r"^\s*[-*>]+\s*", "", text)
    text = text.strip("*_` ")
    text = text.strip()
    if len(text) >= 2 and text[0] in {'"', "“"} and text[-1] in {'"', "”"}:
        text = text[1:-1].strip()
    return text


def extract_frontmatter(lines: list[str]) -> tuple[int | None, str | None]:
    """Pull index/title from simple YAML frontmatter when present."""
    logger.trace("Entering extract_frontmatter")
    if not lines or lines[0].strip() != "---":
        return None, None

    index = None
    title = None

    for line in lines[1:80]:
        if line.strip() == "---":
            break

        index_match = re.match(r"index:\s*(\d+)", line.strip())
        if index_match:
            index = int(index_match.group(1))

        title_match = re.match(r'title:\s*["\']?(.*?)["\']?\s*$', line.strip())
        if title_match:
            title = title_match.group(1)

    return index, title


def split_possible_voice_segments(line: str) -> list[str]:
    """
    Extract quote-like and sentence-like segments.

    Voice lines are often wrapped in bold markdown quotes, but sometimes
    appear as plain text or malformed quoted snippets.
    """
    logger.trace("Entering split_possible_voice_segments")
    original = line.strip()
    if not original:
        return []

    segments: list[str] = []

    # Extract curly/straight quoted spans.
    quote_patterns = [
        r"[“\"]([^“”\"]{5,})[”\"]",
        r"[‘']([^‘’']{5,})[’']",
    ]
    for pattern in quote_patterns:
        for match in re.finditer(pattern, original):
            segments.append(match.group(1).strip())

    if segments:
        seen = set()
        unique_quoted_segments = []
        for segment in segments:
            cleaned = clean_display_text(segment)
            key = normalize_text(cleaned)
            if cleaned and key not in seen:
                seen.add(key)
                unique_quoted_segments.append(cleaned)
        return unique_quoted_segments

    # Add the whole line as a fallback for system notices that are not wrapped
    # in quotation marks by the source converter.
    normalized = normalize_text(original)
    if contains_any_keyword(normalized, VOICE_KEYWORDS):
        segments.append(original)

    # Some lines contain multiple system sentences after one another.
    # Keep the full line, but also add sentence chunks for better line-level output.
    sentence_chunks = re.split(r"(?<=[.!?])\s+", clean_display_text(original))
    if len(sentence_chunks) > 1:
        buffer: list[str] = []
        for chunk in sentence_chunks:
            n = normalize_text(chunk)
            if contains_any_keyword(n, VOICE_KEYWORDS):
                buffer.append(chunk.strip())

        if buffer:
            segments.append(" ".join(buffer))

    # De-duplicate while preserving order.
    seen = set()
    unique_segments = []
    for segment in segments:
        cleaned = clean_display_text(segment)
        key = normalize_text(cleaned)
        if cleaned and key not in seen:
            seen.add(key)
            unique_segments.append(cleaned)

    return unique_segments


def contains_any_keyword(normalized_text: str, keywords: Iterable[str]) -> bool:
    """Find keywords in the normalized text."""
    logger.trace("Entering contains_any_keyword")
    return any(keyword in normalized_text for keyword in keywords)


def keyword_score(normalized_text: str) -> float:
    """Rule score from 0 to 1 based on Voice-like terms."""
    logger.trace("Entering keyword_score")
    score = 0.0

    for marker in STRONG_MARKERS:
        if marker in normalized_text:
            score += 0.10

    # Strong structural combos are much more reliable than isolated keywords:
    # narration can mention "killed", but system notices combine kill/eat verbs
    # with beast souls, geno points, or evolution status.
    if "killed" in normalized_text and "beast soul" in normalized_text:
        score += 0.25
    if "hunted" in normalized_text and "beast soul" in normalized_text:
        score += 0.25
    if ("eaten" in normalized_text or "consumed" in normalized_text) and "geno point" in normalized_text:
        score += 0.25
    if "life essence" in normalized_text and "geno point" in normalized_text:
        score += 0.20
    if "obtained" in normalized_text and "beast soul" in normalized_text:
        score += 0.20
    if "evolution successful" in normalized_text:
        score += 0.35
    if "gene" in normalized_text and "+1" in normalized_text:
        score += 0.20

    # System messages are usually compact; very long matches tend to be normal
    # prose that merely contains a few Voice-like terms.
    word_count = len(normalized_text.split())
    if 3 <= word_count <= 45:
        score += 0.10
    elif word_count > 80:
        score -= 0.20

    # Penalize normal dialogue/narration indicators without discarding the row,
    # so reviewers can still see borderline cases in the review bucket.
    padded = f" {normalized_text} "
    if any(marker in padded for marker in DIALOGUE_MARKERS):
        score -= 0.20

    return max(0.0, min(1.0, score))


def categorize(normalized_text: str) -> str:
    """Categorize a normalized Voice of the World candidate line."""
    logger.trace("Entering categorize")
    matched = []
    for category, terms in CATEGORY_RULES:
        if any(term in normalized_text for term in terms):
            matched.append(category)

    if not matched:
        return "unknown_voice"

    # Prefer more specific categories first when several rule groups match the
    # same short system notice.
    priority = [
        "evolution_status",
        "life_essence",
        "xenogeneic_gene",
        "beast_soul_result",
        "hunted_announcement",
        "kill_announcement",
        "geno_point_gain",
        "gene_lock",
        "eaten_or_consumed",
        "system_notice",
    ]

    for category in priority:
        if category in matched:
            return category

    return matched[0]


def load_seed_lines(seed_path: Path) -> list[str]:
    """Load and clean example Voice lines."""
    logger.trace("Entering load_seed_lines")
    raw = seed_path.read_text(encoding="utf-8", errors="replace")
    seeds: list[str] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        # Extract quoted examples if present.
        extracted = split_possible_voice_segments(line)
        if extracted:
            seeds.extend(extracted)
        else:
            cleaned = clean_display_text(line)
            if cleaned:
                seeds.append(cleaned)

    # De-duplicate.
    deduped = []
    seen = set()
    for seed in seeds:
        key = normalize_text(seed)
        if key and key not in seen:
            seen.add(key)
            deduped.append(seed)

    return deduped


def iter_markdown_files(chapter_dir: Path) -> list[Path]:
    """Return Markdown chapter files below a directory in stable order."""
    logger.trace("Entering iter_markdown_files")
    return sorted(chapter_dir.rglob("*.md"))


def extract_candidates_from_file(path: Path) -> list[Candidate]:
    """Extract Voice of the World candidate lines from one Markdown file."""
    logger.trace("Entering extract_candidates_from_file")
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    chapter_index, title = extract_frontmatter(lines)

    candidates: list[Candidate] = []

    for idx, line in enumerate(lines, start=1):
        segments = split_possible_voice_segments(line)
        if not segments:
            continue

        before = lines[idx - 2].strip() if idx >= 2 else ""
        after = lines[idx].strip() if idx < len(lines) else ""

        for segment in segments:
            normalized = normalize_text(segment)
            kscore = keyword_score(normalized)

            # Keep high-recall candidates:
            # - any keyword score
            # - compact quote-like segments with a strong marker
            if kscore <= 0 and not contains_any_keyword(normalized, VOICE_KEYWORDS):
                continue

            candidates.append(
                Candidate(
                    chapter_file=str(path),
                    chapter_index=chapter_index,
                    title=title,
                    line_number=idx,
                    raw_text=segment,
                    normalized_text=normalized,
                    context_before=clean_display_text(before),
                    context_after=clean_display_text(after),
                    keyword_score=kscore,
                    category=categorize(normalized),
                )
            )

    return candidates


def score_candidates(
    seeds: list[str],
    candidates: list[Candidate],
    likely_threshold: float,
    review_threshold: float,
) -> list[Candidate]:
    """Score candidate lines against seed examples and assign decisions."""
    logger.trace("Entering score_candidates")
    if not seeds:
        raise ValueError("No seed examples found.")

    if not candidates:
        return []

    normalized_seeds = [normalize_text(seed) for seed in seeds]
    normalized_candidates = [candidate.normalized_text for candidate in candidates]

    corpus = normalized_seeds + normalized_candidates

    # Word n-grams work well for formulaic notices while still tolerating
    # minor wording differences between translations.
    vectorizer = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 4),
        min_df=1,
        lowercase=False,
        sublinear_tf=True,
    )

    matrix = vectorizer.fit_transform(corpus)
    # Newer scikit-learn rejects np.matrix from todense(); toarray() keeps the
    # same slicing behavior while returning a supported ndarray.
    matrix_dense = matrix.toarray()
    seed_matrix = matrix_dense[: len(normalized_seeds), :]
    candidate_matrix = matrix_dense[len(normalized_seeds) :, :]

    similarities = cosine_similarity(candidate_matrix, seed_matrix)

    for i, candidate in enumerate(candidates):
        row = similarities[i]
        best_idx = int(row.argmax())
        tfidf_sim = float(row[best_idx])
        matched_seed = seeds[best_idx]

        fuzzy_sim = fuzz.token_set_ratio(candidate.normalized_text, normalize_text(matched_seed)) / 100.0

        # TF-IDF is strongest for formulaic lines; keyword score rescues short
        # system messages; fuzzy score helps with punctuation/casing/word-order
        # variants. The weights keep exact-ish seed matches dominant.
        final = (0.58 * tfidf_sim) + (0.30 * candidate.keyword_score) + (0.12 * fuzzy_sim)

        candidate.tfidf_similarity = round(tfidf_sim, 4)
        candidate.fuzzy_similarity = round(fuzzy_sim, 4)
        candidate.final_score = round(min(1.0, final), 4)
        candidate.matched_seed = matched_seed

        if candidate.final_score >= likely_threshold:
            candidate.decision = "likely"
        elif candidate.final_score >= review_threshold:
            candidate.decision = "review"
        else:
            candidate.decision = "reject"

    return sorted(candidates, key=lambda c: c.final_score, reverse=True)


def write_outputs(scored: list[Candidate], out_dir: Path) -> None:
    """Write outputs output."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # Keep the same rows in CSV, JSONL, Markdown, and optional Excel outputs so
    # downstream review tooling can choose whichever format is easiest.
    all_rows = [asdict(c) for c in scored]
    likely_rows = [asdict(c) for c in scored if c.decision == "likely"]
    review_rows = [asdict(c) for c in scored if c.decision == "review"]

    def write_csv(path: Path, rows: list[dict]) -> None:
        """Write csv output."""
        logger.trace("Entering write_csv")
        if not rows:
            path.write_text("", encoding="utf-8")
            return

        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def write_jsonl(path: Path, rows: list[dict]) -> None:
        """Write jsonl output."""
        logger.trace("Entering write_jsonl")
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_csv(out_dir / "all_candidates.csv", all_rows)
    write_csv(out_dir / "likely_voice_lines.csv", likely_rows)
    write_csv(out_dir / "review_needed.csv", review_rows)

    write_jsonl(out_dir / "all_candidates.jsonl", all_rows)
    write_jsonl(out_dir / "likely_voice_lines.jsonl", likely_rows)
    write_jsonl(out_dir / "review_needed.jsonl", review_rows)

    # Also write a compact markdown report.
    report = [
        "# Voice of the World Search Report",
        "",
        f"- Total candidates: {len(scored)}",
        f"- Likely matches: {len(likely_rows)}",
        f"- Review-needed matches: {len(review_rows)}",
        "",
        "## Top 50 matches",
        "",
    ]

    for c in scored[:50]:
        report.append(
            f"### {c.final_score:.3f} — {Path(c.chapter_file).name}:{c.line_number}"
        )
        report.append("")
        report.append(f"- Decision: `{c.decision}`")
        report.append(f"- Category: `{c.category}`")
        report.append(f"- TF-IDF: `{c.tfidf_similarity}`")
        report.append(f"- Keyword score: `{c.keyword_score}`")
        report.append("")
        report.append(f"> {c.raw_text}")
        report.append("")
        report.append("Closest seed:")
        report.append("")
        report.append(f"> {c.matched_seed}")
        report.append("")

    (out_dir / "report.md").write_text("\n".join(report), encoding="utf-8")

    # Pandas is not necessary, but this creates a convenient Excel-friendly file
    # if the environment supports it.
    try:
        pd.DataFrame(all_rows).to_excel(out_dir / "all_candidates.xlsx", index=False)
        pd.DataFrame(likely_rows).to_excel(out_dir / "likely_voice_lines.xlsx", index=False)
        pd.DataFrame(review_rows).to_excel(out_dir / "review_needed.xlsx", index=False)
    except Exception as exc:
        logger.warning(f"Could not write Excel files: {exc}")


def run_voice_line_search(
    chapters_dir: Path,
    seed_path: Path,
    out_dir: Path,
    likely_threshold: float = 0.65,
    review_threshold: float = 0.45,
) -> VoiceLineSearchSummary:
    """Search Markdown chapters for lines similar to known Voice examples.

    Args:
        chapters_dir: Directory containing chapter Markdown files.
        seed_path: File containing known Voice of the World seed lines.
        out_dir: Directory where reports should be written.
        likely_threshold: Score threshold for likely matches.
        review_threshold: Score threshold for review-needed matches.

    Returns:
        Summary counts for extracted and scored candidates.

    Raises:
        ValueError: If no seed examples are available.
    """
    logger.trace("Entering run_voice_line_search")

    seeds = load_seed_lines(seed_path)
    all_candidates: list[Candidate] = []
    for chapter_path in iter_markdown_files(chapters_dir):
        all_candidates.extend(extract_candidates_from_file(chapter_path))

    scored = score_candidates(
        seeds=seeds,
        candidates=all_candidates,
        likely_threshold=likely_threshold,
        review_threshold=review_threshold,
    )
    write_outputs(scored, out_dir)
    return VoiceLineSearchSummary(
        total_candidates=len(scored),
        likely_count=sum(1 for candidate in scored if candidate.decision == "likely"),
        review_count=sum(1 for candidate in scored if candidate.decision == "review"),
    )


def parse_args() -> argparse.Namespace:
    """Parse args values."""
    logger.trace("Entering parse_args")
    parser = argparse.ArgumentParser(
        description="Find Voice of the World style announcement lines in markdown chapters."
    )

    parser.add_argument(
        "--chapters",
        type=Path,
        required=True,
        help="Directory containing chapter .md files.",
    )
    parser.add_argument(
        "--seeds",
        type=Path,
        required=True,
        help="Path to voice_of_the_world.txt.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output"),
        help="Output directory.",
    )
    parser.add_argument(
        "--likely-threshold",
        type=float,
        default=0.65,
        help="Final score threshold for likely matches.",
    )
    parser.add_argument(
        "--review-threshold",
        type=float,
        default=0.45,
        help="Final score threshold for review bucket.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("logs/trace.log"),
        help="Log file path.",
    )

    return parser.parse_args()


def main() -> int:
    """Run the command-line entrypoint."""
    args = parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(args.log, rotation="1 MB", retention=5, level="INFO")
    logger.add(sys.stderr, level="WARNING")

    if not args.chapters.exists():
        console.print(f"[red]Chapter directory not found:[/red] {args.chapters}")
        return 1

    if not args.seeds.exists():
        console.print(f"[red]Seed file not found:[/red] {args.seeds}")
        return 1

    seeds = load_seed_lines(args.seeds)
    chapter_files = iter_markdown_files(args.chapters)

    logger.info(f"Loaded {len(seeds)} seed lines from {args.seeds}")
    logger.info(f"Found {len(chapter_files)} markdown files in {args.chapters}")

    console.print(f"Loaded [bold]{len(seeds)}[/bold] seed Voice lines.")
    console.print(f"Found [bold]{len(chapter_files)}[/bold] markdown chapter files.")

    all_candidates: list[Candidate] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Extracting candidates", total=len(chapter_files))

        for path in chapter_files:
            try:
                candidates = extract_candidates_from_file(path)
                all_candidates.extend(candidates)
                logger.info(f"{path}: {len(candidates)} candidates")
            except Exception as exc:
                logger.exception(f"Failed to process {path}: {exc}")

            progress.advance(task)

    console.print(f"Extracted [bold]{len(all_candidates)}[/bold] candidate lines.")

    if not all_candidates:
        console.print("[yellow]No candidates found. Try lowering filtering rules or checking input files.[/yellow]")
        return 0

    console.print("Scoring candidates...")

    scored = score_candidates(
        seeds=seeds,
        candidates=all_candidates,
        likely_threshold=args.likely_threshold,
        review_threshold=args.review_threshold,
    )

    write_outputs(scored, args.out)

    likely_count = sum(1 for c in scored if c.decision == "likely")
    review_count = sum(1 for c in scored if c.decision == "review")

    console.print("")
    console.print("[bold]Done.[/bold]")
    console.print(f"Likely matches: [bold]{likely_count}[/bold]")
    console.print(f"Review needed: [bold]{review_count}[/bold]")
    console.print(f"Output directory: [bold]{args.out}[/bold]")
    console.print("")
    console.print("Useful files:")
    console.print(f"- {args.out / 'likely_voice_lines.csv'}")
    console.print(f"- {args.out / 'review_needed.csv'}")
    console.print(f"- {args.out / 'report.md'}")
    console.print(f"- {args.out / 'all_candidates.xlsx'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
