import pygame
import sys
import requests
from spaceEvation.constants import *


class Menu:
    def __init__(self, paciente):
        pygame.init()
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        pygame.display.set_caption("Menu")

        self.font = pygame.font.Font(None, 32)
        self.button_font = pygame.font.SysFont("courier", 24, bold=True)
        self.description_font = pygame.font.SysFont("comicsansms", 20)

        # Cargar la imagen de fondo
        self.background_image = pygame.image.load("sprites/KINEPLAY.png")
        self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # Configuración de colores
        self.button_color = pygame.Color('#03A1CF')
        self.button_hover_color = pygame.Color('#FFBD59')
        self.text_color = pygame.Color('white')
        self.description_text_color = pygame.Color('#FFD700')
        self.description_bg_color = pygame.Color('black')

        # Lista de botones y sus textos
        self.buttons = []

        # Info del paciente
        self.paciente = paciente
        self.dni = self.paciente.get('dni')

        # Obtener aplicaciones del paciente
        self.load_applications(self.dni)

        # Añadir botón de regreso
        self.back_button = pygame.Rect(SCREEN_WIDTH - 150, SCREEN_HEIGHT - 70, 130, 50)

        self.clock = pygame.time.Clock()
        self.done = False
        self.back_pressed = False  # Variable para indicar si se presionó el botón de regreso

    def load_applications(self, dni_paciente):
        url = f"http://ec2-34-202-72-75.compute-1.amazonaws.com/phpmyadmin/pacientes.php?dni={dni_paciente}&action=aplicaciones"

        try:
            response = requests.get(url)
            response.raise_for_status()
            aplicaciones = response.json()
            print(aplicaciones)
            y_pos = SCREEN_HEIGHT // 2 - (30 * len(aplicaciones))
            for app in aplicaciones:
                button_rect = pygame.Rect(0, 0, 500, 50)
                button_rect.center = (SCREEN_WIDTH // 2, y_pos)
                self.buttons.append({
                    "rect": button_rect,
                    "title": app['titulo'],
                    "description": app['descripcion']
                })
                y_pos += 150
        except requests.RequestException as e:
            print(f"Error al cargar las aplicaciones: {e}")

    def draw_button(self, button_info):
        mouse_pos = pygame.mouse.get_pos()
        color = self.button_hover_color if button_info["rect"].collidepoint(mouse_pos) else self.button_color

        pygame.draw.rect(self.screen, color, button_info["rect"], border_radius=10)

        text_surf = self.button_font.render(button_info["title"], True, self.text_color)
        text_rect = text_surf.get_rect(center=button_info["rect"].center)
        self.screen.blit(text_surf, text_rect)

        if button_info["rect"].collidepoint(mouse_pos):
            self.draw_description(button_info["description"], button_info["rect"].midbottom)

    def draw_back_button(self):
        # Dibujar el botón de regreso
        pygame.draw.rect(self.screen, self.button_color, self.back_button, border_radius=10)
        back_text = self.button_font.render("Volver", True, self.text_color)
        back_text_rect = back_text.get_rect(center=self.back_button.center)
        self.screen.blit(back_text, back_text_rect)

    def draw_description(self, description, position):
        words = description.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if self.description_font.size(test_line)[0] < 400:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        text_height = self.description_font.get_linesize()
        box_height = text_height * len(lines) + 10
        box_rect = pygame.Rect(position[0] - 200, position[1] + 20, 400, box_height)
        pygame.draw.rect(self.screen, self.description_bg_color, box_rect, border_radius=10)

        y_offset = box_rect.top + 5
        for line in lines:
            line_surf = self.description_font.render(line, True, self.description_text_color)
            self.screen.blit(line_surf, (box_rect.left + 10, y_offset))
            y_offset += text_height

    def run(self):
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Verificar si se clicó en un botón de aplicaciones
                    for button in self.buttons:
                        if button["rect"].collidepoint(event.pos):
                            print(f"Opción seleccionada: {button['title']}")
                            self.done = True
                            return button["title"]  # Retorna el título del botón seleccionado

                    # Verificar si se clicó en el botón "Volver"
                    if self.back_button.collidepoint(event.pos):
                        print("Botón 'Volver' presionado")
                        self.done = True
                        return None  # Regresar al login

            # Dibujar la imagen de fondo
            self.screen.blit(self.background_image, (0, 0))

            # Dibujar botones de aplicaciones
            for button in self.buttons:
                self.draw_button(button)

            # Dibujar botón de regresar
            self.draw_back_button()

            pygame.display.flip()
            self.clock.tick(30)
        # No es necesario este chequeo aquí, ya que se maneja en la detección de eventos


if __name__ == "__main__":
    dni_paciente = "12345678"  # Aquí el DNI del paciente logueado
    menu = Menu(dni_paciente)
    result = menu.run()  # Guardar el resultado de la ejecución del menú

    if result is None:
        # Lógica para volver al login
        print("Volviendo al login...")
        # Aquí debes llamar a tu lógica de login
