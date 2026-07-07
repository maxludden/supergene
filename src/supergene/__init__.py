"""Super Gene conversion, review, and reporting tools."""

from dotenv import load_dotenv
from loguru import logger

from supergene.converter import (
    BookMetadata,
    ChapterResult,
    ConversionProgress,
    ConversionResult,
    ConversionWarning,
    convert_epub,
)
from supergene.logging import RichLoggerConfig
from supergene.render_table_candidates import render_table_candidates_html
from supergene.supabase_store import (
    SupabaseStorageConfig,
    SupabaseStoreResult,
    store_conversion_in_supabase,
)
from supergene.table_candidates import (
    TableCandidate,
    find_table_candidates,
    write_table_candidate_report
)
from supergene.title_quality import TitleSpellingIssue, find_missing_terminal_t_title_issues


# Load environment variables from .env file if present,
# so they can be used in CLI workflows and tests. Intended to load:
#   - SUPABASE_URL
#   - SUPABASE_KEY
#   - SUPABASE_BUCKET
#   - OPENAI_API_KEY
load_dotenv()

__all__ = [
    "BookMetadata",
    "ChapterResult",
    "ConversionProgress",
    "ConversionResult",
    "ConversionWarning",
    "RichLoggerConfig",
    "SupabaseStorageConfig",
    "SupabaseStoreResult",
    "TableCandidate",
    "TitleSpellingIssue",
    "convert_epub",
    "find_table_candidates",
    "find_missing_terminal_t_title_issues",
    "render_table_candidates_html",
    "store_conversion_in_supabase",
    "write_table_candidate_report",
]
