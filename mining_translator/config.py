import os


def _load_env():
    """Load .env file from project root (if exists)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


_load_env()

# DeepSeek API (default)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# Claude API (optional)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# OpenAI-compatible API (optional)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = "gpt-4o"

DEFAULT_BACKEND = "deepseek"

# Paths (relative to project root)
GLOSSARY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "glossary")
DEFAULT_INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

# Translation parameters
TRANSLATION_TEMPERATURE = 0.1
MAX_TOKENS = 8000

# Logging
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "translator.log")
LOG_LEVEL = "INFO"

# Glossary categories
CATEGORIES = [
    "采矿方法",
    "矿物/矿石",
    "设备/机械",
    "安全",
    "环保",
    "地质/勘探",
    "选矿",
    "冶炼/冶金",
    "合同/法律",
    "其他",
]
