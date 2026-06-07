"""Genereer realistische GL-export voorbeeldbestanden voor twee entiteiten.

Gebruik: python sample_data/genereer_sample.py
"""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

random.seed(42)

# ── Limtrade B.V. (516) — handelsonderneming ─────────────────────────────────
LIMTRADE_REKENINGEN = [
    # (code, omschrijving, type)
    ('8000', 'Omzet producten Nederland',       'omzet'),
    ('8010', 'Omzet producten export',           'omzet'),
    ('8020', 'Omzet dienstverlening',            'omzet'),
    ('7000', 'Inkoopwaarde goederen',            'kost'),
    ('7010', 'Vrachtkosten inkoop',              'kost'),
    ('4000', 'Lonen en salarissen',              'kost'),
    ('4010', 'Sociale lasten',                   'kost'),
    ('4020', 'Pensioenpremies',                  'kost'),
    ('4100', 'Huur bedrijfspand',                'kost'),
    ('4110', 'Gas, water en licht',              'kost'),
    ('4200', 'Lease personenwagens',             'kost'),
    ('4210', 'Brandstof en waskosten',           'kost'),
    ('4220', 'Verzekering voertuigen',           'kost'),
    ('4300', 'Reclame en marketing',             'kost'),
    ('4310', 'Reis- en verblijfkosten',          'kost'),
    ('4400', 'Telefoon en internet',             'kost'),
    ('4410', 'Kantoorbenodigdheden',             'kost'),
    ('4420', 'Accountants- en advieskosten',     'kost'),
    ('4430', 'Verzekeringen',                    'kost'),
    ('4440', 'Abonnementen en lidmaatschappen',  'kost'),
    ('4500', 'Afschrijving inventaris',          'kost'),
    ('4510', 'Afschrijving bedrijfsmiddelen',    'kost'),
    ('4700', 'Rentelasten',                      'kost'),
    ('4710', 'Bankkosten',                       'kost'),
]

LIMTRADE_MAAND_OMZET = {
    1: 95_000, 2: 88_000, 3: 112_000, 4: 105_000,
    5: 130_000, 6: 128_000, 7: 98_000, 8: 85_000,
    9: 125_000, 10: 140_000, 11: 155_000, 12: 145_000,
}

LIMTRADE_OMZET_AANDEEL = {'8000': 0.65, '8010': 0.25, '8020': 0.10}

LIMTRADE_KOSTEN_PCT = {'7000': 0.52}   # inkoopwaarde = 52% van maandomzet

LIMTRADE_KOSTENBED = {
    '7010': 1_800,
    '4000': 22_000, '4010': 4_400, '4020': 2_200,
    '4100': 3_500,  '4110': 950,
    '4200': 1_800,  '4210': 620,   '4220': 280,
    '4300': 800,    '4310': 450,
    '4400': 380,    '4410': 250,   '4420': 1_200, '4430': 320, '4440': 150,
    '4500': 900,    '4510': 650,
    '4700': 380,    '4710': 95,
}

# ── BKC Projecten B.V. (513) — projectontwikkeling ──────────────────────────
BKC_REKENINGEN = [
    ('8000', 'Omzet woningprojecten',             'omzet'),
    ('8010', 'Omzet commercieel vastgoed',         'omzet'),
    ('8020', 'Omzet projectmanagement',            'omzet'),
    ('7000', 'Aanneemkosten / onderaannemers',     'kost'),
    ('7010', 'Materiaalkosten',                    'kost'),
    ('7020', 'Directe projectkosten overig',       'kost'),
    ('4000', 'Lonen projectleiders',               'kost'),
    ('4010', 'Sociale lasten',                     'kost'),
    ('4100', 'Kantoorhuur',                        'kost'),
    ('4110', 'Gas, water en licht',                'kost'),
    ('4400', 'Accountants- en advieskosten',       'kost'),
    ('4410', 'Juridische kosten',                  'kost'),
    ('4420', 'Verzekeringen',                      'kost'),
    ('4500', 'Afschrijving inventaris',            'kost'),
    ('4700', 'Rentelasten projectfinanciering',    'kost'),
    ('4710', 'Bankkosten',                         'kost'),
]

# Lumpy project-omzet (grote projecten die op verschillende momenten gereed zijn)
BKC_MAAND_OMZET = {
    1:  55_000, 2:  30_000, 3: 190_000, 4:  80_000,
    5: 160_000, 6:  95_000, 7:  20_000, 8:  45_000,
    9: 210_000, 10: 130_000, 11: 95_000, 12: 70_000,
}

BKC_OMZET_AANDEEL = {'8000': 0.70, '8010': 0.20, '8020': 0.10}

BKC_KOSTENBED = {
    '7000': None,   # 40% van maandomzet
    '7010': None,   # 8% van maandomzet
    '7020': None,   # 4% van maandomzet
    '4000': 28_000, '4010': 5_600,
    '4100': 2_800,  '4110': 700,
    '4400': 1_500,  '4410': 800, '4420': 450,
    '4500': 600,
    '4700': 1_200,  '4710': 110,
}

BKC_KOSTEN_PCT = {'7000': 0.40, '7010': 0.08, '7020': 0.04}


def _splits(bedrag: float, n: int) -> list[float]:
    """Splits bedrag willekeurig in n stukken (altijd positief)."""
    if n == 1:
        return [round(bedrag, 2)]
    delen: list[float] = []
    rest = bedrag
    for i in range(n - 1):
        deel = round(random.uniform(0.15, 0.70) * rest, 2)
        delen.append(deel)
        rest -= deel
    delen.append(round(rest, 2))
    return delen


def genereer_rijen(
    rekeningen: list[tuple[str, str, str]],
    maand_omzet: dict[int, float],
    omzet_aandeel: dict[str, float],
    kostenbed: dict[str, float | None],
    kosten_pct: dict[str, float] | None,
    jaar: int,
) -> list[dict]:
    rijen: list[dict] = []
    boekstuknr = 1

    for periode in range(1, 13):
        totaal_omzet = maand_omzet[periode]
        kp = kosten_pct or {}

        for code, omschrijving, type_ in rekeningen:
            if type_ == 'omzet':
                aandeel = omzet_aandeel.get(code, 0.0)
                bedrag = totaal_omzet * aandeel * random.uniform(0.92, 1.08)
                debet, credit = 0.0, bedrag
            else:
                if code in kp:
                    bedrag = totaal_omzet * kp[code] * random.uniform(0.93, 1.07)
                elif kostenbed.get(code) is None:
                    # Fallback voor codes die als percentage zijn bedoeld maar niet in kp staan
                    continue
                else:
                    bedrag = kostenbed[code] * random.uniform(0.90, 1.10)
                debet, credit = bedrag, 0.0

            n = 1 if bedrag < 2_000 else random.randint(1, 3)
            debet_delen  = _splits(debet, n) if debet > 0 else [0.0] * n
            credit_delen = _splits(credit, n) if credit > 0 else [0.0] * n

            for d, c in zip(debet_delen, credit_delen):
                dag = random.randint(1, 28)
                rijen.append({
                    'Rekening':       code,
                    'Omschrijving':   omschrijving,
                    'Datum':          f'{dag:02d}-{periode:02d}-{jaar}',
                    'Periode':        periode,
                    'Jaar':           jaar,
                    'Boekstuknummer': f'{jaar}{boekstuknr:05d}',
                    'Debet':          round(d, 2),
                    'Credit':         round(c, 2),
                    'Kostenplaats':   '',
                })
                boekstuknr += 1

    return rijen


def maak_bestand(
    uitvoerpad: Path,
    rekeningen: list[tuple[str, str, str]],
    maand_omzet: dict[int, float],
    omzet_aandeel: dict[str, float],
    kostenbed: dict[str, float | None],
    kosten_pct: dict[str, float] | None,
    jaar: int = 2024,
) -> None:
    rijen = genereer_rijen(rekeningen, maand_omzet, omzet_aandeel, kostenbed, kosten_pct, jaar)
    df = pd.DataFrame(rijen)
    df.to_excel(uitvoerpad, index=False)
    jaaromzet = df[df['Rekening'].str.startswith('8')]['Credit'].sum()
    print(f'  Aangemaakt: {uitvoerpad.name}  ({len(df)} regels, omzet ≈ € {jaaromzet:,.0f})')


if __name__ == '__main__':
    uitvoerdir = Path(__file__).parent
    print('Sample data genereren…')

    maak_bestand(
        uitvoerdir / 'limtrade_516_2024.xlsx',
        LIMTRADE_REKENINGEN,
        LIMTRADE_MAAND_OMZET,
        LIMTRADE_OMZET_AANDEEL,
        LIMTRADE_KOSTENBED,
        LIMTRADE_KOSTEN_PCT,
    )

    maak_bestand(
        uitvoerdir / 'bkc_projecten_513_2024.xlsx',
        BKC_REKENINGEN,
        BKC_MAAND_OMZET,
        BKC_OMZET_AANDEEL,
        BKC_KOSTENBED,
        BKC_KOSTEN_PCT,
    )

    print('Klaar.')
