"""
SMS Parser Tests — real Bank of Baroda & Axis Bank SMS samples.

Run:
    pytest tests/test_sms_parser.py -v

Each test passes a raw SMS string (as received on-device) into parse_sms()
and asserts the parsed output: amount, txn_type, merchant, ref, upi_app.
"""

import pytest

from services.sms_parser.register import parse_sms


# ═══════════════════════════════════════════════════════════════════════
#  BOB — DEBIT  (template: "Rs.X Dr. from A/C ... Cr. to <vpa>. Ref:...")
# ═══════════════════════════════════════════════════════════════════════

BOB_DEBIT_SAMPLES = [
    pytest.param(
        "Rs.15.00 Dr. from A/C XXXXXX3224 and Cr. to bharatpe.9x0t0y0u8m319452@unitype. Ref:616887660365. AvlBal:Rs490.46(2026:06:17 01:27:30). Not you? Call 18005700/5000-BOB",
        15.0, "debit", "bharatpe.9x0t0y0u8m319452@unitype", "616887660365", "unknown",
        id="bob_debit_bharatpe_unitype",
    ),
    pytest.param(
        "Rs.20.00 Dr. from A/C XXXXXX3224 and Cr. to paytmqr6jh87z@ptys. Ref:616661998204. AvlBal:Rs485.46(2026:06:15 10:10:12). Not you? Call 18005700/5000-BOB",
        20.0, "debit", "paytmqr6jh87z@ptys", "616661998204", "paytm",
        id="bob_debit_paytmqr_ptys",
    ),
    pytest.param(
        "Rs.50.00 Dr. from A/C XXXXXX3224 and Cr. to 8959167609@ptaxis. Ref:616508366031. AvlBal:Rs595.46(2026:06:14 05:29:54). Not you? Call 18005700/5000-BOB",
        50.0, "debit", "8959167609@ptaxis", "616508366031", "paytm",
        id="bob_debit_ptaxis",
    ),
    pytest.param(
        "Rs.15.00 Dr. from A/C XXXXXX3224 and Cr. to bharatpe.9p0v0h7e4b566676@fbpe. Ref:616240855299. AvlBal:Rs1411.46(2026:06:11 10:14:47). Not you? Call 18005700/5000-BOB",
        15.0, "debit", "bharatpe.9p0v0h7e4b566676@fbpe", "616240855299", "unknown",
        id="bob_debit_bharatpe_fbpe",
    ),
    pytest.param(
        "Rs.90.00 Dr. from A/C XXXXXX3224 and Cr. to Q588336214@ybl. Ref:738714693829. AvlBal:Rs1426.46(2026:06:10 08:44:11). Not you? Call 18005700/5000-BOB",
        90.0, "debit", "Q588336214@ybl", "738714693829", "phonepe",
        id="bob_debit_ybl_phonepe",
    ),
    pytest.param(
        "Rs.30.00 Dr. from A/C XXXXXX3224 and Cr. to paytm.s1ojcsu@pty. Ref:615838590609. AvlBal:Rs1889.46(2026:06:07 10:51:38). Not you? Call 18005700/5000-BOB",
        30.0, "debit", "paytm.s1ojcsu@pty", "615838590609", "paytm",
        id="bob_debit_paytm_pty",
    ),
    pytest.param(
        "Rs.200.00 Dr. from A/C XXXXXX3224 and Cr. to kppatidar696-1@okicici. Ref:652458499824. AvlBal:Rs1939.46(2026:06:07 07:36:56). Not you? Call 18005700/5000-BOB",
        200.0, "debit", "kppatidar696-1@okicici", "652458499824", "googlepay",
        id="bob_debit_okicici_googlepay",
    ),
    pytest.param(
        "Rs.120.00 Dr. from A/C XXXXXX3224 and Cr. to paytmqr18kjmvfv9c@paytm. Ref:615808497231. AvlBal:Rs2139.46(2026:06:07 04:49:17). Not you? Call 18005700/5000-BOB",
        120.0, "debit", "paytmqr18kjmvfv9c@paytm", "615808497231", "paytm",
        id="bob_debit_paytm_handle",
    ),
    pytest.param(
        "Rs.4000.00 Dr. from A/C XXXXXX3224 and Cr. to 8839993698@ybl. Ref:613885514386. AvlBal:Rs40.69(2026:05:18 02:23:54). Not you? Call 18005700/5000-BOB",
        4000.0, "debit", "8839993698@ybl", "613885514386", "phonepe",
        id="bob_debit_large_ybl",
    ),
    pytest.param(
        "Rs.530.00 Dr. from A/C XXXXXX3224 and Cr. to paytmqr6yjtrg@ptys. Ref:613178707129. AvlBal:Rs156.69(2026:05:11 09:18:53). Not you? Call 18005700/5000-BOB",
        530.0, "debit", "paytmqr6yjtrg@ptys", "613178707129", "paytm",
        id="bob_debit_530_ptys",
    ),
]


@pytest.mark.parametrize(
    "sms, exp_amount, exp_type, exp_merchant, exp_ref, exp_app",
    BOB_DEBIT_SAMPLES,
)
def test_bob_debit(sms, exp_amount, exp_type, exp_merchant, exp_ref, exp_app):
    result, parser_name = parse_sms("BOB", sms)

    assert result is not None, f"Parser returned None for BOB debit SMS"
    assert parser_name == "BOBParser"
    assert result.amount == exp_amount
    assert result.txn_type == exp_type
    assert result.merchant_raw == exp_merchant
    assert result.bank_ref_id == exp_ref
    assert result.upi_app == exp_app


# ═══════════════════════════════════════════════════════════════════════
#  BOB — CREDIT  (template: "...credited with INR X ... UPI Ref No ...")
# ═══════════════════════════════════════════════════════════════════════

BOB_CREDIT_SAMPLES = [
    pytest.param(
        "Dear BOB UPI User: Your account is credited with INR 40.00 on 2026-06-19 06:53:59 PM by UPI Ref No 570617317389; AvlBal: Rs222.46 - BOB",
        40.0, "credit", "Unknown", "570617317389", "unknown",
        id="bob_credit_40",
    ),
    pytest.param(
        "Dear BOB UPI User: Your account is credited with INR 20.00 on 2026-06-15 07:49:33 PM by UPI Ref No 400506797936; AvlBal: Rs505.46 - BOB",
        20.0, "credit", "Unknown", "400506797936", "unknown",
        id="bob_credit_20",
    ),
]


@pytest.mark.parametrize(
    "sms, exp_amount, exp_type, exp_merchant, exp_ref, exp_app",
    BOB_CREDIT_SAMPLES,
)
def test_bob_credit(sms, exp_amount, exp_type, exp_merchant, exp_ref, exp_app):
    result, parser_name = parse_sms("BOB", sms)

    assert result is not None, f"Parser returned None for BOB credit SMS"
    assert parser_name == "BOBParser"
    assert result.amount == exp_amount
    assert result.txn_type == exp_type
    assert result.merchant_raw == exp_merchant
    assert result.bank_ref_id == exp_ref
    assert result.upi_app == exp_app


# ═══════════════════════════════════════════════════════════════════════
#  AXIS — DEBIT  (template: "INR X debited\n...\nUPI/P2M|P2A/ref/merchant")
#  Axis SMS are multi-line on-device; newlines preserved.
# ═══════════════════════════════════════════════════════════════════════

AXIS_DEBIT_SAMPLES = [
    pytest.param(
        "INR 10.00 debited\nA/c no. XX9454\n26-06-26, 08:48:21\nUPI/P2M/654325545108/MAA UMIYA GENERAL S\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        10.0, "debit", "MAA UMIYA GENERAL S", "654325545108",
        id="axis_maa_umiya_10",
    ),
    pytest.param(
        "INR 45.39 debited\nA/c no. XX9454\n24-06-26, 10:37:31\nUPI/P2M/654108579657/UBER INDIA SYSTEMS\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        45.39, "debit", "UBER INDIA SYSTEMS", "654108579657",
        id="axis_uber",
    ),
    pytest.param(
        "INR 2700.00 debited\nA/c no. XX9454\n16-06-26, 17:08:04\nUPI/P2A/616738273131/PIYUSH WAGH\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        2700.0, "debit", "PIYUSH WAGH", "616738273131",
        id="axis_p2a_person_transfer",
    ),
    pytest.param(
        "INR 10.00 debited\nA/c no. XX9454\n06-06-26, 18:23:10\nUPI/P2M/652316208539/GAURAV\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        10.0, "debit", "GAURAV", "652316208539",
        id="axis_gaurav",
    ),
    pytest.param(
        "INR 15.00 debited\nA/c no. XX9454\n03-06-26, 10:16:03\nUPI/P2M/652012478371/BABLU PATIDAR S O P\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        15.0, "debit", "BABLU PATIDAR S O P", "652012478371",
        id="axis_bablu_truncated",
    ),
    pytest.param(
        "INR 100.00 debited\nA/c no. XX9454\n01-06-26, 19:49:05\nUPI/P2M/615292361803/Jasraj Services\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        100.0, "debit", "Jasraj Services", "615292361803",
        id="axis_jasraj",
    ),
    pytest.param(
        "INR 220.00 debited\nA/c no. XX9454\n30-05-26, 20:51:00\nUPI/P2M/651668005949/RAMESH MASALA DOSA\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        220.0, "debit", "RAMESH MASALA DOSA", "651668005949",
        id="axis_ramesh_masala",
    ),
    pytest.param(
        "INR 10.00 debited\nA/c no. XX9454\n22-05-26, 17:09:31\nUPI/P2M/650857747811/PRADEEP KIRANA STOR\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        10.0, "debit", "PRADEEP KIRANA STOR", "650857747811",
        id="axis_pradeep_kirana",
    ),
    pytest.param(
        "INR 5.00 debited\nA/c no. XX9454\n21-05-26, 20:46:03\nUPI/P2A/614130790278/Mukesh Shrivastava\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        5.0, "debit", "Mukesh Shrivastava", "614130790278",
        id="axis_p2a_mukesh",
    ),
    pytest.param(
        "INR 40.00 debited\nA/c no. XX9454\n19-05-26, 22:09:32\nUPI/P2M/650541625464/MAHENDRA SINGH\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank",
        40.0, "debit", "MAHENDRA SINGH", "650541625464",
        id="axis_mahendra",
    ),
]


@pytest.mark.parametrize(
    "sms, exp_amount, exp_type, exp_merchant, exp_ref",
    AXIS_DEBIT_SAMPLES,
)
def test_axis_debit(sms, exp_amount, exp_type, exp_merchant, exp_ref):
    # Axis never has VPA, so upi_app is always "unknown"
    result, parser_name = parse_sms("AXISBK", sms)

    assert result is not None, f"Parser returned None for Axis debit SMS"
    assert parser_name == "AxisParser"
    assert result.amount == exp_amount
    assert result.txn_type == exp_type
    assert result.merchant_raw == exp_merchant
    assert result.bank_ref_id == exp_ref
    assert result.upi_app == "unknown"


# ═══════════════════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

def test_promo_sms_returns_none():
    """Non-financial SMS must be rejected cleanly — not crash, not parse."""
    result, parser_name = parse_sms("PROMO", "Get 50% cashback on your next purchase!")
    assert result is None
    assert parser_name is None


def test_bob_detected_by_body_signature_not_sender():
    """BOBParser matches even if sender_id is unknown — body contains '-BOB'."""
    sms = "Rs.90.00 Dr. from A/C XXXXXX3224 and Cr. to Q588336214@ybl. Ref:738714693829. AvlBal:Rs1426.46(2026:06:10 08:44:11). Not you? Call 18005700/5000-BOB"
    result, parser_name = parse_sms("UNKNOWN-SENDER", sms)

    assert result is not None
    assert parser_name == "BOBParser"
    assert result.amount == 90.0


def test_duplicate_sms_gives_same_ref():
    """Sending the same SMS twice must yield the same bank_ref_id — dedup relies on this."""
    sms = "Rs.200.00 Dr. from A/C XXXXXX3224 and Cr. to kppatidar696-1@okicici. Ref:652458499824. AvlBal:Rs1939.46(2026:06:07 07:36:56). Not you? Call 18005700/5000-BOB"
    r1, _ = parse_sms("BOB", sms)
    r2, _ = parse_sms("BOB", sms)

    assert r1.bank_ref_id == r2.bank_ref_id == "652458499824"
