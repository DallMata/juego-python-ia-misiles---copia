# assignment_detail.py
import pygame
import sys
import requests
from datetime import datetime

try:
    from config import ASIGNACIONES_URL
except ImportError:
    ASIGNACIONES_URL = "http://localhost/usuarios/asignaciones.php"

try:
    from config import JUEGOS_URL
except ImportError:
    JUEGOS_URL = None


# ---------- Utils ----------
def _to_float(v, default=0.0):
    try:
        if v is None or v == "":
            return float(default)
        return float(v)
    except (ValueError, TypeError):
        return float(default)

def _to_int(v, default=0):
    try:
        if v is None or v == "":
            return int(default)
        return int(float(v))
    except (ValueError, TypeError):
        return int(default)

def _to_ts(s, default=0.0):
    try:
        if not s:
            return float(default)
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()
    except Exception:
        return float(default)

def _infer_juegos_url_from_asignaciones(asignaciones_url: str) -> str:
    if not asignaciones_url:
        return "http://localhost/usuarios/juegos.php"
    if asignaciones_url.endswith("asignaciones.php"):
        return asignaciones_url.replace("asignaciones.php", "juegos.php")
    return asignaciones_url.rstrip("/") + "/juegos.php"


class AssignmentDetailScreen:
    """Pantalla intermedia con texto sombreado para legibilidad sobre fondo fotográfico."""

    def __init__(self, screen, paciente, asignacion_row):
        self.screen = screen
        self.W, self.H = self.screen.get_size()
        self.paciente = paciente or {}
        self.asig = asignacion_row or {}

        # Endpoints
        self.asignaciones_url = ASIGNACIONES_URL
        self.juegos_url = JUEGOS_URL or _infer_juegos_url_from_asignaciones(self.asignaciones_url)

        # UI core
        self.clock = pygame.time.Clock()
        self.done = False
        self.result = None  # "play" | "back"

        # Paleta
        self.color_primary        = pygame.Color('#03A1CF')
        self.color_primary_hover  = pygame.Color('#04B7EA')
        self.color_accent         = pygame.Color('#FFBD59')
        self.color_accent_hover   = pygame.Color('#FFD37F')
        self.color_text           = pygame.Color('#FFFFFF')
        self.color_muted          = pygame.Color('#7A8A99')
        self.color_chip           = pygame.Color('#1E3C5A')
        self.color_ok             = pygame.Color( 50,180, 80)
        self.color_stop           = pygame.Color(180, 70, 70)

        # Fondo (foto, sin overlay)
        self.background_image = None
        for path in ("sprites/fondo_kineplay_2.png", "sprites/KINEPLAY.png", "sprites/fondo_kineplay.png"):
            try:
                img = pygame.image.load(path)
                self.background_image = pygame.transform.scale(img, (self.W, self.H))
                break
            except Exception:
                self.background_image = None

        # Fuentes
        self.font_title  = pygame.font.SysFont("arial", 40, bold=True)
        self.font_body   = pygame.font.SysFont("arial", 24)
        self.font_small  = pygame.font.SysFont("arial", 18)
        self.font_button = pygame.font.SysFont("courier", 24, bold=True)

        # Botones (centrados)
        self.btn_w, self.btn_h, self.btn_gap = 180, 50, 40
        total_w = 2*self.btn_w + self.btn_gap
        x0 = (self.W - total_w)//2
        yb = self.H - self.btn_h - 24
        self.btn_play = pygame.Rect(x0,                           yb, self.btn_w, self.btn_h)
        self.btn_back = pygame.Rect(x0 + self.btn_w + self.btn_gap, yb, self.btn_w, self.btn_h)
        self.bottom_margin = (self.H - yb) + 16

        # Tabla (compacta)
        self.table_side_margin = 40
        self.table_area = pygame.Rect(self.table_side_margin, 260, self.W - 2*self.table_side_margin, 220)
        self.row_height = 36
        self.scroll_offset = 0

        # Encabezado interno del panel (barra)
        self.header_height = 32   # barra para headers dentro del panel

        # Anchos base de columnas (3 columnas: Fecha, Puntaje, Tiempo)
        self.COL_W_DATE_BASE  = 200
        self.COL_W_SCORE_BASE = 140
        self.COL_W_TIME_BASE  = 160

        # Datos
        self.stats = None
        self.plays = []
        self.stats_bottom = 260

        self._fetch_all()

    # ---------- Data ----------
    def _fetch_all(self):
        self._fetch_stats()
        self._fetch_plays()

    def _fetch_stats(self):
        try:
            params = {
                "id_asignacion": int(self.asig.get("id_asignacion")),
                "include_stats": 1,
                "auto_close": 1
            }
            r = requests.get(self.asignaciones_url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.stats = (data[0] if isinstance(data, list) and data else None)
                # Propagar campos frescos a la fila original que volverá al menú
                if isinstance(self.asig, dict) and isinstance(self.stats, dict):
                    for k in ("dificultad", "tiempo_minimo_seg", "fecha_inicio", "fecha_fin", "estado"):
                        if k in self.stats:
                            self.asig[k] = self.stats[k]
                    # también stats (pueden servir para debug/mostrar)
                    for k in ("total_jugado_seg", "cant_jugadas", "restante_seg"):
                        if k in self.stats:
                            self.asig[k] = self.stats[k]
            else:
                print("[Detail] asignaciones GET HTTP", r.status_code, r.text[:200])
        except Exception as e:
            print("[Detail] Error stats:", e)

    def _fetch_plays(self):
        try:
            params = {"id_asignacion": int(self.asig.get("id_asignacion"))}
            r = requests.get(self.juegos_url, params=params, timeout=10)
            if r.status_code == 200:
                items = r.json() if isinstance(r.json(), list) else []
                items.sort(key=lambda x: (-_to_int(x.get("puntaje"), -10 ** 9),
                                          -_to_ts(x.get("fecha"), 0.0)))
                self.plays = items
            else:
                print("[Detail] juegos GET HTTP", r.status_code, r.text[:200])
        except Exception as e:
            print("[Detail] Error plays:", e)

    # ---------- Texto con sombra ----------
    def _text_with_shadow(self, text, font, color, pos, shadow_offset=(1,2), shadow_alpha=150):
        txt = font.render(text, True, color)
        shd = font.render(text, True, (0,0,0))
        shd.set_alpha(shadow_alpha)
        self.screen.blit(shd, (pos[0]+shadow_offset[0], pos[1]+shadow_offset[1]))
        self.screen.blit(txt, pos)

    # ---------- Dibujo ----------
    def _mins(self, secs):
        try:
            return int(round((secs or 0)/60))
        except Exception:
            return 0

    def _draw_header(self):
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        else:
            self.screen.fill((10, 14, 22))

        app_title = self.asig.get("aplicacion_titulo") or "Juego"
        self._text_with_shadow(app_title, self.font_title, self.color_text, (40, 30))

        pac_name = f"{self.asig.get('paciente_nombre','')} {self.asig.get('paciente_apellido','')}".strip()
        if pac_name:
            chip = pygame.Surface((300, 34), pygame.SRCALPHA)
            chip.fill(self.color_chip); chip.set_alpha(180)
            self.screen.blit(chip, (40, 85))
            self._text_with_shadow(f"Paciente: {pac_name}", self.font_small, self.color_text, (48, 90))

        estado = int(self.stats.get("estado", self.asig.get("estado", 1))) if self.stats else int(self.asig.get("estado", 1))
        est_text = "Activa" if estado == 1 else "Cerrada"
        est_col = self.color_ok if estado == 1 else self.color_stop
        pill = pygame.Surface((190, 34), pygame.SRCALPHA)
        pill.fill(est_col); pill.set_alpha(200)
        self.screen.blit(pill, (360, 85))
        self._text_with_shadow(f"Asignación: {est_text}", self.font_small, (255,255,255), (368, 90))

    def _draw_stats(self):
        x0, y0 = 40, 130
        line = 40

        source = self.stats or self.asig
        fi = source.get("fecha_inicio", "?")
        ff = source.get("fecha_fin", "?")
        minimo_seg = _to_int(source.get("tiempo_minimo_seg"), 0)
        total_seg = int(round(_to_float((self.stats or {}).get("total_jugado_seg", 0.0), 0.0)))
        restante_seg = max(minimo_seg - total_seg, 0)

        # (label, value) -> label en accent como los headers de la tabla
        rows = [
            ("Fecha Inicio:", fi),
            ("Fecha Fin:", ff),
            ("Tiempo Asignado:", f"{self._mins(minimo_seg)} min"),
            ("Tiempo Acumulado:", f"{self._mins(total_seg)} min"),
            ("Restante:", f"{self._mins(restante_seg)} min"),
        ]

        # Calculamos ancho máx. del label para alinear valores
        max_label_w = 0
        for label, _ in rows:
            lw, _ = self.font_body.size(label)
            if lw > max_label_w:
                max_label_w = lw

        # Un pequeño espacio entre label y valor
        gap = 18
        val_x = x0 + max_label_w + gap

        y = y0
        for label, value in rows:
            # Label en color_accent (igual que headers)
            self._text_with_shadow(label, self.font_body, self.color_accent, (x0, y))
            # Valor en blanco
            self._text_with_shadow(str(value), self.font_body, self.color_text, (val_x, y))
            y += line

        self.stats_bottom = y0 + len(rows) * line

        # Separador bajo las stats
        sep = pygame.Surface((self.W - 80, 2), pygame.SRCALPHA)
        sep.fill((self.color_muted.r, self.color_muted.g, self.color_muted.b, 160))
        self.screen.blit(sep, (40, self.stats_bottom - 10))

    def _layout_table(self):
        top = max(self.stats_bottom + 18, 300)
        available = self.H - self.bottom_margin - top
        target_h = 220
        height = max(140, min(target_h, available))

        self.table_area.update(self.table_side_margin, top, self.W - 2*self.table_side_margin, height)

        avail_w = self.table_area.width - 16
        d, s, t = self.COL_W_DATE_BASE, self.COL_W_SCORE_BASE, self.COL_W_TIME_BASE
        base_total = d + s + t + 2*20  # 3 cols, 2 separadores
        scale = min(1.0, avail_w / base_total) if base_total > 0 else 1.0
        self.COL_W_DATE  = int(d * scale)
        self.COL_W_SCORE = int(s * scale)
        self.COL_W_TIME  = int(t * scale)

        col_x = self.table_area.x + 16
        self.col_xs = [
            col_x,
            col_x + self.COL_W_DATE + 20,
            col_x + self.COL_W_DATE + 20 + self.COL_W_SCORE + 20
        ]

    def _draw_table(self):
        self._layout_table()

        # Panel
        panel = pygame.Surface((self.table_area.width, self.table_area.height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 90))
        self.screen.blit(panel, (self.table_area.x, self.table_area.y))

        # ----- Barra de encabezado dentro del panel -----
        header_rect = pygame.Rect(self.table_area.x, self.table_area.y, self.table_area.width, self.header_height)
        header_bg = pygame.Surface((header_rect.width, header_rect.height), pygame.SRCALPHA)
        header_bg.fill((255, 255, 255, 22))            # leve contraste
        self.screen.blit(header_bg, header_rect.topleft)

        # Títulos (naranja) dentro del header (ya no los atraviesa el borde)
        headers = ["Fecha", "Puntaje", "Tiempo (min)"]
        for i, h in enumerate(headers):
            self._text_with_shadow(h, self.font_body, self.color_accent, (self.col_xs[i], header_rect.y + 6))

        # Borde del panel al final, para que no tape el texto
        pygame.draw.rect(self.screen, self.color_muted, self.table_area, width=2, border_radius=10)

        # Filas (comienzan debajo del header)
        rows_per_page = max(1, (self.table_area.height - self.header_height) // self.row_height)
        start = self.scroll_offset
        end = min(len(self.plays), start + rows_per_page)

        for idx in range(start, end):
            y = self.table_area.y + self.header_height + (idx - start)*self.row_height + 6
            j = self.plays[idx]
            fecha   = str(j.get("fecha", "-"))
            puntaje = _to_int(j.get("puntaje"), 0)
            secs    = _to_float(j.get("tiempo_jugado"), 0.0)
            tmin    = int(round(secs / 60.0))

            if (idx % 2) == 0:
                r = pygame.Rect(self.table_area.x+4, y-4, self.table_area.width-8, self.row_height-2)
                stripe = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                stripe.fill((255,255,255,20))
                self.screen.blit(stripe, (r.x, r.y))

            self._text_with_shadow(fecha,        self.font_small, self.color_text, (self.col_xs[0], y))
            self._text_with_shadow(str(puntaje), self.font_small, self.color_text, (self.col_xs[1], y))
            self._text_with_shadow(f"{tmin}",    self.font_small, self.color_text, (self.col_xs[2], y))

        # Indicador de página — dentro del panel (abajo-derecha)
        if len(self.plays) > rows_per_page:
            page  = (self.scroll_offset // rows_per_page) + 1
            pages = (len(self.plays) + rows_per_page - 1) // rows_per_page
            pi = f"Página {page}/{pages}  (Rueda/↑↓)"
            surf = self.font_small.render(pi, True, self.color_muted)
            px = self.table_area.right - surf.get_width() - 10
            py = self.table_area.bottom - surf.get_height() - 8
            self._text_with_shadow(pi, self.font_small, self.color_muted, (px, py))

    def _draw_buttons(self):
        mouse = pygame.mouse.get_pos()

        # INVERTIDO:
        # Jugar => estilo "Volver": base = accent, hover = accent_hover
        play_color = self.color_accent_hover if self.btn_play.collidepoint(mouse) else self.color_accent
        # Volver => estilo "Jugar": base = primary, hover = primary_hover
        back_color = self.color_primary_hover if self.btn_back.collidepoint(mouse) else self.color_primary

        pygame.draw.rect(self.screen, play_color, self.btn_play, border_radius=12)
        pygame.draw.rect(self.screen, back_color, self.btn_back, border_radius=12)

        # Texto con sombra centrado, acorde al contraste
        tw1, th1 = self.font_button.size("Jugar")
        tw2, th2 = self.font_button.size("Volver")

        # Jugar sobre acento: texto negro para mejor contraste
        self._text_with_shadow("Jugar", self.font_button, (0, 0, 0),
                               (self.btn_play.centerx - tw1 // 2, self.btn_play.centery - th1 // 2))
        # Volver sobre primario: texto blanco
        self._text_with_shadow("Volver", self.font_button, (255, 255, 255),
                               (self.btn_back.centerx - tw2 // 2, self.btn_back.centery - th2 // 2))

        # Si la asignación está cerrada, bloqueamos Jugar como antes
        estado = int(self.stats.get("estado", self.asig.get("estado", 1))) if self.stats else int(
            self.asig.get("estado", 1))
        if estado == 0:
            s = pygame.Surface((self.btn_play.width, self.btn_play.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 120))
            self.screen.blit(s, self.btn_play.topleft)
            warn = "Asignación cerrada"
            tw, th = self.font_small.size(warn)
            self._text_with_shadow(warn, self.font_small, (255, 220, 220),
                                   (self.btn_play.centerx - tw // 2, self.btn_play.bottom + 8))

    # ---------- Loop ----------
    def run(self):
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.btn_play.collidepoint(event.pos):
                        estado = int(self.stats.get("estado", self.asig.get("estado", 1))) if self.stats else int(self.asig.get("estado", 1))
                        if estado == 1:
                            self.result = "play"
                            self.done = True
                    elif self.btn_back.collidepoint(event.pos):
                        self.result = "back"
                        self.done = True
                    if self.table_area.collidepoint(pygame.mouse.get_pos()):
                        if event.button == 4:
                            self.scroll_offset = max(0, self.scroll_offset - 1)
                        if event.button == 5:
                            max_off = max(0, len(self.plays) - ((self.table_area.height - self.header_height) // self.row_height))
                            self.scroll_offset = min(max_off, self.scroll_offset + 1)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.scroll_offset = max(0, self.scroll_offset - 1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        max_off = max(0, len(self.plays) - ((self.table_area.height - self.header_height) // self.row_height))
                        self.scroll_offset = min(max_off, self.scroll_offset + 1)
                    elif event.key == pygame.K_ESCAPE:
                        self.result = "back"; self.done = True

            self._draw_header()
            self._draw_stats()
            self._draw_table()
            self._draw_buttons()

            pygame.display.flip()
            self.clock.tick(60)

        return self.result
