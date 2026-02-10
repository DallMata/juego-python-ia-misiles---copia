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

        # --- imagen para pausa por mano de frente ---
        try:
            self.hand_front_image = pygame.image.load('spaceEvation/sprites/HandSideways.png').convert_alpha()
            self.hand_front_image = pygame.transform.scale(self.hand_front_image, (220, 220))
        except Exception as e:
            print("[UI] No pude cargar sprites/handturned.png:", e)
            self.hand_front_image = None

        # --- inicialización del juego ---
        self.initialize()

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
        # Histéresis (ratio normalizado por ancho de mano)
        self.FRONT_ON_HI = 0.55  # entrar en pausa si dx_ratio >= 0.55
        self.FRONT_ON_LO = 0.40  # salir de pausa si dx_ratio <= 0.45

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
            should_pause = (self.hand_front or self.no_hand)
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
            game_over_text = self.font.render('Presiona Enter para comenzar', True, (255,255,255), (0,0,0))
            game_over_text_rect = game_over_text.get_rect()
            game_over_text_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            self.screen.blit(game_over_text, game_over_text_rect)
        else:
            # Pausa por mano de frente / no detectada
            if self.hand_front or self.no_hand:
                msg = "Girá la mano de costado para continuar" if self.hand_front else "Muestra tu mano a la cámara para continuar"
                paused_text = self.font.render('Juego Pausado', True, (255, 255, 255), (0, 0, 0))
                paused_rect = paused_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                self.screen.blit(paused_text, paused_rect)
                resume_text = self.smaller_font.render(msg, True, (200, 200, 200), (0, 0, 0))
                resume_rect = resume_text.get_rect(center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 40))
                self.screen.blit(resume_text, resume_rect)

                # 👉 Mostrar imagen cuando está pausado por mano de frente
                if self.hand_front and self.hand_front_image is not None:
                    img_rect = self.hand_front_image.get_rect(center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) - 130))
                    self.screen.blit(self.hand_front_image, img_rect)

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

                    if self.started:
                        current_time = pygame.time.get_ticks()
                        if current_time - self.last_angle_print_time >= 100:
                            print(f"Ángulo formado: {degrees} grados")
                            self.last_angle_print_time = current_time
                            self.top_point_trace.append(top_pixel)
                            self.angle_trace.append(degrees)

                    # Dibujo de línea y puntos (debug)
                    cv2.line(self.webcam_image, top_pixel, bottom_pixel, (255, 189, 89), 2)
                    cv2.circle(self.webcam_image, top_pixel, 7, (3, 161, 207), -1)
                    cv2.circle(self.webcam_image, bottom_pixel, 7, (3, 161, 207), -1)

                    # Detección de ángulo -> movimiento
                    self.detect_hand_movement(top, bottom)

                    # --------- PAUSA POR MANO DE FRENTE (palma hacia cámara) ---------
                    lm = hand_landmarks.landmark
                    # Ancho de la "mano" en X (bbox) para normalizar
                    xs = [p.x for p in lm]
                    bbox_w = max(xs) - min(xs)
                    bbox_w = max(bbox_w, 1e-6)  # evitar división por 0

                    # Separación horizontal entre MCP índice (5) y MCP meñique (17), normalizada
                    dx_ratio = abs(lm[5].x - lm[17].x) / bbox_w

                    # Histéresis: evitamos parpadeos al entrar/salir de pausa
                    if not self.hand_front:
                        if dx_ratio >= self.FRONT_ON_HI:
                            self.hand_front = True
                    else:
                        if dx_ratio <= self.FRONT_ON_LO:
                            self.hand_front = False

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
