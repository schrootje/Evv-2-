"""Financiële KPI-berekeningen op basis van een genormaliseerde GL-DataFrame."""
from __future__ import annotations

import pandas as pd

# ── P&L rekeningbereiken ────────────────────────────────────────────────────
# Pas aan aan het werkelijke schema van Kurvers Groep (zie CLAUDE.md)
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

# ── Balans rekeningbereiken ─────────────────────────────────────────────────
# Activa: debet-saldo is positief (bezit)
BALANS_ACTIVA: dict[str, tuple[int, int]] = {
    'Immateriële vaste activa': (100,  999),   # rekeningen 0100–0999
    'Materiële vaste activa':   (1000, 1999),
    'Financiële vaste activa':  (2000, 2999),
    'Voorraden':                (3000, 3099),
    'Debiteuren':               (3100, 3299),
    'Liquide middelen':         (3300, 3499),
}

# Passiva: credit-saldo is positief (schuld / eigen vermogen)
BALANS_PASSIVA: dict[str, tuple[int, int]] = {
    'Eigen vermogen':           (200,  399),   # rekeningen 0200–0399
    'Langlopende schulden':     (5000, 5499),
    'Kortlopende schulden':     (6000, 6499),
}

MAANDNAMEN = {
    1: 'Jan', 2: 'Feb', 3: 'Mrt', 4: 'Apr',
    5: 'Mei', 6: 'Jun', 7: 'Jul', 8: 'Aug',
    9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec',
}


# ── Hulpfuncties ────────────────────────────────────────────────────────────

def _rekening_int(df: pd.DataFrame) -> pd.Series:
    """Extraheer het numerieke deel van de rekeningcode."""
    return pd.to_numeric(
        df['rekening'].astype(str).str.extract(r'^(\d+)', expand=False),
        errors='coerce',
    )


def _filter(df: pd.DataFrame, van: int, tot: int) -> pd.DataFrame:
    code = _rekening_int(df)
    return df.loc[(code >= van) & (code <= tot)]


# ── P&L KPI's ───────────────────────────────────────────────────────────────

def bereken_omzet(df: pd.DataFrame) -> float:
    """Totale omzet (credit − debet op omzetrekeningen 8xxx)."""
    s = _filter(df, *CATEGORIEEN['Omzet'])
    return float(s['credit'].sum() - s['debet'].sum())


def bereken_bruto_marge(df: pd.DataFrame) -> float:
    """Brutowinst = omzet − kostprijs verkopen."""
    kpv = _filter(df, *CATEGORIEEN['Kostprijs verkopen'])
    return bereken_omzet(df) - float(kpv['debet'].sum() - kpv['credit'].sum())


def bereken_kosten(df: pd.DataFrame) -> float:
    """Totale bedrijfskosten (alle P&L-rekeningen behalve omzet)."""
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


def bereken_ebitda(df: pd.DataFrame) -> float:
    """EBITDA = resultaat + afschrijvingen + financiële lasten."""
    afschr = float(_filter(df, *CATEGORIEEN['Afschrijvingen']).pipe(
        lambda s: s['debet'].sum() - s['credit'].sum()
    ))
    rente = float(_filter(df, *CATEGORIEEN['Financiële lasten']).pipe(
        lambda s: s['debet'].sum() - s['credit'].sum()
    ))
    return bereken_resultaat(df) + afschr + rente


def bruto_marge_pct(df: pd.DataFrame) -> float:
    omzet = bereken_omzet(df)
    return bereken_bruto_marge(df) / omzet * 100 if omzet else 0.0


def netto_marge_pct(df: pd.DataFrame) -> float:
    omzet = bereken_omzet(df)
    return bereken_resultaat(df) / omzet * 100 if omzet else 0.0


def ebitda_marge_pct(df: pd.DataFrame) -> float:
    omzet = bereken_omzet(df)
    return bereken_ebitda(df) / omzet * 100 if omzet else 0.0


# ── Overzicht per maand ─────────────────────────────────────────────────────

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


def marge_per_maand(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame met bruto-, netto- en EBITDA-marge per periode (in %)."""
    periodes = sorted(
        int(p) for p in df['periode'].dropna().unique()
        if 1 <= int(p) <= 12
    )
    rijen = []
    for p in periodes:
        sub = df[df['periode'] == p]
        omzet = bereken_omzet(sub)
        if omzet == 0:
            continue
        rijen.append({
            'periode':      p,
            'maand':        MAANDNAMEN.get(p, str(p)),
            'Brutomarge':   bruto_marge_pct(sub),
            'Nettomarge':   netto_marge_pct(sub),
            'EBITDA-marge': ebitda_marge_pct(sub),
        })
    return pd.DataFrame(rijen)


# ── Kosten ─────────────────────────────────────────────────────────────────

def kosten_per_categorie(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame met kostenbedrag per categorie (gesorteerd op bedrag desc.)."""
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


# ── Balanscontrole ──────────────────────────────────────────────────────────

def debet_credit_check(df: pd.DataFrame) -> tuple[float, float, float]:
    """Controleer of totaal debet = totaal credit.

    Returns:
        (totaal_debet, totaal_credit, verschil)
    """
    totaal_d = float(df['debet'].sum())
    totaal_c = float(df['credit'].sum())
    return totaal_d, totaal_c, abs(totaal_d - totaal_c)


def balans_activa(df: pd.DataFrame) -> pd.DataFrame:
    """Saldo per activacategorie (debet-saldo = positief bezit)."""
    rijen = []
    for cat, (van, tot) in BALANS_ACTIVA.items():
        s = _filter(df, van, tot)
        if s.empty:
            continue
        saldo = float(s['debet'].sum() - s['credit'].sum())
        rijen.append({'categorie': cat, 'saldo': saldo})
    return pd.DataFrame(rijen) if rijen else pd.DataFrame(columns=['categorie', 'saldo'])


def balans_passiva(df: pd.DataFrame) -> pd.DataFrame:
    """Saldo per passivacategorie (credit-saldo = positieve schuld)."""
    rijen = []
    for cat, (van, tot) in BALANS_PASSIVA.items():
        s = _filter(df, van, tot)
        if s.empty:
            continue
        saldo = float(s['credit'].sum() - s['debet'].sum())
        rijen.append({'categorie': cat, 'saldo': saldo})
    return pd.DataFrame(rijen) if rijen else pd.DataFrame(columns=['categorie', 'saldo'])


def current_ratio(df: pd.DataFrame) -> float | None:
    """Vlottende activa / kortlopende schulden. Geeft None als geen balansdata."""
    vlottende = 0.0
    for cat in ('Voorraden', 'Debiteuren', 'Liquide middelen'):
        van, tot = BALANS_ACTIVA[cat]
        s = _filter(df, van, tot)
        vlottende += float(s['debet'].sum() - s['credit'].sum())

    van, tot = BALANS_PASSIVA['Kortlopende schulden']
    kortlopend = float(_filter(df, van, tot).pipe(
        lambda s: s['credit'].sum() - s['debet'].sum()
    ))

    if kortlopend <= 0:
        return None
    return vlottende / kortlopend


# ── Interne helpers ────────────────────────────────────────────────────────

def _omzet_per_periode(df: pd.DataFrame) -> pd.Series:
    s = _filter(df, *CATEGORIEEN['Omzet'])
    if s.empty:
        return pd.Series(dtype=float)
    return s.groupby('periode').apply(lambda g: g['credit'].sum() - g['debet'].sum())


def _kosten_per_periode(df: pd.DataFrame) -> pd.Series:
    stukken = [
        _filter(df, van, tot)
        for cat, (van, tot) in CATEGORIEEN.items()
        if cat != 'Omzet'
    ]
    alle = pd.concat(stukken)
    if alle.empty:
        return pd.Series(dtype=float)
    return alle.groupby('periode').apply(lambda g: g['debet'].sum() - g['credit'].sum())
