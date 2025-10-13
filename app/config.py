from pathlib import Path

# Base storage
ROOT_DATA_DIR: Path = Path("USERS_DATA")

# Pattern ammessi per ID (sicuro per cartelle e file)
ALLOWED_ID_PATTERN = r"^[a-zA-Z0-9._-]+$"

STORAGE_MODE = "shared"
