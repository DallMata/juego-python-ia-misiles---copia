import pygame
from spaceEvation.constants import *

class Background(pygame.sprite.Sprite):
    def __init__(self):
        super(Background, self).__init__()

        self.surf = pygame.image.load("spaceEvation/sprites/Starfield 1 - 1024x1024.png")
        background_width = SCREEN_WIDTH
        background_height = SCREEN_HEIGHT
        self.surf = pygame.transform.scale(self.surf, (background_width, background_height))
        self.rect = self.surf.get_rect(bottomleft=(0, SCREEN_HEIGHT))

        self.surf2 = self.surf
        self.rect2 = self.surf2.get_rect(bottomleft=self.rect.topleft)

        # Posiciones iniciales del fondo
        self.ypos = 0
        self.ypos2 = self.ypos - background_height  # Posicionar justo encima

    def update(self, delta_time):
        speed = .05 * delta_time
        self.ypos += speed
        self.ypos2 += speed
        self.rect.y = int(self.ypos)
        self.rect2.y = int(self.ypos2)

        if self.rect.y >= SCREEN_HEIGHT:
            self.ypos = self.rect2.y - self.surf.get_height()
        if self.rect2.y >= SCREEN_HEIGHT:
            self.ypos2 = self.rect.y - self.surf.get_height()

    def render(self, dest):
        dest.blit(self.surf, self.rect)
        dest.blit(self.surf2, self.rect2)
