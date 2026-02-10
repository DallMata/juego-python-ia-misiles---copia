import pygame
import sys
import requests
from spaceEvation.constants import *
from config import ASIGNACIONES_URL  # 👈 usamos asignaciones.php

# Intentar importar la pantalla intermedia
try:
    from assignment_detail import AssignmentDetailScreen
except ImportError:
    try:
        from assignments_detail import AssignmentDetailScreen
    except ImportError as e:
        AssignmentDetailScreen = None
        print("[Aviso] No se pudo importar AssignmentDetailScreen:", e)

# Intentar traer APPS_URL; si no, se infiere desde ASIGNACIONES_URL
try:
    from config import APPS_URL
except ImportError:
    APPS_URL = None


def _infer_apps_url_from_asignaciones(asignaciones_url: str) -> str:
    if not asignaciones_url:
        return "http://localhost/usuarios/aplicaciones.php"
    if asignaciones_url.endswith("asignaciones.php"):
        return asignaciones_url.replace("asignaciones.php", "aplicaciones.php")
    return asignaciones_url.rstrip("/") + "/aplicaciones.php"


def _safe_int(v, default=0):
    try:
        if v is None or v == "":
            return int(default)
        return int(float(v))
    except (ValueError, TypeError):
        return int(default)


class Menu:
    def __init__(self, paciente):
        pygame.init()
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        pygame.display.set_caption("Menú de Juegos")

        # ---------- Paleta ----------
        self.color_primary       = pygame.Color('#03A1CF')
        self.color_primary_hover = pygame.Color('#04B7EA')
        self.color_accent        = pygame.Color('#FFBD59')
        self.color_text          = pygame.Color('#FFFFFF')
        self.color_muted         = pygame.Color('#7A8A99')
        self.color_chip          = pygame.Color('#1E3C5A')

        # ---------- Fuentes ----------
        self.title_font        = pygame.font.SysFont("arial", 48, bold=True)
        self.button_font       = pygame.font.SysFont("courier", 24, bold=True)
        self.description_font  = pygame.font.SysFont("comicsansms", 20)
        self.small_font        = pygame.font.SysFont("arial", 18)

        # ---------- Fondo (foto, sin overlay) ----------
        try:
            self.background_image = pygame.image.load("sprites/fondo_kineplay_1.png")
            self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except Exception:
            self.background_image = None

        # Colores de botones
        self.button_color       = self.color_primary
        self.button_hover_color = self.color_accent
        self.text_color         = self.color_text
        self.description_text_color = pygame.Color('#FFD700')
        self.description_bg_color   = pygame.Color(0, 0, 0, 180)  # semi-transparente

        self.buttons = []

        self.paciente = paciente or {}
        self.dni = self.paciente.get('dni')

        # Mapa de descripciones por app
        self.apps_url = APPS_URL or _infer_apps_url_from_asignaciones(ASIGNACIONES_URL)
        self.app_desc_map = {}  # { id_aplicacion: descripcion }

        self.load_applications(self.dni)

        self.back_button = pygame.Rect(SCREEN_WIDTH - 150, SCREEN_HEIGHT - 70, 130, 50)

        self.clock = pygame.time.Clock()
        self.done = False

    # ---------- Util: texto con sombra ----------
    def _text_with_shadow(self, text, font, color, pos, shadow_offset=(1, 2), shadow_alpha=150):
        txt = font.render(text, True, color)
        shd = font.render(text, True, (0, 0, 0))
        shd.set_alpha(shadow_alpha)
        self.screen.blit(shd, (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]))
        self.screen.blit(txt, pos)

    def _normalize_title(self, raw_title: str) -> str:
        t = (raw_title or "").strip().lower()
        if 'space' in t and 'ev' in t:
            return "Space Evation"
        if ('platform' in t or 'plataform' in t) and 'jump' in t:
            return "Plataform Jump"
        return raw_title or "Juego"

    def _fetch_all_apps(self):
        """Descarga todas las aplicaciones (id_aplicacion, titulo, descripcion) y llena self.app_desc_map."""
        try:
            r = requests.get(self.apps_url, timeout=10)
            if r.status_code != 200:
                print(f"[Apps] HTTP {r.status_code}: {r.text[:200]}")
                return
            rows = r.json() if isinstance(r.json(), list) else []
            for row in rows:
                app_id = row.get("id_aplicacion")
                desc = (row.get("descripcion") or "").strip()
                if app_id is not None:
                    self.app_desc_map[int(app_id)] = desc
        except Exception as e:
            print("[Apps] Error obteniendo aplicaciones:", e)

    def _get_observacion(self, row: dict) -> str:
        """Usa observación de la fila (si viene) o la trae del mapa de aplicaciones."""
        for key in ("observacion", "aplicacion_observacion", "descripcion", "descripcion_app"):
            val = row.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        app_id = row.get("id_aplicacion")
        if app_id is not None:
            desc = self.app_desc_map.get(int(app_id))
            if desc:
                return desc
        return "Observación no disponible. Click para ver detalles."

    def load_applications(self, dni_paciente):
        if not dni_paciente:
            print("Sin DNI: no puedo buscar asignaciones.")
            return

        def fetch(url):
            params = {"dni_paciente": dni_paciente, "activas": 1, "estado": 1}
            resp = requests.get(url, params=params, timeout=10)
            return resp

        try:
            resp = fetch(ASIGNACIONES_URL)
            if resp.status_code == 404 and "/usuarios/" in resp.url:
                alt_url = ASIGNACIONES_URL.replace("/usuarios/", "/")
                print("[Asignaciones] 404, probando fallback:", alt_url)
                resp = fetch(alt_url)

            if resp.status_code != 200:
                print(f"[Asignaciones] HTTP {resp.status_code}: {resp.text[:300]}")
                print("[Asignaciones] URL usada:", resp.url)
                return

            data = resp.json()
            filas = data if isinstance(data, list) else []
            if not filas:
                print("[Asignaciones] Vacías para DNI:", dni_paciente)
                print("[Asignaciones] URL:", resp.url)
                return

            # Traemos descripciones de apps una sola vez
            self._fetch_all_apps()

            y_pos = SCREEN_HEIGHT // 2 - (80 * len(filas) // 2)
            for row in filas:
                title_raw = row.get('aplicacion_titulo') or row.get('titulo') or row.get('nombre')
                title = self._normalize_title(title_raw)

                # Normalizar dificultad por las dudas (si llega como string)
                row['dificultad'] = _safe_int(row.get('dificultad'), 1)

                # Hover = observación de la app
                desc = self._get_observacion(row)

                button_rect = pygame.Rect(0, 0, 520, 56)
                button_rect.center = (SCREEN_WIDTH // 2, y_pos)
                self.buttons.append({
                    "rect": button_rect,
                    "title": title,
                    "description": desc,
                    "asig": row,   # 👈 acá viaja también `dificultad`
                })
                y_pos += 180

            print("[Asignaciones] Cargadas:", [b["title"] for b in self.buttons])
            print("[Asignaciones] Desde:", resp.url)

        except requests.RequestException as e:
            print(f"Error al cargar las asignaciones: {e}")
        except Exception as e:
            print(f"Error parseando asignaciones: {e}")

    # ---------- Header con sombra ----------
    def _draw_header(self):
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        else:
            self.screen.fill((10, 14, 22))

        self._text_with_shadow("Aplicaciones asignadas", self.title_font, self.color_text, (40, 30))

        # Chip con el nombre del paciente
        pac_name = f"{self.paciente.get('nombre','')} {self.paciente.get('apellido','')}".strip()
        if pac_name:
            chip = pygame.Surface((300, 34), pygame.SRCALPHA)
            chip.fill(self.color_chip); chip.set_alpha(180)
            self.screen.blit(chip, (40, 90))
            self._text_with_shadow(f"Paciente: {pac_name}", self.small_font, self.color_text, (48, 95))

    # ---------- Botón de app ----------
    def draw_button(self, button_info):
        mouse_pos = pygame.mouse.get_pos
        hovered = button_info["rect"].collidepoint(pygame.mouse.get_pos())
        color = self.color_primary if hovered else self.color_accent
        # Botón
        pygame.draw.rect(self.screen, color, button_info["rect"], border_radius=12)

        # Texto con sombra centrado
        label = button_info["title"]
        tw, th = self.button_font.size(label)
        tx = button_info["rect"].centerx - tw // 2
        ty = button_info["rect"].centery - th // 2
        self._text_with_shadow(label, self.button_font, (255, 255, 255), (tx, ty))

        # Hover: burbuja de observación
        if hovered:
            self.draw_description(button_info["description"], (button_info["rect"].centerx, button_info["rect"].bottom))

    # ---------- Botón Volver ----------
    def draw_back_button(self):
        hovered = self.back_button.collidepoint(pygame.mouse.get_pos())
        color = self.color_accent if hovered else self.color_primary
        pygame.draw.rect(self.screen, color, self.back_button, border_radius=10)
        tw, th = self.button_font.size("Volver")
        self._text_with_shadow("Volver", self.button_font, (255, 255, 255),
                               (self.back_button.centerx - tw//2, self.back_button.centery - th//2))

    # ---------- Tooltip/Descripción ----------
    def draw_description(self, description, anchor_midbottom):
        # Wrap simple a ~420px
        max_width = 420
        words = description.split()
        lines = []
        cur = ""
        for w in words:
            test = f"{cur} {w}".strip()
            if self.description_font.size(test)[0] <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)

        line_h = self.description_font.get_linesize()
        box_w = max(self.description_font.size(l)[0] for l in lines) + 20
        box_h = line_h * len(lines) + 14

        # Posicionar por debajo del botón, pero sin salir de pantalla
        x_center, y_top = anchor_midbottom[0], anchor_midbottom[1] + 14
        left = max(10, min(x_center - box_w // 2, SCREEN_WIDTH - box_w - 10))
        top = min(y_top, SCREEN_HEIGHT - box_h - 10)

        # Panel semi-transparente
        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        panel.fill(self.description_bg_color)
        self.screen.blit(panel, (left, top))

        # Texto con sombra
        y = top + 7
        for line in lines:
            self._text_with_shadow(line, self.description_font, self.description_text_color, (left + 10, y))
            y += line_h

    # ---------- Loop ----------
    def run(self):
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for button in self.buttons:
                        if button["rect"].collidepoint(event.pos):
                            # Abrimos la pantalla intermedia
                            if AssignmentDetailScreen is None:
                                print("[Aviso] No se encontró AssignmentDetailScreen; yendo directo al juego.")
                                self.done = True
                                # 👉 Ahora devolvemos (title, asig) para poder leer dificultad
                                return (button["title"], button["asig"])

                            detail = AssignmentDetailScreen(self.screen, self.paciente, button["asig"])
                            res = detail.run()
                            if res == "play":
                                self.done = True
                                # 👉 Devolvemos el título y TODA la fila de asignación (incluye dificultad)
                                return (button["title"], button["asig"])
                            # Si fue "back", seguimos en este menú

                    if self.back_button.collidepoint(event.pos):
                        print("Botón 'Volver' presionado")
                        self.done = True
                        return None

            # Dibujo
            if self.background_image:
                self.screen.blit(self.background_image, (0, 0))
            else:
                self.screen.fill((10, 14, 22))

            self._draw_header()
            for button in self.buttons:
                self.draw_button(button)
            self.draw_back_button()

            pygame.display.flip()
            self.clock.tick(30)


if __name__ == "__main__":
    dni_paciente = "12345678"
    menu = Menu({"dni": dni_paciente})
    result = menu.run()
    if result is None:
        print("Volviendo al login...")
    else:
        print("Seleccionado:", result)
