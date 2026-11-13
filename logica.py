import math

DEDOS = ["Pulgar", "Indice", "Medio", "Anular", "Menique"]
NOMBRE_VISIBLE = {"Pulgar": "Pulgar", "Indice": "Índice", "Medio": "Medio",
                  "Anular": "Anular", "Menique": "Meñique"}
NUMERO_DEDO = {"Pulgar": 1, "Indice": 2, "Medio": 3, "Anular": 4, "Menique": 5}

_ARTICULACIONES = {"Indice": (8, 6), "Medio": (12, 10), "Anular": (16, 14), "Menique": (20, 18)}


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def escala(lm):
    return max(dist(lm[0], lm[9]), 1e-6)


def dedos_arriba(lm):
    arriba = {}
    arriba["Pulgar"] = dist(lm[4], lm[9]) > dist(lm[3], lm[9])
    for nombre, (punta, medio) in _ARTICULACIONES.items():
        arriba[nombre] = dist(lm[punta], lm[0]) > dist(lm[medio], lm[0])
    return arriba


def dedos_bajados(lm):
    a = dedos_arriba(lm)
    return [d for d in DEDOS if not a[d]]


def contar(lm):
    return sum(dedos_arriba(lm).values())


def gesto(lm):
    a = dedos_arriba(lm)
    e = escala(lm)
    t, i, m, r, p = (a[d] for d in DEDOS)
    if dist(lm[4], lm[8]) < 0.35 * e and m and r and p:
        return "OK"
    patron = (t, i, m, r, p)
    if patron == (True, False, False, False, False):
        if lm[4].y < lm[2].y - 0.3 * e:
            return "Pulgar arriba"
        if lm[4].y > lm[2].y + 0.3 * e:
            return "Pulgar abajo"
        return "Puño"
    tabla = {
        (False, False, False, False, False): "Puño",
        (False, True, False, False, False): "Señalar",
        (False, True, True, False, False): "Paz",
        (True, True, True, False, False): "Tres",
        (False, True, True, True, False): "Tres",
        (False, True, True, True, True): "Cuatro",
        (True, True, True, True, True): "Mano abierta",
        (False, True, False, False, True): "Rock",
        (True, True, False, False, True): "Te quiero",
        (True, False, False, False, True): "Llamame",
        (True, True, False, False, False): "Pistola",
    }
    return tabla.get(patron, "")
