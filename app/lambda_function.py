"""
RouteIQ — Lambda Handler
Envuelve optimizer.py en una API web con FastAPI.
Mangum traduce las peticiones de AWS Lambda/API Gateway a FastAPI.
"""

import json
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mangum import Mangum
from typing import Optional

# Importar funciones del motor universal
from optimizer import (
    geocodificar, es_link, optimizar_vrp,
    asignar_vehiculos, DEFAULT_CONFIG
)

app = FastAPI(
    title="RouteIQ API",
    description="Optimizador universal de rutas de entrega",
    version="1.0.0"
)

# Permitir peticiones desde cualquier origen (necesario para el frontend web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
#  MODELOS DE DATOS
#  Definen el formato exacto del JSON que recibe y devuelve la API
# ─────────────────────────────────────────────────────────────
class Pedido(BaseModel):
    nombre:    str
    direccion: str                        # link Maps, coords, o dirección texto
    turno:     str                        # debe coincidir con un id en config.turnos
    tipo:      Optional[str] = None       # ch, gr, p, m, etc. según config
    telefono:  Optional[str] = ""
    notas:     Optional[str] = ""


class ConfigNegocio(BaseModel):
    negocio:   dict
    turnos:    list
    vehiculos: dict
    items:     dict
    trafico:   Optional[dict] = None


class SolicitudOptimizar(BaseModel):
    pedidos: list[Pedido]
    config:  Optional[ConfigNegocio] = None   # si no viene, usa DEFAULT_CONFIG


class ParadaRuta(BaseModel):
    orden:     int
    nombre:    str
    direccion: str
    tipo:      str
    telefono:  str
    notas:     str
    coords:    list[float]               # [lat, lon]


class ViajeRuta(BaseModel):
    vehiculo:     str                    # "V1", "V2", etc.
    viaje_num:    int
    turno_id:     str
    turno_nombre: str
    paradas:      list[ParadaRuta]
    capacidad_usada: int
    capacidad_max:   int


class RespuestaOptimizar(BaseModel):
    ok:           bool
    total_pedidos: int
    total_viajes:  int
    tiempo_ms:    int
    viajes:       list[ViajeRuta]
    advertencias: list[str]


# ─────────────────────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────────────────────
@app.get("/")
def raiz():
    return {"servicio": "RouteIQ API", "version": "1.0.0", "estado": "activo"}


@app.get("/health")
def health():
    return {"estado": "ok"}


@app.post("/optimizar", response_model=RespuestaOptimizar)
def optimizar(solicitud: SolicitudOptimizar):
    inicio = time.time()
    advertencias = []

    # Cargar config: la del cliente o la default
    cfg = DEFAULT_CONFIG.copy()
    if solicitud.config:
        cfg.update(solicitud.config.dict())
    if not cfg.get("trafico"):
        cfg["trafico"] = DEFAULT_CONFIG["trafico"]

    ciudad    = cfg["negocio"]["ciudad"]
    deposito  = cfg["negocio"].get("deposito", "")
    tipos_cfg = cfg["items"]["tipos"]
    default_t = cfg["items"]["tipo_default"]
    cap       = cfg["vehiculos"]["capacidad_max"]
    turnos    = {t["id"]: t for t in cfg["turnos"]}

    # Geocodificar depósito
    if not deposito:
        raise HTTPException(400, "Falta 'deposito' en la configuración del negocio")

    deposito_coords = geocodificar(deposito, ciudad)
    if not deposito_coords:
        raise HTTPException(400, f"No se pudo ubicar el depósito: {deposito}")

    # Geocodificar cada pedido
    pedidos_validos = []
    for p in solicitud.pedidos:
        # Validar turno
        if p.turno not in turnos:
            advertencias.append(f"Turno '{p.turno}' inválido para '{p.nombre}' — omitido")
            continue

        coords = geocodificar(p.direccion, ciudad)
        if not coords:
            advertencias.append(f"No se ubicó '{p.nombre}' ({p.direccion[:40]}) — omitido")
            continue

        # Pequeña pausa si usa Nominatim (respeta el rate limit)
        if not es_link(p.direccion):
            time.sleep(1.1)

        pedidos_validos.append({
            "nombre":    p.nombre,
            "direccion": p.direccion,
            "turno":     p.turno,
            "tipo":      p.tipo or default_t,
            "telefono":  p.telefono or "",
            "notas":     p.notas or "",
            "coords":    coords,
        })

    if not pedidos_validos:
        raise HTTPException(422, "Ningún pedido pudo geocodificarse correctamente")

    # Optimizar por turno
    plan = {}
    for tid, turno_cfg in turnos.items():
        grupo = [p for p in pedidos_validos if p["turno"] == tid]
        if grupo:
            plan[tid] = asignar_vehiculos(
                deposito_coords, grupo,
                turno_cfg["hora_salida"], cfg
            )
        else:
            n = cfg["vehiculos"]["cantidad"]
            plan[tid] = {f"V{i+1}": [] for i in range(n)}

    # Construir respuesta
    viajes_resp = []
    for tid, vehs in plan.items():
        turno_info = turnos[tid]
        for veh_key, viajes in vehs.items():
            for vi, viaje in enumerate(viajes, 1):
                cap_usada = sum(
                    next((t["puntos"] for t in tipos_cfg
                          if t["id"] == p.get("tipo", default_t)), 1)
                    for p in viaje
                )
                paradas = [
                    ParadaRuta(
                        orden=i,
                        nombre=p["nombre"],
                        direccion=p["direccion"],
                        tipo=p.get("tipo", default_t),
                        telefono=p.get("telefono",""),
                        notas=p.get("notas",""),
                        coords=list(p["coords"]),
                    )
                    for i, p in enumerate(viaje, 1)
                ]
                viajes_resp.append(ViajeRuta(
                    vehiculo=veh_key,
                    viaje_num=vi,
                    turno_id=tid,
                    turno_nombre=f"{turno_info['nombre']} {turno_info['inicio']}–{turno_info['fin']}",
                    paradas=paradas,
                    capacidad_usada=cap_usada,
                    capacidad_max=cap,
                ))

    return RespuestaOptimizar(
        ok=True,
        total_pedidos=len(pedidos_validos),
        total_viajes=len(viajes_resp),
        tiempo_ms=int((time.time() - inicio) * 1000),
        viajes=viajes_resp,
        advertencias=advertencias,
    )


# ─────────────────────────────────────────────────────────────
#  MANGUM — traduce Lambda ↔ FastAPI
# ─────────────────────────────────────────────────────────────
handler = Mangum(app, lifespan="off")
