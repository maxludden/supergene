from dotenv import load_dotenv

from supergene.converter import (
    BookMetadata,
    ChapterResult,
    ConversionResult,
    ConversionWarning,
    convert_epub,
)
from supergene.supabase_store import (
    SupabaseStorageConfig,
    SupabaseStoreResult,
    store_conversion_in_supabase,
)

load_dotenv()

__all__ = [
    "BookMetadata",
    "ChapterResult",
    "ConversionResult",
    "ConversionWarning",
    "SupabaseStorageConfig",
    "SupabaseStoreResult",
    "convert_epub",
    "store_conversion_in_supabase",
]
