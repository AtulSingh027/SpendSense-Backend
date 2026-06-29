"""
Parser registry — routes incoming SMS to the right bank parser.

Order matters: specific bank parsers are tried first (each checks sender_id).
GenericParser is the fallback — always matches, always tried last.
"""

from typing import Optional, Tuple

from services.sms_parser.base import ParsedTransaction
from services.sms_parser.parsers.main_parser import (
    AxisParser,
    BOBParser,
    GenericParser,
    HDFCParser,
    ICICIParser,
    SBIParser,
)

# Specific parsers first, generic fallback last.
# These are INSTANCES — can_parse() / parse() are instance methods.
PARSERS = [HDFCParser(), ICICIParser(), SBIParser(), BOBParser(), AxisParser()]
FALLBACK = GenericParser()


def parse_sms(sender_id: str, text: str) -> Tuple[Optional[ParsedTransaction], Optional[str]]:
    """
    Try each bank parser in order; return (ParsedTransaction, parser_name) on
    the first successful parse.  Falls back to GenericParser.
    Returns (None, None) if nothing could parse the SMS.
    """
    for parser in PARSERS:
        if parser.can_parse(sender_id, text):
            result = parser.parse(text)
            if result:
                return result, parser.__class__.__name__

    result = FALLBACK.parse(text)
    return (result, "GenericParser") if result else (None, None)