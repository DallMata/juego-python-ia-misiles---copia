import pygame
import sys
import requests
from constants import *

class Login:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        pygame.display.set_caption("Login")

        self.font = pygame.font.Font(None, 32)
        self.label_font = pygame.font.SysFont("courier", 20, bold=True)  # Fuente para el texto "ID:"
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
        self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # Calcular las posiciones centradas
        self.input_box.center = self.screen.get_rect().center
        self.input_box.y += 20  # Ajustar verticalmente
        self.label_box.midbottom = (self.input_box.centerx, self.input_box.top - 5)  # Posicionar el texto "ID:" sobre el campo de texto

        self.paciente = None  # Para almacenar los datos del paciente

    def run(self):
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if self.active:
                        if event.key == pygame.K_RETURN:
                            # Enviar solicitud para buscar al paciente por DNI
                            url = f'http://localhost:80/usuarios/pacientes.php?dni={self.text}'
                            response = requests.get(url)

                            # Verificar la respuesta del servidor
                            if response.status_code == 200:  # Si el paciente existe
                                self.paciente = response.json()  # Obtener los datos del paciente
                                print(f"Paciente encontrado: {self.paciente}")  # Manejar el objeto paciente como quieras
                                dni = self.paciente.get('dni')
                                print(f"DNI:  {dni}")
                                self.done = True  # Continuar con el flujo del juego
                            else:
                                print("Paciente no encontrado o error en la solicitud.")
                                print(f"Error en la solicitud: {response.status_code}, Detalles: {response.text}")
                                self.text = ''  # Limpiar el campo de texto

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
            label_text = self.label_font.render("INGRESE SU DNI:", True, (255, 255, 255))
            self.screen.blit(label_text, self.label_box)

            # Dibujar el campo de texto y el borde
            txt_surface = self.font.render(self.text, True, (255, 255, 255))  # Color del texto blanco
            width = max(200, txt_surface.get_width() + 10)
            self.input_box.w = width
            self.screen.blit(txt_surface, (self.input_box.x + 5, self.input_box.y + 5))
            pygame.draw.rect(self.screen, self.color, self.input_box, 2)
            pygame.display.flip()
            self.clock.tick(30)

    def get_paciente(self):
        return self.paciente  # Método para obtener el paciente

if __name__ == "__main__":
    login = Login()
    login.run()

    # Aquí puedes acceder al paciente después de que se haya encontrado
    paciente = login.get_paciente()
    if paciente:
        print("Paciente listo para el juego:", paciente)
        # Aquí puedes inicializar tu juego y pasarle la información del paciente
        # game = Game(paciente)
        # game.run()
