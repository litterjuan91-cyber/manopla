# ✋ Proyecto Mano

Detección de manos en tiempo real con **Python + MediaPipe + OpenCV**, con 7 modos.

## Instalación (Windows)

1. Instalá Python 3.13: `py install 3.13`
2. Doble clic en **`instalar.bat`** (solo la primera vez)
3. Doble clic en **`iniciar.bat`**: se abre la cámara directamente

La primera vez se descarga el modelo de manos (~8 MB).

## Modos (teclas 1–7)

| # | Modo | Cómo se usa |
|---|------|-------------|
| 1 | Dedo bajado | Pulgar=1 · Índice=2 · Medio=3 · Anular=4 · Meñique=5 |
| 2 | Contar dedos | Una o dos manos, de 0 a 10 |
| 3 | Gestos | Puño, Pulgar arriba/abajo, Señalar, Paz, Tres, Cuatro, Mano abierta, Rock, OK, Te quiero, Llamame, Pistola |
| 4 | Calculadora | Mostrá un número (mantené 1,5 s) → operación (1 dedo=+, 2=−, 3=×, 4=÷) → otro número. `R` reinicia |
| 5 | Mouse virtual | Índice arriba mueve el cursor · juntar índice y medio = clic · 3 dedos arriba = scroll |
| 6 | Volumen | Bajá anular y meñique; la distancia pulgar-índice controla el volumen |
| 7 | Abecedario en señas | Reconoce las 27 letras (A–Z y Ñ) del deletreo con una mano. Mantené la letra quieta 1 s para escribirla. Ver abajo |

Otras teclas: `H` ayuda · `Q` / `ESC` salir

## Modo 7: abecedario en señas

Mostrá la palma a la cámara y formá la letra con una mano. La letra reconocida
aparece grande a la derecha; si la mantenés **quieta 1 segundo** se escribe abajo.

- **Letras estáticas:** A B C D E F G H I K L M N O P Q R S T U V W X Y
- **Letras con movimiento:**
  - **J**: forma de I y dibujá una J con el meñique (bajá y curvá)
  - **Z**: índice extendido y dibujá una Z en el aire
  - **Ñ**: forma de N y mové la mano de lado a lado
- **Espacio:** mano abierta con el pulgar afuera (1 s) o tecla `Espacio`
- **Repetir una letra** (LL, RR): bajá la mano o cambiá de forma un instante
- Teclas: `Retroceso` borra la última letra · `X` borra todo · `D` muestra los datos de la mano

Las formas siguen el alfabeto manual de una mano (el de ASL, que comparte casi
todas sus formas con el de LSA). A, S, T, M, N y E se diferencian solo por dónde
queda el pulgar y son las más difíciles: hacelas con buena luz y la palma
de frente. Si alguna letra no sale, activá `D`, mirá los valores y ajustá
los umbrales al principio de `senas.py`.

## Configuración

Al principio de `main.py`:

```python
CAMARA = 0          # cámara preferida
MAX_MANOS = 2       # 1 o 2
MODO_INICIAL = 1    # modo con el que arranca (1 a 7)
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `iniciar.bat` | Abre el programa |
| `instalar.bat` | Instala las librerías |
| `main.py` | Programa principal: cámara, detección, teclas |
| `modos.py` | Los 7 modos |
| `senas.py` | Reconocimiento de las letras en señas (modo 7) |
| `logica.py` | Lógica de dedos y gestos |
| `extras.py` | Texto con tildes y control de volumen |

## Problemas comunes

| Problema | Solución |
|---|---|
| No abre la cámara | Cerrá procesos "Python" en el Administrador de tareas y revisá *Privacidad → Cámara* en Windows |
| El pulgar falla | Palma de frente a la cámara, buena luz |
| Mouse se mueve raro | Trabajá dentro del recuadro violeta |
