"""Turn a prompt into a project name and a URL-safe slug.

"Create a web app that will help me track my workout." -> "Track My Workout",
slug "track-my-workout-k3x9".
"""

from __future__ import annotations

import re
import secrets
import string

FILLER = re.compile(
    r"^(?:please\s+)?(?:(?:can|could)\s+you\s+)?"
    r"(?:(?:create|build|make|generate|write|design)\s+)?(?:me\s+)?(?:(?:an|a|the)\s+)?"
    r"(?:(?:simple|small|basic)\s+)?"
    r"(?:(?:web\s*app|webapp|website|web\s*site|application|app|tool|page|site)\b\s*)?"
    r"(?:(?:that|which|to|for|where)\s+)?(?:(?:will|would|can)\s+)?"
    r"(?:(?:helps?|lets?|allows?)\s+)?(?:(?:me|us|users|people)\s+)?(?:to\s+)?",
    re.IGNORECASE,
)
SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to"}
ALPHABET = string.ascii_lowercase + string.digits


def project_name(prompt: str, max_words: int = 5) -> str:
    text = FILLER.sub("", prompt.strip(), count=1)
    # The name is the first clause: "track my workouts: log sets..." -> "track my workouts".
    text = re.split(r"[:;,.!?\n(]", text, maxsplit=1)[0]
    words = re.findall(r"[A-Za-z0-9']+", text)[:max_words] or ["My", "App"]
    titled = [
        w.lower() if i and w.lower() in SMALL_WORDS else w[:1].upper() + w[1:]
        for i, w in enumerate(words)
    ]
    return " ".join(titled)[:80]


def slugify(name: str, max_length: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:max_length].rstrip("-") or "app"


def with_suffix(slug: str) -> str:
    """A random tail keeps two "todo app" projects apart and makes URLs hard to guess."""
    return f"{slug}-{''.join(secrets.choice(ALPHABET) for _ in range(4))}"
