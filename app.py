"""Financieel dashboard Kurvers Groep — Streamlit app.

Starten: streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_loader import laad_export, valideer_kolommen
from metrics import (
    MAANDNAMEN,
    balans_activa,
    balans_passiva,
    bereken_ebitda,
    bereken_kosten,
    bereken_omzet,
    bereken_resultaat,
    bruto_marge_pct,
    current_ratio,
    debet_credit_check,
    ebitda_marge_pct,
    kosten_per_categorie,
    marge_per_maand,
    netto_marge_pct,
    resultaat_per_maand,
    top_rekeningen,
)

# ── Opmaak helpers ───────────────────────────────────────────────────────────

def _euro(x: float) -> str:
    return '€ ' + f'{x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def _pct(x: float) -> str:
    return f'{x:.1f}%'


def _ratio(x: float | None) -> str:
    return f'{x:.2f}' if x is not None else 'N.v.t.'


# ── Paden naar voorbeelddata ─────────────────────────────────────────────────
SAMPLE_DIR = Path(__file__).parent / 'sample_data'
LIMTRADE_PAD = SAMPLE_DIR / 'limtrade_516_2024.xlsx'
BKC_PAD = SAMPLE_DIR / 'bkc_projecten_513_2024.xlsx'

# ── Pagina-config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Financieel Dashboard – Kurvers Groep',
    page_icon='📊',
    layout='wide',
)

st.title('📊 Financieel Dashboard – Kurvers Groep')


# ── Data-laad functies (gecached) ────────────────────────────────────────────
@st.cache_data(show_spinner='Gegevens laden…')
def _laad_pad(pad: str) -> pd.DataFrame:
    return laad_export(pad)


@st.cache_data(show_spinner='Gegevens laden…')
def _laad_upload(naam: str, inhoud: bytes) -> pd.DataFrame:
    import io as _io
    suffix = Path(naam).suffix.lower()
    if suffix in ('.xlsx', '.xls'):
        return laad_export(_io.BytesIO(inhoud), bestandsnaam=naam)
    return laad_export(_io.BytesIO(inhoud), bestandsnaam=naam)


# ── Sidebar – entiteiten laden ───────────────────────────────────────────────
with st.sidebar:
    st.header('Entiteiten laden')

    entiteiten: dict[str, pd.DataFrame] = {}

    with st.expander('Voorbeelddata', expanded=True):
        if LIMTRADE_PAD.exists():
            if st.checkbox('Limtrade B.V. (516)', value=True):
                entiteiten['Limtrade 516'] = _laad_pad(str(LIMTRADE_PAD))
        if BKC_PAD.exists():
            if st.checkbox('BKC Projecten B.V. (513)'):
                entiteiten['BKC Projecten 513'] = _laad_pad(str(BKC_PAD))

    geupladen = st.file_uploader(
        'Eigen GL-export(s) uploaden',
        type=['csv', 'xlsx', 'xls'],
        accept_multiple_files=True,
        help='Upload één of meer Exact Online grootboekexports (CSV of XLSX).',
    )
    for f in geupladen:
        naam = Path(f.name).stem
        entiteiten[naam] = _laad_upload(f.name, f.read())

    if not entiteiten:
        st.info('Selecteer of upload minimaal één entiteit.')
        st.stop()

    st.divider()
    st.header('Filters')

    # Entiteitsfilter (toon alleen als er meer dan één is geladen)
    if len(entiteiten) > 1:
        geselecteerd = st.multiselect(
            'Entiteiten weergeven',
            list(entiteiten.keys()),
            default=list(entiteiten.keys()),
        )
        if not geselecteerd:
            st.warning('Selecteer minimaal één entiteit.')
            st.stop()
    else:
        geselecteerd = list(entiteiten.keys())

    filter_jaar = st.selectbox('Boekjaar', [2024, 2023, 2022], index=0)
    filter_periodes = st.multiselect(
        'Periode(s)',
        list(range(1, 13)),
        default=list(range(1, 13)),
        format_func=lambda p: f'{p} – {MAANDNAMEN.get(p, "")}',
    )

# ── Data samenvoegen en valideren ────────────────────────────────────────────
stukken = []
for naam in geselecteerd:
    sub = entiteiten[naam].copy()
    sub['entiteit'] = naam
    stukken.append(sub)
df_rauw = pd.concat(stukken, ignore_index=True)

ok, ontbrekend = valideer_kolommen(df_rauw)
if not ok:
    st.error(
        f'Ontbrekende kolommen: **{", ".join(ontbrekend)}**  \n'
        'Controleer de kolomnamen in het bestand en pas `data_loader.py` aan.'
    )
    with st.expander('Gevonden kolommen'):
        st.write(list(df_rauw.columns))
    st.stop()

# Jaar- en periodefilter
df = df_rauw.copy()
if 'jaar' in df.columns:
    df = df[df['jaar'] == filter_jaar]
if filter_periodes and 'periode' in df.columns:
    df = df[df['periode'].isin(filter_periodes)]

if df.empty:
    st.warning('Geen boekingen gevonden voor de geselecteerde filters.')
    st.stop()

# ── Bereken KPI's ─────────────────────────────────────────────────────────────
omzet     = bereken_omzet(df)
kosten    = bereken_kosten(df)
resultaat = bereken_resultaat(df)
bruto_pct = bruto_marge_pct(df)
netto_pct = netto_marge_pct(df)
ebitda    = bereken_ebitda(df)

# ── Entiteitlabel boven tabs ─────────────────────────────────────────────────
label = ' + '.join(geselecteerd)
if len(geselecteerd) > 1:
    label += ' (consolidatie)'
st.caption(f'**{label}** · boekjaar {filter_jaar}')

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_ov, tab_ko, tab_ra, tab_ba, tab_dt = st.tabs([
    '📈 Overzicht',
    '💸 Kosten',
    "📐 Ratio's",
    '⚖️ Balanscontrole',
    '📋 Details',
])


# ════════════════════════════════════════════════════════════════════════════
# Tab 1 – Overzicht
# ════════════════════════════════════════════════════════════════════════════
with tab_ov:
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric('Omzet',      _euro(omzet))
    k2.metric('Kosten',     _euro(kosten))
    k3.metric('Resultaat',  _euro(resultaat),
              delta=_euro(resultaat),
              delta_color='normal' if resultaat >= 0 else 'inverse')
    k4.metric('Brutomarge', _pct(bruto_pct))
    k5.metric('Nettomarge', _pct(netto_pct))

    st.divider()
    maand_df = resultaat_per_maand(df)

    if maand_df.empty:
        st.info('Geen periodedata beschikbaar.')
    else:
        col_grafiek, col_tabel = st.columns([3, 2])

        with col_grafiek:
            fig = go.Figure()
            fig.add_bar(x=maand_df['maand'], y=maand_df['omzet'],
                        name='Omzet', marker_color='#2196F3')
            fig.add_bar(x=maand_df['maand'], y=maand_df['kosten'],
                        name='Kosten', marker_color='#FF5722')
            fig.add_scatter(x=maand_df['maand'], y=maand_df['resultaat'],
                            name='Resultaat', mode='lines+markers',
                            line=dict(color='#4CAF50', width=2))
            fig.update_layout(
                barmode='group',
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                yaxis_tickformat=',.0f',
                yaxis_tickprefix='€',
                margin=dict(t=40, b=20),
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_tabel:
            weergave = maand_df[['maand', 'omzet', 'kosten', 'resultaat']].copy()
            weergave['omzet']     = weergave['omzet'].map(_euro)
            weergave['kosten']    = weergave['kosten'].map(_euro)
            weergave['resultaat'] = weergave['resultaat'].map(_euro)
            weergave.columns = ['Maand', 'Omzet', 'Kosten', 'Resultaat']
            st.dataframe(weergave, use_container_width=True, hide_index=True, height=380)

    # Meerdere entiteiten: toon vergelijking
    if len(geselecteerd) > 1:
        st.divider()
        st.subheader('Vergelijking per entiteit')
        vergelijking = []
        for naam in geselecteerd:
            sub = entiteiten[naam].copy()
            if 'jaar' in sub.columns:
                sub = sub[sub['jaar'] == filter_jaar]
            if filter_periodes and 'periode' in sub.columns:
                sub = sub[sub['periode'].isin(filter_periodes)]
            vergelijking.append({
                'Entiteit':   naam,
                'Omzet':      _euro(bereken_omzet(sub)),
                'Kosten':     _euro(bereken_kosten(sub)),
                'Resultaat':  _euro(bereken_resultaat(sub)),
                'Nettomarge': _pct(netto_marge_pct(sub)),
            })
        st.dataframe(
            pd.DataFrame(vergelijking),
            use_container_width=True, hide_index=True,
        )


# ════════════════════════════════════════════════════════════════════════════
# Tab 2 – Kosten
# ════════════════════════════════════════════════════════════════════════════
with tab_ko:
    cat_df = kosten_per_categorie(df)

    if cat_df.empty:
        st.info('Geen kostendata gevonden in de geselecteerde periode.')
    else:
        col_taart, col_top = st.columns(2)

        with col_taart:
            fig_pie = px.pie(
                cat_df, values='bedrag', names='categorie',
                title='Kosten naar categorie',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(showlegend=False, margin=dict(t=40, b=20), height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_top:
            top_df = top_rekeningen(df, n=10)
            if not top_df.empty:
                fig_bar = px.bar(
                    top_df.sort_values('bedrag'),
                    x='bedrag', y='omschrijving',
                    orientation='h',
                    title='Top 10 kostenrekeningen',
                    color_discrete_sequence=['#FF5722'],
                )
                fig_bar.update_layout(
                    xaxis_tickformat=',.0f',
                    xaxis_tickprefix='€',
                    yaxis_title='',
                    margin=dict(t=40, b=20),
                    height=400,
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        st.subheader('Kostentabel')
        tabel = cat_df.copy()
        tabel['bedrag'] = tabel['bedrag'].map(_euro)
        tabel.columns = ['Categorie', 'Bedrag']
        st.dataframe(tabel, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# Tab 3 – Ratio's
# ════════════════════════════════════════════════════════════════════════════
with tab_ra:
    r1, r2, r3, r4 = st.columns(4)
    r1.metric('Brutomarge',   _pct(bruto_pct),
              help='(Omzet − Kostprijs verkopen) / Omzet')
    r2.metric('EBITDA-marge', _pct(ebitda_marge_pct(df)),
              help='(Resultaat + Afschrijvingen + Rente) / Omzet')
    r3.metric('Nettomarge',   _pct(netto_pct),
              help='Resultaat / Omzet')
    cr = current_ratio(df)
    r4.metric('Current ratio', _ratio(cr),
              help='Vlottende activa / Kortlopende schulden  '
                   '(> 1 = gezond; N.v.t. als geen balansdata)')

    st.divider()

    marge_df = marge_per_maand(df)
    if marge_df.empty:
        st.info('Onvoldoende periodedata voor margintrend.')
    else:
        fig_marge = go.Figure()
        kleuren = {'Brutomarge': '#2196F3', 'Nettomarge': '#4CAF50', 'EBITDA-marge': '#FF9800'}
        for kolom, kleur in kleuren.items():
            if kolom in marge_df.columns:
                fig_marge.add_scatter(
                    x=marge_df['maand'], y=marge_df[kolom],
                    name=kolom, mode='lines+markers',
                    line=dict(color=kleur, width=2),
                )
        fig_marge.add_hline(y=0, line_dash='dot', line_color='gray')
        fig_marge.update_layout(
            title='Margeontwikkeling per maand',
            yaxis_tickformat='.1f',
            yaxis_ticksuffix='%',
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            margin=dict(t=60, b=20),
            height=360,
        )
        st.plotly_chart(fig_marge, use_container_width=True)

    if cr is None:
        st.info(
            '**Current ratio** vereist balansrekeningen in de export.  \n'
            'Laad een volledige GL-export met rekeningen in de bereiken '
            '3000–3499 (vlottende activa) en 6000–6499 (kortlopende schulden).'
        )


# ════════════════════════════════════════════════════════════════════════════
# Tab 4 – Balanscontrole
# ════════════════════════════════════════════════════════════════════════════
with tab_ba:
    totaal_d, totaal_c, verschil = debet_credit_check(df)
    in_balans = verschil < 0.01

    if in_balans:
        st.success('✅ Debet = Credit — de export is boekhoudkundig in evenwicht.')
    else:
        st.warning(
            f'⚠️ Debet ≠ Credit — verschil: **{_euro(verschil)}**  \n'
            'Dit wijst op een incomplete export (bijv. alleen P&L zonder balansrekeningen).'
        )

    c1, c2, c3 = st.columns(3)
    c1.metric('Totaal debet',  _euro(totaal_d))
    c2.metric('Totaal credit', _euro(totaal_c))
    c3.metric('Verschil',      _euro(verschil),
              delta_color='off' if in_balans else 'inverse')

    st.divider()

    activa_df  = balans_activa(df)
    passiva_df = balans_passiva(df)

    heeft_balansdata = not activa_df.empty or not passiva_df.empty

    if heeft_balansdata:
        col_act, col_pas = st.columns(2)

        with col_act:
            st.subheader('Activa')
            if activa_df.empty:
                st.info('Geen activarekeningen gevonden.')
            else:
                totaal_activa = activa_df['saldo'].sum()
                tabel_a = activa_df.copy()
                tabel_a['saldo'] = tabel_a['saldo'].map(_euro)
                tabel_a.columns = ['Categorie', 'Saldo']
                st.dataframe(tabel_a, use_container_width=True, hide_index=True)
                st.metric('Totaal activa', _euro(totaal_activa))

        with col_pas:
            st.subheader('Passiva')
            if passiva_df.empty:
                st.info('Geen passivarekeningen gevonden.')
            else:
                totaal_passiva = passiva_df['saldo'].sum()
                tabel_p = passiva_df.copy()
                tabel_p['saldo'] = tabel_p['saldo'].map(_euro)
                tabel_p.columns = ['Categorie', 'Saldo']
                st.dataframe(tabel_p, use_container_width=True, hide_index=True)
                st.metric('Totaal passiva', _euro(totaal_passiva))

        if not activa_df.empty and not passiva_df.empty:
            balans_diff = abs(activa_df['saldo'].sum() - passiva_df['saldo'].sum())
            if balans_diff < 0.01:
                st.success('✅ Activa = Passiva')
            else:
                st.warning(f'⚠️ Activa ≠ Passiva — verschil: {_euro(balans_diff)}')
    else:
        st.info(
            '**Balansoverzicht** vereist balansrekeningen in de export.  \n\n'
            'Laad een volledige GL-export met de volgende rekeningen:  \n'
            '- **Activa** — rekeningen 0100–3499 '
            '(vaste activa, voorraden, debiteuren, bank)  \n'
            '- **Passiva** — rekeningen 0200–0399, 5000–5499, 6000–6499 '
            '(eigen vermogen, langlopende en kortlopende schulden)  \n\n'
            'De voorbeelddata bevat alleen P&L-rekeningen (4xxx, 7xxx, 8xxx).'
        )


# ════════════════════════════════════════════════════════════════════════════
# Tab 5 – Details
# ════════════════════════════════════════════════════════════════════════════
with tab_dt:
    weergave_kolommen = [c for c in
                         ['entiteit', 'datum', 'rekening', 'omschrijving',
                          'periode', 'boekstuknummer', 'debet', 'credit', 'netto']
                         if c in df.columns]
    toon_df = df[weergave_kolommen].copy()
    for kolom in ('debet', 'credit', 'netto'):
        if kolom in toon_df.columns:
            toon_df[kolom] = toon_df[kolom].map(lambda x: f'{x:,.2f}')

    st.caption(f'{len(toon_df):,} regels')
    st.dataframe(toon_df, use_container_width=True, hide_index=True)

st.caption('Kurvers Groep — alleen voor intern gebruik')
