# app.py (versão robusta para evitar colunas inexistentes)
import pandas as pd
import numpy as np
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, ctx
import dash_bootstrap_components as dbc
from pathlib import Path

CSV_PATH = Path("ecommerce_estatistica.csv")
if not CSV_PATH.exists():
    raise FileNotFoundError("Coloque ecommerce_estatistica.csv na mesma pasta do app.py")

# lê amostra para ver colunas; se tem Unnamed:0 tenta como index
df_try = pd.read_csv(CSV_PATH, nrows=2)
if "Unnamed: 0" in df_try.columns:
    df = pd.read_csv(CSV_PATH, index_col=0)
else:
    df = pd.read_csv(CSV_PATH)

# função utilitária para encontrar colunas com variantes de nome
def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    # também tenta sem acentos/maiúsculas
    lowered = {col.lower(): col for col in df.columns}
    for c in candidates:
        if c.lower() in lowered:
            return lowered[c.lower()]
    return None

# mapeamento de colunas que usaremos (tente várias possibilidades)
nota_col = find_col(df, ["Nota", "nota", "Rating", "Avaliação", "Avaliacao"])
n_av_col = find_col(df, ["N_Avaliacoes", "N_Avaliações", "N_Avaliações_MinMax", "N_Avaliacoes_MinMax", "N_Avaliações"])
marca_col = find_col(df, ["Marca", "marca", "brand"])
categoria_col = find_col(df, ["Categoria", "categoria", "Subcategoria", "Categoria_Produto", "Categoria_Principal"])
desconto_col = find_col(df, ["Desconto", "desconto", "Desconto_MinMax"])
preco_col = find_col(df, ["Preco", "Preço", "preco", "Preco_MinMax", "Preço_MinMax"])

# se alguma coluna crítica estiver ausente, garante que exista com NaNs para não quebrar
if nota_col is None:
    df["Nota"] = np.nan
    nota_col = "Nota"
if n_av_col is None:
    # tenta também 'N_Avaliações' com acento; se não houver, cria coluna vazia
    df["N_Avaliacoes"] = np.nan
    n_av_col = "N_Avaliacoes"
if marca_col is None:
    df["Marca"] = "Desconhecida"
    marca_col = "Marca"
if preco_col is None:
    df["Preco"] = np.nan
    preco_col = "Preco"
if categoria_col is None:
    # se não existe categoria, usaremos marca como fallback nas opções
    categoria_col = None

# preparar opções do filtro
filter_fields = []
if categoria_col:
    filter_fields.append({"label":"Categoria", "value":"Categoria"})
filter_fields.append({"label":"Marca", "value":"Marca"})

# opções reais (para o segundo dropdown) — geraremos dinamicamente no callback
def options_for(field):
    if field == "Categoria" and categoria_col:
        vals = sorted(df[categoria_col].dropna().unique())
    elif field == "Marca":
        vals = sorted(df[marca_col].dropna().unique())
    else:
        vals = []
    return [{"label": v, "value": v} for v in vals]

# instancia app
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = dbc.Container([
    html.H1("Dashboard de Avaliações - E-commerce", className="text-center mt-4 mb-4"),

    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="filtro",
                options=filter_fields,
                value=filter_fields[0]["value"] if filter_fields else None,
                clearable=False
            ), md=4
        ),
        dbc.Col(
            dcc.Dropdown(id="opcao", options=[], value=None, placeholder="Selecione..."),
            md=8
        )
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="grafico_notas"), md=6),
        dbc.Col(dcc.Graph(id="grafico_avaliacoes"), md=6)
    ])
], fluid=True)

# callback para povoar 'opcao' de acordo com o filtro selecionado
@app.callback(
    Output("opcao", "options"),
    Output("opcao", "value"),
    Input("filtro", "value")
)
def atualizar_opcoes(filtro):
    if filtro == "Categoria" and categoria_col:
        opts = options_for("Categoria")
    elif filtro == "Marca":
        opts = options_for("Marca")
    else:
        opts = []
    val = opts[0]["value"] if opts else None
    # não forçar seleção — damos None para que o usuário escolha; mas podemos pré-selecionar
    return opts, None

# callback principal que atualiza os gráficos
@app.callback(
    Output("grafico_notas", "figure"),
    Output("grafico_avaliacoes", "figure"),
    Input("filtro", "value"),
    Input("opcao", "value")
)
def atualizar_graficos(filtro, opcao):
    # define df_filtrado
    dff = df.copy()
    if filtro == "Categoria" and categoria_col and opcao:
        dff = dff[dff[categoria_col] == opcao]
    elif filtro == "Marca" and opcao:
        dff = dff[dff[marca_col] == opcao]

    # gráfico notas (histograma)
    if dff[nota_col].dropna().empty:
        fig_notas = px.histogram(pd.DataFrame({nota_col:[]}), x=nota_col, title="Distribuição das Notas (sem dados)")
        fig_notas.update_layout(margin=dict(l=20,r=20,t=40,b=20))
    else:
        fig_notas = px.histogram(dff, x=nota_col, nbins=20, title="Distribuição das Notas")
        fig_notas.update_layout(margin=dict(l=20,r=20,t=40,b=20))

    # gráfico avaliações por marca
    if marca_col not in dff.columns or dff[marca_col].dropna().empty:
        fig_av = px.bar(pd.DataFrame({marca_col:[], n_av_col:[]}), x=marca_col, y=n_av_col, title="Avaliações por Marca (sem dados)")
    else:
        # se coluna de número de avaliações existir com nome diferente, usamos n_av_col mapeado
        # tentamos converter para numérico
        if n_av_col in dff.columns:
            dff[n_av_col] = pd.to_numeric(dff[n_av_col], errors="coerce")
            summary = dff.groupby(marca_col)[n_av_col].sum().reset_index().sort_values(n_av_col, ascending=False).head(30)
            if summary.empty:
                fig_av = px.bar(summary, x=marca_col, y=n_av_col, title="Avaliações por Marca (sem dados válidos)")
            else:
                fig_av = px.bar(summary, x=marca_col, y=n_av_col, title="Avaliações por Marca")
        else:
            fig_av = px.bar(pd.DataFrame({marca_col:[], "N_Avaliacoes":[]}), x=marca_col, y="N_Avaliacoes", title="Avaliações por Marca (sem dados)")

    fig_av.update_layout(margin=dict(l=20,r=20,t=40,b=20), xaxis_tickangle=-45)
    return fig_notas, fig_av

if __name__ == "__main__":
    app.run(debug=True)
