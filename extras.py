import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CARPETA = os.path.dirname(os.path.abspath(__file__))

_FUENTES = [
    "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
_cache_fuentes = {}


def _fuente(tam):
    if tam not in _cache_fuentes:
        f = None
        for ruta in _FUENTES:
            if os.path.exists(ruta):
                f = ImageFont.truetype(ruta, tam)
                break
        _cache_fuentes[tam] = f or ImageFont.load_default(size=tam)
    return _cache_fuentes[tam]


class Lienzo:

    def __init__(self):
        self.textos = []

    def texto(self, txt, pos, tam=28, color=(255, 255, 255), borde=3,
              centrado=False, fondo=None):
        self.textos.append((str(txt), pos, tam, color, borde, centrado, fondo))

    def dibujar(self, frame):
        if not self.textos:
            return frame
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(img)
        for txt, (x, y), tam, color, borde, centrado, fondo in self.textos:
            f = _fuente(tam)
            x0, y0, x1, y1 = d.textbbox((0, 0), txt, font=f, stroke_width=borde)
            if centrado:
                x, y = x - (x1 - x0) // 2, y - (y1 - y0) // 2
            if fondo:
                d.rectangle((x - 8, y - 6, x + (x1 - x0) + 8, y + (y1 - y0) + 10), fill=fondo[::-1])
            rgb = color[::-1]
            d.text((x - x0, y - y0), txt, font=f, fill=rgb,
                   stroke_width=borde, stroke_fill=(0, 0, 0))
        self.textos = []
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


class ControlVolumen:

    def __init__(self):
        self._set = self._get = None
        self.metodo = "ninguno"
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            parlantes = AudioUtilities.GetSpeakers()
            if hasattr(parlantes, "EndpointVolume"):
                vol = parlantes.EndpointVolume
            else:
                from ctypes import POINTER, cast
                from comtypes import CLSCTX_ALL
                interfaz = parlantes.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                vol = cast(interfaz, POINTER(IAudioEndpointVolume))
            self._set = lambda x: vol.SetMasterVolumeLevelScalar(float(x), None)
            self._get = vol.GetMasterVolumeLevelScalar
            self.metodo = "pycaw"
        except Exception:
            try:
                import pyautogui
                self._teclas = pyautogui
                self._estimado = 0.5
                self.metodo = "teclas"
            except Exception:
                pass

    def obtener(self):
        if self._get:
            return float(self._get())
        return getattr(self, "_estimado", 0.0)

    def fijar(self, nivel):
        nivel = min(max(nivel, 0.0), 1.0)
        if self._set:
            self._set(nivel)
        elif self.metodo == "teclas":
            pasos = int((nivel - self._estimado) / 0.02)
            if pasos:
                self._teclas.press("volumeup" if pasos > 0 else "volumedown", presses=min(abs(pasos), 5))
                self._estimado += 0.02 * (min(abs(pasos), 5)) * (1 if pasos > 0 else -1)
