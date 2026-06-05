import numpy as np
import pygame
import sys
import math
import random
import os

# --- INITIALIZATION ---
pygame.init()
pygame.mixer.init()

info = pygame.display.Info()
MONITOR_WIDTH, MONITOR_HEIGHT = info.current_w, info.current_h

COLUMN_COUNT, ROW_COUNT = 7, 6
SQUARESIZE = min(MONITOR_WIDTH // 11, (MONITOR_HEIGHT - 250) // 8)
RADIUS = int(SQUARESIZE / 2 - 5)
TOTAL_BOARD_WIDTH = COLUMN_COUNT * SQUARESIZE
TOTAL_BOARD_HEIGHT = ROW_COUNT * SQUARESIZE

# Colors
BLUE_BOARD = (44, 62, 120)
RED_PIECE = (231, 76, 60)
YEL_PIECE = (241, 196, 15)
WHITE = (236, 240, 241)
BLACK = (10, 10, 15)
BTN_GREEN, BTN_YELLOW, BTN_RED, BTN_BLUE = (46, 204, 113), (241, 196, 15), (192, 57, 43), (52, 152, 219)
HOVER_COLOR = (70, 70, 110)
GRADIENT_TOP, GRADIENT_BOT = (60, 20, 40), (20, 30, 60)

# --- RESOURCE HELPERS ---
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def start_music():
    path = resource_path("bg_music.mp3")
    if os.path.exists(path):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)
        except: pass

def create_gradient(w, h):
    surf = pygame.Surface((w, h))
    for y in range(h):
        ratio = y / h
        r = GRADIENT_TOP[0] * (1-ratio) + GRADIENT_BOT[0] * ratio
        g = GRADIENT_TOP[1] * (1-ratio) + GRADIENT_BOT[1] * ratio
        b = GRADIENT_TOP[2] * (1-ratio) + GRADIENT_BOT[2] * ratio
        pygame.draw.line(surf, (int(r), int(g), int(b)), (0, y), (w, y))
    return surf

# --- BUTTON CLASS ---
class Button:
    def __init__(self, text, x, y, width, height, color, hover, val=None):
        self.text, self.rect, self.color, self.hover, self.val = text, pygame.Rect(x, y, width, height), color, hover, val
        self.is_hovered = False
    def draw(self, screen, font):
        c = self.hover if self.is_hovered else self.color
        pygame.draw.rect(screen, c, self.rect, border_radius=15)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=15)
        txt = font.render(self.text, True, WHITE)
        screen.blit(txt, txt.get_rect(center=self.rect.center))
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)

# --- CORE ENGINE ---
def create_board(): return np.zeros((ROW_COUNT, COLUMN_COUNT))
def is_valid(board, c): return board[ROW_COUNT-1][c] == 0
def get_next_row(board, c):
    for r in range(ROW_COUNT):
        if board[r][c] == 0: return r

def winning_move(board, p):
    # Standard 4-in-a-row check logic
    for c in range(COLUMN_COUNT-3):
        for r in range(ROW_COUNT):
            if board[r][c] == p and board[r][c+1] == p and board[r][c+2] == p and board[r][c+3] == p: return True
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT-3):
            if board[r][c] == p and board[r+1][c] == p and board[r+2][c] == p and board[r+3][c] == p: return True
    for c in range(COLUMN_COUNT-3):
        for r in range(ROW_COUNT-3):
            if board[r][c] == p and board[r+1][c+1] == p and board[r+2][c+2] == p and board[r+3][c+3] == p: return True
    for c in range(COLUMN_COUNT-3):
        for r in range(3, ROW_COUNT):
            if board[r][c] == p and board[r-1][c+1] == p and board[r-2][c+2] == p and board[r-3][c+3] == p: return True
    return False

# --- PERSONALIZED AI BRAIN ---
def evaluate_window(window, piece, difficulty_val):
    score = 0
    opp_piece = 1 if piece == 2 else 2

    if window.count(piece) == 4:
        score += 100000
    
    # Easy (val 2): Just looking for its own stacks
    if difficulty_val <= 2:
        if window.count(piece) == 3 and window.count(0) == 1: score += 50
        if window.count(opp_piece) == 3 and window.count(0) == 1: score -= 80 # Weak block

    # Medium (val 5): Balanced Strategist
    elif difficulty_val <= 5:
        if window.count(piece) == 3 and window.count(0) == 1: score += 150
        if window.count(piece) == 2 and window.count(0) == 2: score += 20
        if window.count(opp_piece) == 3 and window.count(0) == 1: score -= 400 # Strong block

    # Impossible (val 8): Perfect Defensive Play
    else:
        if window.count(piece) == 3 and window.count(0) == 1: score += 500
        if window.count(opp_piece) == 3 and window.count(0) == 1: score -= 80000 # Critical block
    
    return score

def score_position(board, piece, diff_val):
    score = 0
    center_array = [int(i) for i in list(board[:, COLUMN_COUNT//2])]
    center_mult = 15 if diff_val > 5 else (5 if diff_val > 2 else 2)
    score += center_array.count(piece) * center_mult

    for r in range(ROW_COUNT):
        row_array = [int(i) for i in list(board[r,:])]
        for c in range(COLUMN_COUNT-3):
            score += evaluate_window(row_array[c:c+4], piece, diff_val)
    for c in range(COLUMN_COUNT):
        col_array = [int(i) for i in list(board[:,c])]
        for r in range(ROW_COUNT-3):
            score += evaluate_window(col_array[r:r+4], piece, diff_val)
    for r in range(ROW_COUNT-3):
        for c in range(COLUMN_COUNT-3):
            window = [board[r+i][c+i] for i in range(4)]
            score += evaluate_window(window, piece, diff_val)
            window = [board[r+3-i][c+i] for i in range(4)]
            score += evaluate_window(window, piece, diff_val)
    return score

def minimax(board, depth, alpha, beta, maxPlay, diff_val):
    order = [3, 2, 4, 1, 5, 0, 6]
    valid_locs = [c for c in order if is_valid(board, c)]
    win2, win1 = winning_move(board, 2), winning_move(board, 1)

    if depth == 0 or win1 or win2 or not valid_locs:
        if win2: return (None, 10000000)
        if win1: return (None, -10000000)
        if not valid_locs: return (None, 0)
        return (None, score_position(board, 2, diff_val))

    if maxPlay:
        v, col = -math.inf, valid_locs[0]
        for c in valid_locs:
            r = get_next_row(board, c); temp = board.copy(); temp[r][c] = 2
            score = minimax(temp, depth-1, alpha, beta, False, diff_val)[1]
            if score > v: v, col = score, c
            alpha = max(alpha, v)
            if alpha >= beta: break
        return col, v
    else:
        v, col = math.inf, valid_locs[0]
        for c in valid_locs:
            r = get_next_row(board, c); temp = board.copy(); temp[r][c] = 1
            score = minimax(temp, depth-1, alpha, beta, True, diff_val)[1]
            if score < v: v, col = score, c
            beta = min(beta, v)
            if alpha >= beta: break
        return col, v

# --- DRAWING ---
def draw_board_only(screen, board, ox, bg, turn_msg, msg_color):
    screen.blit(bg, (0,0))
    f_status = pygame.font.SysFont("arial", 50, bold=True)
    status_surf = f_status.render(turn_msg, True, msg_color)
    screen.blit(status_surf, (MONITOR_WIDTH//2 - status_surf.get_width()//2, 20))
    
    pygame.draw.rect(screen, BLUE_BOARD, (ox, SQUARESIZE+50, TOTAL_BOARD_WIDTH, TOTAL_BOARD_HEIGHT), border_radius=15)
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT):
            px, py = int(ox + c*SQUARESIZE + SQUARESIZE/2), int(SQUARESIZE+50 + (ROW_COUNT-1-r)*SQUARESIZE + SQUARESIZE/2)
            color = BLACK if board[r][c] == 0 else (RED_PIECE if board[r][c] == 1 else YEL_PIECE)
            pygame.draw.circle(screen, color, (px, py), RADIUS)

# --- MAIN ---
def main():
    screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
    bg = create_gradient(MONITOR_WIDTH, MONITOR_HEIGHT)
    ox = (MONITOR_WIDTH - TOTAL_BOARD_WIDTH) // 2 - 120
    f_title, f_med = pygame.font.SysFont("arial", 80, bold=True), pygame.font.SysFont("arial", 45, bold=True)
    start_music()
    state, board, diff_val, turn, msg, m_col = "MENU", create_board(), 5, 0, "", WHITE
    
    while True:
        m_pos = pygame.mouse.get_pos()
        if state == "MENU":
            screen.blit(bg, (0,0))
            screen.blit(f_title.render("CONNECT 4 AI", True, WHITE), (MONITOR_WIDTH//2 - 240, 100))
            bw, bh, cx = 350, 70, MONITOR_WIDTH//2 - 175
            m_btns = [Button("EASY", cx, MONITOR_HEIGHT//2 - 100, bw, bh, BTN_GREEN, HOVER_COLOR, 2),
                      Button("MEDIUM", cx, MONITOR_HEIGHT//2, bw, bh, BTN_YELLOW, HOVER_COLOR, 5),
                      Button("IMPOSSIBLE", cx, MONITOR_HEIGHT//2 + 100, bw, bh, BTN_RED, HOVER_COLOR, 8)]
            for b in m_btns: b.check_hover(m_pos); b.draw(screen, f_med)
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: sys.exit()
                if e.type == pygame.MOUSEBUTTONDOWN:
                    for b in m_btns:
                        if b.is_hovered: diff_val, board, turn, state = b.val, create_board(), random.randint(0,1), "PLAYING"
            pygame.display.flip()

        elif state == "PLAYING":
            if turn == 0:
                pygame.event.clear(pygame.MOUSEBUTTONDOWN) # STOP THE SPAM
                draw_board_only(screen, board, ox, bg, "YOUR TURN", RED_PIECE)
                pygame.display.flip()
                waiting = True
                while waiting:
                    for e in pygame.event.get():
                        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: sys.exit()
                        if e.type == pygame.MOUSEBUTTONDOWN:
                            col = (e.pos[0] - ox) // SQUARESIZE
                            if 0 <= col < COLUMN_COUNT and is_valid(board, col):
                                board[get_next_row(board, col)][col] = 1
                                if winning_move(board, 1): state, msg, m_col = "GAMEOVER", "YOU WIN!", RED_PIECE
                                elif not any(is_valid(board, c) for c in range(COLUMN_COUNT)): state, msg, m_col = "GAMEOVER", "DRAW!", WHITE
                                turn, waiting = 1, False; break
                    if not waiting: break
            else:
                draw_board_only(screen, board, ox, bg, "AI IS THINKING...", YEL_PIECE)
                pygame.display.flip(); pygame.time.wait(800)
                col, _ = minimax(board, diff_val, -math.inf, math.inf, True, diff_val)
                if col is not None:
                    board[get_next_row(board, col)][col] = 2
                    if winning_move(board, 2): state, msg, m_col = "GAMEOVER", "AI WINS!", YEL_PIECE
                    elif not any(is_valid(board, c) for c in range(COLUMN_COUNT)): state, msg, m_col = "GAMEOVER", "DRAW!", WHITE
                turn = 0

        elif state == "GAMEOVER":
            draw_board_only(screen, board, ox, bg, "GAME OVER", WHITE)
            side_x, rem_btn = ox + TOTAL_BOARD_WIDTH + 60, Button("REMATCH", 0, MONITOR_HEIGHT//2 + 20, 240, 70, BTN_BLUE, HOVER_COLOR)
            rem_btn.rect.x = side_x
            screen.blit(f_med.render(msg, True, m_col), (side_x + (240 - f_med.size(msg)[0])//2, MONITOR_HEIGHT//2 - 60))
            rem_btn.check_hover(m_pos); rem_btn.draw(screen, f_med)
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: sys.exit()
                if e.type == pygame.MOUSEBUTTONDOWN and rem_btn.is_hovered: pygame.event.clear(); state = "MENU"
            pygame.display.flip()

if __name__ == "__main__":
    main()