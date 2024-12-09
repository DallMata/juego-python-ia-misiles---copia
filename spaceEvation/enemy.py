import pygame
from spaceEvation.constants import *
import random
from spaceEvation import globals

# Tamano del sprite original del enemigo, si usas otro, pon aqui su tamano
ORIGINAL_SIZE = (154, 154)
MIN_WIDTH = 25
MAX_WIDTH = 50

class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super(Enemy, self).__init__()

        # Tamano aleatorio
        self.width = random.randint(MIN_WIDTH, MAX_WIDTH)
        self.height = (self.width / ORIGINAL_SIZE[0]) * ORIGINAL_SIZE[1]
        #self.width = 50
       # self.height = 50

        # Cargar y escalar la imagen del misil
        self.surf = pygame.image.load('spaceEvation/sprites/missile_5.png').convert_alpha()
        self.surf = pygame.transform.scale(self.surf, (self.width, self.height))

        # Rotar el misil 115 grados en sentido horario (usar -135 para sentido horario)
        self.surf = pygame.transform.rotate(self.surf, -135)

        # Crear la máscara para la colisión
        self.mask = pygame.mask.from_surface(self.surf)

        # Obtener el rectángulo del sprite rotado
        self.rect = self.surf.get_rect(
            center=(
                random.randint(0, SCREEN_WIDTH),
                random.randint(-100, -20)
            )
        )

        # Velocidad semi-aleatoria
        self.speed = 0.2

    def update(self, delta_time):
        # Mover el enemigo hacia abajo
        self.rect.move_ip(0, self.speed * delta_time)
        self.mask = pygame.mask.from_surface(self.surf)
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()
