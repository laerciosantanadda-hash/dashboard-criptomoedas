from pathlib import Path
import sqlite3
from html import escape
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from data_processing import tratar_fontes, dados_demonstracao
from database import assinatura_fontes, salvar_importacao, ler_dados

PASTA = Path(__file__).resolve().parent
BANCO = PASTA / 'criptomoedas.db'
st.set_page_config(page_title='CryptoScope | Mercado em perspectiva', page_icon='◈', layout='wide')
st.markdown('''<style>
.block-container{padding-top:2rem;padding-bottom:2rem;max-width:1550px}
[data-testid="stAppViewContainer"]{background:radial-gradient(ellipse at 85% 0%,#153246 0%,#09111e 52%)}
[data-testid="stSidebar"]{background:#0d1828;border-right:1px solid #233247}
h1{letter-spacing:-1.6px!important;font-weight:750!important} h3{letter-spacing:-.5px}
[data-testid="stMetric"]{background:#111e30;border:1px solid #26384d;border-radius:14px;padding:20px 16px;min-height:125px}
[data-testid="stMetricLabel"]{color:#9eafc5} [data-testid="stMetricValue"]{font-size:1.65rem}
.eyebrow{color:#51dfbd;font-size:12px;letter-spacing:3px;font-weight:700}
.subtitle{color:#9eafc5;margin-top:-10px;margin-bottom:24px}
.pill{display:inline-block;padding:5px 12px;border-radius:20px;background:#173748;color:#76e5c9;font-size:12px}
</style>''', unsafe_allow_html=True)

@st.cache_data(show_spinner='Tratando os dados…')
def carregar(fontes):
    return tratar_fontes(fontes)


def numero(valor, casas=8):
    if pd.isna(valor):
        return '—'
    texto = f'{valor:,.{casas}f}'.rstrip('0').rstrip('.') if casas else f'{valor:,.0f}'
    return texto.translate(str.maketrans({',':'.', '.':','}))


with st.sidebar:
    st.markdown('## ◈ CryptoScope')
    st.caption('SEU OBSERVATÓRIO DE CRIPTOMOEDAS')
    st.divider()
    uploads = st.file_uploader('Importar arquivos CSV', type=['csv'], accept_multiple_files=True,
        help='O nome identifica o par: ETHBTC.csv, ADABTC.csv… Os arquivos selecionados são tratados e salvos automaticamente no banco local.')
    arquivos = sorted(p for p in PASTA.iterdir() if p.is_file() and p.suffix.lower() == '.csv')
    fontes = tuple((u.name, u.getvalue()) for u in uploads) if uploads else tuple((p.name, p.read_bytes()) for p in arquivos)
    avisos = []
    try:
        if fontes:
            importados, avisos = carregar(fontes)
            novo_lote = salvar_importacao(BANCO, importados, assinatura_fontes(fontes))
            if novo_lote:
                st.success(f'{len(importados)} registro(s) processado(s) e salvo(s) no SQLite.')
            else:
                st.caption('Esses arquivos já foram importados. Dados preservados no banco.')
        dados = ler_dados(BANCO)
    except ValueError as erro:
        st.error(str(erro))
        st.info('Use as colunas date, open, high, low, close e volume. Remova os uploads inválidos para consultar o banco.')
        st.stop()
    except (sqlite3.Error, OSError) as erro:
        st.error(f'Não foi possível acessar o banco SQLite: {erro}')
        st.info('Verifique se a pasta do projeto permite gravação e se há espaço em disco.')
        st.stop()
    demo = dados.empty
    if demo:
        dados = dados_demonstracao()
    st.caption('Banco local: criptomoedas.db')
    if not demo:
        st.caption(f'{len(dados):,} registro(s) persistido(s) · {dados.symbol.nunique()} ativo(s)')
    ativo = st.selectbox('Par de negociação', sorted(dados.symbol.unique()))
    base = dados.loc[dados.symbol == ativo].copy()
    minimo, maximo = base.date.min().date(), base.date.max().date()
    periodo = st.date_input('Intervalo de análise', (minimo, maximo), min_value=minimo, max_value=maximo,
        format='DD/MM/YYYY', key=f'datas_{ativo}_{minimo}_{maximo}')
    st.divider()
    st.markdown('**Indicadores no gráfico**')
    mostrar_media = st.toggle('Média móvel · 20 registros', value=True)
    st.caption('A média usa o histórico anterior ao filtro, com janela de 20 registros válidos.')
    st.divider()
    st.caption('Fonte: ' + ('demonstração sintética' if demo else 'banco SQLite · histórico acumulado'))
    st.caption('Datas normalizadas em UTC. Preços na moeda de cotação do par; volume na unidade informada no CSV.')

st.markdown('<div class="eyebrow">MARKET ANALYTICS / DASHBOARD</div>', unsafe_allow_html=True)
st.title('O mercado, em perspectiva.')
st.markdown('<p class="subtitle">Explore o histórico, acompanhe tendências e entenda cada movimento.</p>', unsafe_allow_html=True)
if demo:
    st.info('MODO DEMONSTRAÇÃO • Dados sintéticos, sem cotações reais. Importe seus CSVs para salvar e analisar seus dados. A demonstração não é gravada no banco.')
if avisos:
    with st.expander(f'Qualidade dos dados · {len(avisos)} aviso(s)'):
        for aviso in avisos:
            st.write(aviso)
if len(periodo) != 2:
    st.info('Selecione a data final para visualizar o período.')
    st.stop()
inicio, fim = periodo
base['MM20'] = base.close.rolling(20, min_periods=20).mean()
df = base.loc[(base.date.dt.date >= inicio) & (base.date.dt.date <= fim)].copy()
if df.empty:
    st.warning('Não há registros nesse intervalo. Ajuste as datas na barra lateral.')
    st.stop()
st.markdown(f'### {escape(ativo)} <span class="pill">{len(df):,} registros · {inicio:%d/%m/%Y} → {fim:%d/%m/%Y}</span>', unsafe_allow_html=True)
primeiro, ultimo = df.close.iloc[0], df.close.iloc[-1]
variacao = (ultimo / primeiro - 1) * 100 if primeiro != 0 else None
cards = st.columns(5)
cards[0].metric('Último fechamento', numero(ultimo))
cards[1].metric('Variação no período', '—' if variacao is None else f'{variacao:+.2f}%'.replace('.', ','))
cards[2].metric('Máxima do período', numero(df.high.max()))
cards[3].metric('Mínima do período', numero(df.low.min()))
cards[4].metric('Volume total', numero(df.volume.sum(min_count=1), 2))
st.caption('Variação entre o primeiro e o último fechamento do intervalo selecionado. Máxima e mínima usam os valores disponíveis.')
tab_grafico, tab_resumo = st.tabs(['Visão de mercado', 'Resumo do período'])
with tab_grafico:
    validos = df.dropna(subset=['open', 'high', 'low', 'close'])
    if len(validos) != len(df):
        st.warning(f'{len(df) - len(validos)} registro(s) sem OHLC completo foram omitidos dos candles.')
    if validos.empty:
        st.info('Não há preços OHLC completos para desenhar candles.')
    else:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.05, row_heights=[.77,.23])
        fig.add_trace(go.Candlestick(x=validos.date, open=validos.open, high=validos.high, low=validos.low,
            close=validos.close, name=ativo, increasing_line_color='#51dfbd', decreasing_line_color='#fa7188'), row=1, col=1)
        if mostrar_media:
            fig.add_trace(go.Scatter(x=df.date, y=df.MM20, name='MM20', line=dict(color='#e6b969', width=2)), row=1, col=1)
        fig.add_trace(go.Bar(x=df.date, y=df.volume, name='Volume', marker_color='#426d99', opacity=.75), row=2, col=1)
        fig.update_layout(template='plotly_dark', height=580, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10,r=15,t=35,b=10), xaxis_rangeslider_visible=False,
            legend=dict(orientation='h', y=1.08, x=0), font=dict(color='#aebed2'), hovermode='x unified')
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor='#203047', side='right', title_text='Preço', row=1,col=1)
        fig.update_yaxes(gridcolor='#203047', side='right', title_text='Volume', row=2,col=1)
        st.plotly_chart(fig, use_container_width=True, config={'displaylogo':False})
with tab_resumo:
    a,b,c = st.columns(3)
    a.metric('Fechamento médio', numero(df.close.mean()))
    b.metric('Primeiro fechamento', numero(primeiro))
    c.metric('Registros com OHLC completo', str(len(df.dropna(subset=['open','high','low','close']))))
    st.write('O tratamento remove datas e fechamentos inválidos e mantém a última ocorrência de cada data e ativo. Campos numéricos inválidos ficam vazios. Não há interpolação nem exclusão automática de outliers.')
with st.expander('Explorar e baixar os dados tratados'):
    tabela = df[['date','symbol','open','high','low','close','volume']]
    st.dataframe(tabela, width='stretch', hide_index=True)
    st.download_button('↓ Baixar CSV do período', tabela.to_csv(index=False).encode('utf-8-sig'),
        file_name=f'{ativo}_{inicio}_{fim}.csv', mime='text/csv')
st.caption('◈ CryptoScope · Análise histórica de dados OHLCV · Sem atualização de cotações em tempo real')


