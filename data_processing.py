"""Leitura e normalização de dados OHLCV."""
from pathlib import Path
from io import BytesIO
import re
import csv
import numpy as np
import pandas as pd

REQUIRED = ['date', 'open', 'high', 'low', 'close', 'volume']


def tratar_fontes(fontes):
    tabelas, avisos = [], []
    for nome, conteudo in fontes:
        try:
            df = pd.read_csv(BytesIO(conteudo), sep=None, engine='python', encoding='utf-8-sig')
            df.columns = df.columns.str.strip().str.lower()
            if df.columns.duplicated().any():
                raise ValueError('colunas repetidas após padronização')
            faltando = set(REQUIRED) - set(df.columns)
            if faltando:
                raise ValueError('colunas ausentes: ' + ', '.join(sorted(faltando)))
            df = df[REQUIRED].copy()
            df['date'] = pd.to_datetime(df['date'], errors='coerce', utc=True, format='mixed').dt.tz_localize(None)
            for coluna in REQUIRED[1:]:
                valores = df[coluna].astype(str).str.strip().str.replace(',', '.', regex=False)
                df[coluna] = pd.to_numeric(valores, errors='coerce').replace([np.inf, -np.inf], np.nan).astype(float)
            symbol = re.sub(r'[^A-Z0-9]', '', Path(nome).stem.upper())
            if not symbol:
                raise ValueError('nome sem código de ativo')
            df['symbol'] = symbol
            antes = len(df)
            df = df.dropna(subset=['date', 'close'])
            if antes != len(df):
                avisos.append(f'{nome}: {antes - len(df)} linha(s) removida(s) por data ou fechamento inválido.')
            if df.empty:
                avisos.append(f'{nome}: nenhum registro válido.')
            else:
                tabelas.append(df)
        except (ValueError, UnicodeError, OSError, pd.errors.ParserError, csv.Error) as erro:
            avisos.append(f'{nome}: {erro}')
    if not tabelas:
        raise ValueError('Nenhum registro válido encontrado. ' + ' | '.join(avisos))
    dados = pd.concat(tabelas, ignore_index=True)
    duplicados = dados.duplicated(['date', 'symbol'], keep='last')
    if duplicados.any():
        avisos.append(f'{int(duplicados.sum())} duplicado(s) removido(s); mantida a última ocorrência por data e ativo.')
    return dados.loc[~duplicados].sort_values(['date', 'symbol']).reset_index(drop=True), avisos


def carregar_dados(pasta='.'):
    arquivos = sorted(p for p in Path(pasta).iterdir() if p.is_file() and p.suffix.lower() == '.csv')
    if not arquivos:
        raise ValueError('Nenhum CSV encontrado na pasta do projeto.')
    return tratar_fontes([(p.name, p.read_bytes()) for p in arquivos])


def dados_demonstracao():
    """Série sintética reproduzível, sem cotações reais."""
    rng = np.random.default_rng(42)
    tabelas = []
    for symbol, preco in [('ETHBTC', .045), ('ADABTC', .000008), ('SOLBTC', .0021)]:
        datas = pd.date_range('2025-01-01', periods=180, freq='D')
        close = preco * np.exp(np.cumsum(rng.normal(.001, .025, len(datas))))
        abertura = np.r_[preco, close[:-1]]
        tabelas.append(pd.DataFrame(dict(date=datas, open=abertura,
            high=np.maximum(abertura, close) * (1 + rng.uniform(.002, .025, len(datas))),
            low=np.minimum(abertura, close) * (1 - rng.uniform(.002, .025, len(datas))),
            close=close, volume=rng.uniform(1000, 40000, len(datas)), symbol=symbol)))
    return pd.concat(tabelas).sort_values(['date', 'symbol']).reset_index(drop=True)

