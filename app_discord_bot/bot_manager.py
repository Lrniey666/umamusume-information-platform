"""
Discord Bot 行程管理器
負責從 Django 控制台 Start / Stop / Status 管理 run_discord_bot 子行程。

設計說明：
  · 使用模組層級 _bot_process 記憶當前 session 的 Popen 物件。
  · 同時維護 discord_bot.pid 檔（BASE_DIR/discord_bot.pid），
    以便 Django 重啟後仍能追蹤舊行程。
  · 支援 Windows（tasklist / taskkill）與 Linux/Mac（os.kill）。
"""
import os
import subprocess
import sys
import platform
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
PID_FILE = BASE_DIR / 'discord_bot.pid'

# 模組層級行程參考（Django 重啟後會失效，此時改用 PID 檔追蹤）
_bot_process: subprocess.Popen | None = None


# ── 跨平台工具函式 ─────────────────────────────────────────────────

def _is_pid_alive(pid: int) -> bool:
    """確認 PID 行程是否仍存活（Windows / Unix 均適用）"""
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                capture_output=True, text=True, timeout=3,
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def _kill_pid(pid: int):
    """終止指定 PID 行程（Windows / Unix 均適用）"""
    if platform.system() == 'Windows':
        subprocess.run(
            ['taskkill', '/PID', str(pid), '/F'],
            capture_output=True, timeout=5,
        )
    else:
        import signal
        os.kill(pid, signal.SIGTERM)


# ── 公開 API ──────────────────────────────────────────────────────

def get_bot_status() -> dict:
    """
    回傳 Bot 目前狀態：
    {'running': bool, 'pid': int|None, 'source': 'memory'|'pidfile'|'none'}
    """
    global _bot_process

    # 1. 優先從記憶體中的 Popen 物件判斷
    if _bot_process is not None:
        if _bot_process.poll() is None:
            return {'running': True, 'pid': _bot_process.pid, 'source': 'memory'}
        _bot_process = None  # 行程已結束，清除參考

    # 2. Fallback：讀取 PID 檔
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding='utf-8').strip())
            if _is_pid_alive(pid):
                return {'running': True, 'pid': pid, 'source': 'pidfile'}
        except Exception:
            pass
        # PID 檔存在但行程已死，清除殘留檔案
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    return {'running': False, 'pid': None, 'source': 'none'}


def start_bot() -> tuple[bool, str]:
    """
    啟動 Discord Bot 子行程。
    回傳 (success: bool, message: str)。
    """
    global _bot_process

    status = get_bot_status()
    if status['running']:
        return False, f'Bot 已在運行中（PID: {status["pid"]}）'

    token = os.getenv('DISCORD_BOT_TOKEN', '')
    if not token or token == '你的Bot Token':
        return False, 'DISCORD_BOT_TOKEN 未設定，請先在 .env 填入有效的 Token'

    try:
        cmd = [sys.executable, str(BASE_DIR / 'manage.py'), 'run_discord_bot']

        kwargs: dict = {
            'cwd': str(BASE_DIR),
            'stdout': subprocess.DEVNULL,
            'stderr': subprocess.DEVNULL,
        }
        if platform.system() == 'Windows':
            # CREATE_NEW_PROCESS_GROUP 讓子行程獨立於 Django，
            # 可用 CTRL_BREAK_EVENT 或 taskkill 終止
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs['start_new_session'] = True

        _bot_process = subprocess.Popen(cmd, **kwargs)

        # 寫入 PID 檔，Django 重啟後仍可追蹤
        PID_FILE.write_text(str(_bot_process.pid), encoding='utf-8')

        logger.info(f'[BotManager] Bot 已啟動，PID={_bot_process.pid}')
        return True, f'Bot 已啟動（PID: {_bot_process.pid}）'

    except Exception as e:
        logger.error(f'[BotManager] 啟動失敗：{e}')
        return False, f'啟動失敗：{e}'


def stop_bot() -> tuple[bool, str]:
    """
    停止 Discord Bot 子行程。
    回傳 (success: bool, message: str)。
    """
    global _bot_process

    status = get_bot_status()
    if not status['running']:
        return False, 'Bot 目前未在運行'

    pid = status['pid']
    try:
        if _bot_process is not None and _bot_process.poll() is None:
            _bot_process.terminate()
            try:
                _bot_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f'[BotManager] terminate 超時，強制 kill PID={pid}')
                _bot_process.kill()
        else:
            _kill_pid(pid)

        _bot_process = None
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass

        logger.info(f'[BotManager] Bot 已停止，PID={pid}')
        return True, f'Bot 已停止（PID: {pid}）'

    except Exception as e:
        logger.error(f'[BotManager] 停止失敗：{e}')
        return False, f'停止失敗：{e}'
