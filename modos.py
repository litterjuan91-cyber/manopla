import time

import cv2
import numpy as np

from logica import (NOMBRE_VISIBLE, NUMERO_DEDO, contar, dedos_arriba,
                    dedos_bajados, dist, escala, gesto)

VERDE, AMARILLO, CELESTE, ROJO, BLANCO = (120, 255, 0), (0, 230, 255), (255, 200, 0), (60, 60, 255), (255, 255, 255)


def px(p, frame):
    h, w = frame.shape[:2]
    return int(p.x * w), int(p.y * h)


def numero_grande(lz, frame, texto, color=VERDE, tam=None):
    h, w = frame.shape[:2]
    if tam is None:
        tam = int(h * (0.45 if len(str(texto)) <= 3 else 0.16))
    lz.texto(texto, (w // 2, h // 2), tam=tam, color=color, borde=max(4, tam // 25), centrado=True)


def barra(frame, x, y, ancho, alto, frac, color=VERDE):
    cv2.rectangle(frame, (x, y), (x + ancho, y + alto), (40, 40, 40), -1)
    cv2.rectangle(frame, (x, y), (x + int(ancho * max(0, min(frac, 1))), y + alto), color, -1)
    cv2.rectangle(frame, (x, y), (x + ancho, y + alto), BLANCO, 2)


class Modo:
    nombre = ""
    ayuda = ""

    def activar(self):
        return None

    def procesar(self, frame, manos, lz, dt):
        return None

    def tecla(self, k):
        pass


class ModoDedoBajado(Modo):
    nombre = "Dedo bajado"
    ayuda = "Pulgar=1 Índice=2 Medio=3 Anular=4 Meñique=5"

    def procesar(self, frame, manos, lz, dt):
        h, w = frame.shape[:2]
        if not manos:
            return None
        m = manos[0]
        bajados = dedos_bajados(m.lm)
        if not bajados:
            numero_grande(lz, frame, "-", BLANCO)
            lz.texto("Todos los dedos arriba", (w // 2, h - 90), 30, centrado=True)
            return None
        nums = [NUMERO_DEDO[d] for d in bajados]
        texto = " ".join(map(str, nums))
        numero_grande(lz, frame, texto)
        lz.texto("Bajado: " + ", ".join(NOMBRE_VISIBLE[d] for d in bajados),
                 (w // 2, h - 90), 30, centrado=True)


class ModoContar(Modo):
    nombre = "Contar dedos"
    ayuda = "Usá una o dos manos (0 a 10)"

    def procesar(self, frame, manos, lz, dt):
        if not manos:
            return None
        total = 0
        for m in manos:
            n = contar(m.lm)
            total += n
            x, y = px(m.lm[0], frame)
            lz.texto(f"{m.lado_es}: {n}", (x, min(y + 45, frame.shape[0] - 75)), 28, AMARILLO, centrado=True)
        numero_grande(lz, frame, str(total))


class ModoGestos(Modo):
    nombre = "Gestos"
    ayuda = "Puño, Pulgar arriba/abajo, Paz, Rock, OK, Te quiero, Llamame, Pistola..."

    def procesar(self, frame, manos, lz, dt):
        if not manos:
            return None
        for m in manos[1:]:
            g = gesto(m.lm)
            if g:
                x, y = px(m.lm[0], frame)
                lz.texto(g, (x, min(y + 45, frame.shape[0] - 75)), 30, AMARILLO, centrado=True)
        g = gesto(manos[0].lm)
        if not g:
            numero_grande(lz, frame, "?", BLANCO)
            return None
        numero_grande(lz, frame, g, VERDE, tam=int(frame.shape[0] * 0.13))


class ModoCalculadora(Modo):
    nombre = "Calculadora"
    ayuda = "Mantené 1,5 s para confirmar · Operación: 1 dedo=+ 2=− 3=× 4=÷ · R reinicia"
    OPS = {1: "+", 2: "−", 3: "×", 4: "÷"}
    ESPERA = 1.5

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.estado, self.a, self.op, self.b, self.res = "A", None, None, None, None
        self.actual, self.t, self.bloqueo, self.t_res = None, 0.0, None, 0.0

    def tecla(self, k):
        if k == ord("r"):
            self.reiniciar()

    def _calcular(self):
        a, b = self.a, self.b
        if self.op == "+":
            return a + b
        if self.op == "−":
            return a - b
        if self.op == "×":
            return a * b
        if b == 0:
            return "Error"
        r = a / b
        return int(r) if r == int(r) else round(r, 2)

    def procesar(self, frame, manos, lz, dt):
        h, w = frame.shape[:2]
        expr = f"{'' if self.a is None else self.a} {self.op or ''} {'' if self.b is None else self.b}".strip()
        if self.estado == "RES":
            numero_grande(lz, frame, f"{expr} = {self.res}", VERDE, tam=int(h * 0.15))
            lz.texto("Nueva cuenta en unos segundos (o tecla R)", (w // 2, h - 90), 28, centrado=True)
            self.t_res += dt
            if self.t_res > 5:
                self.reiniciar()
            return None
        val = None
        if manos:
            if self.estado == "OP":
                val = self.OPS.get(contar(manos[0].lm))
            else:
                val = sum(contar(m.lm) for m in manos)
        if self.bloqueo is not None:
            if val != self.bloqueo:
                self.bloqueo = None
            val = None if val == self.bloqueo else val
        if val is not None and val == self.actual:
            self.t += dt
        else:
            self.actual, self.t = val, 0.0
        instr = {"A": "Mostrá el PRIMER número (0-10)",
                 "OP": "Elegí la operación: 1=+  2=−  3=×  4=÷",
                 "B": "Mostrá el SEGUNDO número (0-10)"}[self.estado]
        lz.texto(instr, (w // 2, 95), 32, AMARILLO, centrado=True, fondo=(0, 0, 0))
        lz.texto(expr or " ", (w // 2, h - 140), 48, BLANCO, centrado=True)
        if val is not None:
            numero_grande(lz, frame, str(val), CELESTE)
            barra(frame, w // 2 - 200, h - 80, 400, 25, self.t / self.ESPERA)
        if val is not None and self.t >= self.ESPERA:
            self.bloqueo, self.actual, self.t = val, None, 0.0
            if self.estado == "A":
                self.a, self.estado = val, "OP"
            elif self.estado == "OP":
                self.op, self.estado = val, "B"
            else:
                self.b, self.estado = val, "RES"
                self.res, self.t_res = self._calcular(), 0.0
        return None


class ModoMouse(Modo):
    nombre = "Mouse virtual"
    ayuda = "Índice arriba mueve · juntá índice y medio = clic · 3 dedos = scroll"
    MARGEN = 0.18

    def __init__(self):
        self.gui = None
        self.suave = None
        self.juntos = False
        self.t_click = 0
        self.y_scroll = None

    def activar(self):
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0
            self.gui = pyautogui
            self.pantalla = pyautogui.size()
        except Exception as e:
            self.gui = None
            return f"Falta pyautogui: {e}"
        return None

    def procesar(self, frame, manos, lz, dt):
        h, w = frame.shape[:2]
        m0 = int(w * self.MARGEN), int(h * self.MARGEN)
        cv2.rectangle(frame, m0, (w - m0[0], h - m0[1]), (255, 0, 255), 2)
        if not self.gui:
            lz.texto("Instalá pyautogui para usar este modo", (w // 2, h // 2), 34, ROJO, centrado=True)
            return None
        if not manos:
            self.suave = self.y_scroll = None
            return None
        lm = manos[0].lm
        a = dedos_arriba(lm)
        e = escala(lm)
        if a["Indice"] and a["Medio"] and a["Anular"] and not a["Menique"]:
            y = lm[9].y
            if self.y_scroll is not None:
                delta = (self.y_scroll - y) * 3000
                if abs(delta) > 15:
                    self.gui.scroll(int(delta))
            self.y_scroll = y
            lz.texto("SCROLL", (w // 2, 95), 36, AMARILLO, centrado=True)
            return None
        self.y_scroll = None
        if not a["Indice"]:
            self.suave = None
            return None
        sx, sy = self.pantalla
        nx = (lm[8].x - self.MARGEN) / (1 - 2 * self.MARGEN)
        ny = (lm[8].y - self.MARGEN) / (1 - 2 * self.MARGEN)
        objetivo = np.array([min(max(nx, 0), 1) * (sx - 1), min(max(ny, 0), 1) * (sy - 1)])
        self.suave = objetivo if self.suave is None else self.suave * 0.65 + objetivo * 0.35
        self.gui.moveTo(int(self.suave[0]), int(self.suave[1]))
        cv2.circle(frame, px(lm[8], frame), 12, (255, 0, 255), -1)
        juntos = a["Medio"] and dist(lm[8], lm[12]) < 0.25 * e
        if juntos and not self.juntos and time.time() - self.t_click > 0.4:
            self.gui.click()
            self.t_click = time.time()
            cv2.circle(frame, px(lm[8], frame), 25, VERDE, 4)
            lz.texto("CLIC", (w // 2, 95), 40, VERDE, centrado=True)
        self.juntos = juntos
        return None


class ModoVolumen(Modo):
    nombre = "Volumen"
    ayuda = "Bajá anular y meñique · separá/juntá pulgar e índice"

    def __init__(self):
        self.ctrl = None
        self.nivel = None
        self.ultimo = None

    def activar(self):
        from extras import ControlVolumen
        self.ctrl = ControlVolumen()
        if self.ctrl.metodo == "ninguno":
            return "No se pudo controlar el volumen (instalá pycaw)"
        try:
            self.nivel = self.ultimo = self.ctrl.obtener()
        except Exception:
            self.nivel = self.ultimo = 0.5
        return None

    def procesar(self, frame, manos, lz, dt):
        h, w = frame.shape[:2]
        nivel = self.nivel or 0.0
        if manos and self.ctrl:
            lm = manos[0].lm
            a = dedos_arriba(lm)
            if not a["Anular"] and not a["Menique"]:
                p4, p8 = px(lm[4], frame), px(lm[8], frame)
                cv2.line(frame, p4, p8, (255, 0, 255), 4)
                for p in (p4, p8):
                    cv2.circle(frame, p, 12, (255, 0, 255), -1)
                ratio = dist(lm[4], lm[8]) / escala(lm)
                objetivo = min(max((ratio - 0.25) / (1.3 - 0.25), 0), 1)
                nivel = objetivo if self.nivel is None else self.nivel * 0.7 + objetivo * 0.3
                self.nivel = nivel
                if self.ultimo is None or abs(nivel - self.ultimo) > 0.02:
                    try:
                        self.ctrl.fijar(nivel)
                        self.ultimo = nivel
                    except Exception:
                        pass
            else:
                lz.texto("Bajá anular y meñique para controlar", (w // 2, h - 90), 28, centrado=True)
        barra(frame, 40, 120, 40, h - 260, 0)
        alto = int((h - 260) * nivel)
        cv2.rectangle(frame, (40, 120 + (h - 260) - alto), (80, 120 + (h - 260)), VERDE, -1)
        lz.texto(f"{int(nivel * 100)} %", (60, h - 110), 30, VERDE, centrado=True)
        return None


class ModoSenas(Modo):
    nombre = "Abecedario en señas"
    ayuda = "Mantené 1 s la letra · J Z Ñ con movimiento · Mano abierta = espacio · Retroceso borra · X limpia · D datos"
    ESPERA = 1.0
    QUIETO = 1.8

    def __init__(self):
        from senas import Movimiento, Suavizado
        self.mov = Movimiento()
        self.votos = Suavizado(7)
        self.escrito = ""
        self.detalles = False
        self._reiniciar_mano()

    def _reiniciar_mano(self):
        self.actual, self.t, self.bloqueo = None, 0.0, None
        self.letra_mov, self.t_mov = None, 0.0
        self.previo = None
        self.mov.limpiar()
        self.votos.limpiar()

    def _escribir(self, c):
        if c == " ":
            if self.escrito and not self.escrito.endswith(" "):
                self.escrito += " "
        else:
            self.escrito += c

    def tecla(self, k):
        if k == 32:
            self._escribir(" ")
        elif k == 8:
            self.escrito = self.escrito[:-1]
        elif k == ord("x"):
            self.escrito = ""
        elif k == ord("d"):
            self.detalles = not self.detalles

    def procesar(self, frame, manos, lz, dt):
        from senas import letra, mano_abierta, rasgos
        h, w = frame.shape[:2]
        self._panel_texto(frame, lz)
        if not manos:
            self._reiniciar_mano()
            return None
        r = rasgos(manos[0].lm, w / h)
        estatica = " " if mano_abierta(r) else letra(r)
        votada = self.votos.agregar(estatica)

        # Velocidad de la mano (en "manos por segundo"): las letras estáticas
        # solo se escriben con la mano quieta, así J y Z no escriben I o D.
        pos = r["P"][0][:2] / r["s"]
        vel = 0.0 if self.previo is None else float(np.linalg.norm(pos - self.previo)) / dt
        self.previo = pos
        quieto = vel < self.QUIETO

        lm_mov = self.mov.agregar(time.time(), r, estatica)
        if lm_mov:
            self._escribir(lm_mov)
            self.letra_mov, self.t_mov = lm_mov, 1.2
            self.bloqueo, self.actual, self.t = votada, None, 0.0

        if self.bloqueo is not None and votada != self.bloqueo:
            self.bloqueo = None
        if votada and votada != self.bloqueo:
            if votada == self.actual:
                if quieto:
                    self.t += dt
            else:
                self.actual, self.t = votada, 0.0
        else:
            self.actual, self.t = None, 0.0
        if self.actual and self.t >= self.ESPERA:
            self._escribir(self.actual)
            self.bloqueo, self.actual, self.t = self.actual, None, 0.0

        # Letra grande a la derecha
        x0, y0, x1, y1 = w - 270, 75, w - 20, 345
        cv2.rectangle(frame, (x0, y0), (x1, y1), (25, 25, 25), -1)
        cv2.rectangle(frame, (x0, y0), (x1, y1), (90, 90, 90), 2)
        if self.t_mov > 0:
            self.t_mov -= dt
            grande, color = self.letra_mov, AMARILLO
        elif votada == " ":
            grande, color = "_", CELESTE
        elif votada:
            grande, color = votada, VERDE if votada != self.bloqueo else BLANCO
        else:
            grande, color = "?", (150, 150, 150)
        lz.texto(grande, ((x0 + x1) // 2, (y0 + y1) // 2 - 15), 170, color, borde=6, centrado=True)
        if votada and votada != self.bloqueo and self.t_mov <= 0:
            barra(frame, x0 + 20, y1 - 40, x1 - x0 - 40, 18, self.t / self.ESPERA)
        elif votada == self.bloqueo and votada:
            lz.texto("escrita", ((x0 + x1) // 2, y1 - 32), 22, BLANCO, borde=1, centrado=True)
        if not quieto and votada:
            lz.texto("quieta para escribir", ((x0 + x1) // 2, y1 + 22), 20, AMARILLO, borde=2, centrado=True)
        if self.detalles:
            self._detalles(lz, r, estatica)
        return None

    def _panel_texto(self, frame, lz):
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, h - 110), (w, h - 40), (15, 15, 15), -1)
        txt = self.escrito[-45:] + "_"
        lz.texto(txt, (20, h - 102), 46, BLANCO, borde=2)

    def _detalles(self, lz, r, estatica):
        ext = "".join(f.upper() if r["ext"][f] else "·" for f in "imrp")
        lineas = [
            f"cruda: {estatica or '-'}   extendidos(i m r p): {ext}",
            "curva: " + " ".join(f"{r['curva'][f]:.0f}" for f in "imrp"),
            "apertura: " + " ".join(f"{r['apertura'][f]:.2f}" for f in "imrp"),
            f"pulgar afuera: {'sí' if r['pulgar_afuera'] else 'no'}   x={r['L'][4][0]:.2f} y={r['L'][4][1]:.2f}"
            f"   prof={r['prof_pulgar']:.2f}",
            f"ángulo índice: {r['ang_indice']:.0f}°  mano: {r['ang_mano']:.0f}°  pulgar-índice: {r['ang_pulgar_indice']:.0f}°",
            f"O: pulgar-índice={r['d'](4, 8):.2f} (<0.32)  apertura={r['apertura_media']:.2f} (>0.97)",
            f"E: yemas encima={r['yemas_encima']:+.2f} (>0.25)  apertura={r['apertura_media']:.2f} (>0.95)",
            f"A/T: pulgar afuera del índice={r['pulgar_afuera_indice']:+.2f} (A si >0.12)",
        ]
        for n, l in enumerate(lineas):
            lz.texto(l, (15, 75 + n * 28), 20, AMARILLO, borde=2)


def crear_modos():
    return {1: ModoDedoBajado(), 2: ModoContar(), 3: ModoGestos(), 4: ModoCalculadora(),
            5: ModoMouse(), 6: ModoVolumen(), 7: ModoSenas()}
