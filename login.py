import pygame
import sys
from constants import *

class Login:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        pygame.display.set_caption("Login")

        self.font = pygame.font.Font(None, 32)
        self.label_font = pygame.font.SysFont("courier", 24, bold=True) # Fuente para el texto "ID:"
        self.input_box = pygame.Rect(0, 0, 200, 32)
        self.label_box = pygame.Rect(0, 0, 200, 24)
        self.color_inactive = pygame.Color('#03A1CF')  # Color de fondo del input cuando está inactivo
        self.color_active = pygame.Color('#FFBD59')  # Color de fondo del input cuando está activo
        self.color = self.color_inactive
        self.text = ''
        self.active = False
        self.done = False

        self.clock = pygame.time.Clock()

        # Cargar la imagen de fondo
        self.background_image = pygame.image.load("sprites/KINEPLAY.png")  # Asegúrate de tener la imagen en el directorio

        # Redimensionar la imagen de fondo para que coincida con el tamaño de la pantalla
        self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # Calcular las posiciones centradas
        self.input_box.center = self.screen.get_rect().center
        self.input_box.y += 20  # Ajustar verticalmente

        self.label_box.midbottom = (self.input_box.centerx, self.input_box.top - 5)  # Posicionar el texto "ID:" sobre el campo de texto

    def run(self):
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if self.active:
                        if event.key == pygame.K_RETURN:
                            if self.text == "12345678":
                                self.done = True
                            else:
                                self.text = ''
                        elif event.key == pygame.K_BACKSPACE:
                            self.text = self.text[:-1]
                        else:
                            self.text += event.unicode

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.input_box.collidepoint(event.pos):
                        self.active = not self.active
                    else:
                        self.active = False
                    self.color = self.color_active if self.active else self.color_inactive

            # Dibujar la imagen de fondo redimensionada
            self.screen.blit(self.background_image, (0, 0))

            # Dibujar el texto "ID:" sobre el campo de texto
            label_text = self.label_font.render("INGRESE SU ID:", True, (255, 255, 255))
            self.screen.blit(label_text, self.label_box)

            # Dibujar el campo de texto y el borde
            txt_surface = self.font.render(self.text, True, (255, 255, 255))  # Color del texto blanco
            width = max(200, txt_surface.get_width()+10)
            self.input_box.w = width
            self.screen.blit(txt_surface, (self.input_box.x+5, self.input_box.y+5))
            pygame.draw.rect(self.screen, self.color, self.input_box, 2)
            pygame.display.flip()
            self.clock.tick(30)

if __name__ == "__main__":
    Login().run()
