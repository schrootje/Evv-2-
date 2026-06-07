"""Inladen en valideren van Exact Online GL-exports (CSV of XLSX)."""
from __future__ import annotations

import io
from pathlib import Path
from typing import IO

import pandas as pd

# Bekende kolomnamen per logisch veld (prioriteit: eerste match wint)
KOLOMNAMEN: dict[str, list[str]] = {
    'rekening':       ['Rekening', 'Grootboekrekening', 'RekeningCode', 'GLCode', 'Account Code', 'GL Account'],
    'omschrijving':   ['Omschrijving', 'OmschrijvingRekening', 'Rekening Omschrijving', 'GL Description', 'Description'],
    'datum':          ['Datum', 'Date', 'TransactieDatum', 'Transaction Date', 'Boekdatum'],
    'periode':        ['Periode', 'Period', 'FinancialPeriod', 'Boekperiode', 'Maand'],
    'jaar':           ['Jaar', 'Year', 'FinancialYear', 'Boekjaar'],
    'boekstuknummer': ['Boekstuknummer', 'EntryNumber', 'Boekstuk', 'Entry Number', 'Journaalnummer'],
    'debet':          ['Debet', 'Debit', 'DebitBedrag', 'Debit Amount'],
    'credit':         ['Credit', 'CreditBedrag', 'Credit Amount'],
}

VEREISTE_VELDEN = {'rekening', 'omschrijving', 'periode', 'jaar', 'debet', 'credit'}


def laad_export(bron: str | Path | IO, *, bestandsnaam: str = '') -> pd.DataFrame:
    """Laad een CSV of XLSX en geef een genormaliseerde DataFrame terug.

    Args:
        bron: bestandspad (str/Path) of file-like object (bijv. Streamlit UploadedFile)
        bestandsnaam: originele bestandsnaam bij file-like object, voor type-detectie
    """
    if hasattr(bron, 'read'):
        suffix = Path(bestandsnaam).suffix.lower() if bestandsnaam else '.xlsx'
        if suffix in ('.xlsx', '.xls'):
            df = pd.read_excel(bron, dtype=str)
        else:
            if hasattr(bron, 'getvalue'):
                ruwe_bytes = bron.getvalue()
            else:
                bron.seek(0)
                ruwe_bytes = bron.read()
            df = pd.read_csv(
                io.StringIO(ruwe_bytes.decode('utf-8-sig', errors='replace')),
                sep=None, engine='python', dtype=str,
            )
    else:
        pad = Path(bron)
        if pad.suffix.lower() in ('.xlsx', '.xls'):
            df = pd.read_excel(pad, dtype=str)
        elif pad.suffix.lower() == '.csv':
            df = pd.read_csv(pad, sep=None, engine='python', dtype=str)
        else:
            raise ValueError(f"Bestandsformaat niet ondersteund: {pad.suffix!r}")

    return _normaliseer(df)


def valideer_kolommen(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Controleer of alle vereiste velden aanwezig zijn.

    Returns:
        (alles_aanwezig, lijst_van_ontbrekende_velden)
    """
    ontbrekend = [v for v in VEREISTE_VELDEN if v not in df.columns]
    return (len(ontbrekend) == 0, ontbrekend)


def _vind_kolom(df: pd.DataFrame, veld: str) -> str | None:
    """Zoek de werkelijke kolomnaam voor een logisch veld (case-insensitief)."""
    kolommen_lower = {c.strip().lower(): c for c in df.columns}
    for kandidaat in KOLOMNAMEN.get(veld, []):
        gevonden = kolommen_lower.get(kandidaat.lower())
        if gevonden is not None:
            return gevonden
    return None


def _normaliseer(df: pd.DataFrame) -> pd.DataFrame:
    """Hernoem kolommen naar standaardnamen en parse datatypes."""
    hernoem = {}
    for veld in KOLOMNAMEN:
        gevonden = _vind_kolom(df, veld)
        if gevonden and gevonden != veld:
            hernoem[gevonden] = veld
    df = df.rename(columns=hernoem)

    if 'datum' in df.columns:
        df['datum'] = pd.to_datetime(df['datum'], dayfirst=True, errors='coerce')

    if 'periode' in df.columns:
        df['periode'] = pd.to_numeric(df['periode'], errors='coerce').astype('Int64')

    if 'jaar' in df.columns:
        df['jaar'] = pd.to_numeric(df['jaar'], errors='coerce').astype('Int64')

    for kolom in ('debet', 'credit'):
        if kolom in df.columns:
            df[kolom] = _parse_bedrag(df[kolom])

    if 'debet' in df.columns and 'credit' in df.columns:
        df['netto'] = df['debet'] - df['credit']

    if 'rekening' in df.columns:
        df['rekening'] = df['rekening'].astype(str).str.strip()

    return df


def _parse_bedrag(serie: pd.Series) -> pd.Series:
    """Zet een bedragkolom om naar float.

    Ondersteunt:
    - Standaard (XLSX-numeriek): 61750.50
    - Nederlands (CSV-export):   61.750,50
    - Angelsaksisch:             61,750.50
    """
    tekst = serie.astype(str).str.strip().str.replace(r'\s', '', regex=True)

    # Detecteer Nederlandse opmaak: punt als duizendtalscheider + komma als decimaal
    is_nl = tekst.str.contains(r'\d\.\d{3},', regex=True)

    resultaat = tekst.copy()
    resultaat = resultaat.where(
        ~is_nl,
        tekst.str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
    )
    resultaat = resultaat.where(
        is_nl,
        resultaat.str.replace(',', '', regex=False),
    )

    resultaat = resultaat.str.replace(r'[^\d.\-]', '', regex=True)
    return pd.to_numeric(resultaat, errors='coerce').fillna(0.0)
