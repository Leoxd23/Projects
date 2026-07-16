"""
═══════════════════════════════════════════════════════════════════
  ROUTEIQ — Motor universal de optimización de rutas  🚚
  
  Sirve para cualquier negocio con entregas:
  restaurantes, farmacias, florerías, tiendas, etc.

  Lo específico del negocio va en config.json — el código
  nunca cambia, solo la configuración.

  Algoritmo: Clarke-Wright Savings + 2-opt*
  Costo:     tiempo OSRM × factor tráfico por hora
  Mapas:     Folium (HTML interactivo)
  Geo:       OpenStreetMap Nominatim + OSRM (sin API key)
═══════════════════════════════════════════════════════════════════
  pip install requests folium pandas openpyxl
  python optimizer.py --config mi_negocio.json
═══════════════════════════════════════════════════════════════════
"""

import sys, time, math, re, json, argparse, urllib.parse
import requests, webbrowser
import pandas as pd
import folium
from datetime import datetime
from pathlib import Path
from itertools import combinations

# ═══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN POR DEFECTO
#  Todo esto se sobreescribe con un archivo config.json externo.
#  Así el mismo código sirve para cualquier negocio.
# ═══════════════════════════════════════════════════════════════
DEFAULT_CONFIG = {
    "negocio": {
        "nombre":    "Mi negocio",
        "ciudad":    "Monterrey, Nuevo León, México",
        "deposito":  "",           # dirección o link Google Maps del punto de salida
        "moneda":    "MXN"
    },
    "turnos": [
        {"id": "M", "nombre": "Matutino",   "inicio": "08:00", "fin": "13:00", "hora_salida": 8.0},
        {"id": "V", "nombre": "Vespertino", "inicio": "14:00", "fin": "19:00", "hora_salida": 14.0}
    ],
    "vehiculos": {
        "cantidad":        2,
        "capacidad_max":   10,     # en puntos
        "colores":  [
            ["#1565C0", "#1E88E5", "#90CAF9"],
            ["#BF360C", "#E64A19", "#FFAB91"]
        ]
    },
    "items": {
        "tipos": [
            {"id": "ch", "nombre": "Chico",  "puntos": 1},
            {"id": "gr", "nombre": "Grande", "puntos": 2}
        ],
        "tipo_default": "ch"
    },
    "trafico": {
        "6":1.10, "7":1.55, "8":1.80, "9":1.50, "10":1.20,
        "11":1.15,"12":1.30,"13":1.45,"14":1.35,"15":1.20,
        "16":1.25,"17":1.50,"18":1.85,"19":1.60,"20":1.30,
        "21":1.10,"22":1.00
    }
}


def cargar_config(path_config: str | None) -> dict:
    """
    Carga config.json del negocio.
    Si no existe, usa los valores por defecto.
    Permite mezclar — solo necesitas poner lo que quieres cambiar.
    """
    cfg = DEFAULT_CONFIG.copy()
    if path_config and Path(path_config).exists():
        with open(path_config, encoding="utf-8") as f:
            custom = json.load(f)
        cfg.update(custom)
        print(f"  ✓ Config cargada: {path_config}")
    else:
        print("  ℹ  Usando configuración por defecto")
    return cfg


# ═══════════════════════════════════════════════════════════════
#  GEOCODIFICACIÓN
# ═══════════════════════════════════════════════════════════════
def extraer_coords_gmaps(link: str):
    link = link.strip()
    m = re.match(r"^(-?\d{1,3}\.\d+)\s*[;,]\s*(-?\d{1,3}\.\d+)$", link)
    if m:
        return float(m.group(1)), float(m.group(2))
    link = urllib.parse.unquote(link).replace(" ", "")
    if "goo.gl" in link:
        try:
            r = requests.get(link, allow_redirects=True, timeout=10,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.url != link:
                link = r.url
                print(f"     → {link[:75]}")
        except Exception as e:
            print(f"  !! expand error: {e}")
    for pat in [
        r"/@(-?\d+\.\d+),(-?\d+\.\d+)",
        r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
        r"[?&](?:q|query)=(-?\d+\.\d+),(-?\d+\.\d+)",
        r"[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)",
        r"/(-?\d{1,3}\.\d{4,}),(-?\d{1,3}\.\d{4,})(?:/|$)",
        r"(-?\d{1,3}\.\d{5,}),(-?\d{1,3}\.\d{5,})",
    ]:
        m = re.search(pat, link)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None


def es_link(t: str) -> bool:
    t = t.strip()
    return ("google.com/maps" in t or "goo.gl" in t
            or bool(re.match(r"^-?\d{1,3}\.\d+[,\s]+-?\d{1,3}\.\d+$", t)))


def geocodificar(direccion: str, ciudad: str):
    if es_link(direccion):
        c = extraer_coords_gmaps(direccion)
        if c:
            return c
        print("  ⚠ No se extrajeron coords del link, usando Nominatim...")
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
            params={"q": f"{direccion}, {ciudad}", "format": "json", "limit": 1},
            headers={"User-Agent": "RouteIQ-Optimizer/1.0"}, timeout=10)
        d = r.json()
        if d:
            return float(d[0]["lat"]), float(d[0]["lon"])
    except Exception as e:
        print(f"  ⚠ Nominatim: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
#  MATRIZ DE COSTOS
#  costo(i,j) = tiempo_OSRM(i,j) × factor_tráfico(hora)
# ═══════════════════════════════════════════════════════════════
def factor_trafico(hora: float, trafico_cfg: dict) -> float:
    return trafico_cfg.get(str(int(hora) % 24), 1.15)


def _osrm_tiempo(lat1, lon1, lat2, lon2) -> float:
    url = (f"http://router.project-osrm.org/route/v1/driving/"
           f"{lon1},{lat1};{lon2},{lat2}?overview=false")
    try:
        r = requests.get(url, timeout=8)
        d = r.json()
        if d.get("code") == "Ok":
            return d["routes"][0]["duration"]
    except Exception:
        pass
    # fallback haversine a 25 km/h
    R = 6371000
    p1, p2 = map(math.radians, [lat1, lat2])
    dp = math.radians(lat2-lat1); dl = math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.asin(math.sqrt(a)) / (25000/3600)


def construir_matriz(nodos: list, hora: float, trafico_cfg: dict) -> list:
    n = len(nodos)
    ft = factor_trafico(hora, trafico_cfg)
    M = [[0.0]*n for _ in range(n)]
    print(f"  📡 Matriz {n}×{n} ({n*(n-1)//2} consultas OSRM · tráfico ×{ft:.2f})...")
    for i in range(n):
        for j in range(i+1, n):
            lat1, lon1 = nodos[i]["coords"]
            lat2, lon2 = nodos[j]["coords"]
            t = _osrm_tiempo(lat1, lon1, lat2, lon2) * ft
            M[i][j] = M[j][i] = t
    return M


def ruta_osrm_polyline(coords):
    if len(coords) < 2:
        return coords
    pts = ";".join(f"{lon},{lat}" for lat, lon in coords)
    try:
        r = requests.get(
            f"http://router.project-osrm.org/route/v1/driving/{pts}"
            "?overview=full&geometries=geojson", timeout=15)
        d = r.json()
        if d.get("code") == "Ok":
            return [(lat, lon) for lon, lat in
                    d["routes"][0]["geometry"]["coordinates"]]
    except Exception:
        pass
    return coords


# ═══════════════════════════════════════════════════════════════
#  PUNTOS POR PEDIDO (genérico — lee tipos desde config)
# ═══════════════════════════════════════════════════════════════
def puntos_pedido(pedido: dict, tipos_cfg: list, default_id: str) -> int:
    tipo_id = str(pedido.get("tipo", default_id)).lower()
    for t in tipos_cfg:
        if t["id"] == tipo_id:
            return t["puntos"]
    return 1


# ═══════════════════════════════════════════════════════════════
#  SOLVER VRP — Clarke-Wright Savings + 2-opt*
# ═══════════════════════════════════════════════════════════════
def costo_ruta(ruta_idx, M, D=0):
    if not ruta_idx:
        return 0.0
    c = M[D][ruta_idx[0]]
    for a, b in zip(ruta_idx, ruta_idx[1:]):
        c += M[a][b]
    return c + M[ruta_idx[-1]][D]


def clarke_wright(D, clientes, pedidos, M, cap, tipos_cfg, default_id):
    if not clientes:
        return []
    savings = []
    for i, j in combinations(clientes, 2):
        s = M[D][i] + M[D][j] - M[i][j]
        savings.append((s, i, j))
    savings.sort(reverse=True)

    rutas = {i: [i] for i in clientes}
    owner = {i: i for i in clientes}

    for _, i, j in savings:
        ri, rj = owner.get(i), owner.get(j)
        if ri is None or rj is None or ri == rj:
            continue
        ra, rb = rutas[ri], rutas[rj]
        merged = None
        if ra[-1] == i and rb[0] == j:   merged = ra + rb
        elif rb[-1] == j and ra[0] == i: merged = rb + ra
        elif ra[-1] == i and rb[-1] == j: merged = ra + rb[::-1]
        elif ra[0] == i and rb[0] == j:  merged = ra[::-1] + rb
        if merged is None:
            continue
        cap_m = sum(puntos_pedido(pedidos[k-1], tipos_cfg, default_id) for k in merged)
        if cap_m > cap:
            continue
        nid = merged[0]
        rutas[nid] = merged
        for k in merged:
            owner[k] = nid
        if ri in rutas and ri != nid: del rutas[ri]
        if rj in rutas and rj != nid: del rutas[rj]
    return list(rutas.values())


def two_opt_intra(ruta, M, D=0):
    mejor = ruta[:]
    mc = costo_ruta(mejor, M, D)
    mejorado = True
    while mejorado:
        mejorado = False
        for i in range(len(mejor)-1):
            for j in range(i+2, len(mejor)):
                nueva = mejor[:i+1] + mejor[i+1:j+1][::-1] + mejor[j+1:]
                c = costo_ruta(nueva, M, D)
                if c < mc - 0.5:
                    mejor, mc, mejorado = nueva, c, True
    return mejor


def two_opt_star(rutas, M, D, pedidos, cap, tipos_cfg, default_id):
    rutas = [r[:] for r in rutas]
    mejorado = True
    while mejorado:
        mejorado = False
        for a in range(len(rutas)):
            for b in range(a+1, len(rutas)):
                ra, rb = rutas[a], rutas[b]
                for i in range(len(ra)):
                    for j in range(len(rb)):
                        na = ra[:i+1] + rb[j+1:]
                        nb = rb[:j+1] + ra[i+1:]
                        ca = sum(puntos_pedido(pedidos[k-1], tipos_cfg, default_id) for k in na)
                        cb = sum(puntos_pedido(pedidos[k-1], tipos_cfg, default_id) for k in nb)
                        if ca > cap or cb > cap:
                            continue
                        delta = (costo_ruta(na,M,D)+costo_ruta(nb,M,D)
                                 - costo_ruta(ra,M,D) - costo_ruta(rb,M,D))
                        if delta < -0.5:
                            rutas[a], rutas[b] = na, nb
                            ra, rb = rutas[a], rutas[b]
                            mejorado = True
    return rutas


def optimizar_vrp(deposito_coords, grupo, hora, cfg):
    if not grupo:
        return []
    trafico_cfg = cfg["trafico"]
    tipos_cfg   = cfg["items"]["tipos"]
    default_id  = cfg["items"]["tipo_default"]
    cap         = cfg["vehiculos"]["capacidad_max"]

    nodos = [{"coords": deposito_coords}] + grupo
    M = construir_matriz(nodos, hora, trafico_cfg)
    clientes = list(range(1, len(nodos)))

    print("  🧮 Clarke-Wright Savings...")
    rutas = clarke_wright(0, clientes, grupo, M, cap, tipos_cfg, default_id)
    print("  🔧 2-opt intra...")
    rutas = [two_opt_intra(r, M) for r in rutas]
    if len(rutas) > 1:
        print("  🔧 2-opt* inter...")
        rutas = two_opt_star(rutas, M, 0, grupo, cap, tipos_cfg, default_id)

    viajes = [[grupo[i-1] for i in r] for r in rutas if r]
    costo = sum(costo_ruta(r, M) for r in rutas)
    print(f"  ✓ {len(viajes)} viaje(s) · {costo/60:.1f} min ajustados por tráfico")
    return viajes


# ═══════════════════════════════════════════════════════════════
#  ASIGNACIÓN GEOGRÁFICA DE VEHÍCULOS
#  Divide por longitud → vehículo 1 cubre zona poniente,
#  vehículo 2 cubre zona oriente. Ambos salen simultáneamente.
# ═══════════════════════════════════════════════════════════════
def dividir_zonas(pedidos):
    if not pedidos:
        return [], []
    ord_ = sorted(pedidos, key=lambda p: p["coords"][1])
    mid = len(ord_) // 2 + len(ord_) % 2
    return ord_[:mid], ord_[mid:]


def asignar_vehiculos(deposito_coords, grupo_turno, hora, cfg):
    n = cfg["vehiculos"]["cantidad"]
    if not grupo_turno:
        return {f"V{i+1}": [] for i in range(n)}

    zona_p, zona_o = dividir_zonas(grupo_turno)
    viajes_v1 = optimizar_vrp(deposito_coords, zona_p, hora, cfg) if zona_p else []
    viajes_v2 = optimizar_vrp(deposito_coords, zona_o, hora, cfg) if zona_o else []

    if not viajes_v1: return {"V1": [], "V2": viajes_v2}
    if not viajes_v2: return {"V1": viajes_v1, "V2": []}

    while abs(len(viajes_v1) - len(viajes_v2)) > 1:
        if len(viajes_v1) > len(viajes_v2):
            viajes_v2.append(viajes_v1.pop())
        else:
            viajes_v1.append(viajes_v2.pop())

    return {"V1": viajes_v1, "V2": viajes_v2}


# ═══════════════════════════════════════════════════════════════
#  ENTRADA DE PEDIDOS
#  Las columnas del Excel/CSV son genéricas:
#  nombre, direccion, turno, tipo, telefono, [notas]
# ═══════════════════════════════════════════════════════════════
def cargar_excel(path_str, cfg):
    path = Path(path_str)
    if not path.exists():
        print(f"  ✗ No encontrado: {path_str}"); return []
    df = (pd.read_excel(path) if path.suffix.lower() in (".xlsx",".xls")
          else pd.read_csv(path))
    df.columns = [c.strip().lower() for c in df.columns]
    if not {"nombre","direccion","turno"}.issubset(df.columns):
        print("  ✗ Columnas mínimas: nombre, direccion, turno")
        return []
    turnos_validos = {t["id"] for t in cfg["turnos"]}
    pedidos = []
    for _, row in df.iterrows():
        turno = str(row["turno"]).strip().upper()
        if turno not in turnos_validos:
            print(f"  ⚠ Turno '{turno}' inválido para '{row['nombre']}' — omitido")
            continue
        pedidos.append({
            "nombre":    str(row["nombre"]).strip(),
            "direccion": str(row["direccion"]).strip(),
            "turno":     turno,
            "tipo":      str(row.get("tipo", cfg["items"]["tipo_default"])).strip().lower(),
            "telefono":  str(row.get("telefono","")).strip(),
            "notas":     str(row.get("notas","")).strip(),
        })
    print(f"  ✓ {len(pedidos)} pedidos cargados")
    return pedidos


def capturar_manual(cfg):
    pedidos = []
    turnos_validos = {t["id"]: t["nombre"] for t in cfg["turnos"]}
    tipos_validos  = {t["id"]: t["nombre"] for t in cfg["items"]["tipos"]}
    print("\n  Ingresa pedidos ('fin' para terminar)\n")
    while True:
        n = input("  Nombre       : ").strip()
        if n.lower() == "fin": break
        d = input("  Dirección    : ").strip()
        opts_t = "/".join(turnos_validos.keys())
        while True:
            t = input(f"  Turno [{opts_t}] : ").strip().upper()
            if t in turnos_validos: break
        opts_i = "/".join(tipos_validos.keys())
        while True:
            tp = input(f"  Tipo [{opts_i}]  : ").strip().lower()
            if tp in tipos_validos: break
        tel   = input("  Teléfono     : ").strip()
        notas = input("  Notas        : ").strip()
        pedidos.append({"nombre":n,"direccion":d,"turno":t,
                        "tipo":tp,"telefono":tel,"notas":notas})
        print("  ✓\n")
    return pedidos


# ═══════════════════════════════════════════════════════════════
#  MAPA
# ═══════════════════════════════════════════════════════════════
def generar_mapa(deposito_coords, plan, cfg, archivo):
    colores_veh = cfg["vehiculos"]["colores"]
    turnos_map  = {t["id"]: f"{t['nombre']} {t['inicio']}–{t['fin']}"
                   for t in cfg["turnos"]}

    mapa = folium.Map(location=deposito_coords, zoom_start=13, tiles="OpenStreetMap")
    folium.Marker(deposito_coords,
        popup=f"<b>🏠 {cfg['negocio']['nombre']}</b>",
        icon=folium.Icon(color="red", icon="home", prefix="fa")).add_to(mapa)

    for turno_id, vehs in plan.items():
        label_turno = turnos_map.get(turno_id, turno_id)
        for vi_key, viajes in vehs.items():
            vi_num = int(vi_key[1:]) - 1
            cols = colores_veh[vi_num % len(colores_veh)]
            for vj, viaje in enumerate(viajes):
                color = cols[vj % len(cols)]
                dash  = "6" if vj > 0 else None
                coords_ruta = ([deposito_coords]
                               + [p["coords"] for p in viaje]
                               + [deposito_coords])
                poly = ruta_osrm_polyline(coords_ruta)
                folium.PolyLine(poly, color=color, weight=4.5, opacity=0.85,
                                tooltip=f"{vi_key} · Viaje {vj+1} · {label_turno}",
                                dash_array=dash).add_to(mapa)
                for i, p in enumerate(viaje, 1):
                    html = (f"<div style='font-family:sans-serif;min-width:160px'>"
                            f"<b>#{i} {p['nombre']}</b><br>"
                            f"📦 {p.get('tipo','?').upper()}<br>"
                            f"🚗 {vi_key} · Viaje {vj+1}<br>"
                            f"🕐 {label_turno}<br>"
                            f"{'📞 '+p['telefono'] if p.get('telefono') else ''}"
                            f"{'<br>📝 '+p['notas'] if p.get('notas') else ''}"
                            f"</div>")
                    mc = "blue" if vi_key == "V1" else "orange"
                    folium.Marker(p["coords"],
                        popup=folium.Popup(html, max_width=260),
                        tooltip=f"{vi_key}-V{vj+1} #{i} {p['nombre']}",
                        icon=folium.Icon(color=mc, icon="star", prefix="fa")).add_to(mapa)
                    folium.map.Marker(p["coords"], icon=folium.DivIcon(
                        html=(f'<div style="font-size:10px;font-weight:bold;color:white;'
                              f'background:{color};border-radius:50%;width:20px;height:20px;'
                              f'display:flex;align-items:center;justify-content:center;'
                              f'border:2px solid white;margin:-8px 0 0 -8px">{i}</div>'),
                        icon_size=(20,20))).add_to(mapa)

    # Leyenda dinámica
    items_leyenda = "".join(
        f"<span style='color:{colores_veh[i][0]}'>━━</span> Vehículo {i+1}<br>"
        for i in range(len(colores_veh)))
    leyenda = (
        "<div style='position:fixed;bottom:30px;right:30px;z-index:1000;"
        "background:white;padding:14px 18px;border-radius:10px;"
        "border:1px solid #ccc;font-family:sans-serif;font-size:12px;"
        "box-shadow:0 2px 8px rgba(0,0,0,.15)'>"
        f"<b>🚚 {cfg['negocio']['nombre']}</b><br><br>"
        + items_leyenda +
        "<span style='font-size:10px;color:#888'>Costo = OSRM × tráfico</span></div>")
    mapa.get_root().html.add_child(folium.Element(leyenda))
    mapa.save(archivo)


# ═══════════════════════════════════════════════════════════════
#  REPORTE CONSOLA
# ═══════════════════════════════════════════════════════════════
def imprimir_reporte(deposito_coords, plan, cfg):
    turnos_map = {t["id"]: f"{t['nombre'].upper()} {t['inicio']}–{t['fin']}"
                  for t in cfg["turnos"]}
    tipos_map  = {t["id"]: t["puntos"] for t in cfg["items"]["tipos"]}
    cap        = cfg["vehiculos"]["capacidad_max"]
    sep = "─"*62

    print("\n" + "═"*62)
    print(f"  🚚  {cfg['negocio']['nombre'].upper()} — RUTAS OPTIMIZADAS")
    print("  Clarke-Wright + 2-opt* | Costo: OSRM × tráfico")
    print("═"*62)
    total = 0
    for turno_id in [t["id"] for t in cfg["turnos"]]:
        vehs = plan.get(turno_id, {})
        if not any(v for v in vehs.values()):
            continue
        ft = factor_trafico(
            next(t["hora_salida"] for t in cfg["turnos"] if t["id"]==turno_id),
            cfg["trafico"])
        print(f"\n  {'🌅' if turno_id=='M' else '🌆'}  TURNO {turnos_map[turno_id]}  (×{ft:.2f})")
        for veh, viajes in vehs.items():
            if not viajes: continue
            n_ped = sum(len(v) for v in viajes)
            print(f"\n    🚗 {veh}  —  {len(viajes)} viaje(s)  ·  {n_ped} entregas")
            for vi, viaje in enumerate(viajes, 1):
                cap_u = sum(tipos_map.get(p.get("tipo","ch"),1) for p in viaje)
                print(f"\n      Viaje {vi}  [{cap_u}/{cap} pts]")
                print(f"      {sep[:50]}")
                print(f"      {'#':<3} {'Nombre':<22} {'Tipo':<6} {'Teléfono'}")
                print(f"      {sep[:50]}")
                for i, p in enumerate(viaje, 1):
                    print(f"      {i:<3} {p['nombre'][:21]:<22} "
                          f"{p.get('tipo','?').upper():<6} {p.get('telefono','')}")
                total += len(viaje)
    print(f"\n  ✅ Total entregas del día: {total}")
    print("═"*62 + "\n")


# ═══════════════════════════════════════════════════════════════
#  EXPORTAR EXCEL
# ═══════════════════════════════════════════════════════════════
def exportar_excel(plan, cfg, archivo):
    turnos_map = {t["id"]: f"{t['nombre']} {t['inicio']}–{t['fin']}"
                  for t in cfg["turnos"]}
    filas = []
    for turno_id in [t["id"] for t in cfg["turnos"]]:
        for veh, viajes in plan.get(turno_id, {}).items():
            for vi, viaje in enumerate(viajes, 1):
                for i, p in enumerate(viaje, 1):
                    filas.append({
                        "Turno":       turnos_map.get(turno_id, turno_id),
                        "Vehículo":    veh,
                        "Viaje":       vi,
                        "Orden":       i,
                        "Nombre":      p["nombre"],
                        "Dirección":   p["direccion"],
                        "Tipo":        p.get("tipo","").upper(),
                        "Teléfono":    p.get("telefono",""),
                        "Notas":       p.get("notas",""),
                        "Entregado":   "",
                    })
    pd.DataFrame(filas).to_excel(archivo, index=False)
    print(f"  📄 Hoja de ruta → {archivo}")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="RouteIQ — Optimizador universal de rutas")
    parser.add_argument("--config", help="Ruta al archivo config.json del negocio")
    parser.add_argument("--input",  help="Ruta al Excel/CSV de pedidos (opcional)")
    args = parser.parse_args()

    cfg = cargar_config(args.config)
    ciudad = cfg["negocio"]["ciudad"]

    print("\n" + "═"*62)
    print(f"  🚚  ROUTEIQ — {cfg['negocio']['nombre']}")
    print(f"  {cfg['vehiculos']['cantidad']} vehículos · "
          f"{cfg['vehiculos']['capacidad_max']} pts/viaje · "
          f"{len(cfg['turnos'])} turno(s)")
    print("═"*62)

    # Depósito
    print(f"\n  📍 Localizando punto de salida...")
    deposito_addr = cfg["negocio"]["deposito"]
    if not deposito_addr:
        deposito_addr = input("  Dirección o link Maps del depósito: ").strip()
    deposito_coords = geocodificar(deposito_addr, ciudad)
    if not deposito_coords:
        print("  ✗ No se ubicó el depósito."); sys.exit(1)
    print(f"  ✓ {deposito_coords[0]:.5f}, {deposito_coords[1]:.5f}")

    # Pedidos
    if args.input:
        pedidos = cargar_excel(args.input, cfg)
    else:
        print("\n  ¿Cómo ingresas los pedidos?")
        print("  [1] Archivo Excel/CSV  [2] Manual")
        op = input("\n  Elige: ").strip()
        pedidos = (cargar_excel(input("  Ruta: ").strip(), cfg)
                   if op == "1" else capturar_manual(cfg))

    if not pedidos:
        print("  ✗ Sin pedidos."); sys.exit(0)

    # Geocodificar
    print(f"\n  🌐 Geocodificando {len(pedidos)} direcciones...")
    validos = []
    for p in pedidos:
        link = es_link(p["direccion"])
        print(f"  ... {p['nombre']} [{'Maps' if link else 'Nominatim'}]")
        coords = geocodificar(p["direccion"], ciudad)
        if coords:
            p["coords"] = coords
            validos.append(p)
            print(f"      ✓ {coords[0]:.5f}, {coords[1]:.5f}")
        else:
            print(f"  ⚠  Omitido: '{p['direccion'][:55]}'")
        if not link:
            time.sleep(1.1)

    if not validos:
        print("  ✗ Sin coordenadas válidas."); sys.exit(1)

    # Optimizar por turno
    plan = {}
    for turno_cfg in cfg["turnos"]:
        tid  = turno_cfg["id"]
        hora = turno_cfg["hora_salida"]
        grupo = [p for p in validos if p["turno"] == tid]
        if grupo:
            print(f"\n  ⚙  Turno {turno_cfg['nombre']} ({len(grupo)} entregas · "
                  f"salida {int(hora):02d}:00)...")
            plan[tid] = asignar_vehiculos(deposito_coords, grupo, hora, cfg)
        else:
            plan[tid] = {f"V{i+1}": [] for i in range(cfg["vehiculos"]["cantidad"])}

    # Resultados
    imprimir_reporte(deposito_coords, plan, cfg)

    fecha = datetime.now().strftime("%Y%m%d_%H%M")
    mapa_file = f"ruta_{fecha}.html"
    print("  🗺  Generando mapa...")
    generar_mapa(deposito_coords, plan, cfg, mapa_file)
    print(f"  ✓ Mapa → {mapa_file}")
    webbrowser.open(f"file://{Path(mapa_file).resolve()}")

    if input("\n  ¿Exportar a Excel? [s/N]: ").strip().lower() == "s":
        exportar_excel(plan, cfg, f"rutas_{fecha}.xlsx")

    print("\n  ✅ ¡Listo!\n")


if __name__ == "__main__":
    main()
