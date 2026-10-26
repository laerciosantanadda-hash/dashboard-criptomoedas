"""Persistência local SQLite; importações atômicas e sem duplicação."""
import hashlib
import sqlite3
from contextlib import closing
import pandas as pd

COLUNAS = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']


def conectar(caminho):
    con = sqlite3.connect(str(caminho), timeout=30)
    try:
        con.executescript('''
            CREATE TABLE IF NOT EXISTS cotacoes (
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                open REAL, high REAL, low REAL,
                close REAL NOT NULL, volume REAL,
                PRIMARY KEY (date, symbol)
            );
            CREATE INDEX IF NOT EXISTS idx_cotacoes_symbol_date ON cotacoes(symbol, date);
            CREATE TABLE IF NOT EXISTS importacoes (
                assinatura TEXT PRIMARY KEY,
                registros INTEGER NOT NULL,
                importado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        return con
    except Exception:
        con.close()
        raise


def assinatura_fontes(fontes):
    """Inclui ordem, nomes e conteúdo; uploads iguais não sobrescrevem correções."""
    digest = hashlib.sha256()
    for nome, conteudo in fontes:
        for parte in (nome.encode('utf-8'), conteudo):
            digest.update(len(parte).to_bytes(8, 'big'))
            digest.update(parte)
    return digest.hexdigest()


def salvar_importacao(caminho, dados, assinatura):
    """Insere/atualiza por data e ativo. Retorna False se lote já importado.

    O lote e seu registro são gravados na mesma transação. Dados nulos opcionais
    são armazenados como NULL. A conexão não é compartilhada entre sessões.
    """
    if dados.empty:
        raise ValueError('Não é possível salvar uma importação vazia.')
    linhas = []
    for linha in dados[COLUNAS].itertuples(index=False, name=None):
        data, symbol, *valores = linha
        if pd.isna(data) or pd.isna(valores[3]) or not symbol:
            raise ValueError('Data, ativo e fechamento são obrigatórios.')
        linhas.append((pd.Timestamp(data).isoformat(), str(symbol),
                       *(None if pd.isna(v) else float(v) for v in valores)))
    with closing(conectar(caminho)) as con:
        with con:
            # Serializa importações concorrentes antes de consultar a assinatura.
            con.execute('BEGIN IMMEDIATE')
            if con.execute('SELECT 1 FROM importacoes WHERE assinatura = ?', (assinatura,)).fetchone():
                return False
            con.executemany('''
                INSERT INTO cotacoes(date, symbol, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, symbol) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume
            ''', linhas)
            con.execute('INSERT INTO importacoes(assinatura, registros) VALUES (?, ?)',
                        (assinatura, len(linhas)))
    return True


def ler_dados(caminho):
    with closing(conectar(caminho)) as con:
        dados = pd.read_sql_query('SELECT date, symbol, open, high, low, close, volume FROM cotacoes ORDER BY date, symbol', con)
    dados['date'] = pd.to_datetime(dados['date'], format='mixed', utc=True).dt.tz_localize(None)
    for coluna in ['open', 'high', 'low', 'close', 'volume']:
        dados[coluna] = dados[coluna].astype(float)
    return dados
