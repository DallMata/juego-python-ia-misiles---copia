import pygame
import sys
import requests
from spaceEvation.constants import *
from config import URL  # URL efectiva (local o remota)


class Login:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        pygame.display.set_caption("Login")

        # ---------- Paleta ----------
        self.color_primary       = pygame.Color('#03A1CF')
        self.color_primary_hover = pygame.Color('#40B7EA')
        self.color_accent        = pygame.Color('#FFBD59')
        self.color_text          = pygame.Color('#FFFFFF')
        self.color_muted         = pygame.Color('#7A8A99')
        self.color_chip          = pygame.Color('#1E3C5A')

        # ---------- Fuentes ----------
        self.title_font = pygame.font.SysFont("arial", 48, bold=True)
        self.font       = pygame.font.Font(None, 32)
        self.label_font = pygame.font.SysFont("courier", 20, bold=True)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.button_font = pygame.font.SysFont("courier", 24, bold=True)

        # ---------- Fondo (foto, sin overlay) ----------
        try:
            self.background_image = pygame.image.load("sprites/fondo_kineplay_letras_2.png")
            self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except Exception:
            self.background_image = None

        # Campos de entrada
        self.dni_box   = pygame.Rect(0, 0, 320, 40)   # Acepta Email o DNI
        self.clave_box = pygame.Rect(0, 0, 320, 40)

        self.color_inactive = self.color_chip
        self.color_active   = self.color_accent
        self.dni_color   = self.color_inactive
        self.clave_color = self.color_inactive

        self.dni_text   = ''   # Email o DNI
        self.clave_text = ''
        self.active_dni = False
        self.active_clave = False

        # Toggle mostrar/ocultar password
        self.show_password = False
        self.show_toggle = pygame.Rect(0, 0, 78, 60)  # se posiciona luego
        self._layout_toggle()  # posiciona/ajusta tamaño según el campo de password

        self.done = False
        self.clock = pygame.time.Clock()

        # Posiciones
        center = self.screen.get_rect().center
        self.dni_box.center = center
        self.dni_box.y -= 50
        self.clave_box.center = center
        self.clave_box.y += 20

        # Botón Ingresar
        self.btn_login = pygame.Rect(0, 0, 200, 50)
        self.btn_login.centerx = center[0]
        self.btn_login.y = self.clave_box.bottom + 40

        # Etiquetas
        self.dni_label_pos   = (self.dni_box.x,   self.dni_box.y - 28)
        self.clave_label_pos = (self.clave_box.x, self.clave_box.y - 28)

        # Resultado del login (compat con app.py usa "paciente")
        self.usuario = None
        self.paciente = None

        # Posicionar toggle de password (a la derecha del campo)
        self.show_toggle.center = (self.clave_box.right - 40, self.clave_box.centery)

    def _layout_toggle(self):
        """Encaja el toggle dentro de la caja de password, con ancho según el texto."""
        label = "Ver" if not self.show_password else "Ocultar"
        tw, th = self.small_font.size(label)

        pad_x = 12  # padding horizontal dentro del pill
        margin = 2  # separación del borde interior de la caja
        h = self.clave_box.height - 2 * margin
        w = tw + 2 * pad_x
        w = min(max(w, 80), 130)  # límite razonable

        self.show_toggle.size = (w, h)
        self.show_toggle.top = self.clave_box.y + margin
        self.show_toggle.right = self.clave_box.right - margin

    # ---------- util: texto con sombra ----------
    def _text_with_shadow(self, text, font, color, pos, shadow_offset=(1, 2), shadow_alpha=150):
        txt = font.render(text, True, color)
        shd = font.render(text, True, (0, 0, 0))
        shd.set_alpha(shadow_alpha)
        self.screen.blit(shd, (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]))
        self.screen.blit(txt, pos)

    def _draw_input_text(self, text, box):
        # Texto con sombra dentro del input
        self._text_with_shadow(text, self.font, self.color_text, (box.x + 8, box.y + 8))

    def _attempt_login(self):
        self.dni_text = self.dni_text.strip()
        self.clave_text = self.clave_text.strip()
        if not (self.dni_text and self.clave_text):
            print("Por favor complete ambos campos.")
            return

        print("Enviando datos de login...")
        login_input = self.dni_text
        payload = {'password': self.clave_text}
        if '@' in login_input:
            payload['email'] = login_input
        else:
            payload['dni'] = login_input

        try:
            resp = requests.post(URL, json=payload, timeout=10)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:
                    data = {}

                self.usuario = data.get('usuario') if isinstance(data, dict) else None
                if not self.usuario and isinstance(data, dict):
                    self.usuario = data.get('paciente')

                self.paciente = self.usuario  # compat con app.py
                print("Login exitoso. Usuario:", self.usuario)
                self.done = True
            else:
                txt = resp.text[:300].replace('\n', ' ')
                print(f"Error {resp.status_code}: {txt}")
                print("Email/DNI o contraseña incorrectos.")
                self.dni_text, self.clave_text = '', ''
        except Exception as e:
            print(f"Error al conectar con el servidor: {e}")

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
                        self._attempt_login()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.dni_box.collidepoint(event.pos):
                        self.active_dni = True
                        self.active_clave = False
                    elif self.clave_box.collidepoint(event.pos):
                        self.active_clave = True
                        self.active_dni = False
                    else:
                        self.active_dni = self.active_clave = False

                    # Toggle mostrar password
                    if self.show_toggle.collidepoint(event.pos):
                        self.show_password = not self.show_password
                        self._layout_toggle()  # por si cambia el texto (Ver/Ocultar)

                    # Click botón Ingresar
                    if self.btn_login.collidepoint(event.pos):
                        self._attempt_login()

                    self.dni_color   = self.color_active if self.active_dni else self.color_inactive
                    self.clave_color = self.color_active if self.active_clave else self.color_inactive

            # ---------- Dibujo ----------
            if self.background_image:
                self.screen.blit(self.background_image, (0, 0))
            else:
                self.screen.fill((10, 14, 22))

            # Título
            self._text_with_shadow("Iniciar sesión", self.title_font, self.color_text, (240, 150))

            # Etiquetas con sombra
            self._text_with_shadow("Email / DNI:", self.label_font, self.color_text, self.dni_label_pos)
            self._text_with_shadow("Password:",    self.label_font, self.color_text, self.clave_label_pos)

            # Campos (bordes)
            pygame.draw.rect(self.screen, self.dni_color,   self.dni_box,   width=2, border_radius=8)
            pygame.draw.rect(self.screen, self.clave_color, self.clave_box, width=2, border_radius=8)

            # Texto de inputs (con máscara si corresponde)
            self._draw_input_text(self.dni_text, self.dni_box)
            pwd_to_draw = self.clave_text if self.show_password else ('*' * len(self.clave_text))
            self._draw_input_text(pwd_to_draw, self.clave_box)

            # --- Chip toggle "Ver/Ocultar" con bordes redondeados ---
            label = "Ver" if not self.show_password else "Ocultar"

            # Asegura tamaño/posición correcta por si se redimensionó
            self._layout_toggle()

            chip_surf = pygame.Surface(self.show_toggle.size, pygame.SRCALPHA)
            pygame.draw.rect(
                chip_surf,
                (self.color_chip.r, self.color_chip.g, self.color_chip.b, 190),
                chip_surf.get_rect(),
                border_radius=5  # pill redondeado
            )
            self.screen.blit(chip_surf, self.show_toggle.topleft)

            tw, th = self.small_font.size(label)
            self._text_with_shadow(
                label, self.small_font, self.color_text,
                (self.show_toggle.centerx - tw // 2, self.show_toggle.centery - th // 2)
            )

            # Botón Ingresar (hover)
            mouse = pygame.mouse.get_pos()
            btn_color = self.color_primary_hover if self.btn_login.collidepoint(mouse) else self.color_primary
            pygame.draw.rect(self.screen, btn_color, self.btn_login, border_radius=12)
            bt = "Ingresar"
            btw, bth = self.button_font.size(bt)
            self._text_with_shadow(bt, self.button_font, (255, 255, 255),
                                   (self.btn_login.centerx - btw//2, self.btn_login.centery - bth//2))

            # Hint
            self._text_with_shadow("Tip: también puedes presionar Enter", self.small_font, self.color_muted,
                                   (self.btn_login.centerx - 110, self.btn_login.bottom + 10))

            pygame.display.flip()
            self.clock.tick(30)

    # Compat con tu app.py
    def get_paciente(self):
        return self.paciente

    # Por si luego migrás app.py
    def get_usuario(self):
        return self.usuario


if __name__ == "__main__":
    login = Login()
    login.run()
    usuario = login.get_usuario()
    if usuario:
        print("Usuario listo para el juego 1:", usuario)
