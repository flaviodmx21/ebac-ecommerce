import pandas as pd
from dash import Dash, html, dcc
import plotly.express as px

# Carrega o dataset
df = pd.read_csv("ecommerce_estatistica.csv")

# Cria os gráficos
fig_hist = px.histogram(df, x="Nota", title="Distribuição das Notas")

fig_bar = px.bar(
    df.groupby("Marca")["N_Avaliações"].sum().reset_index(),
    x="Marca",
    y="N_Avaliações",
    title="Avaliações por Marca"
)

# App Dash
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Dashboard de E-commerce"),

    html.H2("Distribuição das Notas"),
    dcc.Graph(figure=fig_hist),

    html.H2("Avaliações por Marca"),
    dcc.Graph(figure=fig_bar),
])

if __name__ == "__main__":
    app.run(debug=True)
