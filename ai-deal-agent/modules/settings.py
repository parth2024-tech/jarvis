"""Centralized config loader."""
from __future__ import annotations
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
PROMPTS_DIR = ROOT / "prompts"


def env(key: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name) as f:
        return yaml.safe_load(f)


def load_prompt(name: str) -> str:
    with open(PROMPTS_DIR / name) as f:
        return f.read()


SOURCES = load_yaml("sources.yaml")
QUERY_TEMPLATES = load_yaml("query_templates.yaml")

REGION = env("REGION", "IN")
HIGH_VALUE_THRESHOLD = float(env("HIGH_VALUE_THRESHOLD_USD", "500"))
