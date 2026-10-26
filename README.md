# CryptoScope — Dashboard de criptomoedas

Painel em Streamlit com filtros por ativo e período, cinco KPIs, candles interativos,
volume, média móvel opcional de 20 registros, tabela expansível e exportação CSV.

## Executar

1. Extraia todo o ZIP, mantendo a pasta `.streamlit`.
2. Abra o terminal dentro da pasta que contém `app.py`.
3. Execute:

   python -m pip install -r requirements.txt
   python -m streamlit run app.py

Abra o endereço indicado pelo Streamlit (normalmente http://localhost:8501).
No Windows, também é possível abrir `iniciar.bat` após instalar o Python com a
opção Add Python to PATH. O script usa um ambiente virtual local.

## Seus dados

Coloque os CSVs junto ao app.py ou importe vários arquivos pela barra lateral.
Uploads têm prioridade sobre os arquivos locais na importação. Todos os dados
tratados são salvos automaticamente no SQLite e o painel consulta o histórico
acumulado do banco. Remova os uploads para voltar a importar os arquivos da pasta.
Alterações no conteúdo invalidam o cache de tratamento.
O nome do arquivo identifica o par: ETHBTC.csv, ADABTC.csv, SOLBTC.csv.
Use nomes sem sufixos de cópia ou descrições adicionais.

Colunas obrigatórias: date, open, high, low, close, volume.
Exemplo de conteúdo de ETHBTC.csv:

    date,open,high,low,close,volume
    2025-01-01,0.034,0.036,0.033,0.035,1200
    2025-01-02,0.035,0.038,0.034,0.037,1500

Use UTF-8, datas ISO (AAAA-MM-DD ou timestamps ISO) e ponto decimal.
Também é aceita vírgula decimal em arquivos separados por ponto e vírgula.
Separadores de milhares nos números não são suportados.

Sem CSVs e com o banco vazio, o painel abre com séries sintéticas, identificadas como
DEMONSTRAÇÃO. Elas não representam cotações reais e não são gravadas como CSVs.
Se os CSVs fornecidos forem inválidos, o erro é exibido sem substituí-los pela demonstração.

## Tratamento e cálculos

- Colunas sem espaços nas extremidades e em caixa baixa.
- Símbolo extraído do nome, em maiúsculas, conservando letras e números.
- Datas inválidas e fechamentos ausentes/inválidos são removidos.
- Datas com fuso são convertidas para UTC; datas sem fuso são interpretadas em UTC.
- Preços e volumes são float. Valores não numéricos e infinitos viram nulos.
- Duplicados por data e ativo: prevalece a última ocorrência na ordem dos arquivos
  (nome em ordem alfabética na pasta, ordem de upload na interface).
- Dados consolidados ordenados por data e ativo.
- Abertura, máxima, mínima ou volume ausentes permanecem na tabela. Os candles
  exigem OHLC completo. Não há preenchimento de preços nem remoção de outliers.
- Variação = (último fechamento / primeiro fechamento - 1) × 100. Com primeiro
  fechamento zero, a variação fica indisponível.
- Máxima/mínima usam high/low disponíveis. Volume total soma os volumes disponíveis;
  fica indisponível quando todos estão vazios. Unidades são as do CSV de origem.
- A média móvel usa 20 observações do histórico do ativo antes de aplicar o filtro
  de datas. Fica vazia até a 20ª observação; não significa necessariamente 20 dias.
- O intervalo inclui os dois dias selecionados, inclusive horários do dia final.

## Arquivos

app.py                  Interface, cache, filtros e visualizações.
data_processing.py      Leitura, limpeza e geração da demonstração sintética.
database.py             Criação, consulta e gravação do banco SQLite.
requirements.txt        Dependências.
.streamlit/config.toml  Tema do painel.
iniciar.bat             Inicializador para Windows.

Validação realizada com Python 3.10, pandas 2.3.3, Streamlit 1.50.0 e Plotly 7.1.0.
Foram verificados o tratamento de CSVs, duplicados, datas em formatos mistos e UTC,
infinitos, arquivos inválidos e a execução do app com troca de ativo, filtro de
período e ativação/desativação da média móvel usando Streamlit AppTest.


## Banco de dados SQLite

Não é necessário instalar um servidor nem uma biblioteca adicional: sqlite3 já
faz parte do Python. O arquivo `criptomoedas.db` é criado automaticamente junto
ao app.py. A pasta precisa permitir gravação.

Ao colocar CSVs na pasta ou enviar arquivos pela interface, o app limpa os dados
e salva o lote válido em uma transação. O painel mostra o histórico acumulado de
todos os ativos importados, mesmo depois de remover os CSVs ou fechar e reabrir o app.
Dados sintéticos de demonstração nunca são inseridos no banco.

A tabela `cotacoes` contém date, symbol, open, high, low, close e volume. A chave
primária composta (date, symbol) impede duplicatas. Um lote novo com a mesma data
e ativo atualiza os preços e o volume, incluindo campos opcionais vazios (NULL).
Registros antigos não presentes no novo CSV permanecem no histórico.

A tabela `importacoes` registra a assinatura SHA-256 dos nomes, ordem e conteúdo
dos arquivos, a quantidade de registros do lote e a data de importação (UTC).
Lotes idênticos são ignorados, inclusive ao mexer nos filtros ou reiniciar o app;
isso evita que um arquivo antigo sobrescreva correções importadas posteriormente.
Para corrigir valores, importe um CSV atualizado. A contagem exibida de registros
processados inclui tanto inserções quanto atualizações, não apenas linhas novas.

Arquivos inválidos exibem um erro sem apagar dados anteriores. Se um lote contiver
arquivos válidos e inválidos, os válidos são importados e os avisos são exibidos.
Para consultar o histórico após um erro de entrada, remova os uploads inválidos
ou retire/corrija os CSVs inválidos da pasta.

Para fazer backup, feche o painel e copie `criptomoedas.db`. Para restaurar, com o
painel fechado, coloque a cópia na pasta do app com esse mesmo nome. O banco é local
à instalação do aplicativo, não fica sincronizado entre computadores.

Testes adicionais: persistência após nova conexão e nova sessão do Streamlit,
atualização por data/ativo, reimportação idempotente, preservação de correções,
valores NULL, múltiplos ativos, entradas inválidas, filtro sem registros e isolamento
dos dados de demonstração. Nenhum dado de teste é incluído no pacote.
