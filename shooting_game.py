"""
シューティングゲーム
プログラミング演習 課題6 - 詳細設計モデルに基づく実装

言語: Python 3 / pygame

クラス構成は詳細設計モデルのクラス図に対応させている。
  <<boundary>> TitleScreen / NameInputScreen / GameScreen / GameOverScreen / HighScoreScreen
  <<control>>  NameInputControl / GameStartControl / MovementControl / BulletControl /
               HighScoreControl / RetryControl / TitleReturnControl
  <<entity>>   Player / PlayerCharacter / Bullet / Enemy / Score

実行方法:
  pip install pygame
  python shooting_game.py
"""

from __future__ import annotations
import sys
import random
import json
import os
import pygame

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
FPS = 60

PLAYER_SIZE = (40, 20)
PLAYER_SPEED = 6
PLAYER_Y = SCREEN_HEIGHT - 60

BULLET_SIZE = (4, 14)
BULLET_SPEED = 10

ENEMY_SIZE = (32, 22)
ENEMY_SPEED = 2
ENEMY_SPAWN_INTERVAL = 45  # フレーム数
ENEMY_SCORE = 100

NAME_MAX_LEN = 10
HIGH_SCORE_FILE = os.path.join(os.path.dirname(__file__), "high_scores.json")
MAX_HIGH_SCORES = 5

WHITE = (240, 240, 240)
BLACK = (10, 10, 15)
RED = (220, 70, 70)
BLUE = (80, 140, 230)
GREEN = (90, 200, 120)
GRAY = (150, 150, 150)
YELLOW = (230, 200, 80)


# ---------------------------------------------------------------------------
# <<entity>> クラス
# ---------------------------------------------------------------------------
class Player:
    """<<entity>> プレイヤー: プレイヤー名を保持する"""

    def __init__(self) -> None:
        self._name: str = ""

    def save_name(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class PlayerCharacter:
    """<<entity>> プレイヤーキャラクタ: 自機の位置を管理する"""

    def __init__(self, x: int, y: int) -> None:
        self._rect = pygame.Rect(x, y, *PLAYER_SIZE)
        self._speed = PLAYER_SPEED

    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    def is_at_right_edge(self) -> bool:
        return self._rect.right >= SCREEN_WIDTH

    def is_at_left_edge(self) -> bool:
        return self._rect.left <= 0

    def move_right(self) -> None:
        self._rect.x = min(self._rect.x + self._speed, SCREEN_WIDTH - self._rect.width)

    def move_left(self) -> None:
        self._rect.x = max(self._rect.x - self._speed, 0)

    def update_position(self, direction: str) -> None:
        if direction == "right":
            self.move_right()
        elif direction == "left":
            self.move_left()

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.polygon(
            surface, BLUE,
            [(self._rect.centerx, self._rect.top),
             (self._rect.left, self._rect.bottom),
             (self._rect.right, self._rect.bottom)],
        )


class Bullet:
    """<<entity>> 弾"""

    def __init__(self, x: int, y: int) -> None:
        self._rect = pygame.Rect(x, y, *BULLET_SIZE)
        self._speed = BULLET_SPEED
        self._alive = True

    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    @property
    def alive(self) -> bool:
        return self._alive

    def move_forward(self) -> None:
        self._rect.y -= self._speed

    def is_off_screen(self) -> bool:
        return self._rect.bottom < 0

    def destroy(self) -> None:
        self._alive = False

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, YELLOW, self._rect)


class Enemy:
    """<<entity>> 敵"""

    def __init__(self, x: int, y: int) -> None:
        self._rect = pygame.Rect(x, y, *ENEMY_SIZE)
        self._speed = ENEMY_SPEED
        self._alive = True

    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    @property
    def alive(self) -> bool:
        return self._alive

    def move_down(self) -> None:
        self._rect.y += self._speed

    def is_off_screen(self) -> bool:
        return self._rect.top > SCREEN_HEIGHT

    def destroy(self) -> None:
        self._alive = False

    def is_hit(self, bullet: Bullet) -> bool:
        return self._rect.colliderect(bullet.rect)

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, RED, self._rect)


class Score:
    """<<entity>> スコア"""

    def __init__(self) -> None:
        self._point = 0

    def add_point(self, point: int) -> None:
        self._point += point

    def get_point(self) -> int:
        return self._point


# ---------------------------------------------------------------------------
# ハイスコア永続化（ファイル入出力。設計モデルの Score を拡張して利用）
# ---------------------------------------------------------------------------
def load_high_scores() -> list[dict]:
    if not os.path.exists(HIGH_SCORE_FILE):
        return []
    try:
        with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_high_score(name: str, point: int) -> list[dict]:
    scores = load_high_scores()
    scores.append({"name": name, "point": point})
    scores.sort(key=lambda s: s["point"], reverse=True)
    scores = scores[:MAX_HIGH_SCORES]
    try:
        with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return scores


# ---------------------------------------------------------------------------
# <<control>> クラス
# ---------------------------------------------------------------------------
class NameInputControl:
    """<<control>> 名前入力管理"""

    def __init__(self, player: Player) -> None:
        self._player = player

    def confirm_input(self, player_name: str) -> bool:
        return 0 < len(player_name) <= NAME_MAX_LEN

    def save_player_name(self, player_name: str) -> None:
        self._player.save_name(player_name)


class MovementControl:
    """<<control>> 移動管理"""

    def __init__(self, character: PlayerCharacter) -> None:
        self._character = character

    def move_right(self) -> None:
        if not self._character.is_at_right_edge():
            self._character.move_right()

    def move_left(self) -> None:
        if not self._character.is_at_left_edge():
            self._character.move_left()


class BulletControl:
    """<<control>> 弾発射管理"""

    def __init__(self, score: Score) -> None:
        self._score = score
        self._bullets: list[Bullet] = []

    @property
    def bullets(self) -> list[Bullet]:
        return self._bullets

    def fire_bullet(self, x: int, y: int) -> None:
        self._bullets.append(Bullet(x, y))

    def update(self, enemies: list[Enemy]) -> None:
        for bullet in self._bullets:
            bullet.move_forward()
            if bullet.is_off_screen():
                bullet.destroy()
                continue
            for enemy in enemies:
                if enemy.alive and enemy.is_hit(bullet):
                    enemy.destroy()
                    bullet.destroy()
                    self._score.add_point(ENEMY_SCORE)
                    break
        self._bullets = [b for b in self._bullets if b.alive]


class HighScoreControl:
    """<<control>> ハイスコア管理"""

    def __init__(self, score: Score) -> None:
        self._score = score

    def execute_show_high_score(self) -> list[dict]:
        return load_high_scores()


# ---------------------------------------------------------------------------
# <<boundary>> クラス
# ---------------------------------------------------------------------------
class TitleScreen:
    """<<boundary>> タイトル画面"""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, big_font: pygame.font.Font) -> None:
        self._screen = screen
        self._font = font
        self._big_font = big_font

    def show(self) -> None:
        self._screen.fill(BLACK)
        title = self._big_font.render("SHOOTING GAME", True, WHITE)
        self._screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 150)))
        opt1 = self._font.render("[SPACE] ゲームスタートを選択する", True, WHITE)
        opt2 = self._font.render("[H] ハイスコアを選択する", True, WHITE)
        self._screen.blit(opt1, opt1.get_rect(center=(SCREEN_WIDTH // 2, 260)))
        self._screen.blit(opt2, opt2.get_rect(center=(SCREEN_WIDTH // 2, 300)))
        pygame.display.flip()


class NameInputScreen:
    """<<boundary>> プレイヤー名入力画面"""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        self._screen = screen
        self._font = font
        self._error_message = ""

    def show_error_message(self, message: str) -> None:
        self._error_message = message

    def show(self, current_input: str) -> None:
        self._screen.fill(BLACK)
        label = self._font.render("プレイヤー名を入力してください (Enterで確定)", True, WHITE)
        self._screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 160)))
        box = pygame.Rect(SCREEN_WIDTH // 2 - 150, 200, 300, 40)
        pygame.draw.rect(self._screen, WHITE, box, 2)
        text = self._font.render(current_input, True, WHITE)
        self._screen.blit(text, (box.x + 8, box.y + 8))
        if self._error_message:
            err = self._font.render(self._error_message, True, RED)
            self._screen.blit(err, err.get_rect(center=(SCREEN_WIDTH // 2, 270)))
        pygame.display.flip()


class GameScreen:
    """<<boundary>> ゲーム画面"""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        self._screen = screen
        self._font = font

    def show(self, character: PlayerCharacter, bullets: list[Bullet],
              enemies: list[Enemy], score: Score) -> None:
        self._screen.fill(BLACK)
        character.draw(self._screen)
        for bullet in bullets:
            bullet.draw(self._screen)
        for enemy in enemies:
            if enemy.alive:
                enemy.draw(self._screen)
        score_text = self._font.render(f"SCORE: {score.get_point()}", True, WHITE)
        self._screen.blit(score_text, (10, 10))
        pygame.display.flip()


class GameOverScreen:
    """<<boundary>> ゲームオーバー画面"""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, big_font: pygame.font.Font) -> None:
        self._screen = screen
        self._font = font
        self._big_font = big_font

    def show(self, score: Score) -> None:
        self._screen.fill(BLACK)
        title = self._big_font.render("GAME OVER", True, RED)
        self._screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 160)))
        score_text = self._font.render(f"SCORE: {score.get_point()}", True, WHITE)
        self._screen.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH // 2, 230)))
        retry_text = self._font.render("[SPACE] リトライを選択する", True, WHITE)
        self._screen.blit(retry_text, retry_text.get_rect(center=(SCREEN_WIDTH // 2, 300)))
        pygame.display.flip()


class HighScoreScreen:
    """<<boundary>> ハイスコア画面"""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, big_font: pygame.font.Font) -> None:
        self._screen = screen
        self._font = font
        self._big_font = big_font

    def show(self, scores: list[dict]) -> None:
        self._screen.fill(BLACK)
        title = self._big_font.render("HIGH SCORE", True, WHITE)
        self._screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 80)))
        if not scores:
            empty = self._font.render("記録がありません", True, GRAY)
            self._screen.blit(empty, empty.get_rect(center=(SCREEN_WIDTH // 2, 200)))
        else:
            for i, s in enumerate(scores):
                line = self._font.render(f"{i + 1}. {s['name']}  {s['point']}", True, WHITE)
                self._screen.blit(line, line.get_rect(center=(SCREEN_WIDTH // 2, 150 + i * 40)))
        back = self._font.render("[ESC] タイトルに戻るを選択する", True, WHITE)
        self._screen.blit(back, back.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)))
        pygame.display.flip()


# ---------------------------------------------------------------------------
# ゲーム全体の制御（状態遷移）
# ---------------------------------------------------------------------------
class GameApp:
    STATE_TITLE = "TITLE"
    STATE_NAME_INPUT = "NAME_INPUT"
    STATE_PLAYING = "PLAYING"
    STATE_GAME_OVER = "GAME_OVER"
    STATE_HIGH_SCORE = "HIGH_SCORE"

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("シューティングゲーム")
        self._screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._clock = pygame.time.Clock()
        self._font = pygame.font.SysFont(None, 28)
        self._big_font = pygame.font.SysFont(None, 56)

        # boundary
        self._title_screen = TitleScreen(self._screen, self._font, self._big_font)
        self._name_input_screen = NameInputScreen(self._screen, self._font)
        self._game_screen = GameScreen(self._screen, self._font)
        self._game_over_screen = GameOverScreen(self._screen, self._font, self._big_font)
        self._high_score_screen = HighScoreScreen(self._screen, self._font, self._big_font)

        # entity
        self._player = Player()

        self._state = self._make_transition = None
        self._name_buffer = ""
        self._high_scores: list[dict] = []

        self._reset_game_entities()
        self._state = self.STATE_TITLE

    def _reset_game_entities(self) -> None:
        self._character = PlayerCharacter(
            SCREEN_WIDTH // 2 - PLAYER_SIZE[0] // 2, PLAYER_Y
        )
        self._score = Score()
        self._movement_control = MovementControl(self._character)
        self._bullet_control = BulletControl(self._score)
        self._enemies: list[Enemy] = []
        self._enemy_spawn_timer = 0

    # -- 各ユースケースに対応する処理 --------------------------------------
    def _handle_title_events(self, events: list[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    # ②ゲームスタートする
                    self._name_buffer = ""
                    self._state = self.STATE_NAME_INPUT
                elif e.key == pygame.K_h:
                    # ⑦ハイスコアを表示する
                    high_score_control = HighScoreControl(self._score)
                    self._high_scores = high_score_control.execute_show_high_score()
                    self._state = self.STATE_HIGH_SCORE

    def _handle_name_input_events(self, events: list[pygame.event.Event]) -> None:
        # ①プレイヤー名を入力する
        control = NameInputControl(self._player)
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    if control.confirm_input(self._name_buffer):
                        control.save_player_name(self._name_buffer)
                        self._reset_game_entities()
                        self._state = self.STATE_PLAYING
                    else:
                        self._name_input_screen.show_error_message(
                            f"1〜{NAME_MAX_LEN}文字以内で入力してください"
                        )
                elif e.key == pygame.K_BACKSPACE:
                    self._name_buffer = self._name_buffer[:-1]
                elif e.unicode and len(self._name_buffer) < NAME_MAX_LEN:
                    self._name_buffer += e.unicode

    def _handle_playing(self, events: list[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                # ⑤弾を発射する
                self._bullet_control.fire_bullet(
                    self._character.rect.centerx - BULLET_SIZE[0] // 2,
                    self._character.rect.top,
                )

        keys = pygame.key.get_pressed()
        if keys[pygame.K_RIGHT]:
            # ③右に移動する
            self._movement_control.move_right()
        if keys[pygame.K_LEFT]:
            # ④左に移動する
            self._movement_control.move_left()

        # 敵の生成
        self._enemy_spawn_timer += 1
        if self._enemy_spawn_timer >= ENEMY_SPAWN_INTERVAL:
            self._enemy_spawn_timer = 0
            x = random.randint(0, SCREEN_WIDTH - ENEMY_SIZE[0])
            self._enemies.append(Enemy(x, -ENEMY_SIZE[1]))

        # 弾の更新・当たり判定
        self._bullet_control.update(self._enemies)

        # 敵の移動
        for enemy in self._enemies:
            if enemy.alive:
                enemy.move_down()
                if enemy.rect.colliderect(self._character.rect):
                    self._state = self.STATE_GAME_OVER
        self._enemies = [en for en in self._enemies if en.alive and not en.is_off_screen()]

        self._game_screen.show(self._character, self._bullet_control.bullets,
                                self._enemies, self._score)

    def _handle_game_over_events(self, events: list[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                # ⑥リトライする
                save_high_score(self._player.name, self._score.get_point())
                self._reset_game_entities()
                self._state = self.STATE_TITLE

    def _handle_high_score_events(self, events: list[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                # ⑧タイトル画面に戻る
                self._state = self.STATE_TITLE

    # -- メインループ --------------------------------------------------------
    def run(self) -> None:
        while True:
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            if self._state == self.STATE_TITLE:
                self._handle_title_events(events)
                self._title_screen.show()
            elif self._state == self.STATE_NAME_INPUT:
                self._handle_name_input_events(events)
                self._name_input_screen.show(self._name_buffer)
            elif self._state == self.STATE_PLAYING:
                self._handle_playing(events)
            elif self._state == self.STATE_GAME_OVER:
                self._handle_game_over_events(events)
                self._game_over_screen.show(self._score)
            elif self._state == self.STATE_HIGH_SCORE:
                self._handle_high_score_events(events)
                self._high_score_screen.show(self._high_scores)

            self._clock.tick(FPS)


if __name__ == "__main__":
    GameApp().run()
