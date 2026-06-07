"""Genereer een realistisch GL-export voorbeeldbestand voor Limtrade B.V. (admin 516).

Gebruik: python sample_data/genereer_sample.py
"""
import random
import pandas as pd
from pathlib import Path

random.seed(42)

REKENINGEN = [
    # (code, omschrijving, type)  — type: 'omzet' of 'kost'
    # Omzet
    ('8000', 'Omzet producten Nederland',       'omzet'),
    ('8010', 'Omzet producten export',           'omzet'),
    ('8020', 'Omzet dienstverlening',            'omzet'),
    # Kostprijs
    ('7000', 'Inkoopwaarde goederen',            'kost'),
    ('7010', 'Vrachtkosten inkoop',              'kost'),
    # Personeelskosten
    ('4000', 'Lonen en salarissen',              'kost'),
    ('4010', 'Sociale lasten',                   'kost'),
    ('4020', 'Pensioenpremies',                  'kost'),
    # Huisvesting
    ('4100', 'Huur bedrijfspand',                'kost'),
    ('4110', 'Gas, water en licht',              'kost'),
    # Autokosten
    ('4200', 'Lease personenwagens',             'kost'),
    ('4210', 'Brandstof en waskosten',           'kost'),
    ('4220', 'Verzekering voertuigen',           'kost'),
    # Verkoopkosten
    ('4300', 'Reclame en marketing',             'kost'),
    ('4310', 'Reis- en verblijfkosten',          'kost'),
    # Algemene kosten
    ('4400', 'Telefoon en internet',             'kost'),
    ('4410', 'Kantoorbenodigdheden',             'kost'),
    ('4420', 'Accountants- en advieskosten',     'kost'),
    ('4430', 'Verzekeringen',                    'kost'),
    ('4440', 'Abonnementen en lidmaatschappen',  'kost'),
    # Afschrijvingen
    ('4500', 'Afschrijving inventaris',          'kost'),
    ('4510', 'Afschrijving bedrijfsmiddelen',    'kost'),
    # Financieel
    ('4700', 'Rentelasten',                      'kost'),
    ('4710', 'Bankkosten',                       'kost'),
]

# Maandelijkse basiswaarden (realistisch voor een middelgrote handelsonderneming)
MAAND_OMZET = {
    1: 95_000, 2: 88_000, 3: 112_000, 4: 105_000,
    5: 130_000, 6: 128_000, 7: 98_000, 8: 85_000,
    9: 125_000, 10: 140_000, 11: 155_000, 12: 145_000,
}

REKENING_MAANDBEDRAGEN = {
    # omzetrekeningen: (aandeel van totale maandomzet)
    '8000': 0.65, '8010': 0.25, '8020': 0.10,
    # kostenrekeningen: vast maandbedrag (bij benadering)
    '7000': None,  # 52% van omzet (berekend dynamisch)
    '7010': 1_800,
    '4000': 22_000, '4010': 4_400, '4020': 2_200,
    '4100': 3_500, '4110': 950,
    '4200': 1_800, '4210': 620, '4220': 280,
    '4300': 800, '4310': 450,
    '4400': 380, '4410': 250, '4420': 1_200, '4430': 320, '4440': 150,
    '4500': 900, '4510': 650,
    '4700': 380, '4710': 95,
}


def genereer_rijen(jaar: int) -> list[dict]:
    rijen = []
    boekstuknr = 1

    for periode in range(1, 13):
        totaal_omzet = MAAND_OMZET[periode]

        for code, omschrijving, type_ in REKENINGEN:
            if type_ == 'omzet':
                aandeel = REKENING_MAANDBEDRAGEN.get(code, 0)
                bedrag = totaal_omzet * aandeel * random.uniform(0.92, 1.08)
                debet, credit = 0.0, round(bedrag, 2)
            else:
                if code == '7000':
                    bedrag = totaal_omzet * 0.52 * random.uniform(0.95, 1.05)
                else:
                    basis = REKENING_MAANDBEDRAGEN.get(code, 0)
                    bedrag = basis * random.uniform(0.9, 1.1)
                debet, credit = round(bedrag, 2), 0.0

            # Soms worden grote bedragen in meerdere boekingen gesplitst
            n_boekingen = 1 if bedrag < 2_000 else random.randint(1, 3)
            restant_d, restant_c = debet, credit

            for i in range(n_boekingen):
                dag = random.randint(1, 28)
                datum = f"{dag:02d}-{periode:02d}-{jaar}"
                if i < n_boekingen - 1:
                    deel = round(random.uniform(0.2, 0.8) * (restant_d or restant_c), 2)
                    d = deel if debet > 0 else 0.0
                    c = deel if credit > 0 else 0.0
                    restant_d -= d
                    restant_c -= c
                else:
                    d, c = round(restant_d, 2), round(restant_c, 2)

                rijen.append({
                    'Rekening':       code,
                    'Omschrijving':   omschrijving,
                    'Datum':          datum,
                    'Periode':        periode,
                    'Jaar':           jaar,
                    'Boekstuknummer': f"{jaar}{boekstuknr:05d}",
                    'Debet':          d,
                    'Credit':         c,
                    'Kostenplaats':   '',
                })
                boekstuknr += 1

    return rijen


if __name__ == '__main__':
    uitvoerpad = Path(__file__).parent / 'limtrade_516_2024.xlsx'
    rijen = genereer_rijen(2024)
    df = pd.DataFrame(rijen)
    df.to_excel(uitvoerpad, index=False)
    print(f"Voorbeeldbestand aangemaakt: {uitvoerpad}  ({len(df)} regels)")
