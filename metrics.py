"""Financiële KPI-berekeningen op basis van een genormaliseerde GL-DataFrame."""
import pandas as pd

# Rekeningbereiken — pas aan aan het werkelijke schema van Limtrade / Kurvers Groep
CATEGORIEEN: dict[str, tuple[int, int]] = {
    'Omzet':                (8000, 8999),
    'Kostprijs verkopen':   (7000, 7499),
    'Personeelskosten':     (4000, 4099),
    'Huisvestingskosten':   (4100, 4199),
    'Autokosten':           (4200, 4299),
    'Verkoopkosten':        (4300, 4399),
    'Algemene kosten':      (4400, 4499),
    'Afschrijvingen':       (4500, 4599),
    'Financiële lasten':    (4700, 4799),
}

MAANDNAMEN = {
    1: 'Jan', 2: 'Feb', 3: 'Mrt', 4: 'Apr',
    5: 'Mei', 6: 'Jun', 7: 'Jul', 8: 'Aug',
    9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec',
}


def _rekening_int(df: pd.DataFrame) -> pd.Series:
    """Extraheer het numerieke deel van de rekeningcode."""
    return pd.to_numeric(
        df['rekening'].astype(str).str.extract(r'^(\d+)', expand=False),
        errors='coerce',
    )


def _filter(df: pd.DataFrame, van: int, tot: int) -> pd.DataFrame:
    code = _rekening_int(df)
    return df.loc[(code >= van) & (code <= tot)]


def bereken_omzet(df: pd.DataFrame) -> float:
    """Totale omzet (credit − debet op omzetrekeningen 8xxx)."""
    s = _filter(df, *CATEGORIEEN['Omzet'])
    return float(s['credit'].sum() - s['debet'].sum())


def bereken_bruto_marge(df: pd.DataFrame) -> float:
    """Brutowinst = omzet − kostprijs verkopen."""
    omzet = bereken_omzet(df)
    kpv = _filter(df, *CATEGORIEEN['Kostprijs verkopen'])
    kostprijs = float(kpv['debet'].sum() - kpv['credit'].sum())
    return omzet - kostprijs


def bereken_kosten(df: pd.DataFrame) -> float:
    """Totale bedrijfskosten (alle kostenrekeningen behalve omzet)."""
    totaal = 0.0
    for cat, (van, tot) in CATEGORIEEN.items():
        if cat == 'Omzet':
            continue
        s = _filter(df, van, tot)
        totaal += float(s['debet'].sum() - s['credit'].sum())
    return totaal


def bereken_resultaat(df: pd.DataFrame) -> float:
    """Bedrijfsresultaat = omzet − kosten."""
    return bereken_omzet(df) - bereken_kosten(df)


def bruto_marge_pct(df: pd.DataFrame) -> float:
    omzet = bereken_omzet(df)
    if omzet == 0:
        return 0.0
    return bereken_bruto_marge(df) / omzet * 100


def netto_marge_pct(df: pd.DataFrame) -> float:
    omzet = bereken_omzet(df)
    if omzet == 0:
        return 0.0
    return bereken_resultaat(df) / omzet * 100


def resultaat_per_maand(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame met per periode: omzet, kosten en resultaat."""
    omzet_reeks = _omzet_per_periode(df)
    kosten_reeks = _kosten_per_periode(df)

    periodes = sorted(set(omzet_reeks.index) | set(kosten_reeks.index))
    tabel = pd.DataFrame({
        'periode':  periodes,
        'maand':    [MAANDNAMEN.get(int(p), str(p)) for p in periodes],
        'omzet':    [float(omzet_reeks.get(p, 0.0)) for p in periodes],
        'kosten':   [float(kosten_reeks.get(p, 0.0)) for p in periodes],
    })
    tabel['resultaat'] = tabel['omzet'] - tabel['kosten']
    return tabel


def kosten_per_categorie(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame met kostenbedrag per categorie (gesorteerd op bedrag)."""
    rijen = []
    for cat, (van, tot) in CATEGORIEEN.items():
        if cat == 'Omzet':
            continue
        s = _filter(df, van, tot)
        bedrag = float(s['debet'].sum() - s['credit'].sum())
        if bedrag > 0:
            rijen.append({'categorie': cat, 'bedrag': bedrag})
    return (
        pd.DataFrame(rijen)
        .sort_values('bedrag', ascending=False)
        .reset_index(drop=True)
    )


def top_rekeningen(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Grootste kostenrekeningen op nettobasis (debet − credit)."""
    kostendf = pd.concat([
        _filter(df, van, tot)
        for cat, (van, tot) in CATEGORIEEN.items()
        if cat != 'Omzet'
    ])
    if kostendf.empty:
        return pd.DataFrame(columns=['rekening', 'omschrijving', 'bedrag'])

    grouped = (
        kostendf
        .groupby(['rekening', 'omschrijving'], as_index=False)
        .agg(debet=('debet', 'sum'), credit=('credit', 'sum'))
    )
    grouped['bedrag'] = grouped['debet'] - grouped['credit']
    return (
        grouped[grouped['bedrag'] > 0]
        .nlargest(n, 'bedrag')[['rekening', 'omschrijving', 'bedrag']]
        .reset_index(drop=True)
    )


def _omzet_per_periode(df: pd.DataFrame) -> pd.Series:
    s = _filter(df, *CATEGORIEEN['Omzet'])
    if s.empty:
        return pd.Series(dtype=float)
    return s.groupby('periode').apply(lambda g: g['credit'].sum() - g['debet'].sum())


def _kosten_per_periode(df: pd.DataFrame) -> pd.Series:
    stukken = []
    for cat, (van, tot) in CATEGORIEEN.items():
        if cat == 'Omzet':
            continue
        stukken.append(_filter(df, van, tot))
    if not stukken:
        return pd.Series(dtype=float)
    alle = pd.concat(stukken)
    if alle.empty:
        return pd.Series(dtype=float)
    return alle.groupby('periode').apply(lambda g: g['debet'].sum() - g['credit'].sum())
