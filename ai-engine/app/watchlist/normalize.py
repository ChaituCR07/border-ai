import re
from dataclasses import dataclass

from app.anpr.plate_format import PlateFormats, clean_text
from app.watchlist.models import ENTITY_TYPES, PLATE_TYPES, RISK_LEVELS, InvalidEntry

_FORMATS = PlateFormats(["indian", "generic"])
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


@dataclass
class PreparedEntry:
    entity_type: str
    identifier: str
    normalized: str
    name: str
    description: str
    risk_level: str


def normalize_plate(text: str) -> str:
    """The form used everywhere for matching: cleaned, upper-case, OCR look-alikes corrected by position."""
    return _FORMATS.check(text).text


def clean_free_text(value, max_len: int, field: str, required: bool = False) -> str:
    s = _CONTROL.sub(" ", value or "")
    s = " ".join(s.split())
    if required and not s:
        raise InvalidEntry(f"{field} is required")
    if len(s) > max_len:
        raise InvalidEntry(f"{field} is longer than {max_len} characters")
    return s


def prepare_entry(entity_type, identifier, name, risk_level, description="") -> PreparedEntry:
    et = (entity_type or "").upper()
    rl = (risk_level or "").upper()
    if et not in ENTITY_TYPES:
        raise InvalidEntry(f"entity_type must be one of {ENTITY_TYPES}")
    if rl not in RISK_LEVELS:
        raise InvalidEntry(f"risk_level must be one of {RISK_LEVELS}")

    identifier = clean_free_text(identifier, 64, "identifier", required=True)
    name = clean_free_text(name, 200, "name", required=True)
    description = clean_free_text(description, 2000, "description")

    if et in PLATE_TYPES:
        if not 5 <= len(clean_text(identifier)) <= 11:
            raise InvalidEntry("a plate identifier must contain 5 to 11 letters or digits")
        fmt = _FORMATS.check(identifier)
        if fmt.level == "invalid":
            raise InvalidEntry("identifier is not a valid plate")
        normalized = fmt.text
    else:
        normalized = identifier.lower()
    return PreparedEntry(et, identifier, normalized, name, description, rl)


def validate_update_fields(fields: dict) -> dict:
    """Validate the fields an update may change. Unknown fields are rejected."""
    out = {}
    for key, value in fields.items():
        if value is None:
            continue
        if key == "name":
            out[key] = clean_free_text(value, 200, "name", required=True)
        elif key == "description":
            out[key] = clean_free_text(value, 2000, "description")
        elif key == "risk_level":
            rl = str(value).upper()
            if rl not in RISK_LEVELS:
                raise InvalidEntry(f"risk_level must be one of {RISK_LEVELS}")
            out[key] = rl
        else:
            raise InvalidEntry(f"field {key!r} cannot be updated")
    return out
