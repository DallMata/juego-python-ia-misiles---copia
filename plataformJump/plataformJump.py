import pygame
from pygame.locals import *
import random
from plataformJump.player import Player
from plataformJump.constants import *
from plataformJump.background import Background
from plataformJump.events import *
from plataformJump.gameplatform import GamePlatform
from plataformJump.money import Money
from plataformJump.enemy import Enemy
from plataformJump.shield import Shield
import globals
import math
import requests
import json
from datetime import datetime
import cv2
import mediapipe as mp
from plataformJump.webcam import Webcam

# --- endpoints / headers / timeouts ---
from config import JUEGOS_URL, REQUEST_TIMEOUT, DEFAULT_HEADERS
try:
    from config import APP_PLATFORM_JUMP_ID
except ImportError:
    APP_PLATFORM_JUMP_ID = 2  # fallback si no lo definiste en config.py


def _clamp(v, lo, hi):
    try:
        v = int(v)
    except Exception:
        v = lo
    return max(lo, min(hi, v))


class Game:
    def __init__(self, paciente, asignacion=None, dificultad=None):
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        self.clock = pygame.time.Clock()
        self.running = True
        self.pause_image = pygame.image.load('plataformJump/sprites/HandFront.png').convert_alpha()
        self.pause_image = pygame.transform.scale(self.pause_image, (200, 200))

        # Hand Landmarks
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        pygame.init()
        pygame.display.set_caption("Plataformas")

        # Tiempo de impresión de ángulos
        self.last_angle_print_time = 0

        # Fondos
        self.background1 = Background(True, .05, "2", 0)
        self.background2 = Background(False, .2, "3", 40)

        self.font = pygame.font.Font('freesansbold.ttf', 32)
        self.smaller_font = pygame.font.Font('freesansbold.ttf', 22)

        # Sonidos
        self.powerup_sound = pygame.mixer.Sound("plataformJump/sound/powerup.wav")
        self.powerup_sound.set_volume(.1)
        self.death_sound = pygame.mixer.Sound("plataformJump/sound/grunt2.wav")

        # Paciente
        self.paciente = paciente
        print(f'PACIENTE: {paciente}')
        self.dni = self.paciente.get('dni')
        print(f"DNI EN GAME:  {self.dni}")

        # Dificultad de control gestual 1..3 (backend o parámetro directo; default 3)
        self.asignacion = asignacion or {}
        dif_backend = self.asignacion.get("dificultad", None)
        self.dificultad_control = _clamp(
            dificultad if dificultad is not None else (dif_backend if dif_backend is not None else 3), 1, 3
        )
        print(f"[Platform Jump] Dificultad de control (gestos): {self.dificultad_control}")

        # Traces por dedo/articulación (id_tipo: ver mapeo más abajo)
        self.angle_trace_3  = []
        self.angle_trace_2  = []
        self.angle_trace_1  = []
        self.angle_trace_7  = []
        self.angle_trace_6  = []
        self.angle_trace_5  = []
        self.angle_trace_11 = []
        self.angle_trace_10 = []
        self.angle_trace_9  = []
        self.angle_trace_15 = []
        self.angle_trace_14 = []
        self.angle_trace_13 = []
        self.angle_trace_19 = []
        self.angle_trace_18 = []
        self.angle_trace_17 = []

        self.initialize()

    def initialize(self):
        self.player = Player()
        self.no_hand = False
        self.dead = False
        self.hand_turned = False
        self.paused = False

        self.prev_distance = None

        self.webcam = Webcam().start()
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.1, min_tracking_confidence=0.1)

        self.handWasClosed = False
        self.overlay_is_closed = False  # para UI

        self.platforms = []
        platform = GamePlatform(20, 0)
        self.platforms.append(platform)
        self.difficulty = 1
        self.group_platforms = pygame.sprite.Group()
        self.group_platforms.add(platform)
        self.platformWillBeCreated = False

        self.start_time = pygame.time.get_ticks()
        self.last_frame_time = -1

        self.score = 0
        self.text_score = None
        self.text_score_rect = None

        self.powerups = []
        self.group_powerups = pygame.sprite.Group()
        pygame.time.set_timer(CREATE_NEW_MONEY, 1000)

        self.enemies = []
        self.group_enemies = pygame.sprite.Group()
        pygame.time.set_timer(CREATE_NEW_ENEMY, 15000)

        self.shields = []
        self.group_shields = pygame.sprite.Group()
        pygame.time.set_timer(CREATE_NEW_SHIELD, 10000)

        # ROI de mano
        self.max_hand_surf_height = 0
        self.hand_left_x = 0
        self.hand_right_x = 0
        self.hand_top_y = 0
        self.hand_bottom_y = 0

        self.music_paused = False
        self._setup_music()

    def _setup_music(self):
        try:
            pygame.mixer.music.load("plataformJump/sound/PlataformJumpMusic.mp3")
            pygame.mixer.music.set_volume(0.35)  # volumen 0.0..1.0
            pygame.mixer.music.play(loops=-1, fade_ms=1500)  # loop infinito con fade-in
            print("[MUSIC] BGM reproduciendo en loop")
        except Exception as e:
            print("[MUSIC] No pude cargar bgm:", e)

    # ---------- SAVE GAME (único POST por partida) ----------
    def save_game_data(self):
        # segundos jugados
        tiempo_total = (pygame.time.get_ticks() - self.start_time) / 1000.0
        fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Mapea id_tipo -> trace correspondiente
        # índice (7,6,5) | medio (11,10,9) | anular (15,14,13) | meñique (19,18,17) | pulgar (3,2,1)
        traces = [
            (29, self.angle_trace_7),  (28, self.angle_trace_6),  (27, self.angle_trace_5),
            (33, self.angle_trace_11), (32, self.angle_trace_10), (31, self.angle_trace_9),
            (37, self.angle_trace_15), (36, self.angle_trace_14), (35, self.angle_trace_13),
            (41, self.angle_trace_19), (40, self.angle_trace_18), (39, self.angle_trace_17),
            (25, self.angle_trace_3),  (24, self.angle_trace_2),  (23, self.angle_trace_1),
        ]

        datos = []
        # en este juego guardaste cada 200 ms
        SAMPLE_MS = 200
        for id_tipo, trace in traces:
            for i, ang in enumerate(trace):
                if ang is None:
                    continue
                datos.append({"tiempo": i * SAMPLE_MS, "angulo": float(ang), "id_tipo": id_tipo})

        payload = {
            "id_usuario_paciente": self.paciente.get("id_usuario"),
            "id_aplicacion": APP_PLATFORM_JUMP_ID,          # 👈 ID de Plataform Jump
            "tiempo_jugado": round(tiempo_total, 2),
            "fecha": fecha_inicio,
            "puntaje": int(self.score / 1000),
            "datos": datos,
            "dni": self.dni,  # opcional
        }

        try:
            print(f"[PJ POST] {JUEGOS_URL} -> datos:{len(datos)}")
            r = requests.post(JUEGOS_URL, json=payload, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
            print(f"[PJ POST] HTTP {r.status_code}: {r.text[:300]}")
        except Exception as e:
            print(f"[PJ POST] Error al enviar resultado: {e}")
            # opcional: guardar offline
            try:
                with open("pending_scores.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"url": JUEGOS_URL, "data": payload}) + "\n")
                print("[PJ POST] Guardado offline en pending_scores.jsonl")
            except Exception as e2:
                print("[PJ POST] No se pudo guardar offline:", e2)

    def update(self, delta_time):
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                # si se cierra la ventana y estabas jugando, guardá
                if not self.dead:
                    self.dead = True
                self.save_game_data()
                self.running = False

            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                if not self.dead:
                    self.dead = True
                self.save_game_data()
                self.running = False

        if self.dead:
            # esperar ENTER o ESC para reiniciar; solo guardamos UNA vez
            for event in events:
                if event.type == KEYDOWN and (event.key == K_RETURN or event.key == K_ESCAPE):
                    self.save_game_data()
                    self.initialize()
            return

        # ---------- Pausa real por mano girada o no detectada ----------
        should_pause = (self.hand_turned or self.no_hand)
        if should_pause:
            if not self.music_paused:
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
                self.music_paused = True
            return  # ← se corta ANTES de aplicar input/juego
        else:
            if self.music_paused and not self.dead:
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass
                self.music_paused = False

        # input y lógica normal
        for event in events:
            if event.type == KEYDOWN and event.key == K_SPACE:
                self.player.jump()
            elif event.type == KEYUP and event.key == K_SPACE:
                self.player.cancel_jump()
            elif event.type == HAND_CLOSED:
                self.player.jump()
            elif event.type == HAND_OPENED:
                self.player.cancel_jump()
            elif event.type == CREATE_NEW_PLATFORM:
                self.platformWillBeCreated = False
                min_tiles = 3 if self.difficulty <= 3 else 1
                max_tiles = max(4, 12 - self.difficulty)
                tileNumber = random.randrange(min_tiles, max_tiles)
                min_space = min(150, 90 + (self.difficulty * 2))
                max_space = max(350, 200 + (self.difficulty * 2))
                space = random.randrange(min_space, max_space)
                platform = GamePlatform(tileNumber, SCREEN_WIDTH + space)
                self.platforms.append(platform)
                self.group_platforms.add(platform)
            elif event.type == CREATE_NEW_MONEY:
                money = Money()
                self.powerups.append(money)
                self.group_powerups.add(money)
                pygame.time.set_timer(CREATE_NEW_MONEY, random.randint(3000, 10000))
            elif event.type == CREATE_NEW_ENEMY:
                enemy = Enemy()
                self.enemies.append(enemy)
                self.group_enemies.add(enemy)
                min_time = max(2000, 4000 - self.difficulty * 500)
                max_time = max(4000, 10000 - self.difficulty * 500)
                pygame.time.set_timer(CREATE_NEW_ENEMY, random.randint(min_time, max_time))
            elif event.type == CREATE_NEW_SHIELD:
                shield = Shield()
                self.shields.append(shield)
                self.group_shields.add(shield)
                pygame.time.set_timer(CREATE_NEW_SHIELD, random.randint(10000, 20000))

        if not self.player.dead:
            self.background1.update(delta_time)
            self.background2.update(delta_time)
            self.player.update(delta_time, self.group_platforms, self.group_powerups, self.group_enemies, self.group_shields)

            if self.player.dead or self.player.rect.top > SCREEN_HEIGHT:
                if self.player.shield:
                    self.player.shield_save()
                else:
                    self.dead = True
                    pygame.mixer.Sound.play(self.death_sound)

            if self.player.addScore > 0:
                self.score += (self.player.addScore * 1000)
                self.player.addScore = 0
                pygame.mixer.Sound.play(self.powerup_sound)

            for platform in self.platforms:
                platform.update(delta_time)

            self.group_powerups.update(delta_time)
            self.group_enemies.update(delta_time)
            self.group_shields.update(delta_time)

            if (SCREEN_WIDTH - self.platforms[-1].rect.right > 0) and not self.platformWillBeCreated:
                self.platformWillBeCreated = True
                pygame.event.post(pygame.event.Event(CREATE_NEW_PLATFORM))

            seconds = int((pygame.time.get_ticks() - self.start_time) / 1000)
            self.difficulty = int(1 + (seconds / 10))
            globals.game_speed = 1 + (self.difficulty * .2)

            self.score += globals.game_speed * delta_time
            self.text_score = self.font.render('Score: ' + str(int(self.score / 1000)), True, (255, 255, 255))
            self.text_score_rect = self.text_score.get_rect()
            self.text_score_rect.y = 10
            self.text_score_rect.x = (SCREEN_WIDTH // 2) - (self.text_score_rect.width // 2)

    def render(self):
        self.screen.fill((92, 89, 92))
        self.background1.render(self.screen)
        self.background2.render(self.screen)

        if self.webcam.lastFrame is not None:
            self.render_camera()

        for platform in self.platforms:
            self.screen.blit(platform.surf, platform.rect)

        self.screen.blit(self.player.surf, self.player.rect)
        if self.player.shield:
            self.screen.blit(self.player.shieldSurf, self.player.shieldRect)

        for powerup in self.group_powerups:
            self.screen.blit(powerup.surf, powerup.rect)
        for enemy in self.group_enemies.sprites():
            self.screen.blit(enemy.surf, enemy.rect)
        for shield in self.group_shields:
            self.screen.blit(shield.surf, shield.rect)

        if self.text_score is not None:
            self.screen.blit(self.text_score, self.text_score_rect)

        # Overlay de estado de mano (arriba-izquierda)
        status = "CERRADA" if self.overlay_is_closed else "ABIERTA"
        status_color = (220, 80, 80) if self.overlay_is_closed else (60, 200, 90)
        txt = self.smaller_font.render(f"Mano: {status}", True, (255, 255, 255))
        pad = 8
        box = pygame.Surface((txt.get_width() + pad * 2, txt.get_height() + pad * 2), pygame.SRCALPHA)
        box.fill((0, 0, 0, 140))
        self.screen.blit(box, (10, 10))
        self.screen.blit(txt, (10 + pad, 10 + pad))
        pygame.draw.circle(self.screen, status_color, (10 + pad + txt.get_width() + 14, 10 + pad + txt.get_height() // 2), 6)

        if self.dead:
            dead = self.font.render('GAME OVER :(', True, (255, 255, 255), (0, 0, 0))
            dead_rect = dead.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(dead, dead_rect)
            retry = self.smaller_font.render('Presiona enter para reintentar', True, (200, 200, 200), (0, 0, 0))
            retry_rect = retry.get_rect(center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 40))
            self.screen.blit(retry, retry_rect)
        elif self.hand_turned:
            paused_text = self.font.render('Juego Pausado', True, (255, 255, 255), (0, 0, 0))
            paused_rect = paused_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(paused_text, paused_rect)
            resume_text = self.smaller_font.render('Endereza la mano para continuar', True, (200, 200, 200), (0, 0, 0))
            resume_rect = resume_text.get_rect(center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 40))
            self.screen.blit(resume_text, resume_rect)
            pause_image_rect = self.pause_image.get_rect(center=((SCREEN_WIDTH // 2), (SCREEN_HEIGHT // 2) - 150))
            self.screen.blit(self.pause_image, pause_image_rect)
        elif self.no_hand:
            paused_text = self.font.render('Juego Pausado', True, (255, 255, 255), (0, 0, 0))
            paused_rect = paused_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(paused_text, paused_rect)
            resume_text = self.smaller_font.render('Muestra tu mano a la cámara continuar', True, (200, 200, 200), (0, 0, 0))
            resume_rect = resume_text.get_rect(center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 40))
            self.screen.blit(resume_text, resume_rect)

        pygame.display.flip()

    def render_camera(self):
        # Limpiar coordenadas del cuadro de la mano
        self.hand_left_x  = max(0, self.hand_left_x)
        self.hand_right_x = min(1, self.hand_right_x)
        self.hand_top_y   = max(0, self.hand_top_y)
        self.hand_bottom_y= min(1, self.hand_bottom_y)

        if self.webcam_image is not None:
            hand_center_x = int(self.webcam.width() * self.hand_left_x + (self.hand_right_x - self.hand_left_x) * self.webcam.width() / 2)
            hand_center_y = int(self.webcam.height() * self.hand_top_y + (self.hand_bottom_y - self.hand_top_y) * self.webcam.height() / 2)

            crop_size = 200
            half = crop_size // 2
            x1 = max(hand_center_x - half, 0)
            x2 = min(hand_center_x + half, self.webcam_image.shape[1])
            y1 = max(hand_center_y - half, 0)
            y2 = min(hand_center_y + half, self.webcam_image.shape[0])

            if x2 - x1 < crop_size:
                if x1 == 0: x2 = min(crop_size, self.webcam_image.shape[1])
                elif x2 == self.webcam_image.shape[1]: x1 = max(self.webcam_image.shape[1] - crop_size, 0)
            if y2 - y1 < crop_size:
                if y1 == 0: y2 = min(crop_size, self.webcam_image.shape[0])
                elif y2 == self.webcam_image.shape[0]: y1 = max(self.webcam_image.shape[0] - crop_size, 0)

            roi = self.webcam_image[y1:y2, x1:x2]
            hand_surf = pygame.image.frombuffer(roi.tobytes(), roi.shape[1::-1], "BGR")
            self.screen.blit(hand_surf, (0, 0))

    def loop(self):
        with self.mp_hands.Hands(max_num_hands=1) as self.hands:
            while self.running:
                if not self.webcam.ready():
                    continue
                time = pygame.time.get_ticks()
                delta_time = 1 if self.last_frame_time == -1 else (time - self.last_frame_time)
                self.last_frame_time = time
                self.process_camera()
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

            # Estado por defecto hasta comprobar
            self.hand_turned = False
            self.no_hand = True

            if results.multi_hand_landmarks is not None:
                self.no_hand = False

                # Puede haber etiqueta por mano (Right/Left)
                hands = results.multi_hand_landmarks
                labels = results.multi_handedness if results.multi_handedness else [None] * len(hands)

                for handed, hand_landmarks in zip(labels, hands):
                    # Label “Right/Left” para esta mano
                    handed_label = None
                    try:
                        if handed and handed.classification:
                            handed_label = handed.classification[0].label  # 'Right' o 'Left'
                    except Exception:
                        handed_label = None

                    self.mp_drawing.draw_landmarks(
                        image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=1, circle_radius=1),
                        self.mp_drawing.DrawingSpec(color=(150, 150, 150), thickness=1)
                    )

                    # landmarks en normalizado (0..1) -> también a px para cálculos verticales de siempre
                    def to_px(p): return (int(p.x * self.webcam.width()), int(p.y * self.webcam.height()))
                    lm = hand_landmarks.landmark

                    l0 = to_px(lm[0]);  l1 = to_px(lm[1]);  l2 = to_px(lm[2]);  l3 = to_px(lm[3]);  l4 = to_px(lm[4])
                    l5 = to_px(lm[5]);  l6 = to_px(lm[6]);  l7 = to_px(lm[7]);  l8 = to_px(lm[8])
                    l9 = to_px(lm[9]);  l10 = to_px(lm[10]); l11 = to_px(lm[11]); l12 = to_px(lm[12])
                    l13 = to_px(lm[13]); l14 = to_px(lm[14]); l15 = to_px(lm[15]); l16 = to_px(lm[16])
                    l17 = to_px(lm[17]); l18 = to_px(lm[18]); l19 = to_px(lm[19]); l20 = to_px(lm[20])

                    # ROI mano
                    self.hand_left_x  = lm[5].x - .3
                    self.hand_right_x = lm[17].x + .3
                    self.hand_top_y   = lm[9].y - .3
                    self.hand_bottom_y= lm[0].y + .3

                    # ---------- TUS ÁNGULOS (para telemetría, igual que antes) ----------
                    a7  = self.calculate_angle(l6, l7, l8)
                    a6  = self.calculate_angle(l5, l6, l7)
                    a5  = self.calculate_angle(l0, l5, l6)

                    a11 = self.calculate_angle(l10, l11, l12)
                    a10 = self.calculate_angle(l9,  l10, l11)
                    a9  = self.calculate_angle(l0,  l9,  l10)

                    a15 = self.calculate_angle(l14, l15, l16)
                    a14 = self.calculate_angle(l13, l14, l15)
                    a13 = self.calculate_angle(l0,  l13, l17)

                    a19 = self.calculate_angle(l18, l19, l20)
                    a18 = self.calculate_angle(l17, l18, l19)
                    a17 = self.calculate_angle(l0,  l17, l18)

                    a3  = self.calculate_angle(l2,  l3,  l4)
                    a2  = self.calculate_angle(l1,  l2,  l3)
                    a1  = self.calculate_angle(l0,  l1,  l2)

                    # Pausa por orientación: setear bandera y (solo si NO está girada) registrar telemetría
                    self.hand_turned = self.check_hand_orientation(hand_landmarks)
                    if (not self.hand_turned) and (not self.dead):
                        current_time = pygame.time.get_ticks()
                        if current_time - self.last_angle_print_time >= 200:
                            self.last_angle_print_time = current_time
                            self.angle_trace_7.append(a7);   self.angle_trace_6.append(a6);   self.angle_trace_5.append(a5)
                            self.angle_trace_11.append(a11); self.angle_trace_10.append(a10); self.angle_trace_9.append(a9)
                            self.angle_trace_15.append(a15); self.angle_trace_14.append(a14); self.angle_trace_13.append(a13)
                            self.angle_trace_19.append(a19); self.angle_trace_18.append(a18); self.angle_trace_17.append(a17)
                            self.angle_trace_3.append(a3);   self.angle_trace_2.append(a2);   self.angle_trace_1.append(a1)

                    # ---------- DETECCIÓN POR DIFICULTAD ----------
                    d = int(self.dificultad_control)

                    # 1) Dedo pulgar en eje X según mano y “landmark umbral” por dificultad
                    if d == 1:
                        thumb_thr_idx = 3  # THUMB_IP
                    elif d == 2:
                        thumb_thr_idx = 2  # THUMB_MCP
                    else:
                        thumb_thr_idx = 1  # THUMB_CMC

                    tip_x = lm[4].x
                    thr_x = lm[thumb_thr_idx].x

                    # Si no tenemos label de mano, inferimos (MCP pulgar vs MCP índice)
                    if handed_label is None:
                        is_right = (lm[2].x < lm[5].x)
                    else:
                        is_right = (handed_label == 'Right')

                    # Pulgar cerrado en X (con imagen espejada)
                    thumb_closed_x = (tip_x > thr_x) if is_right else (tip_x < thr_x)

                    # 2) Cuatro dedos largos verticales según dificultad (Y crece hacia abajo)
                    if d == 3:  # TIP por DEBAJO de MCP
                        longs_closed = (
                            (l8[1]  > l5[1])  and
                            (l12[1] > l9[1])  and
                            (l16[1] > l13[1]) and
                            (l20[1] > l17[1])
                        )
                    elif d == 2:  # TIP por DEBAJO de PIP
                        longs_closed = (
                            (l8[1]  > l6[1])  and
                            (l12[1] > l10[1]) and
                            (l16[1] > l14[1]) and
                            (l20[1] > l18[1])
                        )
                    else:  # d == 1 (TIP por DEBAJO de DIP)
                        longs_closed = (
                            (l8[1]  > l7[1])  and
                            (l12[1] > l11[1]) and
                            (l16[1] > l15[1]) and
                            (l20[1] > l19[1])
                        )

                    # 3) Mano cerrada = 4 largos cerrados Y pulgar cerrado
                    is_closed_now = longs_closed and thumb_closed_x

                    # Disparador de doble salto (ambas transiciones disparan HAND_CLOSED)
                    if (not self.handWasClosed) and is_closed_now:
                        pygame.event.post(pygame.event.Event(HAND_CLOSED))
                        self.handWasClosed = True
                    elif self.handWasClosed and (not is_closed_now):
                        pygame.event.post(pygame.event.Event(HAND_CLOSED))
                        self.handWasClosed = False

                    # Overlay instantáneo correcto
                    self.overlay_is_closed = is_closed_now

            else:
                # No hay mano este frame
                self.no_hand = True
                # opcional: podrías setear overlay a abierta
                # self.overlay_is_closed = False

            _ = cv2.waitKey(1) & 0xFF

    def calculate_angle(self, point_a, point_b, point_c):
        vector_ab = (point_b[0] - point_a[0], point_b[1] - point_a[1])
        vector_bc = (point_c[0] - point_b[0], point_c[1] - point_b[1])
        mag_ab = math.hypot(vector_ab[0], vector_ab[1])
        mag_bc = math.hypot(vector_bc[0], vector_bc[1])
        if mag_ab == 0 or mag_bc == 0:
            return None
        dot = vector_ab[0] * vector_bc[0] + vector_ab[1] * vector_bc[1]
        cos_angle = max(-1.0, min(1.0, dot / (mag_ab * mag_bc)))
        angle_deg = math.degrees(math.acos(cos_angle))
        # regla especial que tenías (alineación)
        if point_c[0] <= point_a[0]:
            return 0.0
        return angle_deg

    def check_hand_orientation(self, landmarks):
        index_base = landmarks.landmark[5]
        pinky_base = landmarks.landmark[17]
        return abs(index_base.x - pinky_base.x) < 0.03
