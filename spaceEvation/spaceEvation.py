import math
import random
import requests
import pygame
from gameMenu import Menu
from plataformJump.plataformJump import Game as plataformJump

from config import JUEGOS_URL, REQUEST_TIMEOUT, DEFAULT_HEADERS

import json
from datetime import datetime

import cv2
import mediapipe as mp
from pygame.locals import *

from spaceEvation.globals import game_speed  # Si globals tiene un __init__.py, si no, deja así.
import globals
from spaceEvation.background import Background
from spaceEvation.constants import *
from spaceEvation.enemy import Enemy
from spaceEvation.events import *
from spaceEvation.player import Player
from spaceEvation.webcam import Webcam


class Game:
    def __init__(self, paciente, asignacion=None, dificultad=None):
        # --- Pygame / pantalla ---
        pygame.init()
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        pygame.display.set_caption("Misiles")
        self.clock = pygame.time.Clock()
        self.running = True
        self.started = False

        # --- Estado de usuario/asignación ---
        self.paciente   = paciente or {}
        self.asignacion = asignacion or {}

        # clamp para Space Evation (1..5)
        def _clamp(x, lo, hi):
            try:
                x = int(x)
            except Exception:
                x = 1
            return max(lo, min(hi, x))

        # prioridad: param > asignacion.dificultad > 1
        if dificultad is not None:
            self.dificultad = _clamp(dificultad, 1, 5)
        elif isinstance(self.asignacion, dict) and 'dificultad' in self.asignacion:
            self.dificultad = _clamp(self.asignacion.get('dificultad'), 1, 5)
        else:
            self.dificultad = 1

        print(f"[SpaceEvation] Dificultad aplicada: {self.dificultad}")

        # --- Mediapipe manos ---
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # --- fuentes / fondo ---
        self.font = pygame.font.Font('freesansbold.ttf', 32)
        self.smaller_font = pygame.font.Font('freesansbold.ttf', 22)
        self.background = Background()

        # --- rastros / tiempo impresión de ángulos ---
        self.last_angle_print_time = 0
        self.top_point_trace = []
        self.angle_trace = []

        # --- paciente/dni visibles en logs ---
        print(f'PACIENTE: {self.paciente}')
        self.dni = self.paciente.get('dni')
        print(f"DNI EN GAME:  {self.dni}")

        # --- menú y otros juegos (como antes) ---
        self.menu = Menu(self.paciente)
        self.PlataformJump = plataformJump

        # --- Imágenes de instrucciones de movimiento ---
        try:
            self.hand_neutral_image = self.load_instruction_image(
                "spaceEvation/sprites/mano_sideways_neutra_sin_flecha.png"
            )

            self.hand_flexion_image = self.load_instruction_image(
                "spaceEvation/sprites/mano_flexion_45.png"
            )

            self.hand_extension_image = self.load_instruction_image(
                "spaceEvation/sprites/mano_extension_45.png"
            )

            self.hand_rotate_up_image = self.load_instruction_image(
                "spaceEvation/sprites/gire_mano_hacia_arriba.png"
            )

        except Exception as e:
            print("[UI] No se pudieron cargar las imágenes de instrucciones:", e)

            self.hand_neutral_image = None
            self.hand_flexion_image = None
            self.hand_extension_image = None
            self.hand_rotate_up_image = None

        # --- inicialización del juego ---
        self.initialize()

    def load_instruction_image(self, path, max_width=280, max_height=280):
        """
        Carga una imagen transparente y la escala sin deformar su proporción.
        """
        image = pygame.image.load(path).convert_alpha()

        original_width = image.get_width()
        original_height = image.get_height()

        if original_width <= 0 or original_height <= 0:
            return image

        scale_factor = min(
            max_width / original_width,
            max_height / original_height
        )

        new_width = max(1, int(original_width * scale_factor))
        new_height = max(1, int(original_height * scale_factor))

        return pygame.transform.smoothscale(
            image,
            (new_width, new_height)
        )

    def render_instruction_image(self, image, center_y=None):
        if image is None:
            return

        if center_y is None:
            center_y = SCREEN_HEIGHT // 2 - 150

        image_rect = image.get_rect(
            center=(
                SCREEN_WIDTH // 2,
                center_y
            )
        )

        self.screen.blit(image, image_rect)
    def get_intro_animation_frame(self):
        """
        Secuencia:
        neutra -> flexión -> neutra -> extensión
        """
        frames = [
            self.hand_neutral_image,
            self.hand_flexion_image,
            self.hand_neutral_image,
            self.hand_extension_image
        ]

        elapsed_time = (
                pygame.time.get_ticks()
                - self.intro_animation_start
        )

        frame_index = (
                              elapsed_time // self.INTRO_FRAME_DURATION
                      ) % len(frames)

        return frames[int(frame_index)]

    def initialize(self):
        self.start_time = pygame.time.get_ticks()
        self.last_frame_time = self.start_time

        # Player con dificultad
        self.player = Player(dificultad=self.dificultad)

        self.movement = 0

        # Timers de enemigos
        self.enemy_timer = 1000
        pygame.time.set_timer(ADD_ENEMY, self.enemy_timer)

        self.enemies = pygame.sprite.Group()
        self.lost = False
        self.score = 0

        # Webcam
        self.webcam = Webcam().start()

        # bounding de mano
        self.max_hand_surf_height = 0
        self.hand_left_x = 0
        self.hand_right_x = 0
        self.hand_top_y = 0
        self.hand_bottom_y = 0

        # Pausa por mano
        self.no_hand = True
        self.hand_front = False  # True = palma de frente -> pausar

        # Estados de orientación de la mano
        self.hand_front = False  # La palma está mirando a cámara
        self.hand_not_upright = False  # Los dedos no están apuntando hacia arriba
        self.hand_tilted = False  # La mano está inclinada hacia adelante

        # Detección palma/canto usando la normal 3D de la palma
        self.PALM_FRONT_ON = 0.75
        self.PALM_FRONT_OFF = 0.6

        # Máxima inclinación permitida del eje de la mano respecto de la vertical
        self.MAX_UPRIGHT_ANGLE = 42.0

        # Detección adicional de inclinación hacia adelante
        self.TILT_ON = 0.88
        self.TILT_OFF = 0.72

        self.UPRIGHT_BAD_ON = 42.0
        self.UPRIGHT_BAD_OFF = 34.0

        # Valores suavizados
        self.palm_front_score = None
        self.hand_tilt_ratio = None
        self.HAND_SMOOTH_ALPHA = 0.15

        self.last_hand_debug_time = 0

        # Animación instructiva inicial
        self.has_detected_hand_once = False
        self.intro_animation_start = pygame.time.get_ticks()

        # Duración de cada imagen de la animación
        self.INTRO_FRAME_DURATION = 650

        # Música
        self.music_paused = False
        self._setup_music()

    def _setup_music(self):
        try:
            pygame.mixer.music.load("spaceEvation/sound/SpaceEvationMusic.mp3")
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(loops=-1, fade_ms=1500)
            print("[MUSIC] BGM reproduciendo en loop")
        except Exception as e:
            print("[MUSIC] No pude cargar bgm_loop.ogg:", e)

    def update(self, delta_time):
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False

                elif event.key == K_RETURN:
                    if self.lost:
                        self.initialize()  # Reinicia el juego si se perdió
                    else:
                        self.started = True

        if self.lost or not self.started:
            for event in events:
                if event.type == KEYDOWN and event.key == K_RETURN:
                    self.initialize()
                    self.started = True
        else:
            # ---------- Pausa real por mano de frente o no detectada ----------
            should_pause = (
                    self.no_hand
                    or self.hand_front
                    or self.hand_not_upright
                    or self.hand_tilted
            )
            if should_pause:
                if not self.music_paused:
                    try:
                        pygame.mixer.music.pause()
                    except Exception:
                        pass
                    self.music_paused = True
                return  # no avanzar juego mientras está pausado
            else:
                if self.music_paused:
                    try:
                        pygame.mixer.music.unpause()
                    except Exception:
                        pass
                    self.music_paused = False

            # ---------- Juego en marcha ----------
            globals.game_speed = 1 + ((pygame.time.get_ticks() - self.start_time) / 1000) * .1
            self.score = self.score + (delta_time * globals.game_speed)

            for event in events:
                if event.type == ADD_ENEMY:
                    num = random.randint(1, 2)
                    for e in range(num):
                        enemy = Enemy()
                        self.enemies.add(enemy)

                    self.enemy_timer = 1000 - ((globals.game_speed - 1) * 100)
                    if self.enemy_timer < 50:
                        self.enemy_timer = 50
                    pygame.time.set_timer(ADD_ENEMY, int(self.enemy_timer))

            self.player.update(self.movement, delta_time)
            self.enemies.update(delta_time)
            self.process_collisions()
            self.background.update(delta_time)

    def process_collisions(self):
        # Colisiones con máscara
        collide = pygame.sprite.spritecollide(self.player, self.enemies, False, pygame.sprite.collide_mask)
        if collide:
            self.lost = True
            self.save_game_data()  # Guardar los datos cuando el juego termine

    def save_game_data(self):
        if not self.started:
            print("El juego no ha comenzado. No se guardarán los datos.")
            return

        tiempo_total = (pygame.time.get_ticks() - self.start_time) / 1000.0
        fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        data = {
            "id_usuario_paciente": self.paciente.get("id_usuario"),
            "id_aplicacion": 1,  # Space Evation
            "tiempo_jugado": round(tiempo_total, 2),
            "fecha": fecha_inicio,
            "puntaje": int(round(self.score / 1000)),
            "datos": [
                {"tiempo": i * 100, "angulo": float(angle), "id_tipo": 22}
                for i, angle in enumerate(self.angle_trace)
            ],
            "dni": self.dni,
        }

        try:
            print(f"[POST score] {JUEGOS_URL} -> (len datos: {len(data.get('datos', []))})")
            resp = requests.post(
                JUEGOS_URL,
                json=data,
                headers=DEFAULT_HEADERS,
                timeout=REQUEST_TIMEOUT
            )
            print(f"[POST score] HTTP {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            print(f"[POST score] Error al enviar resultado: {e}")
            try:
                with open("pending_scores.jsonl", "a", encoding="utf-8") as f:
                    import json
                    f.write(json.dumps({"url": JUEGOS_URL, "data": data}) + "\n")
                print("[POST score] Guardado offline en pending_scores.jsonl")
            except Exception as e2:
                print("[POST score] No se pudo guardar offline:", e2)

    def render(self):
        self.screen.fill((0,0,0))

        self.background.render(self.screen)

        if self.webcam.lastFrame is not None:
            self.render_camera()

        self.screen.blit(self.player.surf, self.player.rect)

        for e in self.enemies:
            self.screen.blit(e.surf, e.rect)

        display_score = round(self.score/1000)
        text_score = self.font.render('Score: ' + str(display_score), True, (255,255,255))
        scoreTextRect = text_score.get_rect()
        scoreTextRect.bottom = SCREEN_HEIGHT-5
        scoreTextRect.left = 5
        self.screen.blit(text_score, scoreTextRect)

        # Mensajes
        if self.lost:
            game_over_text = self.font.render('GAME OVER :(', True, (255,255,255), (0,0,0))
            game_over_text_rect = game_over_text.get_rect()
            game_over_text_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            self.screen.blit(game_over_text, game_over_text_rect)

            retry_text = self.smaller_font.render('Presiona Enter para reintentar', True, (200,200,200), (0,0,0))
            retry_text_rect = retry_text.get_rect()
            retry_text_rect.center = (SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 40)
            self.screen.blit(retry_text, retry_text_rect)
        elif not self.started:
            start_text = self.font.render(
                "Presioná Enter para comenzar",
                True,
                (255, 255, 255),
                (0, 0, 0)
            )

            start_rect = start_text.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT // 2 + 100
                )
            )

            self.screen.blit(start_text, start_rect)

            # Mostrar la demostración solamente hasta detectar una mano
            if not self.has_detected_hand_once:
                instruction_text = self.smaller_font.render(
                    "Realizá flexión y extensión de muñeca",
                    True,
                    (220, 220, 220),
                    (0, 0, 0)
                )

                instruction_rect = instruction_text.get_rect(
                    center=(
                        SCREEN_WIDTH // 2,
                        SCREEN_HEIGHT // 2 + 145
                    )
                )

                self.screen.blit(instruction_text, instruction_rect)

                intro_frame = self.get_intro_animation_frame()

                self.render_instruction_image(
                    intro_frame,
                    center_y=SCREEN_HEIGHT // 2 - 100
                )
        else:
            # Pausa por mano de frente / no detectada
            if (
                    self.hand_front
                    or self.hand_not_upright
                    or self.hand_tilted
                    or self.no_hand
            ):
                if (
                        self.hand_front
                        or self.hand_not_upright
                        or self.hand_tilted
                        or self.no_hand
                ):
                    instruction_image = None

                    if self.no_hand:
                        msg = "Mostrá tu mano a la cámara para continuar"

                        # La animación solo aparece antes de detectar la primera mano
                        if not self.has_detected_hand_once:
                            instruction_image = self.get_intro_animation_frame()

                    elif self.hand_front:
                        msg = "Mostrá el canto de la mano a la cámara"
                        instruction_image = self.hand_neutral_image

                    elif self.hand_not_upright:
                        msg = "Mantené los dedos apuntando hacia arriba"
                        instruction_image = self.hand_rotate_up_image

                    else:
                        msg = "Enderezá la muñeca para continuar"
                        instruction_image = self.hand_rotate_up_image

                    paused_text = self.font.render(
                        "Juego pausado",
                        True,
                        (255, 255, 255),
                        (0, 0, 0)
                    )

                    paused_rect = paused_text.get_rect(
                        center=(
                            SCREEN_WIDTH // 2,
                            SCREEN_HEIGHT // 2 + 90
                        )
                    )

                    self.screen.blit(paused_text, paused_rect)

                    resume_text = self.smaller_font.render(
                        msg,
                        True,
                        (220, 220, 220),
                        (0, 0, 0)
                    )

                    resume_rect = resume_text.get_rect(
                        center=(
                            SCREEN_WIDTH // 2,
                            SCREEN_HEIGHT // 2 + 130
                        )
                    )

                    self.screen.blit(resume_text, resume_rect)

                    self.render_instruction_image(
                        instruction_image,
                        center_y=SCREEN_HEIGHT // 2 - 90
                    )
        pygame.display.flip()

    def loop(self):
        with self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.1,
            min_tracking_confidence=0.1
        ) as self.hands:
            while self.running:
                if not self.lost:
                    if not self.webcam.ready():
                        continue
                    self.process_camera()

                time = pygame.time.get_ticks()
                delta_time = time - self.last_frame_time
                self.last_frame_time = time
                self.update(delta_time)
                self.render()
                self.clock.tick(60)
            pygame.quit()

    def process_camera(self):
        image = self.webcam.read()
        if image is not None:
            image.flags.writeable = False
            image = cv2.flip(image, 1)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            results = self.hands.process(image)
            self.webcam_image = image

            # Por defecto: no hay mano hasta probar
            self.no_hand = True

            if results.multi_hand_landmarks is not None:
                self.no_hand = False

                # La animación inicial no volverá a aparecer durante esta partida
                self.has_detected_hand_once = True

                for hand_landmarks in results.multi_hand_landmarks:

                    self.mp_drawing.draw_landmarks(
                        image,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=1, circle_radius=1),
                        self.mp_drawing.DrawingSpec(color=(150, 150, 150), thickness=1)
                    )

                    # Coordenadas de la mano (arriba y abajo)
                    top = (hand_landmarks.landmark[9].x, hand_landmarks.landmark[9].y)
                    bottom = (hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y)

                    # Bounding para mini-ventana
                    self.hand_left_x = hand_landmarks.landmark[4].x - .1
                    self.hand_right_x = hand_landmarks.landmark[20].x + .1
                    self.hand_top_y = hand_landmarks.landmark[12].y - .1
                    self.hand_bottom_y = hand_landmarks.landmark[0].y + .1

                    # Convertir a píxeles
                    top_pixel = (int(top[0] * self.webcam.width()), int(top[1] * self.webcam.height()))
                    bottom_pixel = (int(bottom[0] * self.webcam.width()), int(bottom[1] * self.webcam.height()))

                    # Ángulo para tu telemetría/detección de movimiento
                    delta_x = top_pixel[0] - bottom_pixel[0]
                    delta_y = top_pixel[1] - bottom_pixel[1]
                    radians = math.atan2(delta_x, delta_y)
                    degrees = math.degrees(radians)

                    if degrees < 0:
                        degrees = 180 + degrees
                    else:
                        degrees = -180 + degrees

                    # Dibujo de línea y puntos (debug)
                    cv2.line(self.webcam_image, top_pixel, bottom_pixel, (255, 189, 89), 2)
                    cv2.circle(self.webcam_image, top_pixel, 7, (3, 161, 207), -1)
                    cv2.circle(self.webcam_image, bottom_pixel, 7, (3, 161, 207), -1)

                    # Detección de ángulo -> movimiento
                    self.detect_hand_movement(top, bottom)

                    # --------- ORIENTACIÓN CORRECTA DE LA MANO ---------
                    lm = hand_landmarks.landmark

                    def vector_3d(point_a, point_b):
                        """
                        Vector que va desde point_a hasta point_b.
                        """
                        return (
                            lm[point_b].x - lm[point_a].x,
                            lm[point_b].y - lm[point_a].y,
                            lm[point_b].z - lm[point_a].z
                        )

                    def vector_length(vector):
                        return math.sqrt(
                            vector[0] ** 2
                            + vector[1] ** 2
                            + vector[2] ** 2
                        )

                    def cross_product(vector_a, vector_b):
                        return (
                            vector_a[1] * vector_b[2] - vector_a[2] * vector_b[1],
                            vector_a[2] * vector_b[0] - vector_a[0] * vector_b[2],
                            vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0]
                        )

                    def distance_2d(point_a, point_b):
                        return math.hypot(
                            lm[point_b].x - lm[point_a].x,
                            lm[point_b].y - lm[point_a].y
                        )

                    # ==========================================================
                    # 1. DETECTAR PALMA DE FRENTE O CANTO
                    # ==========================================================

                    # Dos vectores contenidos en el plano de la palma:
                    # muñeca -> MCP índice
                    wrist_to_index = vector_3d(0, 5)

                    # muñeca -> MCP meñique
                    wrist_to_pinky = vector_3d(0, 17)

                    # La normal es perpendicular al plano de la palma
                    palm_normal = cross_product(
                        wrist_to_index,
                        wrist_to_pinky
                    )

                    normal_length = vector_length(palm_normal)

                    if normal_length > 1e-6:
                        # Componente Z normalizada.
                        #
                        # Alta: la palma mira hacia la cámara.
                        # Baja: estamos mostrando el canto.
                        raw_front_score = abs(palm_normal[2]) / normal_length

                        if self.palm_front_score is None:
                            self.palm_front_score = raw_front_score
                        else:
                            self.palm_front_score = (
                                    self.HAND_SMOOTH_ALPHA * raw_front_score
                                    + (1.0 - self.HAND_SMOOTH_ALPHA)
                                    * self.palm_front_score
                            )

                        if not self.hand_front:
                            if self.palm_front_score >= self.PALM_FRONT_ON:
                                self.hand_front = True
                        else:
                            if self.palm_front_score <= self.PALM_FRONT_OFF:
                                self.hand_front = False

                    # ==========================================================
                    # 2. COMPROBAR QUE LA MANO APUNTE HACIA ARRIBA
                    # ==========================================================

                    # Eje principal de la mano:
                    # muñeca (0) -> MCP del dedo medio (9)
                    hand_axis_x = lm[9].x - lm[0].x
                    hand_axis_y = lm[9].y - lm[0].y

                    # En una imagen, Y disminuye al ir hacia arriba.
                    # Por eso usamos -hand_axis_y como componente vertical superior.
                    upright_angle = abs(
                        math.degrees(
                            math.atan2(
                                hand_axis_x,
                                -hand_axis_y
                            )
                        )
                    )

                    # Histéresis para evitar bloquear/desbloquear cerca del límite
                    if not self.hand_not_upright:
                        if upright_angle >= self.UPRIGHT_BAD_ON:
                            self.hand_not_upright = True
                    else:
                        if upright_angle <= self.UPRIGHT_BAD_OFF:
                            self.hand_not_upright = False

                    # ==========================================================
                    # 3. DETECCIÓN ADICIONAL DE INCLINACIÓN HACIA ADELANTE
                    # ==========================================================

                    palm_width_2d = distance_2d(5, 17)
                    palm_length_2d = distance_2d(0, 9)

                    if palm_length_2d > 1e-6:
                        raw_tilt_ratio = palm_width_2d / palm_length_2d

                        if self.hand_tilt_ratio is None:
                            self.hand_tilt_ratio = raw_tilt_ratio
                        else:
                            self.hand_tilt_ratio = (
                                    self.HAND_SMOOTH_ALPHA * raw_tilt_ratio
                                    + (1.0 - self.HAND_SMOOTH_ALPHA)
                                    * self.hand_tilt_ratio
                            )

                        if not self.hand_tilted:
                            if self.hand_tilt_ratio >= self.TILT_ON:
                                self.hand_tilted = True
                        else:
                            if self.hand_tilt_ratio <= self.TILT_OFF:
                                self.hand_tilted = False

                    # ==========================================================
                    # DEBUG PARA CALIBRAR
                    # ==========================================================

                    current_time = pygame.time.get_ticks()

                    if current_time - self.last_hand_debug_time >= 250:
                        print(
                            "[HAND] "
                            f"front_score={self.palm_front_score:.3f} | "
                            f"front={self.hand_front} | "
                            f"upright_angle={upright_angle:.1f}° | "
                            f"not_upright={self.hand_not_upright} | "
                            f"tilt_ratio={self.hand_tilt_ratio:.3f} | "
                            f"tilted={self.hand_tilted}"
                        )

                        self.last_hand_debug_time = current_time

                        # ==========================================================
                        # REGISTRAR ÁNGULO SOLO CON LA MANO EN POSICIÓN CORRECTA
                        # ==========================================================

                        valid_hand_position = (
                                not self.hand_front
                                and not self.hand_not_upright
                                and not self.hand_tilted
                        )

                        current_time = pygame.time.get_ticks()

                        if self.started and valid_hand_position:
                            if current_time - self.last_angle_print_time >= 100:
                                print(f"Ángulo válido registrado: {degrees:.2f} grados")

                                self.last_angle_print_time = current_time
                                self.top_point_trace.append(top_pixel)
                                self.angle_trace.append(degrees)

                        else:
                            self.last_angle_print_time = current_time
            else:
                self.hand_front = False
                self.hand_not_upright = False
                self.hand_tilted = False

                self.palm_front_score = None
                self.hand_tilt_ratio = None

    def detect_hand_movement(self, top, bottom):
        radians = math.atan2(bottom[1] - top[1], bottom[0] - top[0])
        degrees = math.degrees(radians)

        # Angulo de deteccion de 70 a 110 (-1 a 1)
        min_degrees = 70
        max_degrees = 110
        degree_range = max_degrees - min_degrees

        if degrees < min_degrees: degrees = min_degrees
        if degrees > max_degrees: degrees = max_degrees

        self.movement = ( ((degrees-min_degrees) / degree_range) * 2) - 1

    def render_camera(self):
        # Limpiar coordenadas del cuadro de la mano
        if self.hand_left_x < 0: self.hand_left_x = 0
        if self.hand_right_x > 1: self.hand_right_x = 1
        if self.hand_top_y < 0: self.hand_top_y = 0
        if self.hand_bottom_y > 1: self.hand_bottom_y = 1

        if self.webcam_image is not None:
            # Centro en px
            hand_center_x = int(self.webcam.width() * self.hand_left_x + (
                        self.hand_right_x - self.hand_left_x) * self.webcam.width() / 2)
            hand_center_y = int(self.webcam.height() * self.hand_top_y + (
                        self.hand_bottom_y - self.hand_top_y) * self.webcam.height() / 2)

            crop_size = 200
            half_crop_size = crop_size // 2

            x1 = max(hand_center_x - half_crop_size, 0)
            x2 = min(hand_center_x + half_crop_size, self.webcam_image.shape[1])
            y1 = max(hand_center_y - half_crop_size, 0)
            y2 = min(hand_center_y + half_crop_size, self.webcam_image.shape[0])

            if x2 - x1 < crop_size:
                if x1 == 0:
                    x2 = min(crop_size, self.webcam_image.shape[1])
                elif x2 == self.webcam_image.shape[1]:
                    x1 = max(self.webcam_image.shape[1] - crop_size, 0)
            if y2 - y1 < crop_size:
                if y1 == 0:
                    y2 = min(crop_size, self.webcam_image.shape[0])
                elif y2 == self.webcam_image.shape[0]:
                    y1 = max(self.webcam_image.shape[0] - crop_size, 0)

            roi = self.webcam_image[y1:y2, x1:x2]
            hand_surf = pygame.image.frombuffer(roi.tobytes(), roi.shape[1::-1], "BGR")
            self.screen.blit(hand_surf, (0, 0))
