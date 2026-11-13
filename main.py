import os
import sys
import time
import urllib.request
from collections import namedtuple

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from extras import CARPETA, Lienzo
from modos import crear_modos

CAMARA = 0
MAX_MANOS = 2
MODO_INICIAL = 1
ANCHO, ALTO = 1280, 720

MODELO = os.path.join(CARPETA, "hand_landmarker.task")
URL_MODELO = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
              "hand_landmarker/float16/1/hand_landmarker.task")
VENTANA = "Proyecto Mano"

Mano = namedtuple("Mano", ["lm", "lado", "lado_es"])

CONEXIONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
              (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
              (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]
COLOR_DEDO = [(0, 200, 255), (0, 255, 0), (255, 200, 0), (255, 0, 200), (0, 100, 255)]


def descargar_modelo():
    if not os.path.exists(MODELO):
        print("Descargando modelo de manos (~8 MB)...")
        urllib.request.urlretrieve(URL_MODELO, MODELO)


def abrir_camara(preferida=0, ancho=1280, alto=720):
    if sys.platform == "win32":
        metodos = [("DirectShow", cv2.CAP_DSHOW), ("Media Foundation", cv2.CAP_MSMF), ("Auto", cv2.CAP_ANY)]
    else:
        metodos = [("Auto", cv2.CAP_ANY)]
    indices = list(dict.fromkeys([preferida, 0, 1, 2]))
    for idx in indices:
        for nombre, api in metodos:
            print(f"Probando cámara {idx} con {nombre}...", end=" ", flush=True)
            cap = cv2.VideoCapture(idx, api)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
                for _ in range(10):
                    ok, frame = cap.read()
                    if ok and frame is not None:
                        print(f"OK ({frame.shape[1]}x{frame.shape[0]})")
                        return cap
                    time.sleep(0.1)
                cap.release()
                cap = cv2.VideoCapture(idx, api)
                ok, frame = cap.read() if cap.isOpened() else (False, None)
                if ok and frame is not None:
                    print(f"OK ({frame.shape[1]}x{frame.shape[0]})")
                    return cap
            cap.release()
            print("no")
    raise SystemExit(
        "\nNo se pudo abrir ninguna cámara. Revisá:\n"
        "  1. Configuración de Windows > Privacidad y seguridad > Cámara:\n"
        "     activá 'Acceso a la cámara' y 'Permitir que las apps de escritorio accedan a la cámara'.\n"
        "  2. Que no quede otro Python abierto: cerrá ventanas negras viejas o, en el\n"
        "     Administrador de tareas, finalizá los procesos 'Python'.\n"
        "  3. Que la cámara funcione en la app 'Cámara' de Windows (y después cerrala).\n"
        "  4. Si es notebook: algunas tienen una tecla o tapa física para la cámara.")


def dibujar_mano(frame, lm):
    h, w = frame.shape[:2]
    pts = [(int(p.x * w), int(p.y * h)) for p in lm]
    for a, b in CONEXIONES:
        cv2.line(frame, pts[a], pts[b], (230, 230, 230), 2, cv2.LINE_AA)
    for i, p in enumerate(pts):
        color = (255, 255, 255) if i == 0 else COLOR_DEDO[(i - 1) // 4]
        cv2.circle(frame, p, 5, color, -1, cv2.LINE_AA)


class App:
    def __init__(self, detector=None, captura=None):
        self.modos = crear_modos()
        self.n_modo = MODO_INICIAL if MODO_INICIAL in self.modos else 1
        self.mensaje, self.t_mensaje = "", 0.0
        self.ayuda = False
        self.lienzo = Lienzo()
        self.fps = 0.0
        if detector is None:
            descargar_modelo()
            opciones = vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=MODELO),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=MAX_MANOS,
                min_hand_detection_confidence=0.6,
                min_tracking_confidence=0.5,
            )
            detector = vision.HandLandmarker.create_from_options(opciones)
        self.detector = detector
        self.cap = captura if captura is not None else abrir_camara(CAMARA, ANCHO, ALTO)
        self.cambiar_modo(self.n_modo)

    def avisar(self, texto, seg=3.0):
        self.mensaje, self.t_mensaje = texto, seg
        print(texto)

    def cambiar_modo(self, n):
        self.n_modo = n
        error = self.modos[n].activar()
        if error:
            self.avisar(error, 5)

    def tecla(self, k):
        if k in (27, ord("q")):
            return False
        if ord("1") <= k <= ord("0") + len(self.modos):
            self.cambiar_modo(k - ord("0"))
        elif k == ord("h"):
            self.ayuda = not self.ayuda
        else:
            self.modos[self.n_modo].tecla(k)
        return True


    def paso(self, frame, ts_ms, dt):
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts_ms)
        manos = []
        for i, lm in enumerate(res.hand_landmarks or []):
            lado = res.handedness[i][0].category_name if res.handedness else "Right"
            manos.append(Mano(lm, lado, "Derecha" if lado == "Right" else "Izquierda"))
            dibujar_mano(frame, lm)
        modo = self.modos[self.n_modo]
        lz = self.lienzo
        modo.procesar(frame, manos, lz, dt)
        self._interfaz(frame, manos, modo, lz, dt)
        return lz.dibujar(frame)

    def _interfaz(self, frame, manos, modo, lz, dt):
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (w, 60), (25, 25, 25), -1)
        lz.texto(f"[{self.n_modo}] {modo.nombre}", (15, 12), 30, (120, 255, 0))
        lz.texto(f"FPS {self.fps:4.0f}", (w - 130, 18), 22, (200, 200, 200))
        for m in manos:
            x = int(m.lm[0].x * w)
            y = int(m.lm[0].y * h)
            lz.texto(m.lado_es, (x, min(y + 12, h - 30)), 20, (255, 255, 255), borde=2, centrado=True)
        if not manos and self.n_modo in (1, 2, 3, 5, 7):
            lz.texto("Mostrá la mano a la cámara", (w // 2, h // 2), 40, (255, 255, 255), centrado=True)
        cv2.rectangle(frame, (0, h - 40), (w, h), (25, 25, 25), -1)
        pie = modo.ayuda + "   ·   H = ayuda   ·   Q = salir"
        lz.texto(pie[:150], (15, h - 32), 20, (220, 220, 220), borde=1)
        if self.t_mensaje > 0:
            self.t_mensaje -= dt
            lz.texto(self.mensaje, (w // 2, 80), 26, (0, 230, 255), centrado=True, fondo=(0, 0, 0))
        if self.ayuda:
            lineas = ["MODOS", "1 Dedo bajado      2 Contar dedos    3 Gestos",
                      "4 Calculadora      5 Mouse virtual   6 Volumen",
                      "7 Abecedario en señas", "",
                      "H ayuda   Q / ESC salir"]
            cv2.rectangle(frame, (w // 2 - 430, h // 2 - 160), (w // 2 + 430, h // 2 + 120), (0, 0, 0), -1)
            for i, l in enumerate(lineas):
                lz.texto(l, (w // 2 - 400, h // 2 - 135 + i * 45), 26, (255, 255, 255), borde=1)


    def correr(self):
        cv2.namedWindow(VENTANA, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(VENTANA, 1280, 720)
        inicio = previo = time.time()
        ultimo_ts = -1
        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    print("No llegan imágenes de la cámara.")
                    break
                ahora = time.time()
                dt = max(ahora - previo, 1e-3)
                previo = ahora
                self.fps = self.fps * 0.9 + (1 / dt) * 0.1
                ts = max(int((ahora - inicio) * 1000), ultimo_ts + 1)
                ultimo_ts = ts
                salida = self.paso(frame, ts, dt)
                cv2.imshow(VENTANA, salida)
                k = cv2.waitKey(1)
                if k != -1 and not self.tecla(k & 0xFF):
                    break
                if cv2.getWindowProperty(VENTANA, cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            self.cerrar()

    def cerrar(self):
        self.cap.release()
        cv2.destroyAllWindows()
        try:
            self.detector.close()
        except Exception:
            pass

if __name__ == "__main__":
    os.chdir(CARPETA)
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        MODO_INICIAL = int(sys.argv[1])
    App().correr()
