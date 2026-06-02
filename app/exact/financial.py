from typing import Any

from app.exact.client import ExactClient


def get_gl_accounts(search: str | None = None) -> list[dict]:
    client = ExactClient()
    params: dict = {}
    if search:
        params["$filter"] = f"substringof('{search}', Description) eq true"
    return client.get("/financial/GLAccounts", params=params or None)


def get_gl_account(account_id: str) -> dict:
    client = ExactClient()
    results = client.get(f"/financial/GLAccounts(guid'{account_id}')")
    if not results:
        raise ValueError(f"Grootboekrekening {account_id} niet gevonden.")
    return results[0]


def get_journals() -> list[dict]:
    client = ExactClient()
    return client.get("/financial/Journals")


def get_transaction_lines(
    journal_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    gl_account_id: str | None = None,
) -> list[dict]:
    client = ExactClient()
    filters: list[str] = []
    if journal_code:
        filters.append(f"Journal eq '{journal_code}'")
    if date_from:
        filters.append(f"Date ge datetime'{date_from}T00:00:00'")
    if date_to:
        filters.append(f"Date le datetime'{date_to}T23:59:59'")
    if gl_account_id:
        filters.append(f"GLAccount eq guid'{gl_account_id}'")
    params = {"$filter": " and ".join(filters)} if filters else None
    return client.get("/financialtransactions/TransactionLines", params=params)


def get_balance_sheet(period: int | None = None, year: int | None = None) -> list[dict]:
    client = ExactClient()
    params: dict = {}
    if period is not None:
        params["$filter"] = f"ReportingPeriod eq {period}"
    if year is not None:
        f = params.get("$filter", "")
        year_filter = f"ReportingYear eq {year}"
        params["$filter"] = f"{f} and {year_filter}" if f else year_filter
    return client.get("/financial/BalanceSheets", params=params or None)


def get_profit_and_loss(period: int | None = None, year: int | None = None) -> list[dict]:
    client = ExactClient()
    params: dict = {}
    if period is not None:
        params["$filter"] = f"ReportingPeriod eq {period}"
    if year is not None:
        f = params.get("$filter", "")
        year_filter = f"ReportingYear eq {year}"
        params["$filter"] = f"{f} and {year_filter}" if f else year_filter
    return client.get("/financial/PLAccountsPerYear", params=params or None)


def create_journal_entry(payload: dict) -> Any:
    client = ExactClient()
    return client.post("/generaljournalentry/GeneralJournalEntries", payload)


def get_outstanding_invoices_payable() -> list[dict]:
    """Openstaande crediteuren."""
    client = ExactClient()
    return client.get("/financial/OutstandingInvoicesPayable")


def get_outstanding_invoices_receivable() -> list[dict]:
    """Openstaande debiteuren."""
    client = ExactClient()
    return client.get("/financial/OutstandingInvoicesReceivable")
