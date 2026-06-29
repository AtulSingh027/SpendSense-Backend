"""
Base types for the SMS parser layer.

This file defines ParsedTransaction (the output of every parser) and
BaseParser (the abstract base every bank-specific parser inherits from).

IMPORTANT: This file must NOT import from .parsers — parsers import from here.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List


# ---------------------------------------------------------------------------
# Parser output
# ---------------------------------------------------------------------------

@dataclass
class ParsedTransaction:
    amount: float
    txn_type: str                # "debit" | "credit"
    merchant_raw: str
    bank_ref_id: Optional[str]
    upi_app: str


# ---------------------------------------------------------------------------
# Abstract base parser — strategy pattern
# ---------------------------------------------------------------------------

class BaseParser(ABC):
    sender_patterns: List[str] = []

    def can_parse(self, sender_id: str, text: str) -> bool:
        """Default check: does the sender match any of our known patterns?"""
        return any(p in sender_id.upper() for p in self.sender_patterns)

    @abstractmethod
    def parse(self, text: str) -> Optional[ParsedTransaction]:
        ...

    # -------------------------------------------------------------------
    # UPI app guessing (shared by all parsers)
    # -------------------------------------------------------------------
    # Best-effort MERCHANT'S collection platform — NOT "which app you used".
    # VPA handle reflects the payee's PSP, not the payer's front-end app.
    # Sourced from publicly reported handle→PSP mappings; treat as a hint,
    # not ground truth.
    HANDLE_PLATFORM_MAP = {
        "ybl": "phonepe",  "ibl": "phonepe",  "axl": "phonepe",
        "okaxis": "googlepay", "okicici": "googlepay", "okhdfc": "googlepay",
        "okhdfcbank": "googlepay", "oksbi": "googlepay",
        "paytm": "paytm", "pty": "paytm", "ptys": "paytm", "ptaxis": "paytm",
    }

    @classmethod
    def _guess_upi_app(cls, text: str) -> str:
        t = text.lower()
        # Explicit app name mentioned in the SMS body (rare, but check first)
        if "phonepe" in t:
            return "phonepe"
        if "gpay" in t or "googlepay" in t:
            return "googlepay"
        if "paytm" in t:
            return "paytm"
        # Fall back to VPA handle suffix, e.g. "...@ybl" → phonepe
        handle_match = re.search(r"@([\w]+)", t)
        if handle_match:
            handle = handle_match.group(1)
            if handle in cls.HANDLE_PLATFORM_MAP:
                return cls.HANDLE_PLATFORM_MAP[handle]
        return "unknown"