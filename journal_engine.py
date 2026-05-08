import re

# ── Account categories ──────────────────────────────────────────────────────
REAL_ACCOUNTS = {
    "cash", "bank", "furniture", "machinery", "equipment", "land", "building",
    "vehicle", "computer", "stock", "inventory", "goods", "gold", "silver",
    "tools", "plant", "premises", "property", "assets", "investments",
}

PERSONAL_ACCOUNTS = {
    "capital", "drawings", "loan", "creditor", "debtor", "supplier",
    "customer", "partner", "owner", "vendor", "payable", "receivable",
    "ram", "shyam", "mohan", "raj", "vijay", "anita", "priya", "sharma",
    "kumar", "gupta", "singh", "bank account",
}

NOMINAL_ACCOUNTS = {
    "salary", "salaries", "rent", "wages", "interest", "commission",
    "discount", "advertisement", "advertising", "repair", "repairs",
    "expense", "expenses", "loss", "profit", "income", "revenue",
    "purchase", "purchases", "sales", "sale", "return", "insurance",
    "depreciation", "bad debt", "charity", "donation", "tax", "fine",
    "penalty", "freight", "carriage", "postage", "stationery", "printing",
    "electricity", "water", "telephone", "travel", "entertainment",
    "maintenance", "subscription",
}

# ── Keyword triggers ─────────────────────────────────────────────────────────
TRANSACTION_PATTERNS = [
    # bought / purchased
    {
        "triggers": ["bought", "purchased", "buy"],
        "debit_hint": "asset_or_purchase",
        "credit_hint": "payment_source",
    },
    # sold
    {
        "triggers": ["sold", "sell"],
        "debit_hint": "payment_source",
        "credit_hint": "asset_or_sales",
    },
    # paid
    {
        "triggers": ["paid", "pay", "payment made"],
        "debit_hint": "expense_or_asset",
        "credit_hint": "payment_source",
    },
    # received
    {
        "triggers": ["received", "receive", "receipt"],
        "debit_hint": "payment_source",
        "credit_hint": "income_or_asset",
    },
    # invested / started business
    {
        "triggers": ["invested", "invest", "started business", "commenced"],
        "debit_hint": "payment_source",
        "credit_hint": "capital",
    },
    # withdrawn / withdrew
    {
        "triggers": ["withdrawn", "withdrew", "withdrawal", "drawings"],
        "debit_hint": "drawings",
        "credit_hint": "payment_source",
    },
    # borrowed / loan taken
    {
        "triggers": ["borrowed", "loan taken", "took loan"],
        "debit_hint": "payment_source",
        "credit_hint": "loan",
    },
    # deposited into bank
    {
        "triggers": ["deposited", "deposit"],
        "debit_hint": "bank",
        "credit_hint": "cash",
    },
    # issued / given
    {
        "triggers": ["issued", "gave", "given"],
        "debit_hint": "expense_or_asset",
        "credit_hint": "payment_source",
    },
]


def extract_amount(text: str) -> float:
    """Extract numeric amount from text."""
    text_clean = text.replace(",", "").replace("₹", "").replace("rs", "").replace("rs.", "")
    numbers = re.findall(r"\d+(?:\.\d+)?", text_clean)
    if numbers:
        return float(max(numbers, key=lambda x: float(x)))
    return 0.0


def extract_accounts(text: str):
    """Extract potential account names from the transaction text."""
    text_lower = text.lower()
    found_accounts = []

    all_accounts = list(REAL_ACCOUNTS) + list(PERSONAL_ACCOUNTS) + list(NOMINAL_ACCOUNTS)
    all_accounts.sort(key=len, reverse=True)  # match longer phrases first

    for acc in all_accounts:
        if acc in text_lower:
            found_accounts.append(acc)

    # Also extract capitalized words that might be personal accounts (names)
    words = re.findall(r"\b[A-Z][a-z]+\b", text)
    skip = {"Bought", "Sold", "Paid", "Received", "Invested", "Withdrew",
            "Deposited", "Borrowed", "Enter", "Generate", "Cash", "Bank"}
    for w in words:
        if w not in skip and w.lower() not in [a for a in found_accounts]:
            found_accounts.append(w.lower())

    return list(dict.fromkeys(found_accounts))  # deduplicate preserving order


def classify_account(name: str) -> str:
    name_lower = name.lower()
    for acc in REAL_ACCOUNTS:
        if acc in name_lower:
            return "real"
    for acc in PERSONAL_ACCOUNTS:
        if acc in name_lower:
            return "personal"
    for acc in NOMINAL_ACCOUNTS:
        if acc in name_lower:
            return "nominal"
    return "unknown"


def title_account(name: str) -> str:
    return " ".join(w.capitalize() for w in name.split())


def detect_payment_source(text_lower: str) -> str:
    if "cheque" in text_lower or "check" in text_lower or "bank" in text_lower:
        return "bank"
    if "credit" in text_lower:
        return "credit"
    return "cash"


def generate_journal_entry(transaction: str) -> dict:
    """Main engine: parse transaction → return journal entry dict."""
    text_lower = transaction.lower().strip()
    amount = extract_amount(transaction)

    if amount == 0:
        return {
            "success": False,
            "error": "Could not detect an amount in the transaction.",
            "transaction": transaction,
        }

    # ── Match transaction pattern ───────────────────────────────────────────
    matched_pattern = None
    matched_trigger = None
    for pattern in TRANSACTION_PATTERNS:
        for trigger in pattern["triggers"]:
            if trigger in text_lower:
                matched_pattern = pattern
                matched_trigger = trigger
                break
        if matched_pattern:
            break

    if not matched_pattern:
        return {
            "success": False,
            "error": "Could not identify transaction type. Try using keywords like bought, sold, paid, received, invested.",
            "transaction": transaction,
        }

    # ── Extract accounts ────────────────────────────────────────────────────
    accounts = extract_accounts(transaction)
    payment_src = detect_payment_source(text_lower)

    # ── Build debit / credit based on pattern hint ──────────────────────────
    hint_d = matched_pattern["debit_hint"]
    hint_c = matched_pattern["credit_hint"]

    def resolve_account(hint, accounts, payment_src, text_lower):
        if hint == "payment_source":
            return payment_src
        if hint == "capital":
            return "capital"
        if hint == "cash":
            return "cash"
        if hint == "bank":
            return "bank"
        if hint == "drawings":
            return "drawings"
        if hint == "loan":
            # find a name or use generic
            for acc in accounts:
                if acc not in REAL_ACCOUNTS and acc not in NOMINAL_ACCOUNTS and acc not in {"cash", "bank"}:
                    return acc + " (loan)"
            return "loan"
        # asset_or_purchase / asset_or_sales / expense_or_asset / income_or_asset
        non_payment = [a for a in accounts if a not in {"cash", "bank", "cheque"}]
        if non_payment:
            return non_payment[0]
        # fallback guesses
        if "asset" in hint:
            return "asset"
        if "purchase" in hint:
            return "purchases"
        if "sales" in hint:
            return "sales"
        if "expense" in hint:
            return "expense"
        if "income" in hint:
            return "income"
        return "account"

    debit_acc = resolve_account(hint_d, accounts, payment_src, text_lower)
    credit_acc = resolve_account(hint_c, accounts, payment_src, text_lower)

    # Handle special case: invested → debit the asset they invested
    if matched_trigger in ("invested", "invest", "started business", "commenced"):
        non_capital = [a for a in accounts if a not in {"capital", "cash", "bank"}]
        if non_capital:
            debit_acc = non_capital[0]
        else:
            debit_acc = payment_src

    # Ensure debit ≠ credit
    if debit_acc == credit_acc:
        if credit_acc == "cash":
            credit_acc = "capital"
        else:
            debit_acc = "cash"

    # ── Narration ────────────────────────────────────────────────────────────
    narration = f"Being {transaction.strip().lower()}"

    return {
        "success": True,
        "transaction": transaction,
        "debit": {
            "account": title_account(debit_acc),
            "type": classify_account(debit_acc),
            "amount": amount,
        },
        "credit": {
            "account": title_account(credit_acc),
            "type": classify_account(credit_acc),
            "amount": amount,
        },
        "narration": narration,
        "amount": amount,
        "rule_applied": f"{classify_account(debit_acc).capitalize()} Account → {classify_account(credit_acc).capitalize()} Account",
    }
