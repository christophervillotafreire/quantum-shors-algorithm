import yaml
from pathlib import Path


# Global variable to hold the configuration
_settings = None


def load_settings(config_path: str = "common/settings.yaml"):
    """Load settings from a YAML file into the global _settings variable."""
    global _settings
    settings_file = Path(config_path)
    if not settings_file.exists():
        raise FileNotFoundError(f"Settings file not found: {config_path}")

    with settings_file.open("r") as f:
        _settings = yaml.safe_load(f)


def get_settings():
    """Return the loaded configuration."""
    if _settings is None:
        raise ValueError("Settings not loaded. Call load_settings() first.")
    return _settings


def get_settings_value_for_key(key: str, default=None):
    """Get a specific config value by key (e.g., 'database.host')."""
    if _settings is None:
        raise ValueError("Settings not loaded. Call load_settings() first.")

    keys = key.split(".")
    value = _settings
    for k in keys:
        value = value.get(k, default)
        if value is default:
            break
    return value