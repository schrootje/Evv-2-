"""Financieel dashboard Kurvers Groep — Streamlit app.

Starten: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

from data_loader import laad_export, valideer_kolommen
from metrics import (
    bereken_omzet,
    bereken_kosten,
    bereken_resultaat,
    bruto_marge_pct,
    netto_marge_pct,
    resultaat_per_maand,
    kosten_per_categorie,
    top_rekeningen,
    MAANDNAMEN,
)

EURO = lambda x: f"€ {x:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
PCT = lambda x: f"{x:.1f}%"

SAMPLE_PAD = Path(__file__).parent / 'sample_data' / 'limtrade_516_2024.xlsx'

st.set_page_config(
    page_title='Financieel Dashboard – Kurvers Groep',
    page_icon='📊',
    layout='wide',
)

st.title('📊 Financieel Dashboard – Kurvers Groep')

# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('Gegevens laden')

    gebruik_sample = st.checkbox(
        'Voorbeelddata gebruiken (Limtrade 2024)',
        value=not SAMPLE_PAD.exists() is False,
        disabled=not SAMPLE_PAD.exists(),
        help='Laadt de meegeleverde voorbeelddata uit sample_data/',
    )

    geupload = st.file_uploader(
        'Of upload een eigen GL-export (CSV / XLSX)',
        type=['csv', 'xlsx', 'xls'],
        disabled=gebruik_sample,
    )

    st.divider()
    st.header('Filters')
    filter_jaar = st.selectbox('Boekjaar', [2024, 2023, 2022], index=0)
    filter_periodes = st.multiselect(
        'Periode(s)',
        options=list(range(1, 13)),
        default=list(range(1, 13)),
        format_func=lambda p: f"{p} – {MAANDNAMEN.get(p, '')}",
    )


# ─── Data laden ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner='Gegevens laden…')
def _laad(pad: str) -> pd.DataFrame:
    return laad_export(pad)


@st.cache_data(show_spinner='Gegevens laden…')
def _laad_bytes(naam: str, inhoud: bytes) -> pd.DataFrame:
    import io
    suffix = Path(naam).suffix.lower()
    if suffix in ('.xlsx', '.xls'):
        return laad_export(io.BytesIO(inhoud))
    else:
        return laad_export(io.StringIO(inhoud.decode('utf-8-sig', errors='replace')))


df_rauw: pd.DataFrame | None = None

if gebruik_sample and SAMPLE_PAD.exists():
    df_rauw = _laad(str(SAMPLE_PAD))
elif geupload is not None:
    df_rauw = _laad_bytes(geupload.name, geupload.read())

if df_rauw is None:
    st.info(
        'Laad een GL-export om te beginnen.  \n'
        'Gebruik de sidebar om een bestand te uploaden of de voorbeelddata te activeren.'
    )
    st.stop()

# ─── Kolomvalidatie ──────────────────────────────────────────────────────────
ok, ontbrekend = valideer_kolommen(df_rauw)
if not ok:
    st.error(
        f'De volgende vereiste kolommen ontbreken in het bestand: **{", ".join(ontbrekend)}**  \n'
        'Controleer de kolomnamen en pas `data_loader.py` aan waar nodig.'
    )
    with st.expander('Gevonden kolommen in het bestand'):
        st.write(list(df_rauw.columns))
    st.stop()

# ─── Filteren op jaar en periode ─────────────────────────────────────────────
df = df_rauw.copy()
if 'jaar' in df.columns:
    df = df[df['jaar'] == filter_jaar]
if filter_periodes and 'periode' in df.columns:
    df = df[df['periode'].isin(filter_periodes)]

if df.empty:
    st.warning('Geen boekingen gevonden voor de geselecteerde filters.')
    st.stop()

# ─── KPI-kaarten ─────────────────────────────────────────────────────────────
omzet     = bereken_omzet(df)
kosten    = bereken_kosten(df)
resultaat = bereken_resultaat(df)
bruto_pct = bruto_marge_pct(df)
netto_pct = netto_marge_pct(df)

st.subheader('Samenvatting')
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric('Omzet',           EURO(omzet))
k2.metric('Kosten',          EURO(kosten))
k3.metric('Resultaat',       EURO(resultaat),
          delta=EURO(resultaat),
          delta_color='normal' if resultaat >= 0 else 'inverse')
k4.metric('Brutomarge',      PCT(bruto_pct))
k5.metric('Nettomarge',      PCT(netto_pct))

st.divider()

# ─── Maandoverzicht ──────────────────────────────────────────────────────────
st.subheader('Maandoverzicht')

maand_df = resultaat_per_maand(df)

if not maand_df.empty:
    col_links, col_rechts = st.columns([2, 1])

    with col_links:
        fig = go.Figure()
        fig.add_bar(
            x=maand_df['maand'], y=maand_df['omzet'],
            name='Omzet', marker_color='#2196F3',
        )
        fig.add_bar(
            x=maand_df['maand'], y=maand_df['kosten'],
            name='Kosten', marker_color='#FF5722',
        )
        fig.add_scatter(
            x=maand_df['maand'], y=maand_df['resultaat'],
            name='Resultaat', mode='lines+markers',
            line=dict(color='#4CAF50', width=2),
        )
        fig.update_layout(
            barmode='group',
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            yaxis_tickformat='€,.0f',
            margin=dict(t=40, b=20),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_rechts:
        weergave = maand_df[['maand', 'omzet', 'kosten', 'resultaat']].copy()
        weergave['omzet']     = weergave['omzet'].map(EURO)
        weergave['kosten']    = weergave['kosten'].map(EURO)
        weergave['resultaat'] = weergave['resultaat'].map(EURO)
        weergave.columns = ['Maand', 'Omzet', 'Kosten', 'Resultaat']
        st.dataframe(weergave, use_container_width=True, hide_index=True)

st.divider()

# ─── Kostenverdeling ──────────────────────────────────────────────────────────
st.subheader('Kostenverdeling')

cat_df = kosten_per_categorie(df)

if not cat_df.empty:
    col_taart, col_top = st.columns(2)

    with col_taart:
        fig_pie = px.pie(
            cat_df, values='bedrag', names='categorie',
            title='Kosten naar categorie',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, margin=dict(t=40, b=20), height=380)
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
                xaxis_tickformat='€,.0f',
                yaxis_title='',
                margin=dict(t=40, b=20),
                height=380,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ─── Detailtabel ─────────────────────────────────────────────────────────────
with st.expander('Alle boekingen (ruwe data)'):
    weergave_kolommen = [c for c in ['datum', 'rekening', 'omschrijving', 'periode',
                                      'boekstuknummer', 'debet', 'credit', 'netto']
                         if c in df.columns]
    toon_df = df[weergave_kolommen].copy()
    for kolom in ('debet', 'credit', 'netto'):
        if kolom in toon_df.columns:
            toon_df[kolom] = toon_df[kolom].map(lambda x: f"{x:,.2f}")
    st.dataframe(toon_df, use_container_width=True, hide_index=True)

st.caption('Kurvers Groep — Limtrade B.V. (admin 516) · alleen voor intern gebruik')
