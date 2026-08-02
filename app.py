import os

import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html


# -------------------------------------------------------------------
# Datos analíticos calculados previamente
# Estos valores todavía no corresponden a la simulación.
# -------------------------------------------------------------------
resultados_analiticos = pd.DataFrame(
    {
        "Escenario": ["Sistema actual", "Sistema propuesto"],
        "Tiempo de espera": [4.657, 1.800],
    }
)


# -------------------------------------------------------------------
# Gráfico inicial
# -------------------------------------------------------------------
figura_espera = px.bar(
    resultados_analiticos,
    x="Escenario",
    y="Tiempo de espera",
    title="Tiempo promedio de espera en cola",
    labels={
        "Escenario": "Escenario",
        "Tiempo de espera": "Minutos",
    },
    text_auto=".2f",
)

figura_espera.update_layout(
    title_x=0.5,
    yaxis_title="Minutos",
)


# -------------------------------------------------------------------
# Aplicación Dash
# -------------------------------------------------------------------
app = Dash(__name__)

# Gunicorn utilizará este objeto para ejecutar la aplicación en Azure.
server = app.server


app.layout = html.Div(
    style={
        "fontFamily": "Arial, sans-serif",
        "maxWidth": "1100px",
        "margin": "0 auto",
        "padding": "30px",
        "backgroundColor": "#f7f8fa",
    },
    children=[
        html.H1(
            "Simulación de un sistema de colas M/M/1",
            style={
                "textAlign": "center",
                "marginBottom": "10px",
            },
        ),
        html.H2(
            "Caja principal de una heladería",
            style={
                "textAlign": "center",
                "fontWeight": "normal",
                "marginTop": "0",
            },
        ),
        html.Hr(),
        html.Div(
            style={
                "backgroundColor": "white",
                "padding": "20px",
                "marginTop": "25px",
                "borderRadius": "8px",
            },
            children=[
                html.H3("Estado del proyecto"),
                html.P(
                    "La aplicación Dash funciona correctamente. "
                    "La simulación de eventos discretos se incorporará "
                    "en la siguiente etapa."
                ),
            ],
        ),
        html.Div(
            style={
                "display": "flex",
                "gap": "20px",
                "marginTop": "20px",
                "flexWrap": "wrap",
            },
            children=[
                html.Div(
                    style={
                        "backgroundColor": "white",
                        "padding": "20px",
                        "borderRadius": "8px",
                        "flex": "1",
                        "minWidth": "240px",
                    },
                    children=[
                        html.H3("Sistema actual"),
                        html.P("λ = 21.8182 clientes por hora"),
                        html.P("μ = 30.9119 clientes por hora"),
                        html.P("Wq = 4.657 minutos"),
                    ],
                ),
                html.Div(
                    style={
                        "backgroundColor": "white",
                        "padding": "20px",
                        "borderRadius": "8px",
                        "flex": "1",
                        "minWidth": "240px",
                    },
                    children=[
                        html.H3("Sistema propuesto"),
                        html.P("λ = 21.8182 clientes por hora"),
                        html.P("μ = 40 clientes por hora"),
                        html.P("Wq = 1.800 minutos"),
                    ],
                ),
            ],
        ),
        html.Div(
            style={
                "backgroundColor": "white",
                "padding": "20px",
                "marginTop": "20px",
                "borderRadius": "8px",
            },
            children=[
                dcc.Graph(
                    id="grafico-espera",
                    figure=figura_espera,
                )
            ],
        ),
    ],
)


# -------------------------------------------------------------------
# Servidor de desarrollo
# Este bloque se utiliza en Codespaces, no en Azure.
# -------------------------------------------------------------------
if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8050))

    app.run(
        host="0.0.0.0",
        port=puerto,
        debug=True,
    )