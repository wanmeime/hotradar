import logging
import sys
from datetime import datetime
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 日志目录
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 默认输出目录（TrendWatch 标准路径）
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

# 平台配置
PLATFORMS = {
    "weibo": {
        "name": "微博",
        "url": "https://s.weibo.com/top/summary",
        "enabled": True,
    },
    "douyin": {
        "name": "抖音",
        "url": "https://www.douyin.com/hot",
        "enabled": True,
    },
    "zhihu": {
        "name": "知乎",
        "url": "https://www.zhihu.com/hot",
        "enabled": True,
    },
    "xiaohongshu": {
        "name": "小红书",
        "url": "https://www.xiaohongshu.com/explore",
        "enabled": True,
    },
}

# User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# 日志配置
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(name: str = "hotradar") -> logging.Logger:
    """配置日志"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    # 文件输出
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)

    return logger
