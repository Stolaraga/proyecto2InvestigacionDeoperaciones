from __future__ import annotations

import numpy as np
import pandas as pd


def validar_parametros(
    lambda_hora: float,
    mu_hora: float,
    n_clientes: int,
    replicas: int,
) -> None:
    """
    Verifica que los parámetros permitan ejecutar un modelo M/M/1 estable.
    """

    if lambda_hora <= 0 or mu_hora <= 0:
        raise ValueError("λ y μ deben ser mayores que cero.")

    if lambda_hora >= mu_hora:
        raise ValueError(
            "El sistema no es estable: debe cumplirse λ < μ."
        )

    if n_clientes < 100:
        raise ValueError(
            "Use al menos 100 clientes por réplica."
        )

    if replicas < 1:
        raise ValueError(
            "Debe ejecutar al menos una réplica."
        )


def indicadores_teoricos(
    lambda_hora: float,
    mu_hora: float,
) -> dict[str, float]:
    """
    Calcula los indicadores analíticos del modelo M/M/1.
    """

    validar_parametros(
        lambda_hora=lambda_hora,
        mu_hora=mu_hora,
        n_clientes=100,
        replicas=1,
    )

    rho = lambda_hora / mu_hora

    return {
        "rho": rho,
        "Ls": lambda_hora / (mu_hora - lambda_hora),
        "Lq": (
            lambda_hora**2
            / (mu_hora * (mu_hora - lambda_hora))
        ),
        "Ws_min": 60 / (mu_hora - lambda_hora),
        "Wq_min": (
            60
            * lambda_hora
            / (mu_hora * (mu_hora - lambda_hora))
        ),
        "P0": 1 - rho,
    }


def simular_una_corrida(
    lambda_hora: float,
    mu_hora: float,
    n_clientes: int,
    semilla: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    """
    Simula una corrida de un sistema M/M/1 con disciplina FIFO.
    """

    validar_parametros(
        lambda_hora=lambda_hora,
        mu_hora=mu_hora,
        n_clientes=n_clientes,
        replicas=1,
    )

    generador = np.random.default_rng(semilla)

    # Los tiempos se trabajan en minutos.
    media_interarribo = 60 / lambda_hora
    media_servicio = 60 / mu_hora

    tiempos_interarribo = generador.exponential(
        scale=media_interarribo,
        size=n_clientes,
    )

    tiempos_servicio = generador.exponential(
        scale=media_servicio,
        size=n_clientes,
    )

    # Tiempo acumulado de llegada de cada cliente.
    llegadas = np.cumsum(tiempos_interarribo)

    inicios_servicio = np.empty(n_clientes)
    salidas = np.empty(n_clientes)

    for indice in range(n_clientes):
        if indice == 0:
            inicios_servicio[indice] = llegadas[indice]
        else:
            inicios_servicio[indice] = max(
                llegadas[indice],
                salidas[indice - 1],
            )

        salidas[indice] = (
            inicios_servicio[indice]
            + tiempos_servicio[indice]
        )

    tiempos_espera = inicios_servicio - llegadas
    tiempos_sistema = salidas - llegadas

    clientes = pd.DataFrame(
        {
            "cliente": np.arange(1, n_clientes + 1),
            "interarribo_min": tiempos_interarribo,
            "llegada_min": llegadas,
            "servicio_min": tiempos_servicio,
            "inicio_servicio_min": inicios_servicio,
            "espera_min": tiempos_espera,
            "salida_min": salidas,
            "tiempo_sistema_min": tiempos_sistema,
        }
    )

    # Se construye la secuencia de eventos para calcular
    # la cantidad de clientes en el sistema y en la cola.
    eventos = pd.concat(
        [
            pd.DataFrame(
                {
                    "tiempo_min": llegadas,
                    "evento": "Llegada",
                    "prioridad": 1,
                }
            ),
            pd.DataFrame(
                {
                    "tiempo_min": salidas,
                    "evento": "Salida",
                    "prioridad": 0,
                }
            ),
        ],
        ignore_index=True,
    )

    eventos = eventos.sort_values(
        ["tiempo_min", "prioridad"],
        kind="mergesort",
    ).reset_index(drop=True)

    clientes_sistema = 0
    area_sistema = 0.0
    area_cola = 0.0
    area_ocupado = 0.0
    tiempo_anterior = 0.0
    cola_maxima = 0

    registros_eventos = []

    for evento in eventos.itertuples(index=False):
        intervalo = evento.tiempo_min - tiempo_anterior

        area_sistema += clientes_sistema * intervalo

        clientes_cola_antes = max(
            clientes_sistema - 1,
            0,
        )

        area_cola += clientes_cola_antes * intervalo

        if clientes_sistema > 0:
            area_ocupado += intervalo

        if evento.evento == "Llegada":
            clientes_sistema += 1
        else:
            clientes_sistema -= 1

        clientes_cola = max(
            clientes_sistema - 1,
            0,
        )

        cola_maxima = max(
            cola_maxima,
            clientes_cola,
        )

        registros_eventos.append(
            (
                evento.tiempo_min,
                evento.evento,
                clientes_sistema,
                clientes_cola,
            )
        )

        tiempo_anterior = evento.tiempo_min

    eventos_estado = pd.DataFrame(
        registros_eventos,
        columns=[
            "tiempo_min",
            "evento",
            "clientes_sistema",
            "clientes_cola",
        ],
    )

    horizonte_simulacion = salidas[-1]

    utilizacion = area_ocupado / horizonte_simulacion

    metricas = {
        "rho": utilizacion,
        "Ls": area_sistema / horizonte_simulacion,
        "Lq": area_cola / horizonte_simulacion,
        "Ws_min": float(tiempos_sistema.mean()),
        "Wq_min": float(tiempos_espera.mean()),
        "P0": 1 - utilizacion,
        "espera_max_min": float(tiempos_espera.max()),
        "cola_max": float(cola_maxima),
        "porcentaje_sin_espera": float(
            np.isclose(tiempos_espera, 0.0).mean()
            * 100
        ),
        "tasa_efectiva_hora": float(
            n_clientes
            / (horizonte_simulacion / 60)
        ),
    }

    return clientes, eventos_estado, metricas


def simular_replicaciones(
    lambda_hora: float,
    mu_hora: float,
    n_clientes: int = 5000,
    replicas: int = 10,
    semilla_base: int = 2026,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, float],
]:
    """
    Ejecuta varias réplicas independientes y obtiene
    los indicadores promedio.
    """

    validar_parametros(
        lambda_hora=lambda_hora,
        mu_hora=mu_hora,
        n_clientes=n_clientes,
        replicas=replicas,
    )

    resumen = []

    clientes_detalle = None
    eventos_detalle = None

    for replica in range(replicas):
        semilla_replica = semilla_base + replica

        clientes, eventos, metricas = simular_una_corrida(
            lambda_hora=lambda_hora,
            mu_hora=mu_hora,
            n_clientes=n_clientes,
            semilla=semilla_replica,
        )

        metricas["replica"] = replica + 1
        resumen.append(metricas)

        # Se conserva la primera réplica para los gráficos.
        if replica == 0:
            clientes_detalle = clientes
            eventos_detalle = eventos

    resumen_replicas = pd.DataFrame(resumen)

    promedios = (
        resumen_replicas
        .drop(columns="replica")
        .mean()
        .to_dict()
    )

    return (
        clientes_detalle,
        eventos_detalle,
        resumen_replicas,
        promedios,
    )