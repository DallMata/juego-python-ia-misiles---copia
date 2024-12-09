import pygame
import sys
import requests
from spaceEvation.constants import *


class Login:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        pygame.display.set_caption("Login")

        self.font = pygame.font.Font(None, 32)
        self.label_font = pygame.font.SysFont("courier", 20, bold=True)

        # Campos de entrada
        self.dni_box = pygame.Rect(0, 0, 200, 32)
        self.clave_box = pygame.Rect(0, 0, 200, 32)
        self.color_inactive = pygame.Color('#03A1CF')
        self.color_active = pygame.Color('#FFBD59')
        self.dni_color = self.color_inactive
        self.clave_color = self.color_inactive
        self.dni_text = ''
        self.clave_text = ''
        self.active_dni = False
        self.active_clave = False

        # Bandera de estado
        self.done = False
        self.clock = pygame.time.Clock()

        # Imagen de fondo
        self.background_image = pygame.image.load("sprites/KINEPLAY.png")
        self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # Posicionar los campos
        center = self.screen.get_rect().center
        self.dni_box.center = center
        self.dni_box.y -= 20
        self.clave_box.center = center
        self.clave_box.y += 40

        # Etiquetas
        self.dni_label_box = pygame.Rect(self.dni_box.x, self.dni_box.y - 30, 200, 24)
        self.clave_label_box = pygame.Rect(self.clave_box.x, self.clave_box.y - 30, 200, 24)

        self.paciente = None

    def run(self):
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if self.active_dni:
                        if event.key == pygame.K_BACKSPACE:
                            self.dni_text = self.dni_text[:-1]
                        else:
                            self.dni_text += event.unicode
                    elif self.active_clave:
                        if event.key == pygame.K_BACKSPACE:
                            self.clave_text = self.clave_text[:-1]
                        else:
                            self.clave_text += event.unicode

                    if event.key == pygame.K_RETURN:
                        if self.dni_text and self.clave_text:
                            url = f'http://localhost:80/usuarios/pacientes.php?dni={self.dni_text}'
                           # payload = {'dni': self.dni_text, 'clave': self.clave_text}
                            response = requests.get(url)

                            if response.status_code == 200:
                                self.paciente = response.json()
                                print(f"Paciente encontrado: {self.paciente}")
                                if self.dni_text == paciente.dni and self.clave_text == paciente.clave:
                                    self.done = True
                                else:
                                    print("DNI o clave incorrectos.")
                                    self.dni_text, self.clave_text = '', ''  # Limpiar campos
                        else:
                            print("Por favor complete ambos campos.")

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.dni_box.collidepoint(event.pos):
                        self.active_dni = True
                        self.active_clave = False
                    elif self.clave_box.collidepoint(event.pos):
                        self.active_clave = True
                        self.active_dni = False
                    else:
                        self.active_dni = self.active_clave = False

                    self.dni_color = self.color_active if self.active_dni else self.color_inactive
                    self.clave_color = self.color_active if self.active_clave else self.color_inactive

            # Dibujar la pantalla
            self.screen.blit(self.background_image, (0, 0))

            # Etiquetas
            dni_label = self.label_font.render("DNI:", True, (255, 255, 255))
            clave_label = self.label_font.render("Clave:", True, (255, 255, 255))
            self.screen.blit(dni_label, self.dni_label_box.topleft)
            self.screen.blit(clave_label, self.clave_label_box.topleft)

            # Campos de texto
            dni_surface = self.font.render(self.dni_text, True, (255, 255, 255))
            clave_surface = self.font.render(self.clave_text, True, (255, 255, 255))
            self.screen.blit(dni_surface, (self.dni_box.x + 5, self.dni_box.y + 5))
            self.screen.blit(clave_surface, (self.clave_box.x + 5, self.clave_box.y + 5))
            pygame.draw.rect(self.screen, self.dni_color, self.dni_box, 2)
            pygame.draw.rect(self.screen, self.clave_color, self.clave_box, 2)

            pygame.display.flip()
            self.clock.tick(30)

    def get_paciente(self):
        return self.paciente


if __name__ == "__main__":
    login = Login()
    login.run()
    paciente = login.get_paciente()
    if paciente:
        print("Paciente listo para el juego:", paciente)
