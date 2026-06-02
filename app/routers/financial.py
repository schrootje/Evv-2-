from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.exact import financial as fin

router = APIRouter(prefix="/financial", tags=["Financieel / Grootboek"])


class JournalEntryLine(BaseModel):
    GLAccount: str  # GUID van de grootboekrekening
    Description: str | None = None
    AmountDC: float  # Bedrag in de administratievaluta


class JournalEntryPayload(BaseModel):
    JournalCode: str
    Date: str  # ISO datum: "2024-01-15"
    Description: str | None = None
    Lines: list[JournalEntryLine]


def _handle(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Exact Online API fout: {e}")


@router.get("/gl-accounts", summary="Grootboekrekeningen ophalen")
def list_gl_accounts(search: str | None = Query(default=None, description="Zoek op omschrijving")):
    return _handle(fin.get_gl_accounts, search)


@router.get("/gl-accounts/{account_id}", summary="Één grootboekrekening ophalen")
def get_gl_account(account_id: str):
    return _handle(fin.get_gl_account, account_id)


@router.get("/journals", summary="Dagboeken ophalen")
def list_journals():
    return _handle(fin.get_journals)


@router.get("/transaction-lines", summary="Boekingsregels ophalen")
def list_transaction_lines(
    journal: str | None = Query(default=None, description="Filter op dagboekcode"),
    date_from: str | None = Query(default=None, description="Begindatum (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="Einddatum (YYYY-MM-DD)"),
    gl_account_id: str | None = Query(default=None, description="Filter op grootboekrekening GUID"),
):
    return _handle(fin.get_transaction_lines, journal, date_from, date_to, gl_account_id)


@router.get("/balance-sheet", summary="Balans ophalen")
def balance_sheet(
    period: int | None = Query(default=None, description="Periodnummer (1-12)"),
    year: int | None = Query(default=None, description="Boekjaar (bijv. 2024)"),
):
    return _handle(fin.get_balance_sheet, period, year)


@router.get("/profit-and-loss", summary="Verlies- en winstrekening ophalen")
def profit_and_loss(
    period: int | None = Query(default=None, description="Periodnummer (1-12)"),
    year: int | None = Query(default=None, description="Boekjaar (bijv. 2024)"),
):
    return _handle(fin.get_profit_and_loss, period, year)


@router.get("/outstanding-payable", summary="Openstaande crediteuren")
def outstanding_payable():
    return _handle(fin.get_outstanding_invoices_payable)


@router.get("/outstanding-receivable", summary="Openstaande debiteuren")
def outstanding_receivable():
    return _handle(fin.get_outstanding_invoices_receivable)


@router.post("/journal-entries", summary="Journaalpost aanmaken")
def create_journal_entry(payload: JournalEntryPayload):
    entry = {
        "JournalCode": payload.JournalCode,
        "Date": f"/Date({payload.Date})/",
        "Description": payload.Description,
        "GeneralJournalEntryLines": {
            "results": [
                {
                    "GLAccount": line.GLAccount,
                    "Description": line.Description,
                    "AmountDC": line.AmountDC,
                }
                for line in payload.Lines
            ]
        },
    }
    return _handle(fin.create_journal_entry, entry)
