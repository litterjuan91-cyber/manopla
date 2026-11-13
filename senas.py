"""Reconocimiento del abecedario dactilológico (deletreo con una mano).

Las letras estáticas se reconocen por la forma de la mano en cada cuadro.
J, Z y Ñ llevan movimiento y se reconocen siguiendo la trayectoria:
  J = forma de I y "dibujar" una J con el meñique (bajar y curvar)
  Z = índice extendido y dibujar una Z en el aire
  Ñ = forma de N y mover la mano de lado a lado

Todas las medidas están normalizadas por el tamaño de la mano
(distancia muñeca → nudillo del dedo medio = 1), así que no importa
lo cerca o lejos que esté la mano de la cámara.

Si alguna letra cuesta, ajustá los UMBRALES de abajo; en el modo 7
la tecla D muestra los valores en vivo para calibrar.
"""
import math
from collections import Counter, deque

import numpy as np

# ---------------------------------------------------------------- umbrales
EXT = 65             # curvatura total (°) por debajo de la cual un dedo está extendido
EXT_LEJOS = 1.80     # ...o si la yema está así de lejos de la muñeca (y no muy curvado)
EXT_CERCA = 1.45     # yema más cerca que esto → nunca extendido (D, O, C)
PULGAR_AFUERA = 0.45  # distancia mínima pulgar–nudillo del índice para "pulgar afuera"
PULGAR_LADO = 0.12    # cuánto debe sobresalir el pulgar hacia afuera del índice
TOQUE = 0.38          # distancia para considerar que dos yemas se tocan
V_SEPARACION = 1.45   # puntas índice–medio vs. nudillos: más separadas → V (si no, U/H)
CRUCE = 0.04          # índice cruzado sobre el medio (R)
PARALELO = 40         # ángulo pulgar–índice por debajo del cual son paralelos (G, Q)
O_TOQUE = 0.32        # O: punta del pulgar contra la punta del índice
O_APERTURA = 0.97     # O: apertura mínima (en el puño cerrado las yemas tocan la palma)
C_APERTURA = 1.30     # apertura media de los dedos para C
E_ENCIMA = 0.25       # E: cuánto quedan las yemas por encima de la punta del pulgar
E_APERTURA = 0.95     # E: apertura media mínima (en el puño las yemas se esconden en la palma)
A_AFUERA = 0.12       # A: cuánto sobresale el pulgar por fuera del índice (si no, T)
S_BAJO = 0.12         # pulgar por debajo de los nudillos de la base → S
S_ADELANTE = -0.15    # pulgar por delante de los dedos (profundidad) → S
X_GANCHO = 0.25       # cuánto se eleva la falange del índice en la X
LADO_GRADOS = 35      # inclinación máxima para considerar que el dedo apunta "de lado"

DEDOS4 = {"i": (5, 6, 7, 8), "m": (9, 10, 11, 12), "r": (13, 14, 15, 16), "p": (17, 18, 19, 20)}


def _norm(v):
    return float(np.linalg.norm(v))


def _flexion(a, b, c):
    """Ángulo (°) que dobla la articulación b: 0 = recto."""
    u, v = b - a, c - b
    nu, nv = _norm(u), _norm(v)
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, float(u @ v) / (nu * nv)))))


def _angulo(u, v):
    nu, nv = _norm(u), _norm(v)
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, float(u @ v) / (nu * nv)))))


def apunta(grados):
    """'arriba', 'abajo' o 'lado' según el ángulo en pantalla (90 = arriba)."""
    if abs(grados) < LADO_GRADOS or abs(grados) > 180 - LADO_GRADOS:
        return "lado"
    return "arriba" if grados > 0 else "abajo"


def rasgos(lm, aspecto=16 / 9):
    """Calcula las medidas de la mano que usa el clasificador."""
    P = np.array([[p.x * aspecto, p.y, p.z * aspecto] for p in lm], dtype=float)
    s = _norm(P[9] - P[0]) or 1e-6
    # Marco propio de la mano: y = muñeca→medio, x = meñique→índice (lado del pulgar positivo)
    uy = (P[9] - P[0]) / s
    t = P[5] - P[17]
    ux = t - (t @ uy) * uy
    ux = ux / _norm(ux) if _norm(ux) > 1e-9 else np.array([1.0, 0.0, 0.0])
    uz = np.cross(ux, uy)
    L = (P - P[0]) @ np.vstack([ux, uy, uz]).T / s

    def d(i, j):
        return _norm(P[i] - P[j]) / s

    curva, nudillo, apertura, ext = {}, {}, {}, {}
    for f, (a, b, c, e) in DEDOS4.items():
        f1 = _flexion(P[0], P[a], P[b])
        f2 = _flexion(P[a], P[b], P[c])
        f3 = _flexion(P[b], P[c], P[e])
        curva[f] = f1 + f2 + f3
        nudillo[f] = f1
        apertura[f] = d(e, 0) / max(d(a, 0), 1e-6)
        if apertura[f] < EXT_CERCA:
            ext[f] = False
        else:
            ext[f] = curva[f] < EXT or (apertura[f] > EXT_LEJOS and curva[f] < 100)

    vm = P[9] - P[0]
    vi = P[8] - P[5]
    vt = P[4] - P[2]
    return {
        "P": P, "L": L, "s": s, "d": d,
        "curva": curva, "nudillo": nudillo, "apertura": apertura, "ext": ext,
        "pulgar_afuera": d(4, 5) > PULGAR_AFUERA and L[4][0] > L[5][0] + PULGAR_LADO,
        "ang_indice": math.degrees(math.atan2(-vi[1], vi[0])),
        "ang_mano": math.degrees(math.atan2(-vm[1], vm[0])),
        "ang_pulgar_indice": _angulo(vt, vi),
        "prof_pulgar": (P[4][2] - (P[7][2] + P[11][2]) / 2) / s,
        # Rasgos en el plano de la palma (más confiables que la profundidad):
        "yemas_encima": float(np.mean([L[k][1] for k in (8, 12, 16, 20)]) - L[4][1]),
        "apertura_media": float(np.mean(list(apertura.values()))),
        "pulgar_afuera_indice": float(L[4][0] - max(L[5][0], L[6][0])),
    }


def mano_abierta(r):
    return all(r["ext"].values()) and r["pulgar_afuera"]


def letra(r):
    """Devuelve la letra estática (A–Y sin J) o '' si no reconoce ninguna."""
    E, L, d = r["ext"], r["L"], r["d"]
    i, m, a, p = E["i"], E["m"], E["r"], E["p"]
    pa = r["pulgar_afuera"]
    dir_i = apunta(r["ang_indice"])
    abajo = dir_i == "abajo" or apunta(r["ang_mano"]) == "abajo"

    # Cuatro dedos arriba
    if i and m and a and p:
        return "" if pa else "B"
    if i and m and a and not p:
        return "W"
    if m and a and p and not i:
        return "F" if d(4, 8) < TOQUE + 0.1 else ""

    # Índice y medio
    if i and m and not a and not p:
        if L[8][0] < L[12][0] - CRUCE:
            return "R"
        if (d(4, 10) < TOQUE or d(4, 9) < TOQUE) and L[4][1] > L[5][1] - 0.1:
            return "P" if abajo else "K"
        if d(8, 12) / max(d(5, 9), 1e-6) > V_SEPARACION:
            return "V"
        if dir_i == "lado":
            return "H"
        return "P" if abajo else "U"

    # Solo índice
    if i and not m and not a and not p:
        if pa or r["ang_pulgar_indice"] < PARALELO and d(4, 5) > PULGAR_AFUERA:
            if r["ang_pulgar_indice"] < PARALELO or dir_i != "arriba":
                return "Q" if dir_i == "abajo" else "G"
            return "L"
        if dir_i == "abajo":
            return "Q"
        if dir_i == "lado":
            return "G"
        return "D"

    # Solo meñique
    if p and not i and not m and not a:
        return "Y" if pa else "I"

    if any(E.values()):
        return ""

    # ---- Ningún dedo extendido: X, O, C, E y la familia del puño
    # X: índice en gancho (falange levantada) y el resto cerrados
    if (L[6][1] - L[5][1] > X_GANCHO and L[10][1] - L[9][1] < X_GANCHO * 0.6
            and r["apertura"]["m"] < 1.15):
        return "X"

    ap = np.mean([r["apertura"][f] for f in "imrp"])
    # O: las yemas se juntan con el pulgar formando un aro, LEJOS de la palma.
    # (En el puño también se tocan pulgar e índice, pero las yemas están en la palma.)
    toca = min(d(4, 8), d(4, 12))
    if r["apertura_media"] > O_APERTURA and (
            d(4, 8) < O_TOQUE or (toca < O_TOQUE + 0.1 and r["yemas_encima"] < E_ENCIMA)):
        return "O"
    if ap > C_APERTURA and d(4, 8) > TOQUE * 0.8:
        return "C"
    # E: yemas dobladas apoyadas ENCIMA del pulgar (en S, M, N y T el pulgar
    # queda a la altura de las yemas o por arriba, y las yemas se esconden)
    if (r["yemas_encima"] > E_ENCIMA and r["apertura_media"] > E_APERTURA
            and L[4][0] < L[5][0]):
        return "E"

    # Puño: depende de dónde queda el pulgar
    # A: pulgar recto al costado, claramente por FUERA del índice.
    # En la T queda metido entre índice y medio (pegado o por dentro del índice).
    x = L[4][0]
    if r["pulgar_afuera_indice"] > A_AFUERA:
        return "A"
    # S: el pulgar cruza por delante, por DEBAJO de la línea de nudillos de la base;
    # en T, N y M la punta asoma entre los dedos, a la altura de esos nudillos.
    altura_nudillos = (L[5][1] + L[9][1] + L[13][1]) / 3
    if L[4][1] < altura_nudillos - S_BAJO or r["prof_pulgar"] < S_ADELANTE:
        return "S"
    huecos = {"T": (L[5][0] + L[9][0]) / 2,
              "N": (L[9][0] + L[13][0]) / 2,
              "M": (L[13][0] + L[17][0]) / 2}
    return min(huecos, key=lambda k: abs(huecos[k] - x))


# ---------------------------------------------------------------- movimiento

def _reversiones(xs, umbral):
    """Cuántas veces cambia de sentido una secuencia (con histéresis)."""
    n, sentido, ref = 0, 0, xs[0]
    for x in xs[1:]:
        if sentido == 0:
            if abs(x - ref) > umbral:
                sentido, ref = (1 if x > ref else -1), x
        elif sentido * (x - ref) > 0:
            ref = x
        elif abs(x - ref) > umbral:
            n += 1
            sentido, ref = -sentido, x
    return n


class Movimiento:
    """Sigue la mano unos instantes para detectar J, Z y Ñ."""
    VENTANA = 1.6

    def __init__(self):
        self.h = deque()

    def limpiar(self):
        self.h.clear()

    def agregar(self, t, r, estatica):
        E, P, s = r["ext"], r["P"], r["s"]
        forma = ("menique" if E["p"] and not (E["i"] or E["m"] or E["r"]) else
                 "indice" if E["i"] and not (E["m"] or E["r"] or E["p"]) else
                 "n" if estatica in ("N", "M", "T") else "")
        self.h.append((t, forma, P[8][:2] / s, P[20][:2] / s, P[0][:2] / s))
        while self.h and t - self.h[0][0] > self.VENTANA:
            self.h.popleft()
        letra_mov = self._detectar()
        if letra_mov:
            self.limpiar()
        return letra_mov

    def _tramo(self, forma, tolerancia=0.25):
        """Últimos cuadros donde predomina una forma de mano."""
        tramo = []
        fuera = 0
        for e in reversed(self.h):
            if e[1] == forma:
                tramo.append(e)
            else:
                fuera += 1
                if fuera > max(3, len(tramo) * tolerancia):
                    break
        return tramo[::-1]

    def _detectar(self):
        # J: meñique que baja y se curva
        tr = self._tramo("menique")
        if len(tr) >= 6 and tr[-1][0] - tr[0][0] > 0.3:
            pts = np.array([e[3] for e in tr])
            k = int(np.argmax(pts[:, 1]))
            baja = pts[k, 1] - pts[0, 1]
            curva = abs(pts[-1, 0] - pts[k, 0]) if k < len(pts) - 2 else 0
            recorrido = float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))
            if baja > 0.45 and curva > 0.25 and recorrido > 0.9:
                return "J"
        # Z: índice que va y vuelve en horizontal mientras baja
        tr = self._tramo("indice")
        if len(tr) >= 8 and tr[-1][0] - tr[0][0] > 0.4:
            pts = np.array([e[2] for e in tr])
            ancho = pts[:, 0].max() - pts[:, 0].min()
            baja = pts[-1, 1] - pts[0, 1]
            if ancho > 0.6 and baja > 0.4 and _reversiones(pts[:, 0], 0.35) >= 2:
                return "Z"
        # Ñ: forma de N moviéndose de lado a lado
        tr = self._tramo("n", tolerancia=0.4)
        if len(tr) >= 8 and tr[-1][0] - tr[0][0] > 0.4:
            pts = np.array([e[4] for e in tr])
            ancho = pts[:, 0].max() - pts[:, 0].min()
            vertical = pts[:, 1].max() - pts[:, 1].min()
            if ancho > 0.35 and vertical < ancho and _reversiones(pts[:, 0], 0.15) >= 2:
                return "Ñ"
        return None


class Suavizado:
    """Votación de los últimos cuadros para que la letra no parpadee."""

    def __init__(self, n=7):
        self.v = deque(maxlen=n)

    def limpiar(self):
        self.v.clear()

    def agregar(self, x):
        self.v.append(x)
        letra_top, veces = Counter(self.v).most_common(1)[0]
        return letra_top if veces > len(self.v) // 2 else ""
