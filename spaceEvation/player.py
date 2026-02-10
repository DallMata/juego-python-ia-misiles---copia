import os
import json
import pygame
from spaceEvation.constants import *

# Tamaño original del sprite del cohete
ORIGINAL_SIZE = (512, 512)
WIDTH = 70
HEIGHT = int(WIDTH * ORIGINAL_SIZE[1] / ORIGINAL_SIZE[0])

# Velocidad base del juego (antes era SPEED = 0.3)
BASE_SPEED = 0.9


def _clamp(value, vmin, vmax):
    """Mantiene 'value' dentro del rango [vmin, vmax]."""
    return max(vmin, min(vmax, value))


def _get_dificultad_from_env(default=1):
    """
    Intenta leer la dificultad de variables de entorno:
    - KINEPLAY_ASIG (JSON con campo 'dificultad')
    - KINEPLAY_DIFICULTAD (entero simple)
    Fallback: 'default'
    """
    # 1) JSON completo de la asignación (si lo dejaste desde app.py)
    asig_json = os.getenv("KINEPLAY_ASIG")
    if asig_json:
        try:
            obj = json.loads(asig_json)
            if isinstance(obj, dict) and "dificultad" in obj:
                return int(obj["dificultad"])
        except Exception:
            pass

    # 2) Entero directo
    dif_env = os.getenv("KINEPLAY_DIFICULTAD")
    if dif_env and str(dif_env).strip().isdigit():
        try:
            return int(dif_env)
        except Exception:
            pass

    return int(default)


class Player(pygame.sprite.Sprite):
    def __init__(self, dificultad=None):
        super(Player, self).__init__()

        # --------- Dificultad -> velocidad ---------
        # Si no viene por parámetro, la buscamos en el entorno
        dif = _get_dificultad_from_env(1) if dificultad is None else int(dificultad)

        # Space Evation usa 1..5 (por backend ya viene normalizado, pero protegemos igual)
        dif = _clamp(dif, 1, 5)

        # Tu fórmula: factor = 1 - (dificultad * 0.15)
        #  - dif=1  -> factor=0.85
        #  - dif=5  -> factor=0.25
        # Le aplicamos clamp para que nunca caiga a 0 o negativo.
        speed_factor = 1.0 - (dif * 0.15)
        speed_factor = _clamp(speed_factor, 0.10, 1.00)  # mínimo 10% de la velocidad base

        self.dificultad = dif
        self.speed = BASE_SPEED * speed_factor

        # Debug util (podés comentarlo si molesta):
        print(f"[Player] dificultad={self.dificultad} factor={speed_factor:.2f} speed={self.speed:.3f}")

        # --------- Sprite & colisión ---------
        self.surf = pygame.image.load("spaceEvation/sprites/rocket.png").convert_alpha()
        self.surf = pygame.transform.scale(self.surf, (WIDTH, HEIGHT))
        self.update_mask()

        # Guardar para manejar bien las rotaciones
        self.original_surf = self.surf
        self.lastRotation = 0

        self.rect = self.surf.get_rect(
            center=(
                (SCREEN_WIDTH / 2) - (WIDTH / 2),
                (SCREEN_HEIGHT - HEIGHT),
            )
        )

    def update(self, movement, delta_time):
        # Usamos la velocidad que depende de la dificultad
        self.rect.move_ip(self.speed * movement * delta_time, 0)

        # Rotación (suavizada con lerp)
        rotation = 45 * movement * -1
        self.surf = pygame.transform.rotate(
            self.original_surf, self.lerp(self.lastRotation, rotation, 0.5)
        )
        self.lastRotation = rotation
        self.update_mask()

        # Limites de pantalla
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.top <= 0:
            self.rect.top = 0
        if self.rect.bottom >= SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

    def lerp(self, a: float, b: float, t: float) -> float:
        return (1 - t) * a + t * b

    def update_mask(self):
        # Máscara con 80% del tamaño para “perdonar” colisiones
        mask_w = int(WIDTH * 0.8)
        mask_h = int(HEIGHT * 0.8)
        maskSurface = pygame.transform.scale(self.surf, (mask_w, mask_h))
        self.mask = pygame.mask.from_surface(maskSurface)
