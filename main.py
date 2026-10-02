import pygame
import random
import time
import sys
import math
import array
import os

# ============================================================
# INITIALIZATION
# ============================================================

pygame.init()

try:
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    AUDIO_OK = True
except Exception as e:
    print(f"Audio init failed: {e}")
    AUDIO_OK = False

MIN_WIDTH = 900
MIN_HEIGHT = 600
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 760

screen = pygame.display.set_mode(
    (DEFAULT_WIDTH, DEFAULT_HEIGHT),
    pygame.RESIZABLE
)

pygame.display.set_caption("TypeFlow - Speed Typing Game")
clock = pygame.time.Clock()

# ============================================================
# BACKGROUND IMAGE — LOAD & SCALE (COVER MODE)
# ============================================================

BACKGROUND_IMAGE_PATH = "assets/background.jpg"

_background_original = None
_background_scaled = None
_background_dark_overlay = None


def load_background():
    global _background_original
    if os.path.isfile(BACKGROUND_IMAGE_PATH):
        try:
            _background_original = pygame.image.load(
                BACKGROUND_IMAGE_PATH
            ).convert()
            print(f"[TypeFlow] Loaded background: {BACKGROUND_IMAGE_PATH}")
            return True
        except Exception as e:
            print(f"[TypeFlow] Failed to load background: {e}")
            _background_original = None
            return False
    else:
        print(f"[TypeFlow] Background not found: {BACKGROUND_IMAGE_PATH}")
        _background_original = None
        return False


def scale_background(width, height):
    """Scale background to COVER full screen (crop overflow, no black bars)."""
    global _background_scaled, _background_dark_overlay

    if _background_original is None:
        _background_scaled = None
        return

    if width <= 0 or height <= 0:
        return

    orig_w, orig_h = _background_original.get_size()
    if orig_w == 0 or orig_h == 0:
        _background_scaled = None
        return

    ratio_w = width / orig_w
    ratio_h = height / orig_h
    ratio = max(ratio_w, ratio_h)

    new_w = int(orig_w * ratio)
    new_h = int(orig_h * ratio)

    scaled = pygame.transform.smoothscale(
        _background_original, (new_w, new_h)
    )

    crop_x = (new_w - width) // 2
    crop_y = (new_h - height) // 2

    crop_x = max(0, min(crop_x, new_w - width))
    crop_y = max(0, min(crop_y, new_h - height))

    cropped = pygame.Surface((width, height))
    cropped.blit(scaled, (0, 0), (crop_x, crop_y, width, height))

    _background_scaled = cropped

    _background_dark_overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    _background_dark_overlay.fill((0, 0, 0, 160))


def draw_background():
    if _background_scaled is None:
        return False
    screen.blit(_background_scaled, (0, 0))
    if _background_dark_overlay is not None:
        screen.blit(_background_dark_overlay, (0, 0))
    return True


# ============================================================
# SPLASH SCREEN — 2 IMAGES
# ============================================================

SPLASH_FILES = [
    "assets/splash1.jpg",
    "assets/splash2.jpg",
]

SPLASH_DURATION_PER_IMAGE = 2.5
SPLASH_FADE_TIME = 0.6

_splash_images = []
_splash_start_time = None
_splash_current_index = 0
_splash_done = False


def load_splash_images():
    images = []
    for path in SPLASH_FILES:
        if os.path.isfile(path):
            try:
                img = pygame.image.load(path).convert()
                images.append(img)
                print(f"[TypeFlow] Loaded splash: {path}")
            except Exception as e:
                print(f"[TypeFlow] Failed to load {path}: {e}")
        else:
            print(f"[TypeFlow] Splash file not found: {path}")
    return images


def scale_to_fit(surface, max_w, max_h):
    w, h = surface.get_size()
    if w == 0 or h == 0:
        return surface
    ratio = min(max_w / w, max_h / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    return pygame.transform.smoothscale(surface, (new_w, new_h))


def draw_splash():
    global _splash_current_index, _splash_done

    width, height = screen.get_size()
    screen.fill((0, 0, 0))

    if not _splash_images:
        font = pygame.font.SysFont("arial", 72, bold=True)
        text = font.render("TypeFlow", True, (255, 255, 255))
        rect = text.get_rect(center=(width // 2, height // 2))
        screen.blit(text, rect)
        return

    elapsed = time.time() - _splash_start_time
    total_per_image = SPLASH_DURATION_PER_IMAGE + SPLASH_FADE_TIME

    idx = int(elapsed // total_per_image)
    if idx >= len(_splash_images):
        _splash_done = True
        return

    _splash_current_index = idx
    local_time = elapsed - (idx * total_per_image)

    if local_time < SPLASH_FADE_TIME:
        alpha = local_time / SPLASH_FADE_TIME
    elif local_time > SPLASH_DURATION_PER_IMAGE:
        fade_progress = (local_time - SPLASH_DURATION_PER_IMAGE) / SPLASH_FADE_TIME
        alpha = max(0.0, 1.0 - fade_progress)
    else:
        alpha = 1.0

    alpha = max(0.0, min(1.0, alpha))

    img = _splash_images[idx]
    zoom = 1.0 + 0.05 * (local_time / total_per_image)
    target_w = int(width * 0.75 * zoom)
    target_h = int(height * 0.75 * zoom)

    scaled = scale_to_fit(img, target_w, target_h)
    scaled = scaled.convert_alpha()
    scaled.set_alpha(int(255 * alpha))

    rect = scaled.get_rect(center=(width // 2, height // 2))
    screen.blit(scaled, rect)

    dot_y = height - 50
    dot_gap = 30
    total_dots = len(_splash_images)
    start_x = width // 2 - (total_dots - 1) * dot_gap // 2

    for i in range(total_dots):
        cx = start_x + i * dot_gap
        if i == idx:
            pygame.draw.circle(screen, (255, 255, 255), (cx, dot_y), 8)
        else:
            pygame.draw.circle(screen, (80, 80, 80), (cx, dot_y), 6)


def start_splash():
    global _splash_images, _splash_start_time, _splash_done, _splash_current_index
    _splash_images = load_splash_images()
    _splash_start_time = time.time()
    _splash_done = False
    _splash_current_index = 0


# ============================================================
# SOUND ENGINE
# ============================================================

SAMPLE_RATE = 22050


def generate_tone(freq, duration_ms, volume=0.5, wave="square"):
    if not AUDIO_OK:
        return None
    try:
        n_samples = int(SAMPLE_RATE * duration_ms / 1000)
        buf = array.array("h")
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            env = 1.0
            fade = int(n_samples * 0.15)
            if i > n_samples - fade and fade > 0:
                env = (n_samples - i) / fade
            if wave == "square":
                val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            elif wave == "saw":
                val = 2.0 * (t * freq - math.floor(t * freq + 0.5))
            elif wave == "sine":
                val = math.sin(2 * math.pi * freq * t)
            elif wave == "noise":
                val = random.uniform(-1, 1)
            else:
                val = math.sin(2 * math.pi * freq * t)
            sample = int(val * volume * env * 32767)
            sample = max(-32768, min(32767, sample))
            buf.append(sample)
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception as e:
        print(f"Tone generation failed: {e}")
        return None


def generate_sweep(f1, f2, duration_ms, volume=0.5, wave="square"):
    if not AUDIO_OK:
        return None
    try:
        n_samples = int(SAMPLE_RATE * duration_ms / 1000)
        buf = array.array("h")
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            freq = f1 + (f2 - f1) * (i / n_samples)
            env = 1.0
            fade = int(n_samples * 0.15)
            if i > n_samples - fade and fade > 0:
                env = (n_samples - i) / fade
            if wave == "square":
                val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            else:
                val = math.sin(2 * math.pi * freq * t)
            sample = int(val * volume * env * 32767)
            sample = max(-32768, min(32767, sample))
            buf.append(sample)
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception as e:
        print(f"Sweep generation failed: {e}")
        return None


def generate_arpeggio(notes, note_ms, volume=0.5):
    if not AUDIO_OK:
        return None
    try:
        buf = array.array("h")
        for freq in notes:
            n_samples = int(SAMPLE_RATE * note_ms / 1000)
            for i in range(n_samples):
                t = i / SAMPLE_RATE
                env = 1.0
                fade = int(n_samples * 0.2)
                if i > n_samples - fade and fade > 0:
                    env = (n_samples - i) / fade
                val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
                sample = int(val * volume * env * 32767)
                sample = max(-32768, min(32767, sample))
                buf.append(sample)
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception as e:
        print(f"Arpeggio generation failed: {e}")
        return None


def generate_key_click(volume=0.7, pitch=1.0, click_sharpness=1.0,
                       thump_level=0.6):
    if not AUDIO_OK:
        return None
    try:
        duration_ms = 40
        n_samples = int(SAMPLE_RATE * duration_ms / 1000)
        buf = array.array("h")
        click_freq = 3000 * pitch
        thump_freq = 120 * pitch

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            attack = 0.3 / SAMPLE_RATE
            if t < attack:
                env_click = t / attack
            else:
                env_click = math.exp(-t * 150 * click_sharpness)
            env_thump = math.exp(-t * 50)

            click = random.uniform(-1, 1) * env_click
            click += 0.4 * math.sin(2 * math.pi * click_freq * t) * env_click
            thump = math.sin(2 * math.pi * thump_freq * t) * env_thump

            val = (click * 1.0 + thump * thump_level * 0.7)
            val = math.tanh(val * 1.3)
            val = max(-1.0, min(1.0, val))

            sample = int(val * volume * 32767)
            sample = max(-32768, min(32767, sample))
            buf.append(sample)
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception as e:
        print(f"Key click generation failed: {e}")
        return None


def generate_enter_click(volume=0.8):
    if not AUDIO_OK:
        return None
    try:
        duration_ms = 60
        n_samples = int(SAMPLE_RATE * duration_ms / 1000)
        buf = array.array("h")
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            attack = 0.5 / SAMPLE_RATE
            if t < attack:
                env = t / attack
            else:
                env = math.exp(-t * 60)
            thump = math.sin(2 * math.pi * 90 * t) * env
            click = random.uniform(-1, 1) * math.exp(-t * 150)
            val = click * 0.5 + thump * 0.9
            val = math.tanh(val * 1.3)
            sample = int(val * volume * 32767)
            sample = max(-32768, min(32767, sample))
            buf.append(sample)
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception as e:
        print(f"Enter click failed: {e}")
        return None


def generate_error_thud(volume=0.7):
    if not AUDIO_OK:
        return None
    try:
        duration_ms = 80
        n_samples = int(SAMPLE_RATE * duration_ms / 1000)
        buf = array.array("h")
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            attack = 1.0 / SAMPLE_RATE
            if t < attack:
                env = t / attack
            else:
                env = math.exp(-t * 45)
            thump = math.sin(2 * math.pi * 70 * t) * env
            thump += 0.4 * math.sin(2 * math.pi * 140 * t) * env
            thump = math.tanh(thump * 1.8)
            sample = int(thump * volume * 32767)
            sample = max(-32768, min(32767, sample))
            buf.append(sample)
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception as e:
        print(f"Error thud failed: {e}")
        return None


SOUNDS = {}

if AUDIO_OK:
    SOUNDS["correct"] = generate_arpeggio([988, 1319], 80, volume=0.5)
    SOUNDS["wrong_word"] = generate_sweep(300, 100, 200, 0.5, "saw")
    SOUNDS["streak"] = generate_arpeggio([523, 659, 784, 1047], 100, volume=0.5)
    SOUNDS["start"] = generate_sweep(300, 900, 250, 0.5, "square")
    SOUNDS["gameover"] = generate_sweep(500, 100, 700, 0.5, "square")
    SOUNDS["pause"] = generate_tone(440, 100, 0.4, "square")
    SOUNDS["theme"] = generate_sweep(1200, 600, 100, 0.4, "square")
    SOUNDS["beep"] = generate_tone(1200, 60, 0.4, "square")
    SOUNDS["select"] = generate_tone(660, 40, 0.35, "square")


MECH_KEY_SOUNDS = []
MECH_ENTER_SOUNDS = []

if AUDIO_OK:
    MECH_KEY_SOUNDS.append(generate_key_click(volume=0.7, pitch=1.0,
                                              click_sharpness=0.9,
                                              thump_level=0.6))
    MECH_KEY_SOUNDS.append(generate_key_click(volume=0.65, pitch=1.1,
                                              click_sharpness=1.1,
                                              thump_level=0.7))
    MECH_KEY_SOUNDS.append(generate_key_click(volume=0.75, pitch=0.95,
                                              click_sharpness=0.8,
                                              thump_level=0.65))
    MECH_KEY_SOUNDS.append(generate_key_click(volume=0.68, pitch=1.05,
                                              click_sharpness=1.0,
                                              thump_level=0.6))
    MECH_KEY_SOUNDS.append(generate_key_click(volume=0.72, pitch=1.0,
                                              click_sharpness=1.2,
                                              thump_level=0.75))

    MECH_ENTER_SOUNDS.append(generate_enter_click(volume=0.8))
    MECH_ENTER_SOUNDS.append(generate_enter_click(volume=0.85))
    MECH_ENTER_SOUNDS.append(generate_enter_click(volume=0.78))

    SOUNDS["mech_error"] = generate_error_thud(volume=0.7)


def play_mech_key():
    if not sound_enabled or not AUDIO_OK:
        return
    if MECH_KEY_SOUNDS:
        snd = random.choice(MECH_KEY_SOUNDS)
        if snd:
            try:
                snd.play()
            except Exception:
                pass


def play_mech_enter():
    if not sound_enabled or not AUDIO_OK:
        return
    if MECH_ENTER_SOUNDS:
        snd = random.choice(MECH_ENTER_SOUNDS)
        if snd:
            try:
                snd.play()
            except Exception:
                pass


sound_enabled = True
_last_countdown_second = None


def play_sound(name):
    if not sound_enabled or not AUDIO_OK:
        return
    snd = SOUNDS.get(name)
    if snd is not None:
        try:
            snd.play()
        except Exception:
            pass


# ============================================================
# THEME SYSTEM — 5 CLEAN THEMES
# ============================================================

THEMES = {
    "RETRO_ARCADE": {
        "name": "RETRO ARCADE",
        "bg": (40, 40, 40), "card": (60, 56, 54),
        "card_2": (80, 73, 69), "card_hover": (100, 92, 84),
        "border": (146, 131, 116), "white": (251, 241, 199),
        "text": (235, 219, 178), "muted": (168, 153, 132),
        "accent": (214, 93, 14), "accent_dark": (140, 60, 10),
        "cyan": (104, 157, 106), "green": (152, 151, 26),
        "red": (204, 36, 29), "yellow": (215, 153, 33),
        "purple": (177, 98, 134), "black": (20, 20, 20),
        "font_name": "couriernew", "mono_font": "couriernew",
        "scanlines": True, "screen_shake": True,
        "flash": True, "vignette": True, "glow": True,
    },
    "GREEN_APPLE": {
        "name": "GREEN APPLE",
        "bg": (14, 22, 18), "card": (22, 34, 28),
        "card_2": (30, 46, 38), "card_hover": (40, 60, 50),
        "border": (58, 84, 70), "white": (235, 250, 240),
        "text": (210, 230, 218), "muted": (128, 156, 140),
        "accent": (52, 199, 89), "accent_dark": (28, 130, 58),
        "cyan": (86, 214, 180), "green": (100, 220, 130),
        "red": (232, 78, 88), "yellow": (240, 200, 80),
        "purple": (150, 190, 130), "black": (6, 12, 9),
        "font_name": "arial", "mono_font": "consolas",
        "scanlines": False, "screen_shake": False,
        "flash": False, "vignette": False, "glow": False,
    },
    "BURGANDY": {
        "name": "BURGANDY",
        "bg": (26, 10, 16), "card": (42, 16, 24),
        "card_2": (56, 22, 32), "card_hover": (74, 30, 42),
        "border": (104, 44, 58), "white": (250, 235, 238),
        "text": (232, 208, 214), "muted": (168, 128, 138),
        "accent": (180, 42, 78), "accent_dark": (120, 24, 50),
        "cyan": (200, 150, 130), "green": (110, 180, 130),
        "red": (232, 82, 96), "yellow": (224, 176, 96),
        "purple": (200, 120, 170), "black": (12, 4, 8),
        "font_name": "arial", "mono_font": "consolas",
        "scanlines": False, "screen_shake": False,
        "flash": False, "vignette": False, "glow": False,
    },
    "GLACIER": {
        "name": "GLACIER",
        "bg": (14, 22, 32), "card": (22, 34, 48),
        "card_2": (30, 46, 64), "card_hover": (42, 62, 84),
        "border": (62, 92, 120), "white": (240, 248, 255),
        "text": (208, 224, 240), "muted": (128, 152, 178),
        "accent": (74, 168, 224), "accent_dark": (38, 108, 168),
        "cyan": (110, 216, 240), "green": (100, 200, 170),
        "red": (232, 96, 112), "yellow": (235, 200, 120),
        "purple": (150, 160, 232), "black": (6, 12, 20),
        "font_name": "arial", "mono_font": "consolas",
        "scanlines": False, "screen_shake": False,
        "flash": False, "vignette": False, "glow": False,
    },
    "SILVER": {
        "name": "SILVER",
        "bg": (24, 26, 30), "card": (36, 38, 44),
        "card_2": (48, 51, 58), "card_hover": (62, 66, 74),
        "border": (92, 96, 106), "white": (245, 246, 248),
        "text": (214, 218, 224), "muted": (140, 146, 156),
        "accent": (168, 178, 192), "accent_dark": (110, 118, 130),
        "cyan": (150, 200, 210), "green": (140, 200, 160),
        "red": (220, 100, 110), "yellow": (225, 195, 130),
        "purple": (180, 170, 200), "black": (12, 14, 18),
        "font_name": "arial", "mono_font": "consolas",
        "scanlines": False, "screen_shake": False,
        "flash": False, "vignette": False, "glow": False,
    },
}

THEME_ORDER = [
    "RETRO_ARCADE", "GREEN_APPLE", "BURGANDY", "GLACIER", "SILVER",
]

active_theme_name = "RETRO_ARCADE"
theme = THEMES[active_theme_name]

ACCENT_ORANGE = (255, 120, 30)
ACCENT_ORANGE_DARK = (200, 80, 0)


def darken(color, factor=0.45):
    return (
        int(color[0] * factor),
        int(color[1] * factor),
        int(color[2] * factor),
    )


def get_section_colors():
    name = active_theme_name

    if name == "RETRO_ARCADE":
        return ((214, 93, 14), (204, 36, 29), (152, 151, 26))
    elif name == "GREEN_APPLE":
        return ((52, 199, 89), (232, 78, 88), (86, 214, 180))
    elif name == "BURGANDY":
        return ((180, 42, 78), (232, 82, 96), (200, 150, 130))
    elif name == "GLACIER":
        return ((74, 168, 224), (232, 96, 112), (110, 216, 240))
    elif name == "SILVER":
        return ((168, 178, 192), (220, 100, 110), (150, 200, 210))

    return (ACCENT_ORANGE, ACCENT_ORANGE, ACCENT_ORANGE)


def switch_theme():
    global active_theme_name, theme
    global BG, CARD, CARD_2, CARD_HOVER, BORDER, WHITE, TEXT, MUTED
    global INDIGO, INDIGO_DARK, CYAN, GREEN, RED, YELLOW, PURPLE, BLACK
    global FONT_TITLE, FONT_HERO, FONT_BIG, FONT_MEDIUM, FONT_NORMAL
    global FONT_SMALL, FONT_TINY, FONT_WORD, FONT_INPUT

    idx = THEME_ORDER.index(active_theme_name)
    active_theme_name = THEME_ORDER[(idx + 1) % len(THEME_ORDER)]
    theme = THEMES[active_theme_name]

    BG = theme["bg"]
    CARD = theme["card"]
    CARD_2 = theme["card_2"]
    CARD_HOVER = theme["card_hover"]
    BORDER = theme["border"]
    WHITE = theme["white"]
    TEXT = theme["text"]
    MUTED = theme["muted"]
    INDIGO = theme["accent"]
    INDIGO_DARK = theme["accent_dark"]
    CYAN = theme["cyan"]
    GREEN = theme["green"]
    RED = theme["red"]
    YELLOW = theme["yellow"]
    PURPLE = theme["purple"]
    BLACK = theme["black"]

    fn = theme["font_name"]
    mn = theme["mono_font"]

    # ===== FONT SIZE + BOLD UPDATED =====
    FONT_TITLE = pygame.font.SysFont(fn, 48, bold=True)
    FONT_HERO = pygame.font.SysFont(fn, 58, bold=True)
    FONT_BIG = pygame.font.SysFont(fn, 38, bold=True)
    FONT_MEDIUM = pygame.font.SysFont(fn, 28, bold=True)
    FONT_NORMAL = pygame.font.SysFont(fn, 24, bold=True)
    FONT_SMALL = pygame.font.SysFont(fn, 20, bold=True)
    FONT_TINY = pygame.font.SysFont(fn, 16, bold=True)
    FONT_WORD = pygame.font.SysFont(mn, 50, bold=True)
    FONT_INPUT = pygame.font.SysFont(mn, 36, bold=True)

    play_sound("theme")


BG = theme["bg"]
CARD = theme["card"]
CARD_2 = theme["card_2"]
CARD_HOVER = theme["card_hover"]
BORDER = theme["border"]
WHITE = theme["white"]
TEXT = theme["text"]
MUTED = theme["muted"]
INDIGO = theme["accent"]
INDIGO_DARK = theme["accent_dark"]
CYAN = theme["cyan"]
GREEN = theme["green"]
RED = theme["red"]
YELLOW = theme["yellow"]
PURPLE = theme["purple"]
BLACK = theme["black"]

# ===== INITIAL FONT SIZE + BOLD UPDATED =====
FONT_TITLE = pygame.font.SysFont(theme["font_name"], 48, bold=True)
FONT_HERO = pygame.font.SysFont(theme["font_name"], 58, bold=True)
FONT_BIG = pygame.font.SysFont(theme["font_name"], 38, bold=True)
FONT_MEDIUM = pygame.font.SysFont(theme["font_name"], 28, bold=True)
FONT_NORMAL = pygame.font.SysFont(theme["font_name"], 24, bold=True)
FONT_SMALL = pygame.font.SysFont(theme["font_name"], 20, bold=True)
FONT_TINY = pygame.font.SysFont(theme["font_name"], 16, bold=True)
FONT_WORD = pygame.font.SysFont(theme["mono_font"], 50, bold=True)
FONT_INPUT = pygame.font.SysFont(theme["mono_font"], 36, bold=True)

# ============================================================
# EFFECTS STATE
# ============================================================

shake_intensity = 0
shake_decay = 0.85
flash_alpha = 0
flash_decay = 25
flash_color = (255, 255, 255)
correct_flash_alpha = 0
scanline_surface = None
vignette_surface = None


def build_scanlines(width, height):
    global scanline_surface
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, 3):
        pygame.draw.line(surf, (0, 0, 0, 45), (0, y), (width, y), 1)
    scanline_surface = surf


def build_vignette(width, height):
    global vignette_surface
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2
    cy = height // 2
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    steps = 40
    for i in range(steps):
        radius = int(max_dist * (1 - i / steps))
        alpha = int(120 * (i / steps) ** 2)
        if radius > 0:
            pygame.draw.circle(
                surf, (0, 0, 0, alpha), (cx, cy), radius,
                width=max(1, (width // steps) + 1)
            )
    vignette_surface = surf


def trigger_shake(intensity=8):
    global shake_intensity
    if theme["screen_shake"]:
        shake_intensity = max(shake_intensity, intensity)


def trigger_flash(color=(255, 255, 255), alpha=100):
    global flash_alpha, flash_color
    if theme["flash"]:
        flash_alpha = alpha
        flash_color = color


def trigger_correct_flash():
    global correct_flash_alpha
    if theme["flash"]:
        correct_flash_alpha = 60


# ============================================================
# WORD / SENTENCE BASE DATA
# ============================================================

EASY_BASE = [
    "apple", "banana", "computer", "python", "coding", "school", "student",
    "keyboard", "mouse", "monitor", "internet", "program", "software",
    "hardware", "science", "technology", "university", "education",
    "hello", "world", "future", "learning", "book", "chair", "class",
    "cloud", "desk", "door", "dream", "earth", "family", "flower",
    "friend", "game", "garden", "home", "house", "language", "lesson",
    "light", "market", "mobile", "money", "music", "paper", "phone",
    "picture", "planet", "screen", "teacher", "time", "today", "tree",
    "water", "weather", "window", "work", "team", "people", "country",
    "city", "river", "road", "story", "problem", "answer", "question",
    "example", "project",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "10", "20", "25", "50", "99", "100", "101", "123", "200", "500",
    "999", "1000", "2024", "2025", "2026", "2030", "1234", "5678", "12345",
    "apple123", "Apple123", "student2026", "code123", "python3",
    "school2026", "hello123", "user123",
    "hello!", "world!", "good@day", "test#1", "user_123",
    "hello-world", "good_day", "price$10", "score=100",
    "x+10", "x-5", "x*2", "x/2",
    "Hello", "World", "Python", "Code", "Apple", "Book", "Cat", "Dog",
    "Red", "Blue", "Sun", "Moon", "Star", "Tree", "Fish",
    "Hello!", "World!", "Python!", "Code!", "Hi!",
    "Code1", "Test2", "Run3", "Go4", "Try5",
    "A1", "B2", "C3", "X1", "Y2", "Z3",
    "user1", "user2", "pass1", "name1", "id1",
    "user_1", "test_2", "file_3",
    "A_B", "X_Y", "P_Q",
    "Hi!", "Ok!", "Yes!", "No!",
    "aB", "Ab", "xY", "Yx",
    "Go!", "Run!", "Try!", "Win!",
    "123abc", "abc123", "A1b2",
    "Cat1", "Dog2", "Bird3",
    "Hi@1", "Bye@2", "Ok@3",
    "user@1", "test@2", "admin@3",
    "1+2", "3-1", "2*3", "8/2",
    "x=1", "y=2", "z=3",
    "a+b", "c-d", "e*f",
    "UP", "DOWN", "LEFT", "RIGHT",
    "Open", "Close", "Start", "Stop",
]

MEDIUM_BASE = [
    "ability", "absolute", "account", "activity", "address", "advance",
    "adventure", "analysis", "application", "approach", "argument",
    "article", "balance", "behavior", "benefit", "business", "calendar",
    "challenge", "character", "choice", "communication", "community",
    "company", "complete", "condition", "connection", "control", "culture",
    "customer", "database", "decision", "development", "difference",
    "direction", "education", "environment", "experience", "feature",
    "function", "government", "information", "internet", "knowledge",
    "management", "message", "method", "operation", "organization",
    "performance", "planning", "platform", "practice", "process",
    "programming", "research", "resource", "security", "service",
    "software", "solution", "system", "technology", "university",
    "website", "developer", "engineering", "networking", "algorithm",
    "10", "20", "30", "40", "50", "100", "101", "111", "123", "200",
    "250", "300", "365", "500", "512", "750", "800", "999", "1000",
    "1024", "1500", "2024", "2025", "2026", "2030", "2040", "5000",
    "10000", "12345", "54321", "123456",
    "Python3", "Python3.12", "Python2026", "Java8", "Java17", "Java21",
    "C++11", "C++17", "C++20", "HTML5", "CSS3", "ES6", "NodeJS18",
    "NodeJS20", "Windows10", "Windows11", "Android14", "Android15",
    "IPv4", "IPv6", "CSE2026", "Student2026", "Developer2026",
    "x=10", "x=100", "x==10", "x!=10", "x>=10", "x<=10",
    "a+b", "a-b", "a*b", "a/b", "x%2", "x++", "x--", "a&&b", "a||b",
    "!true", "user_name", "student_id", "account_id", "file_name",
    "data_value", "max_value", "hello-world", "hello_world",
    "test-case", "test_case", "password@123", "admin#2026", "data$2026",
    "student@gmail.com", "user@gmail.com", "admin@example.com",
    "test@example.com",
    "google.com", "github.com", "example.com", "www.google.com",
    "www.example.com", "https://google.com", "https://github.com"
]

HARD_BASE = [
    "abstraction", "algorithm", "architecture", "authentication",
    "authorization", "automation", "availability", "benchmark",
    "classification", "configuration", "cryptography", "cybersecurity",
    "decentralization", "deployment", "documentation", "encryption",
    "framework", "implementation", "infrastructure", "integration",
    "intelligence", "interoperability", "optimization", "parallelism",
    "programming", "reliability", "scalability", "simulation",
    "specification", "synchronization", "transformation", "virtualization",
    "visualization", "computation", "concurrency", "complexity",
    "dependency", "distributed", "evaluation", "execution", "interface",
    "prediction", "recognition", "regression", "supervised",
    "unsupervised", "dataset", "training", "validation", "accuracy",
    "precision", "recall", "generalization", "representation",
    "reconstruction", "interpretation", "vulnerability",
    "confidentiality", "integrity", "responsibility", "professionalism",
    "entrepreneurship", "microcontroller", "microprocessor",
    "Python", "JavaScript", "TypeScript", "ReactJS", "NodeJS",
    "MongoDB", "MySQL", "GitHub", "GitLab", "Linux", "Windows",
    "Android", "Arduino",
    "0000", "0001", "0010", "0101", "0110", "1000", "1010", "1111",
    "1234", "5678", "9999", "10000", "12345", "54321", "123456",
    "654321", "999999", "2024", "2025", "2026", "2027", "2030",
    "2040", "2050", "1234567890",
    "Python3.12", "Python3.13", "Java8", "Java11", "Java17", "Java21",
    "C++11", "C++14", "C++17", "C++20", "C++23", "C#10", "C#12",
    "HTML5", "CSS3", "ES6", "NodeJS18", "NodeJS20", "NodeJS22",
    "Android14", "Android15", "Windows10", "Windows11", "IPv4", "IPv6",
    "CSE2026", "AI2026", "ML2026",
    "x=100", "x==100", "x!=100", "x>=100", "x<=100", "x+y", "x-y",
    "x*y", "x/y", "x%2", "x**2", "a+b*c", "(a+b)*c", "x&&y", "x||y",
    "!x", "x++", "++x", "x--", "--x",
    "user_name", "student_id", "account_id", "file_name", "data_value",
    "max_value", "min_value", "hello-world", "hello_world", "test-case",
    "test_case", "password@123", "admin@2026!", "user#2026", "data$2026",
    "aB3$xY9!", "A7@bC#21", "xYz_123!", "QwErTy@2026", "AaBbCc123!",
    "aA1!bB2@cC3#", "XyZ@123#AbC", "r2D2@C3PO", "AI_ML@2026!",
    "WebDev#2026!", "CyberSec@2026!", "Robotics#2026!", "Arduino@UNO#2026",
    "student@gmail.com", "student2026@gmail.com", "Student2026@gmail.com",
    "admin@example.com", "developer@github.com", "Developer@GitHub.com",
    "https://google.com", "https://github.com", "https://example.com",
    "www.google.com", "www.GitHub.com", "www.example.com"
]

EASY_SENTENCES = [
    "I like coding.", "Good morning!", "Good Morning!", "HELLO World!",
    "My name is Razibul.", "I am a Student.", "I like Python.",
    "Coding is fun!", "Practice every day.", "Keep learning!",
    "Keep Coding!", "Work hard and learn.", "Technology is useful.",
    "Books help us learn.", "Students need practice.",
    "Always check your work.", "Small steps create progress.",
    "Learning takes time.", "Never stop learning!",
    "Hello World!", "My name is John.", "I am 20 years old.",
    "I have 2 cats.", "The sky is Blue.", "I love Python!",
    "User name is john_123.", "Score = 100.", "x = 10 and y = 20.",
    "Hi! How are you?", "Good morning, friend!", "Today is a good day.",
    "I like ice cream.", "The book is on the table.", "She is a teacher.",
    "He is a doctor.", "We are students.", "It is 5 PM now.",
    "My ID is 2026.", "Call me at 9 AM.", "I love my family.",
    "The cat is sleeping.", "The dog is running.",
    "I go to school every day.", "My favorite color is Blue.",
    "The sun is bright today.", "I have a new book.",
    "We play games after school.", "She reads a book.",
    "He writes a letter.", "They are good friends.", "I eat an apple.",
    "The flower is beautiful.", "Birds can fly high.",
    "Fish live in water.", "My mother cooks food.",
    "My father goes to work.", "I love my country.",
    "The moon is bright tonight.", "Stars shine in the sky.",
    "I brush my teeth twice.", "Wash your hands before eating.",
    "Drink water every day.", "Eat healthy food.",
    "Sleep early at night.", "Wake up early in the morning.",
    "I like to draw pictures.", "Music makes me happy.",
    "Dancing is fun.", "Reading books is good.",
    "Let us go to the park.", "The weather is nice.",
    "It is raining outside.", "Take an umbrella with you.",
    "I wear a red shirt.", "My shoes are black.",
    "The car is fast.", "The bus is slow.",
    "I can ride a bicycle.", "We travel by train.",
]

MEDIUM_SENTENCES = [
    "I like programming because it helps me solve real problems.",
    "Learning Python is easier when you practice every single day.",
    "Good software should be simple, useful, and easy to understand.",
    "Students can improve their skills by solving problems regularly.",
    "Technology changes quickly, so developers must keep learning.",
    "A clean program is easier to read, test, debug, and maintain.",
    "Practice makes your typing faster, more accurate, and more comfortable.",
    "Always check your code carefully before running the program.",
    "Computer science is about solving problems using logical thinking.",
    "A good developer writes code that other people can understand.",
    "Small mistakes can create big problems in a software project.",
    "Learning new technologies can create better opportunities in the future.",
    "Python3 is easy to learn!",
    "I started CSE in 2026.",
    "My score is 95%, but I want 100%!",
    "Student_ID = 2026.",
    "The value of x is 100.",
    "User@2026 is ready!",
    "Code#123 is a test case.",
    "Version 2.0 is better than version 1.0.",
    "Use Python3.12 for this project.",
    "The password is P@ss123!",
    "Email me at Student2026@gmail.com.",
    "Visit https://github.com for more information.",
    "User_ID = 101 and Score = 95%.",
    "Login with Admin@123! to continue.",
    "Order #2026 costs $150.50 only.",
    "Call me at +880-1712-345678.",
    "Version 2.5.1 has 3 new features!",
    "Email: user_2026@yahoo.com is active.",
    "Press Ctrl+S to save file_01.txt.",
    "Formula: (a+b)*2 = 100% correct.",
    "IP address is 192.168.0.1:8080.",
    "Use @username and #hashtag in posts.",
    "50% discount on orders above $99!",
    "Student ID: CSE-2026-045 is valid.",
    "Time is 10:30 AM, Date: 05/10/2026.",
    "Code: x = y + 10 * (z - 5) / 2;",
    "Total: 3 items @ $25.99 = $77.97.",
    "The quick brown fox jumps over the lazy dog.",
    "A journey of a thousand miles begins with a single step.",
    "Practice makes perfect, so keep trying every single day.",
    "Success comes to those who work hard and never give up.",
    "Knowledge is power, but action turns knowledge into results.",
    "Learning to code opens many doors in the modern world.",
    "Always write clean code that others can easily understand.",
    "Debugging is twice as hard as writing the code in the first place.",
    "Premature optimization is the root of all evil in programming.",
    "Simplicity is the ultimate sophistication in software design.",
    "The best way to predict the future is to invent it.",
    "Any fool can write code that a computer can understand.",
    "Good programmers write code that humans can understand.",
    "First solve the problem, then write the code.",
    "Talk is cheap. Show me the code.",
    "Programs must be written for people to read.",
    "Make it work, make it right, make it fast.",
    "The only way to learn a new programming language is by writing programs in it.",
    "Testing leads to failure, and failure leads to understanding.",
    "Deleted code is debugged code.",
    "A good programmer is someone who always looks both ways before crossing a one-way street.",
    "Before software can be reusable, it first has to be usable.",
    "Programming is not about typing; it is about thinking.",
    "The function of good software is to make the complex appear simple.",
]

HARD_SENTENCES = [
    "I enjoy learning programming because it helps me solve real-world problems.",
    "A good software developer should understand both technology and user requirements.",
    "Learning Python3 becomes easier when you practice coding for at least 1 hour every day.",
    "Students can improve their programming skills by solving different problems and debugging their code.",
    "Technology is changing rapidly, so developers must continuously learn new tools, frameworks, and techniques.",
    "Clean and readable code makes software easier to test, maintain, debug, and improve in the future.",
    "A successful project requires proper planning, teamwork, communication, testing, and continuous improvement.",
    "Machine learning systems need reliable data, suitable algorithms, proper training, and accurate evaluation.",
    "Cybersecurity is important because personal information, financial data, and business systems must be protected.",
    "Programming is not only about writing code; it is also about understanding problems and designing effective solutions.",
    "A good algorithm can reduce execution time and make a computer program more efficient and reliable.",
    "Artificial Intelligence, Machine Learning, and Robotics are rapidly changing the way people use technology.",
    "The developer should check every input carefully because unexpected data can create errors or security problems.",
    "Practice typing every character correctly because accuracy is important when writing code, passwords, and commands.",
    "Modern applications often use databases, APIs, cloud services, authentication, encryption, and automated testing.",
    "Python3.12 is a powerful programming language used for AI, ML, automation, and data analysis.",
    "My CSE2026 project uses Python3, HTML5, CSS3, and JavaScript to build a modern web application.",
    "The final score is 95%, but my target is 100% because accuracy matters more than speed.",
    "Student_ID = 2026, and the system should verify the ID before allowing the user to continue.",
    "The value of x is 100, while the value of y is 50; therefore, x + y = 150.",
    "Use Password@123! only as a typing example; never use simple passwords for real accounts.",
    "The user entered Admin@2026! but the system rejected it because the password was incorrect.",
    "Email the project report to Student2026@gmail.com before 11:59 PM on 30 September 2026.",
    "Visit https://github.com and search for useful open-source projects related to Python3 and Machine Learning.",
    "Windows11, Android15, Linux, and macOS provide different environments for software development.",
    "The expression x>=100 && y<=50 is true only when both conditions are satisfied.",
    "Use C++20 when you need modern language features, better abstractions, and efficient programming techniques.",
    "AI_ML@2026! is an example of a case-sensitive string containing uppercase letters, lowercase letters, numbers, and symbols.",
    "A7@bC#21 is different from a7@bc#21 because uppercase and lowercase characters are treated as different.",
    "Version 3.13.0 may contain new features, but developers should always read the official documentation before upgrading.",
    "Robotics#2026! combines letters, numbers, and symbols, making it useful as a difficult typing example.",
    "The system must validate username, password, email, and Student_ID before creating a new account.",
    "Machine Learning models require training data, validation data, testing data, suitable parameters, and careful evaluation.",
    "Good developers do not simply make code work; they also consider readability, security, performance, scalability, and maintainability.",
    "When typing a case-sensitive sentence, you must carefully type every uppercase letter, lowercase letter, number, space, and symbol correctly.",
    "The API key is sk_live_4eC39HqLyjWDarjtT1zdp7dc, keep it secret!",
    "Run command: python3 -m pip install --upgrade pip==24.0.",
    "URL: https://api.github.com/users/Student2026/repos?per_page=100",
    "Regex pattern: ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$",
    "File path: /home/user/Documents/Project_2026/final_report_v2.1.pdf",
    "Database: mongodb://admin:P@ssw0rd123@localhost:27017/mydb",
    "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
    "Condition: (x >= 100 && y <= 50) || (z != 0 && w == 25%)",
    "Email: Developer2026+test@gmail.com replied at 11:59 PM!",
    "IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334 is valid.",
    "SHA-256: a3f5c9e1b7d2f8a4c6e0b3d9f1a7c5e2b8d4f6a0c3e7b1d5f9a2c6e0b4d8f2a6",
    "Use C++17's std::optional<T> for safer code!",
    "Password: Tr0ub4dor&3 is stronger than password123.",
    "JSON: {\"name\": \"Razibul\", \"age\": 22, \"cgpa\": 3.75}",
    "Command: sudo apt-get install -y nodejs@18.19.0 npm@10.2.4",
    "The user @razibul_2026 paid $49.99 for order #ORD-2026-0451.",
    "Config: DEBUG=True, PORT=8080, HOST=127.0.0.1, TIMEOUT=30s.",
    "Hash: $2b$12$KIXQx8Y7Z9W3vN5mP1qR8uT4sL6jH2gF0dC9bA7eS3wX1yZ5vU8nM",
    "Formula: E = mc^2 where m=1kg and c=3x10^8 m/s.",
    "Access token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789 expires in 30 days.",
    "The only way to do great work is to love what you do, and keep doing it every single day.",
    "A distributed system is one in which the failure of a computer you didn't even know existed can render your own computer unusable.",
    "There are only two hard things in computer science: cache invalidation, naming things, and off-by-one errors.",
    "Any application that can be written in JavaScript will eventually be written in JavaScript.",
    "The most important property of a program is whether it accomplishes the intention of its user.",
    "Programs are meant to be read by humans and only incidentally for computers to execute.",
    "Debugging is like being the detective in a crime movie where you are also the murderer.",
    "Computer science is no more about computers than astronomy is about telescopes.",
    "The best error message is the one that never shows up because the code prevented the error.",
    "Beware of bugs in the above code; I have only proved it correct, not tried it.",
    "Measuring programming progress by lines of code is like measuring aircraft building progress by weight.",
    "Optimism is an occupational hazard of programming; feedback is the treatment.",
    "Before you use a new library, understand what problem it solves and whether you actually need it.",
    "Reading documentation carefully can save you hours of debugging and searching online forums.",
    "Version control systems like Git allow developers to track changes, collaborate, and revert mistakes.",
    "A unit test verifies that a specific piece of code works correctly in isolation from the rest of the system.",
    "Continuous integration automatically runs tests whenever code changes are pushed to the repository.",
    "Refactoring improves the internal structure of code without changing its external behavior.",
    "Code reviews help teams catch bugs early, share knowledge, and maintain consistent coding standards.",
    "The Single Responsibility Principle states that a class should have only one reason to change.",
    "Functional programming emphasizes immutability, pure functions, and avoiding side effects.",
    "Object-oriented programming organizes code around objects that combine data and behavior.",
    "Asynchronous programming allows multiple tasks to run concurrently without blocking the main thread.",
    "Microservices architecture divides an application into small, independently deployable services.",
    "Cloud computing provides on-demand access to computing resources over the internet.",
]

# ============================================================
# CASE-SENSITIVE VARIATIONS
# ============================================================


def make_case_variants(text):
    variants = set()
    variants.add(text)
    variants.add(text.lower())
    variants.add(text.upper())
    variants.add(text.capitalize())
    variants.add(text.title())

    result1 = ""
    upper = True
    for char in text:
        if char.isalpha():
            result1 += char.upper() if upper else char.lower()
            upper = not upper
        else:
            result1 += char
    variants.add(result1)

    result2 = ""
    upper = False
    for char in text:
        if char.isalpha():
            result2 += char.upper() if upper else char.lower()
            upper = not upper
        else:
            result2 += char
    variants.add(result2)

    result3 = ""
    counter = 0
    for char in text:
        if char.isalpha():
            if counter % 3 == 0:
                result3 += char.upper()
            else:
                result3 += char.lower()
            counter += 1
        else:
            result3 += char
    variants.add(result3)

    return list(variants)


def expand_case_variants(items):
    result = []
    for item in items:
        result.extend(make_case_variants(item))
    return list(set(result))


EASY_WORDS = list(set(
    expand_case_variants(EASY_BASE) + expand_case_variants(EASY_SENTENCES)
))
MEDIUM_WORDS = list(set(
    expand_case_variants(MEDIUM_BASE) + expand_case_variants(MEDIUM_SENTENCES)
))
HARD_WORDS = list(set(
    expand_case_variants(HARD_BASE) + expand_case_variants(HARD_SENTENCES)
))

# ============================================================
# BACKGROUND
# ============================================================

background_mode = "THEME"
rgb_r = 15
rgb_g = 18
rgb_b = 30


def get_background():
    if background_mode == "THEME":
        return BG
    if background_mode == "DARK":
        return (15, 18, 30)
    if background_mode == "GRAY":
        return (55, 60, 72)
    if background_mode == "WHITE":
        return (238, 241, 246)
    if background_mode == "BLACK":
        return BLACK
    if background_mode == "RGB":
        return (rgb_r, rgb_g, rgb_b)
    return BG


def update_rgb():
    global rgb_r, rgb_g, rgb_b
    rgb_r += random.choice([-1, 0, 1])
    rgb_g += random.choice([-1, 0, 1])
    rgb_b += random.choice([-1, 0, 1])
    rgb_r = max(15, min(70, rgb_r))
    rgb_g = max(15, min(70, rgb_g))
    rgb_b = max(20, min(90, rgb_b))


# ============================================================
# GAME STATE
# ============================================================

difficulty = "EASY"
selected_timer = 60
game_state = "MENU"

current_word = ""
user_input = ""
wrong_positions = set()

score = 0
correct_keystrokes = 0
wrong_keystrokes = 0
total_keystrokes = 0
completed_words = 0
streak = 0
best_streak = 0

start_time = None
elapsed_time = 0
time_left = 60
pause_started = None

message = ""
message_color = WHITE
message_until = 0

fullscreen = False
custom_timer_mode = False
custom_timer_input = ""

_esc_pressed_time = 0

# ============================================================
# GAME FUNCTIONS
# ============================================================


def get_words():
    if difficulty == "EASY":
        return EASY_WORDS
    if difficulty == "MEDIUM":
        return MEDIUM_WORDS
    return HARD_WORDS


def generate_word():
    return random.choice(get_words())


def reset_statistics():
    global score, correct_keystrokes, wrong_keystrokes, total_keystrokes
    global completed_words, streak, best_streak, elapsed_time
    global _last_countdown_second

    score = 0
    correct_keystrokes = 0
    wrong_keystrokes = 0
    total_keystrokes = 0
    completed_words = 0
    streak = 0
    best_streak = 0
    elapsed_time = 0
    wrong_positions.clear()
    _last_countdown_second = None


def start_game():
    global game_state, current_word, user_input
    global start_time, elapsed_time, time_left, pause_started

    reset_statistics()
    current_word = generate_word()
    user_input = ""
    elapsed_time = 0
    time_left = selected_timer
    pause_started = None
    start_time = time.time()
    game_state = "PLAYING"
    play_sound("start")


def restart_game():
    start_game()


def get_accuracy():
    if total_keystrokes == 0:
        return 100.0
    return (correct_keystrokes / total_keystrokes) * 100


def get_wpm():
    if elapsed_time <= 0:
        return 0
    return int(completed_words / (elapsed_time / 60))


def show_message(text, color=WHITE, duration=1.2):
    global message, message_color, message_until
    message = text
    message_color = color
    message_until = time.time() + duration


def toggle_pause():
    global game_state, pause_started, start_time

    if game_state == "PLAYING":
        pause_started = time.time()
        game_state = "PAUSED"
        play_sound("pause")
    elif game_state == "PAUSED":
        if pause_started is not None:
            pause_duration = time.time() - pause_started
            start_time += pause_duration
        pause_started = None
        game_state = "PLAYING"
        play_sound("pause")


def finish_game():
    global game_state, elapsed_time, time_left
    elapsed_time = selected_timer
    time_left = 0
    game_state = "GAME_OVER"
    play_sound("gameover")


def submit_word():
    global current_word, user_input, score
    global completed_words, streak, best_streak
    global wrong_keystrokes, total_keystrokes

    if user_input == current_word:
        completed_words += 1
        streak += 1
        best_streak = max(best_streak, streak)
        score += len(current_word) * 10

        play_mech_enter()

        if streak >= 5:
            score += 100
            play_sound("streak")
        elif streak >= 3:
            score += 50
            play_sound("correct")
        else:
            play_sound("correct")

        if difficulty == "MEDIUM":
            score += 25
        elif difficulty == "HARD":
            score += 75

        show_message("Correct!", GREEN)
        trigger_correct_flash()

        current_word = generate_word()
        user_input = ""
        wrong_positions.clear()
    else:
        wrong_keystrokes += 1
        total_keystrokes += 1
        streak = 0

        if difficulty == "HARD":
            score = max(0, score - 75)
        elif difficulty == "MEDIUM":
            score = max(0, score - 30)
        else:
            score = max(0, score - 10)

        show_message("Incorrect word!", RED)
        trigger_shake(10)
        trigger_flash(RED, 80)
        play_sound("wrong_word")
        play_sound("mech_error")


# ============================================================
# DRAWING HELPERS
# ============================================================


def draw_text(text, font, color, x, y, center=False):
    surface = font.render(str(text), True, color)
    if center:
        rect = surface.get_rect(center=(x, y))
    else:
        rect = surface.get_rect(topleft=(x, y))
    screen.blit(surface, rect)
    return rect


def rounded_rect(rect, color, radius=12, border=None, border_width=1):
    pygame.draw.rect(screen, color, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(
            screen, border, rect,
            width=border_width, border_radius=radius
        )


def get_fitted_font(text, max_width, base_size=30, minimum_size=14,
                    font_name=None, bold=False):
    if font_name is None:
        font_name = theme["mono_font"]
    size = base_size
    while size > minimum_size:
        font = pygame.font.SysFont(font_name, size, bold=bold)
        if font.size(text)[0] <= max_width:
            return font
        size -= 1
    return pygame.font.SysFont(font_name, minimum_size, bold=bold)


# ============================================================
# TOP BAR
# ============================================================


def draw_top_bar():
    width, height = screen.get_size()
    top_bar_surf = pygame.Surface((width, 110), pygame.SRCALPHA)
    top_bar_surf.fill((*CARD, 220))
    screen.blit(top_bar_surf, (0, 0))
    pygame.draw.line(screen, BORDER, (0, 109), (width, 109), 1)

    draw_text("TypeFlow", FONT_TITLE, WHITE, 32, 18)
    draw_text("SPEED TYPING", FONT_TINY, CYAN, 36, 68)

    if AUDIO_OK:
        sound_label = "SOUND: ON" if sound_enabled else "SOUND: OFF"
        sound_color = GREEN if sound_enabled else RED
    else:
        sound_label = "SOUND: N/A"
        sound_color = MUTED

    draw_text(sound_label, FONT_TINY, sound_color, 220, 68)

    badge_y = 37
    badge_h = 36

    timer_w = 105
    timer = pygame.Rect(width - 32 - timer_w, badge_y, timer_w, badge_h)
    timer_color = CYAN
    if game_state == "PLAYING":
        if time_left <= 10:
            timer_color = RED
        elif time_left <= 20:
            timer_color = YELLOW

    rounded_rect(timer, (30, 35, 52), 18)
    draw_text(
        f"{int(time_left)}s", FONT_SMALL, timer_color,
        timer.centerx, timer.centery, True
    )

    if difficulty == "EASY":
        badge_color = GREEN
    elif difficulty == "MEDIUM":
        badge_color = YELLOW
    else:
        badge_color = RED

    diff_text_w = FONT_SMALL.size(difficulty)[0]
    diff_w = max(100, diff_text_w + 30)

    badge = pygame.Rect(timer.x - 10 - diff_w, badge_y, diff_w, badge_h)
    rounded_rect(badge, (30, 35, 52), 18)
    draw_text(
        difficulty, FONT_SMALL, badge_color,
        badge.centerx, badge.centery, True
    )

    theme_text = theme["name"]
    theme_text_w = FONT_TINY.size(theme_text)[0]
    theme_w = max(120, theme_text_w + 30)

    theme_badge = pygame.Rect(badge.x - 10 - theme_w, badge_y, theme_w, badge_h)
    rounded_rect(theme_badge, (30, 35, 52), 18)
    draw_text(
        theme_text, FONT_TINY, PURPLE,
        theme_badge.centerx, theme_badge.centery, True
    )


# ============================================================
# STATISTICS
# ============================================================


def draw_stat_card(rect, title, value, color):
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    surf.fill((*CARD, 220))
    screen.blit(surf, (rect.x, rect.y))
    pygame.draw.rect(screen, BORDER, rect, width=1, border_radius=14)
    draw_text(title, FONT_TINY, MUTED, rect.x + 18, rect.y + 14)
    draw_text(value, FONT_MEDIUM, color, rect.x + 18, rect.y + 42)


def draw_stats():
    width, height = screen.get_size()
    margin = 32
    gap = 12
    available = width - margin * 2
    card_width = (available - gap * 5) / 6
    y = 135

    stats = [
        ("SCORE", score, INDIGO),
        ("WPM", get_wpm(), CYAN),
        ("ACCURACY", f"{get_accuracy():.1f}%", GREEN),
        ("CORRECT", correct_keystrokes, GREEN),
        ("WRONG", wrong_keystrokes, RED),
        ("STREAK", streak, YELLOW)
    ]

    for i, (title, value, color) in enumerate(stats):
        x = margin + i * (card_width + gap)
        rect = pygame.Rect(int(x), y, int(card_width), 85)
        draw_stat_card(rect, title, value, color)


# ============================================================
# TARGET CARD
# ============================================================


def draw_target_card():
    width, height = screen.get_size()
    rect = pygame.Rect(32, 242, width - 64, 145)

    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    surf.fill((*CARD, 220))
    screen.blit(surf, (rect.x, rect.y))
    pygame.draw.rect(screen, BORDER, rect, width=1, border_radius=18)

    draw_text(
        "TYPE THE FOLLOWING", FONT_TINY, MUTED,
        rect.x + 24, rect.y + 15
    )

    max_width = rect.width - 50
    # ===== TARGET WORD FONT SIZE + BOLD UPDATED =====
    target_font = get_fitted_font(
        current_word, max_width, 55, 22, None, True
    )

    if target_font.size(current_word)[0] <= max_width:
        total_width = target_font.size(current_word)[0]
        x = rect.centerx - total_width // 2
        y = rect.centery + 15
        y -= target_font.get_height() // 2

        for i, char in enumerate(current_word):
            if i in wrong_positions:
                char_color = RED
            elif (i < len(user_input) and user_input[i] == current_word[i]):
                char_color = GREEN
            else:
                char_color = WHITE

            char_surface = target_font.render(char, True, char_color)
            screen.blit(char_surface, (x, y))
            x += char_surface.get_width()
        return

    words = current_word.split(" ")
    lines = []
    current_line = ""
    character_start = 0

    for word in words:
        test_line = word if not current_line else current_line + " " + word
        if target_font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append((current_line, character_start))
                character_start += len(current_line) + 1
            current_line = word

    if current_line:
        lines.append((current_line, character_start))

    line_height = target_font.get_height() + 5
    total_height = len(lines) * line_height
    start_y = rect.centery - total_height // 2 + 10

    for line_text, start_index in lines:
        line_width = target_font.size(line_text)[0]
        x = rect.centerx - line_width // 2

        for local_index, char in enumerate(line_text):
            real_index = start_index + local_index
            if real_index in wrong_positions:
                char_color = RED
            elif (real_index < len(user_input)
                  and user_input[real_index] == current_word[real_index]):
                char_color = GREEN
            else:
                char_color = WHITE

            char_surface = target_font.render(char, True, char_color)
            screen.blit(char_surface, (x, start_y))
            x += char_surface.get_width()

        start_y += line_height


# ============================================================
# INPUT BOX
# ============================================================


def draw_input_card():
    width, height = screen.get_size()
    rect = pygame.Rect(32, 407, width - 64, 110)

    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    surf.fill((*CARD_2, 220))
    screen.blit(surf, (rect.x, rect.y))
    pygame.draw.rect(screen, INDIGO, rect, width=2, border_radius=18)

    draw_text("YOUR INPUT", FONT_TINY, MUTED, rect.x + 24, rect.y + 16)

    max_width = rect.width - 55
    # ===== INPUT FONT SIZE + BOLD UPDATED =====
    input_font = get_fitted_font(user_input, max_width, 38, 18, None, True)

    draw_text(user_input, input_font, WHITE, rect.x + 24, rect.y + 52)

    text_width = input_font.size(user_input)[0]
    cursor_x = rect.x + 24 + text_width + 3
    cursor_x = min(cursor_x, rect.right - 20)

    pygame.draw.line(
        screen, CYAN,
        (cursor_x, rect.y + 48), (cursor_x, rect.y + 88), 2
    )

    progress = 0
    if current_word:
        progress = min(1, len(user_input) / len(current_word))

    progress_rect = pygame.Rect(
        rect.x + 24, rect.bottom - 8, rect.width - 48, 3
    )
    pygame.draw.rect(screen, BORDER, progress_rect)
    pygame.draw.rect(screen, CYAN, (
        progress_rect.x, progress_rect.y,
        int(progress_rect.width * progress),
        progress_rect.height
    ))


# ============================================================
# CONTROL BAR
# ============================================================


def draw_bottom_help():
    width, height = screen.get_size()

    # ===== BOTTOM HELP FONT UPDATED =====
    bold_font = pygame.font.SysFont(theme["font_name"], 20, bold=True)

    controls = [
        ("F1", "Pause"),
        ("ENTER", "Submit"),
        ("BACKSPACE", "Delete"),
        ("F11", "Fullscreen"),
        ("F12", "Exit"),
        ("ESC", "Menu"),
    ]

    y = height - 42
    rendered = []
    total_width = 0
    gap = 30

    for key, label in controls:
        key_surface = bold_font.render(key, True, CYAN)
        label_surface = bold_font.render(label, True, WHITE)
        item_width = (
            key_surface.get_width() + 7 + label_surface.get_width()
        )
        rendered.append((key_surface, label_surface, item_width))
        total_width += item_width

    total_width += gap * (len(rendered) - 1)
    x = (width - total_width) // 2

    for key_surface, label_surface, item_width in rendered:
        screen.blit(key_surface, (x, y))
        screen.blit(
            label_surface,
            (x + key_surface.get_width() + 7, y)
        )
        x += item_width + gap


# ============================================================
# MESSAGE
# ============================================================


def draw_message():
    if message and time.time() < message_until:
        width, height = screen.get_size()
        rect = pygame.Rect(width // 2 - 170, height - 105, 340, 46)
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((*CARD_2, 240))
        screen.blit(surf, (rect.x, rect.y))
        pygame.draw.rect(screen, message_color, rect, width=1, border_radius=20)
        draw_text(
            message, FONT_SMALL, message_color,
            rect.centerx, rect.centery, True
        )


# ============================================================
# MENU BUTTON — NO BORDER, AUTO-CONTRAST TEXT
# ============================================================


def menu_button(rect, text, active=False, color=ACCENT_ORANGE,
                dark_color=None):
    """Solid flat button — NO border, auto-contrast text."""
    if dark_color is None:
        dark_color = darken(color, 0.55)

    bg_color = color if active else dark_color

    # Auto-pick text color based on background luminance
    r, g, b = bg_color
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    text_color = (12, 14, 22) if luminance > 0.62 else (248, 250, 255)

    # Solid rounded fill (no border)
    pygame.draw.rect(screen, bg_color, rect, border_radius=10)

    # Subtle top highlight for active buttons
    if active:
        highlight = pygame.Surface((rect.width, 2), pygame.SRCALPHA)
        highlight.fill((255, 255, 255, 40))
        screen.blit(highlight, (rect.x + 6, rect.y + 2))

    # ===== MENU BUTTON FONT SIZE + BOLD UPDATED =====
    font = pygame.font.SysFont(theme["font_name"], 22, bold=True)
    draw_text(text, font, text_color, rect.centerx, rect.centery, True)


# ============================================================
# MENU — THEME-AWARE + NO BORDER + DYNAMIC SCALING
# ============================================================


def draw_menu():
    """Menu with dynamic scaling + theme-aware colors + no borders."""
    width, height = screen.get_size()

    diff_color, timer_color, theme_color = get_section_colors()
    diff_dark = darken(diff_color)
    timer_dark = darken(timer_color)
    theme_dark = darken(theme_color)

    scale = min(width / 1280, height / 760)
    scale = max(0.7, min(1.3, scale))

    title_y = int(height * 0.09)
    subtitle_y = int(height * 0.16)

    draw_text("TypeFlow", FONT_HERO, WHITE, width // 2, title_y, True)
    draw_text(
        "A clean and simple speed typing experience",
        FONT_NORMAL, MUTED, width // 2, subtitle_y, True
    )

    panel_w = min(int(860 * scale), width - 80)
    panel_h = min(int(500 * scale), height - 180)
    panel_x = (width - panel_w) // 2
    panel_y = int(height * 0.20)

    panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    pygame.draw.rect(screen, BORDER, panel, width=1, border_radius=22)

    # ===== MENU LABEL FONT UPDATED =====
    label_font = pygame.font.SysFont(
        theme["font_name"], max(16, int(22 * scale)), bold=True
    )

    row1_y = panel.y + int(58 * scale)
    row2_y = panel.y + int(168 * scale)
    row3_y = panel.y + int(235 * scale)
    row4_y = panel.y + int(340 * scale)

    btn_h = max(40, int(50 * scale))
    inner_w = panel_w - int(60 * scale)
    gap = int(12 * scale)

    # ── DIFFICULTY ─────────────────────────────
    draw_text(
        "DIFFICULTY", label_font, diff_color,
        panel.x + int(30 * scale), panel.y + int(25 * scale)
    )

    button_width = (inner_w - gap * 2) // 3

    easy = pygame.Rect(panel.x + int(30 * scale), row1_y, button_width, btn_h)
    medium = pygame.Rect(easy.right + gap, row1_y, button_width, btn_h)
    hard = pygame.Rect(medium.right + gap, row1_y, button_width, btn_h)

    menu_button(easy, "EASY", difficulty == "EASY",
                diff_color, diff_dark)
    menu_button(medium, "MEDIUM", difficulty == "MEDIUM",
                diff_color, diff_dark)
    menu_button(hard, "HARD", difficulty == "HARD",
                diff_color, diff_dark)

    # ── TIME LIMIT ─────────────────────────────
    draw_text(
        "TIME LIMIT", label_font, timer_color,
        panel.x + int(30 * scale), panel.y + int(135 * scale)
    )

    timer_values = [
        (30, "30 SEC"), (60, "60 SEC"),
        (120, "120 SEC"), (180, "180 SEC")
    ]
    timer_btn_w = (inner_w - gap * 3) // 4

    for i, (value, label) in enumerate(timer_values):
        rect = pygame.Rect(
            panel.x + int(30 * scale) + i * (timer_btn_w + gap),
            row2_y, timer_btn_w, btn_h
        )
        menu_button(rect, label, selected_timer == value,
                    timer_color, timer_dark)

    # ── CUSTOM TIMER ───────────────────────────
    custom_rect = pygame.Rect(
        panel.x + int(30 * scale), row3_y, inner_w, btn_h - 2
    )
    menu_button(
        custom_rect,
        f"CUSTOM TIMER   {selected_timer} SEC   |   Press T",
        False, timer_color, timer_dark
    )

    # ── THEME & SOUND ──────────────────────────
    draw_text(
        "THEME & SOUND", label_font, theme_color,
        panel.x + int(30 * scale), panel.y + int(310 * scale)
    )

    theme_btn_w = int(inner_w * 0.64)
    sound_btn_w = inner_w - theme_btn_w - gap

    theme_rect = pygame.Rect(
        panel.x + int(30 * scale), row4_y, theme_btn_w, btn_h - 3
    )
    menu_button(
        theme_rect,
        f"THEME:  {theme['name']}   |   P",
        True, theme_color, theme_dark
    )

    if AUDIO_OK:
        snd_label = f"SOUND: {'ON' if sound_enabled else 'OFF'}  |  N"
    else:
        snd_label = "SOUND: N/A"

    sound_rect = pygame.Rect(
        theme_rect.right + gap, row4_y, sound_btn_w, btn_h - 3
    )
    menu_button(sound_rect, snd_label, True,
                theme_color, theme_dark)

    # ── START BUTTON ───────────────────────────
    start_w = int(360 * scale)
    start_h = int(58 * scale)
    start_rect = pygame.Rect(
        panel.centerx - start_w // 2,
        panel.y + int(410 * scale),
        start_w, start_h
    )
    rounded_rect(start_rect, timer_color, 12)
    # ===== START BUTTON FONT UPDATED =====
    draw_text(
        "PRESS SPACE TO START",
        pygame.font.SysFont(
            theme["font_name"], max(16, int(28 * scale)), bold=True
        ),
        WHITE,
        start_rect.centerx, start_rect.centery, True
    )

    # ── BOTTOM HINT (Descriptive Key Guide) ────
    # ===== HINT FONT UPDATED =====
    hint_font = pygame.font.SysFont(
        theme["font_name"], max(13, int(17 * scale)), bold=True
    )

    hint_items = [
        ("E / M / H", "Difficulty"),
        ("1 2 3 4", "Time"),
        ("T", "Custom Timer"),
        ("P", "Theme"),
        ("N", "Sound"),
        ("F11", "Fullscreen"),
        ("F12", "Exit"),
    ]

    sep = "  •  "
    sep_surface = hint_font.render(sep, True, MUTED)
    sep_w = sep_surface.get_width()

    rendered_items = []
    total_w = 0
    for key_label, desc in hint_items:
        key_surf = hint_font.render(key_label, True, CYAN)
        eq_surf = hint_font.render(" = ", True, MUTED)
        desc_surf = hint_font.render(desc, True, WHITE)
        item_w = key_surf.get_width() + eq_surf.get_width() + desc_surf.get_width()
        rendered_items.append((key_surf, eq_surf, desc_surf, item_w))
        total_w += item_w

    total_w += sep_w * (len(rendered_items) - 1)

    if total_w > width - 40:
        hint_font_small = pygame.font.SysFont(
            theme["font_name"], max(12, int(15 * scale)), bold=True
        )
        line1 = "E / M / H = Difficulty     1 2 3 4 = Time     T = Custom Timer"
        line2 = "P = Theme     N = Sound     F11 = Fullscreen     F12 = Exit"
        s1 = hint_font_small.render(line1, True, WHITE)
        s2 = hint_font_small.render(line2, True, WHITE)
        screen.blit(s1, s1.get_rect(center=(width // 2, height - 42)))
        screen.blit(s2, s2.get_rect(center=(width // 2, height - 22)))
    else:
        start_x = (width - total_w) // 2
        hint_y = height - 28

        x = start_x
        for i, (key_surf, eq_surf, desc_surf, item_w) in enumerate(rendered_items):
            screen.blit(key_surf, (x, hint_y))
            x += key_surf.get_width()
            screen.blit(eq_surf, (x, hint_y))
            x += eq_surf.get_width()
            screen.blit(desc_surf, (x, hint_y))
            x += desc_surf.get_width()

            if i < len(rendered_items) - 1:
                screen.blit(sep_surface, (x, hint_y))
                x += sep_w


# ============================================================
# PAUSE SCREEN
# ============================================================


def draw_pause():
    width, height = screen.get_size()

    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((5, 7, 12, 210))
    screen.blit(overlay, (0, 0))

    draw_text(
        "PAUSED", FONT_HERO, YELLOW,
        width // 2, height // 2 - 70, True
    )
    draw_text(
        "Press F1 to continue", FONT_MEDIUM, WHITE,
        width // 2, height // 2, True
    )
    draw_text(
        "R  Restart  •  M  Mute  •  ESC  Menu  •  F12  Exit",
        FONT_SMALL, MUTED,
        width // 2, height // 2 + 55, True
    )


# ============================================================
# RESULT CARD
# ============================================================


def draw_result_card(rect, title, value, color):
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    surf.fill((*CARD, 220))
    screen.blit(surf, (rect.x, rect.y))
    pygame.draw.rect(screen, BORDER, rect, width=1, border_radius=15)
    draw_text(title, FONT_TINY, MUTED, rect.centerx, rect.y + 18, True)
    draw_text(value, FONT_BIG, color, rect.centerx, rect.y + 60, True)


# ============================================================
# GAME OVER
# ============================================================


def draw_game_over():
    width, height = screen.get_size()

    _, timer_color, _ = get_section_colors()

    draw_text("TIME'S UP", FONT_HERO, WHITE, width // 2, 70, True)
    draw_text(
        "Your typing session is complete", FONT_NORMAL, MUTED,
        width // 2, 120, True
    )

    card_width = 200
    card_height = 105
    gap = 15
    total_width = card_width * 4 + gap * 3
    start_x = (width - total_width) // 2
    y = 165

    results = [
        ("SCORE", score, INDIGO),
        ("WPM", get_wpm(), CYAN),
        ("ACCURACY", f"{get_accuracy():.1f}%", GREEN),
        ("BEST STREAK", best_streak, YELLOW)
    ]

    for i, (title, value, color) in enumerate(results):
        rect = pygame.Rect(
            start_x + i * (card_width + gap),
            y, card_width, card_height
        )
        draw_result_card(rect, title, value, color)

    detail = pygame.Rect(width // 2 - 350, 300, 700, 190)
    surf = pygame.Surface((detail.width, detail.height), pygame.SRCALPHA)
    surf.fill((*CARD, 220))
    screen.blit(surf, (detail.x, detail.y))
    pygame.draw.rect(screen, BORDER, detail, width=1, border_radius=18)

    draw_text("SESSION DETAILS", FONT_SMALL, MUTED, detail.x + 25, detail.y + 20)
    draw_text(f"Correct Keystrokes:  {correct_keystrokes}", FONT_NORMAL, GREEN, detail.x + 30, detail.y + 65)
    draw_text(f"Wrong Keystrokes:    {wrong_keystrokes}", FONT_NORMAL, RED, detail.x + 30, detail.y + 105)
    draw_text(f"Total Keystrokes:    {total_keystrokes}", FONT_NORMAL, WHITE, detail.x + 30, detail.y + 145)
    draw_text(f"Words Completed: {completed_words}", FONT_NORMAL, CYAN, detail.x + 380, detail.y + 65)
    draw_text(f"Difficulty: {difficulty}", FONT_NORMAL, WHITE, detail.x + 380, detail.y + 105)
    draw_text(f"Time: {selected_timer}s", FONT_NORMAL, WHITE, detail.x + 380, detail.y + 145)

    play = pygame.Rect(width // 2 - 210, 530, 200, 55)
    menu = pygame.Rect(width // 2 + 10, 530, 200, 55)

    rounded_rect(play, timer_color, 12)
    surf = pygame.Surface((menu.width, menu.height), pygame.SRCALPHA)
    surf.fill((*CARD, 220))
    screen.blit(surf, (menu.x, menu.y))
    pygame.draw.rect(screen, BORDER, menu, width=1, border_radius=12)

    draw_text("PLAY AGAIN", FONT_MEDIUM, WHITE, play.centerx, play.centery, True)
    draw_text("MENU", FONT_MEDIUM, TEXT, menu.centerx, menu.centery, True)

    bold_font = pygame.font.SysFont(theme["font_name"], 20, bold=True)
    hint_text = "SPACE = Play Again  •  M = Mute  •  ESC = Menu  •  F12 = Exit"
    hint_surface = bold_font.render(hint_text, True, WHITE)
    hint_rect = hint_surface.get_rect(center=(width // 2, 625))
    screen.blit(hint_surface, hint_rect)


# ============================================================
# CUSTOM TIMER
# ============================================================


def draw_custom_timer():
    width, height = screen.get_size()

    _, timer_color, _ = get_section_colors()

    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((5, 7, 12, 220))
    screen.blit(overlay, (0, 0))

    panel = pygame.Rect(width // 2 - 300, height // 2 - 180, 600, 360)
    rounded_rect(panel, CARD, 20, BORDER)

    draw_text("CUSTOM TIMER", FONT_BIG, WHITE, panel.centerx, panel.y + 55, True)
    draw_text("Enter time in seconds", FONT_SMALL, MUTED, panel.centerx, panel.y + 92, True)

    input_box = pygame.Rect(panel.x + 80, panel.y + 125, 440, 65)
    rounded_rect(input_box, CARD_2, 12)

    draw_text(custom_timer_input, FONT_INPUT, WHITE, input_box.centerx, input_box.centery, True)
    draw_text("5 - 999 seconds", FONT_TINY, CYAN, panel.centerx, panel.y + 215, True)
    draw_text("ENTER  Save", FONT_SMALL, GREEN, panel.x + 160, panel.y + 270, True)
    draw_text("ESC  Cancel", FONT_SMALL, RED, panel.x + 440, panel.y + 270, True)


# ============================================================
# ESC DOUBLE-TAP EXIT
# ============================================================


def handle_esc_exit():
    global _esc_pressed_time
    now = time.time()
    if now - _esc_pressed_time < 0.6:
        return True
    _esc_pressed_time = now
    return False


# ============================================================
# MENU KEY HANDLER
# ============================================================


def handle_menu_key(event):
    global difficulty, selected_timer, background_mode
    global custom_timer_mode, custom_timer_input, sound_enabled

    key = event.key

    if key == pygame.K_e:
        difficulty = "EASY"
        play_sound("select")
    elif key == pygame.K_m:
        difficulty = "MEDIUM"
        play_sound("select")
    elif key == pygame.K_h:
        difficulty = "HARD"
        play_sound("select")
    elif key == pygame.K_1:
        selected_timer = 30
        play_sound("select")
    elif key == pygame.K_2:
        selected_timer = 60
        play_sound("select")
    elif key == pygame.K_3:
        selected_timer = 120
        play_sound("select")
    elif key == pygame.K_4:
        selected_timer = 180
        play_sound("select")
    elif key == pygame.K_t:
        custom_timer_input = ""
        custom_timer_mode = True
        play_sound("select")
    elif key == pygame.K_p:
        switch_theme()
    elif key == pygame.K_n:
        sound_enabled = not sound_enabled
        if sound_enabled:
            play_sound("select")
    elif key == pygame.K_SPACE:
        start_game()


# ============================================================
# CUSTOM TIMER KEY HANDLER
# ============================================================


def handle_custom_timer_key(event):
    global custom_timer_input, selected_timer, custom_timer_mode

    if event.key == pygame.K_ESCAPE:
        custom_timer_mode = False
        custom_timer_input = ""
        return

    if event.key == pygame.K_BACKSPACE:
        custom_timer_input = custom_timer_input[:-1]
        return

    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        if custom_timer_input.isdigit():
            value = int(custom_timer_input)
            if 5 <= value <= 999:
                selected_timer = value
                custom_timer_mode = False
                custom_timer_input = ""
                play_sound("select")
            else:
                show_message("Enter 5 - 999 seconds", RED)
        else:
            show_message("Enter a number", RED)
        return

    if event.unicode and event.unicode.isdigit():
        if len(custom_timer_input) < 3:
            custom_timer_input += event.unicode


# ============================================================
# GAME KEY HANDLER
# ============================================================


def handle_game_key(event):
    global user_input, correct_keystrokes, wrong_keystrokes
    global total_keystrokes, streak, score, game_state, sound_enabled

    if event.key == pygame.K_F1:
        toggle_pause()
        return

    if event.key == pygame.K_ESCAPE:
        game_state = "MENU"
        return

    if game_state == "PAUSED":
        if event.key == pygame.K_m:
            sound_enabled = not sound_enabled
            if sound_enabled:
                play_sound("select")
            return
        if event.key == pygame.K_r:
            restart_game()
            return
        return

    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        submit_word()
        return

    if event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
        if user_input:
            removed_index = len(user_input) - 1
            user_input = user_input[:-1]
            wrong_positions.discard(removed_index)
            play_mech_key()
        return

    ignored_keys = {
        pygame.K_LSHIFT, pygame.K_RSHIFT,
        pygame.K_LCTRL, pygame.K_RCTRL,
        pygame.K_LALT, pygame.K_RALT,
        pygame.K_CAPSLOCK, pygame.K_TAB,
        pygame.K_F2, pygame.K_F3, pygame.K_F4, pygame.K_F5,
        pygame.K_F6, pygame.K_F7, pygame.K_F8, pygame.K_F9,
        pygame.K_F10, pygame.K_F11, pygame.K_F12,
        pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN,
        pygame.K_HOME, pygame.K_END, pygame.K_INSERT,
        pygame.K_PAGEUP, pygame.K_PAGEDOWN
    }

    if event.key in ignored_keys:
        return

    typed_char = event.unicode
    if not typed_char or not typed_char.isprintable():
        return

    total_keystrokes += 1
    index = len(user_input)

    if (index < len(current_word)
            and typed_char == current_word[index]):
        correct_keystrokes += 1
        wrong_positions.discard(index)
        user_input += typed_char
        play_mech_key()
        return

    wrong_keystrokes += 1
    streak = 0

    if index < len(current_word):
        wrong_positions.add(index)

    if difficulty == "HARD":
        score = max(0, score - 10)
    elif difficulty == "MEDIUM":
        score = max(0, score - 5)
    else:
        score = max(0, score - 2)

    trigger_shake(6)
    trigger_flash(RED, 40)
    play_sound("mech_error")

    if index < len(current_word):
        expected = current_word[index]
        show_message(f"Expected '{expected}'", RED, 0.7)
    else:
        show_message("Extra character!", RED, 0.7)


# ============================================================
# FULLSCREEN
# ============================================================


def toggle_fullscreen():
    global fullscreen, screen
    fullscreen = not fullscreen

    if fullscreen:
        info = pygame.display.Info()
        screen_w = info.current_w
        screen_h = info.current_h

        screen = pygame.display.set_mode(
            (screen_w, screen_h),
            pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        )
    else:
        screen = pygame.display.set_mode(
            (DEFAULT_WIDTH, DEFAULT_HEIGHT),
            pygame.RESIZABLE
        )

    w, h = screen.get_size()
    print(f"[TypeFlow] Fullscreen={fullscreen} | Size={w}x{h}")

    build_scanlines(w, h)
    build_vignette(w, h)
    scale_background(w, h)

    pygame.event.clear()
    pygame.event.pump()
    pygame.display.flip()
    pygame.time.wait(50)


# ============================================================
# RETRO EFFECTS
# ============================================================


def apply_shake():
    global shake_intensity
    if shake_intensity < 0.5:
        shake_intensity = 0
        return (0, 0)
    ox = random.randint(-int(shake_intensity), int(shake_intensity))
    oy = random.randint(-int(shake_intensity), int(shake_intensity))
    shake_intensity *= shake_decay
    return (ox, oy)


def draw_scanlines():
    if theme["scanlines"] and scanline_surface is not None:
        screen.blit(scanline_surface, (0, 0))


def draw_vignette():
    if theme["vignette"] and vignette_surface is not None:
        screen.blit(vignette_surface, (0, 0))


def draw_flash():
    global flash_alpha, correct_flash_alpha

    if flash_alpha > 0:
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*flash_color, int(flash_alpha)))
        screen.blit(overlay, (0, 0))
        flash_alpha = max(0, flash_alpha - flash_decay)

    if correct_flash_alpha > 0:
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, int(correct_flash_alpha)))
        screen.blit(overlay, (0, 0))
        correct_flash_alpha = max(0, correct_flash_alpha - 5)


# ============================================================
# BUILD INITIAL EFFECTS
# ============================================================

_w, _h = screen.get_size()
build_scanlines(_w, _h)
build_vignette(_w, _h)

# ============================================================
# LOAD BACKGROUND
# ============================================================

load_background()
scale_background(_w, _h)

# ============================================================
# START SPLASH SCREEN
# ============================================================

start_splash()

# ============================================================
# MAIN LOOP
# ============================================================

running = True
splash_phase = True

while running:

    clock.tick(60)

    if splash_phase:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN:
                splash_phase = False
                break
            if event.type == pygame.MOUSEBUTTONDOWN:
                splash_phase = False
                break

        if not running:
            break

        if _splash_done:
            splash_phase = False
            continue

        if _splash_images:
            total_duration = len(_splash_images) * (
                SPLASH_DURATION_PER_IMAGE + SPLASH_FADE_TIME
            )
            if time.time() - _splash_start_time > total_duration:
                splash_phase = False
                continue

        draw_splash()
        pygame.display.flip()
        continue

    if background_mode == "RGB":
        update_rgb()

    ox, oy = apply_shake()

    if not draw_background():
        screen.fill(get_background())

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False
            continue

        if event.type == pygame.VIDEORESIZE:
            if not fullscreen:
                new_width = max(MIN_WIDTH, event.w)
                new_height = max(MIN_HEIGHT, event.h)
                screen = pygame.display.set_mode(
                    (new_width, new_height), pygame.RESIZABLE
                )
                build_scanlines(new_width, new_height)
                build_vignette(new_width, new_height)
                scale_background(new_width, new_height)
            continue

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_F12:
                running = False
                break

            if event.key == pygame.K_ESCAPE:
                if handle_esc_exit():
                    running = False
                    break

            if event.key == pygame.K_F11:
                toggle_fullscreen()
                continue

            if custom_timer_mode:
                handle_custom_timer_key(event)
                continue

            if game_state == "MENU":
                handle_menu_key(event)
                continue

            if game_state in ("PLAYING", "PAUSED"):
                handle_game_key(event)
                continue

            if game_state == "GAME_OVER":
                if event.key == pygame.K_m:
                    sound_enabled = not sound_enabled
                    if sound_enabled:
                        play_sound("select")
                elif event.key == pygame.K_SPACE:
                    start_game()
                elif event.key == pygame.K_ESCAPE:
                    game_state = "MENU"

    if not running:
        break

    if game_state == "PLAYING":
        if start_time is not None:
            elapsed_time = time.time() - start_time
            time_left = max(0, selected_timer - elapsed_time)

            sec = int(time_left)
            if 0 < sec <= 5 and sec != _last_countdown_second:
                _last_countdown_second = sec
                play_sound("beep")

            if time_left <= 0:
                finish_game()

    if game_state == "MENU":
        draw_menu()
    elif game_state == "PLAYING":
        draw_top_bar()
        draw_stats()
        draw_target_card()
        draw_input_card()
        draw_bottom_help()
        draw_message()
    elif game_state == "PAUSED":
        draw_top_bar()
        draw_stats()
        draw_target_card()
        draw_input_card()
        draw_pause()
    elif game_state == "GAME_OVER":
        draw_game_over()

    if custom_timer_mode:
        draw_custom_timer()

    draw_scanlines()
    draw_vignette()
    draw_flash()

    if ox != 0 or oy != 0:
        snapshot = screen.copy()
        screen.fill(get_background())
        screen.blit(snapshot, (ox, oy))

    pygame.display.flip()


pygame.quit()
sys.exit()