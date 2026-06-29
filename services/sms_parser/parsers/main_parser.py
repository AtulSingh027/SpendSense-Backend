"""
All bank-specific SMS parsers in one file (V1).

Each parser inherits BaseParser and implements:
  - sender_patterns  (list of sender-ID substrings that route to this parser)
  - parse(text)      (returns ParsedTransaction or None)

Some parsers override can_parse() for body-signature matching (e.g. BOB).
"""

import re
from typing import Optional

from services.sms_parser.base import BaseParser, ParsedTransaction


# ── HDFC ──────────────────────────────────────────────────────────────

class HDFCParser(BaseParser):
    sender_patterns = ["HDFCBK"]

    AMOUNT_RE = re.compile(r"Rs\.?\s?([\d,]+\.?\d*)\s?(debited|credited)", re.I)
    VPA_RE = re.compile(r"(?:to|from)\s+VPA\s+([\w.\-@]+)", re.I)
    REF_RE = re.compile(r"Ref\.?\s?(?:No\.?)?\s?(\d{6,})", re.I)

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        m = self.AMOUNT_RE.search(text)
        if not m:
            return None
        amount = float(m.group(1).replace(",", ""))
        txn_type = "debit" if m.group(2).lower() == "debited" else "credit"
        vpa = self.VPA_RE.search(text)
        ref = self.REF_RE.search(text)
        return ParsedTransaction(
            amount=amount,
            txn_type=txn_type,
            merchant_raw=vpa.group(1) if vpa else "Unknown",
            bank_ref_id=ref.group(1) if ref else None,
            upi_app=self._guess_upi_app(text),
        )


# ── ICICI ─────────────────────────────────────────────────────────────

class ICICIParser(BaseParser):
    sender_patterns = ["ICICIB", "ICICIT"]

    AMOUNT_RE = re.compile(r"INR\s?([\d,]+\.?\d*)\s?(debited|credited|credit|debit)", re.I)
    VPA_RE = re.compile(r"(?:to|from|VPA)\s*[:\-]?\s*([\w.\-@]+)", re.I)
    REF_RE = re.compile(r"(?:Ref|RRN)\.?\s?(?:No\.?)?\s?[:\-]?\s?(\d{6,})", re.I)

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        m = self.AMOUNT_RE.search(text)
        if not m:
            return None
        amount = float(m.group(1).replace(",", ""))
        txn_type = "debit" if m.group(2).lower().startswith("debit") else "credit"
        vpa = self.VPA_RE.search(text)
        ref = self.REF_RE.search(text)
        return ParsedTransaction(
            amount=amount,
            txn_type=txn_type,
            merchant_raw=vpa.group(1) if vpa else "Unknown",
            bank_ref_id=ref.group(1) if ref else None,
            upi_app=self._guess_upi_app(text),
        )


# ── SBI ───────────────────────────────────────────────────────────────

class SBIParser(BaseParser):
    sender_patterns = ["SBIUPI", "SBIINB", "ATMSBI"]

    AMOUNT_RE = re.compile(r"Rs\.?([\d,]+\.?\d*)\s?(debited|credited)", re.I)
    VPA_RE = re.compile(r"(?:trf to|by)\s+([\w.\-@\s]+?)(?:\sRef|\son|$)", re.I)
    REF_RE = re.compile(r"Ref\s?(?:No)?\s?[:\-]?\s?(\d{6,})", re.I)

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        m = self.AMOUNT_RE.search(text)
        if not m:
            return None
        amount = float(m.group(1).replace(",", ""))
        txn_type = "debit" if m.group(2).lower() == "debited" else "credit"
        vpa = self.VPA_RE.search(text)
        ref = self.REF_RE.search(text)
        return ParsedTransaction(
            amount=amount,
            txn_type=txn_type,
            merchant_raw=vpa.group(1).strip() if vpa else "Unknown",
            bank_ref_id=ref.group(1) if ref else None,
            upi_app=self._guess_upi_app(text),
        )


# ── Bank of Baroda ────────────────────────────────────────────────────

class BOBParser(BaseParser):
    """Bank of Baroda — has TWO distinct SMS templates:
    1) Debit:  'Rs.X Dr. from A/C ... and Cr. to <vpa>. Ref:<ref>. AvlBal:...'
    2) Credit: 'Your account is credited with INR X ... by UPI Ref No <ref>; AvlBal:...'
    Real sender ID unknown until tested on-device — matching on body signature too."""

    sender_patterns = ["BOB", "BOIBNK", "BOIIND"]

    DEBIT_RE = re.compile(r"Rs\.?\s?([\d,]+\.?\d*)\s?Dr", re.I)
    DEBIT_MERCHANT_RE = re.compile(r"Cr\.?\s*to\s+(\S+?)\.?\s+Ref", re.I)
    DEBIT_REF_RE = re.compile(r"Ref:?\s?(\d{6,})", re.I)

    CREDIT_RE = re.compile(r"credited with INR\s?([\d,]+\.?\d*)", re.I)
    CREDIT_REF_RE = re.compile(r"UPI Ref No\s?(\d{6,})", re.I)

    def can_parse(self, sender_id: str, text: str) -> bool:
        return (
            any(p in sender_id.upper() for p in self.sender_patterns)
            or "-BOB" in text.upper()
            or "BOB UPI USER" in text.upper()
        )

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        # Try debit template first
        debit_amt = self.DEBIT_RE.search(text)
        if debit_amt:
            merchant = self.DEBIT_MERCHANT_RE.search(text)
            ref = self.DEBIT_REF_RE.search(text)
            return ParsedTransaction(
                amount=float(debit_amt.group(1).replace(",", "")),
                txn_type="debit",
                merchant_raw=merchant.group(1).rstrip(".") if merchant else "Unknown",
                bank_ref_id=ref.group(1) if ref else None,
                upi_app=self._guess_upi_app(text),
            )

        # Try credit template
        credit_amt = self.CREDIT_RE.search(text)
        if credit_amt:
            ref = self.CREDIT_REF_RE.search(text)
            return ParsedTransaction(
                amount=float(credit_amt.group(1).replace(",", "")),
                txn_type="credit",
                merchant_raw="Unknown",     # this template never names the sender
                bank_ref_id=ref.group(1) if ref else None,
                upi_app="unknown",          # no VPA in this template at all
            )

        return None


# ── Axis Bank ─────────────────────────────────────────────────────────

class AxisParser(BaseParser):
    """Axis Bank — NEVER includes a VPA/handle. Only gives a P2M/P2A reference
    and a merchant/person name (often truncated by the bank to ~20 chars —
    that truncation is consistent per merchant, so it's still a stable key
    for categorization even though it's not the full name)."""

    sender_patterns = ["AXISBK", "AXIS"]

    AMOUNT_RE = re.compile(r"INR\s?([\d,]+\.?\d*)\s?(debited|credited)", re.I)
    REF_MERCHANT_RE = re.compile(r"UPI/(P2M|P2A)/(\d+)/(.+)", re.I)

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        amt = self.AMOUNT_RE.search(text)
        if not amt:
            return None
        amount = float(amt.group(1).replace(",", ""))
        txn_type = "debit" if amt.group(2).lower() == "debited" else "credit"

        merchant_raw = "Unknown"
        ref = None
        ref_match = self.REF_MERCHANT_RE.search(text)
        if ref_match:
            ref = ref_match.group(2)
            merchant_raw = ref_match.group(3).strip()

        return ParsedTransaction(
            amount=amount,
            txn_type=txn_type,
            merchant_raw=merchant_raw,
            bank_ref_id=ref,
            upi_app="unknown",  # structurally absent from this SMS template
        )


# ── Generic Fallback ──────────────────────────────────────────────────

class GenericParser(BaseParser):
    """Fallback for unrecognized senders — loose keyword matching.
    Handles two common styles:
      1) "...debited..."/"...credited..." (HDFC/ICICI/SBI-ish)
      2) "...Dr. from.../Cr. to..."       (BOB, Canara, Union Bank-ish)
    """

    AMOUNT_RE = re.compile(r"(?:Rs\.?|INR)\s?([\d,]+\.?\d*)", re.I)
    TYPE_WORD_RE = re.compile(r"(debited|credited|debit|credit)", re.I)
    TYPE_ABBR_RE = re.compile(r"\b(Dr|Cr)\.?\b", re.I)
    REF_RE = re.compile(r"(?:Ref|RRN|Txn)\.?\s?(?:No\.?|ID)?\s?[:\-]?\s?(\d{6,})", re.I)
    MERCHANT_RE = re.compile(r"(?:Cr\.?\s?to|to\s+VPA|to)\s+([\w.\-]+@[\w.\-]+)", re.I)

    def can_parse(self, sender_id: str, text: str) -> bool:
        return True  # always tried last, as fallback

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        amt = self.AMOUNT_RE.search(text)
        if not amt:
            return None
        amount = float(amt.group(1).replace(",", ""))

        txn_type = None
        word_match = self.TYPE_WORD_RE.search(text)
        if word_match:
            txn_type = "debit" if word_match.group(1).lower().startswith("debit") else "credit"
        else:
            abbr_match = self.TYPE_ABBR_RE.search(text)
            if abbr_match:
                txn_type = "debit" if abbr_match.group(1).lower() == "dr" else "credit"

        if not txn_type:
            return None

        ref = self.REF_RE.search(text)
        merchant = self.MERCHANT_RE.search(text)

        return ParsedTransaction(
            amount=amount,
            txn_type=txn_type,
            merchant_raw=merchant.group(1) if merchant else "Unknown",
            bank_ref_id=ref.group(1) if ref else None,
            upi_app=self._guess_upi_app(text),
        )