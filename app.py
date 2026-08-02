import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import (
    Dash,
    Input,
    Output,
    State,
    dash_table,
    dcc,
    html,
)

from simulacion.modelo_mm1 import (
    indicadores_teoricos,
    simular_replicaciones,
)


app = Dash(__name__)

# Objeto que utilizará Gunicorn en Azure.
server = app.server


def tarjeta(titulo: str, componente) -> html.Div:
    return html.Div(
        [
            html.H3(
                titulo,
                style={"marginTop": "0"},
            ),
            componente,
        ],
        style={
            "backgroundColor": "white",
            "padding": "18px",
            "borderRadius": "10px",
            "boxShadow": (
                "0 2px 8px rgba(0, 0, 0, 0.08)"
            ),
        },
    )


app.layout = html.Div(
    [
        html.H1(
            "Simulación de un sistema de colas M/M/1",
            style={
                "textAlign": "center",
                "marginBottom": "5px",
            },
        ),
        html.P(
            "Caja principal de una heladería",
            style={
                "textAlign": "center",
                "fontSize": "18px",
            },
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label(
                            "Tasa de llegada λ (clientes/h)"
                        ),
                        dcc.Input(
                            id="lambda-hora",
                            type="number",
                            value=21.8182,
                            min=0.01,
                            step=0.0001,
                            style={"width": "100%"},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Label(
                            "Tasa de servicio actual μ "
                            "(clientes/h)"
                        ),
                        dcc.Input(
                            id="mu-actual",
                            type="number",
                            value=30.9119,
                            min=0.01,
                            step=0.0001,
                            style={"width": "100%"},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Label(
                            "Tasa de servicio propuesta μ "
                            "(clientes/h)"
                        ),
                        dcc.Input(
                            id="mu-propuesto",
                            type="number",
                            value=40,
                            min=0.01,
                            step=0.0001,
                            style={"width": "100%"},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Label(
                            "Clientes por réplica"
                        ),
                        dcc.Input(
                            id="clientes-replica",
                            type="number",
                            value=5000,
                            min=100,
                            step=100,
                            style={"width": "100%"},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Label(
                            "Número de réplicas"
                        ),
                        dcc.Input(
                            id="replicas",
                            type="number",
                            value=10,
                            min=1,
                            max=30,
                            step=1,
                            style={"width": "100%"},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Label("Semilla"),
                        dcc.Input(
                            id="semilla",
                            type="number",
                            value=2026,
                            step=1,
                            style={"width": "100%"},
                        ),
                    ]
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": (
                    "repeat(auto-fit, "
                    "minmax(210px, 1fr))"
                ),
                "gap": "15px",
                "marginBottom": "18px",
            },
        ),
        html.Button(
            "Ejecutar simulación",
            id="boton-simular",
            n_clicks=0,
            style={
                "padding": "12px 22px",
                "fontSize": "16px",
                "cursor": "pointer",
            },
        ),
        html.Div(
            id="mensaje",
            style={
                "marginTop": "15px",
                "fontWeight": "bold",
            },
        ),
        html.Div(
            [
                tarjeta(
                    "Indicadores comparativos",
                    dash_table.DataTable(
                        id="tabla-indicadores",
                        columns=[
                            {
                                "name": "Indicador",
                                "id": "Indicador",
                            },
                            {
                                "name": "Actual teórico",
                                "id": "Actual teórico",
                            },
                            {
                                "name": "Actual simulado",
                                "id": "Actual simulado",
                            },
                            {
                                "name": "Propuesto teórico",
                                "id": "Propuesto teórico",
                            },
                            {
                                "name": "Propuesto simulado",
                                "id": "Propuesto simulado",
                            },
                        ],
                        data=[],
                        style_table={
                            "overflowX": "auto"
                        },
                        style_cell={
                            "fontFamily": "Arial",
                            "padding": "8px",
                            "textAlign": "center",
                        },
                        style_header={
                            "fontWeight": "bold"
                        },
                    ),
                ),
                tarjeta(
                    "Comparación de tiempos",
                    dcc.Graph(
                        id="grafico-comparacion"
                    ),
                ),
                tarjeta(
                    "Evolución de la cola",
                    dcc.Graph(
                        id="grafico-cola"
                    ),
                ),
                tarjeta(
                    "Distribución de los tiempos de espera",
                    dcc.Graph(
                        id="grafico-distribucion"
                    ),
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "1fr",
                "gap": "20px",
                "marginTop": "20px",
            },
        ),
    ],
    style={
        "fontFamily": "Arial, sans-serif",
        "maxWidth": "1200px",
        "margin": "0 auto",
        "padding": "25px",
        "backgroundColor": "#f5f6f8",
    },
)


def reducir_eventos(
    eventos: pd.DataFrame,
    max_puntos: int = 2500,
) -> pd.DataFrame:
    """
    Reduce los puntos enviados al navegador para evitar
    gráficos excesivamente pesados.
    """

    paso = max(
        len(eventos) // max_puntos,
        1,
    )

    reducido = eventos.iloc[::paso].copy()

    if reducido.index[-1] != eventos.index[-1]:
        reducido = pd.concat(
            [
                reducido,
                eventos.iloc[[-1]],
            ],
            ignore_index=True,
        )

    return reducido


@app.callback(
    Output("mensaje", "children"),
    Output("tabla-indicadores", "data"),
    Output("grafico-comparacion", "figure"),
    Output("grafico-cola", "figure"),
    Output("grafico-distribucion", "figure"),
    Input("boton-simular", "n_clicks"),
    State("lambda-hora", "value"),
    State("mu-actual", "value"),
    State("mu-propuesto", "value"),
    State("clientes-replica", "value"),
    State("replicas", "value"),
    State("semilla", "value"),
)
def actualizar_dashboard(
    n_clicks,
    lambda_hora,
    mu_actual,
    mu_propuesto,
    clientes_replica,
    replicas,
    semilla,
):
    try:
        lambda_hora = float(lambda_hora)
        mu_actual = float(mu_actual)
        mu_propuesto = float(mu_propuesto)
        clientes_replica = int(clientes_replica)
        replicas = int(replicas)
        semilla = int(semilla)

        teorico_actual = indicadores_teoricos(
            lambda_hora,
            mu_actual,
        )

        teorico_propuesto = indicadores_teoricos(
            lambda_hora,
            mu_propuesto,
        )

        (
            clientes_actual,
            eventos_actual,
            _,
            sim_actual,
        ) = simular_replicaciones(
            lambda_hora=lambda_hora,
            mu_hora=mu_actual,
            n_clientes=clientes_replica,
            replicas=replicas,
            semilla_base=semilla,
        )

        (
            clientes_propuesto,
            eventos_propuesto,
            _,
            sim_propuesto,
        ) = simular_replicaciones(
            lambda_hora=lambda_hora,
            mu_hora=mu_propuesto,
            n_clientes=clientes_replica,
            replicas=replicas,
            semilla_base=semilla + 1000,
        )

        indicadores = [
            (
                "Utilización (%)",
                "rho",
                100,
            ),
            (
                "Clientes en el sistema",
                "Ls",
                1,
            ),
            (
                "Clientes en cola",
                "Lq",
                1,
            ),
            (
                "Tiempo en el sistema (min)",
                "Ws_min",
                1,
            ),
            (
                "Tiempo en cola (min)",
                "Wq_min",
                1,
            ),
            (
                "Sistema ocioso (%)",
                "P0",
                100,
            ),
        ]

        tabla = []

        for nombre, clave, factor in indicadores:
            tabla.append(
                {
                    "Indicador": nombre,
                    "Actual teórico": round(
                        teorico_actual[clave]
                        * factor,
                        3,
                    ),
                    "Actual simulado": round(
                        sim_actual[clave]
                        * factor,
                        3,
                    ),
                    "Propuesto teórico": round(
                        teorico_propuesto[clave]
                        * factor,
                        3,
                    ),
                    "Propuesto simulado": round(
                        sim_propuesto[clave]
                        * factor,
                        3,
                    ),
                }
            )

        comparacion = pd.DataFrame(
            [
                {
                    "Categoría": "Actual - Wq",
                    "Origen": "Teórico",
                    "Minutos": (
                        teorico_actual["Wq_min"]
                    ),
                },
                {
                    "Categoría": "Actual - Wq",
                    "Origen": "Simulado",
                    "Minutos": (
                        sim_actual["Wq_min"]
                    ),
                },
                {
                    "Categoría": "Actual - Ws",
                    "Origen": "Teórico",
                    "Minutos": (
                        teorico_actual["Ws_min"]
                    ),
                },
                {
                    "Categoría": "Actual - Ws",
                    "Origen": "Simulado",
                    "Minutos": (
                        sim_actual["Ws_min"]
                    ),
                },
                {
                    "Categoría": "Propuesto - Wq",
                    "Origen": "Teórico",
                    "Minutos": (
                        teorico_propuesto["Wq_min"]
                    ),
                },
                {
                    "Categoría": "Propuesto - Wq",
                    "Origen": "Simulado",
                    "Minutos": (
                        sim_propuesto["Wq_min"]
                    ),
                },
                {
                    "Categoría": "Propuesto - Ws",
                    "Origen": "Teórico",
                    "Minutos": (
                        teorico_propuesto["Ws_min"]
                    ),
                },
                {
                    "Categoría": "Propuesto - Ws",
                    "Origen": "Simulado",
                    "Minutos": (
                        sim_propuesto["Ws_min"]
                    ),
                },
            ]
        )

        figura_comparacion = px.bar(
            comparacion,
            x="Categoría",
            y="Minutos",
            color="Origen",
            barmode="group",
            text_auto=".2f",
            title=(
                "Resultados teóricos y simulados"
            ),
        )

        figura_comparacion.update_layout(
            title_x=0.5
        )

        cola_actual = reducir_eventos(
            eventos_actual
        )

        cola_actual["Escenario"] = (
            "Sistema actual"
        )

        cola_propuesta = reducir_eventos(
            eventos_propuesto
        )

        cola_propuesta["Escenario"] = (
            "Sistema propuesto"
        )

        cola = pd.concat(
            [
                cola_actual,
                cola_propuesta,
            ],
            ignore_index=True,
        )

        figura_cola = px.line(
            cola,
            x="tiempo_min",
            y="clientes_cola",
            color="Escenario",
            title=(
                "Longitud de la cola durante "
                "la primera réplica"
            ),
            labels={
                "tiempo_min": (
                    "Tiempo simulado (min)"
                ),
                "clientes_cola": (
                    "Clientes en cola"
                ),
            },
        )

        figura_cola.update_traces(
            line_shape="hv"
        )

        figura_cola.update_layout(
            title_x=0.5
        )

        esperas = pd.concat(
            [
                clientes_actual[
                    ["espera_min"]
                ].assign(
                    Escenario="Sistema actual"
                ),
                clientes_propuesto[
                    ["espera_min"]
                ].assign(
                    Escenario=(
                        "Sistema propuesto"
                    )
                ),
            ],
            ignore_index=True,
        )

        figura_distribucion = px.histogram(
            esperas,
            x="espera_min",
            color="Escenario",
            nbins=50,
            barmode="overlay",
            opacity=0.65,
            title=(
                "Distribución de los tiempos "
                "de espera"
            ),
            labels={
                "espera_min": (
                    "Tiempo de espera (min)"
                )
            },
        )

        figura_distribucion.update_layout(
            title_x=0.5
        )

        mensaje = (
            f"Simulación completada: "
            f"{replicas} réplicas de "
            f"{clientes_replica:,} clientes "
            f"por escenario."
        )

        return (
            mensaje,
            tabla,
            figura_comparacion,
            figura_cola,
            figura_distribucion,
        )

    except (TypeError, ValueError) as error:
        figura_vacia = go.Figure()

        figura_vacia.update_layout(
            title=(
                "No fue posible ejecutar "
                "la simulación"
            )
        )

        return (
            f"Error: {error}",
            [],
            figura_vacia,
            figura_vacia,
            figura_vacia,
        )


if __name__ == "__main__":
    puerto = int(
        os.environ.get("PORT", 8050)
    )

    app.run(
        host="0.0.0.0",
        port=puerto,
        debug=True,
    )