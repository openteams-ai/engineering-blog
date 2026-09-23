"""
The social brief: a short summary of a post, written by its author, that seeds its
LinkedIn copy.

The field descriptions are the questions authors (and their AI assistants)
see as comments in social/<slug>.yml, so they are written for a human reader.
"""

import json
from pathlib import Path
from typing import List, Literal, get_args

import yaml
from pydantic import BaseModel, Field, field_validator

SOCIAL_DIR = Path("social")
# Short enough to reject one-liners like "Compares package managers.", long
# enough to pass every example in the fill-social-brief skill.
MIN_WORDS = 8

Audience = Literal[
    "data-scientists",
    "ml-ai-engineers",
    "python-developers",
    "platform-devops-engineers",
    "security-compliance-engineers",
    "oss-maintainers",
    "engineering-leaders",
]


class SocialBrief(BaseModel):
    """The author's answers. Order here is the order in the file."""

    problem: str = Field(
        description="What problem does this article solve? (1-2 sentences)"
    )
    what_it_does: str = Field(
        description="What does the article build, test, compare, or argue? (1-2 sentences)"
    )
    remember_one_thing: str = Field(
        description="If readers remember one thing, what should it be? (1 sentence)"
    )
    audience: List[Audience] = Field(
        min_length=1, description="Who should read this? Pick one or more:"
    )

    @field_validator("problem", "what_it_does", "remember_one_thing")
    @classmethod
    def specific_enough(cls, value: str) -> str:
        words = len(value.split())
        if words == 0:
            raise ValueError("is empty")
        if words < MIN_WORDS:
            raise ValueError(
                f"is only {words} words. Say more: at least {MIN_WORDS} words, with the "
                "article's specifics (tools, numbers, what was tested or argued)."
            )
        return value


def brief_path(post_path: Path) -> Path:
    """Map posts/<file> to social/<slug>.yml, using the frontmatter slug."""
    text = post_path.read_text(encoding="utf-8")
    slug = None
    if text.startswith("---"):
        meta = yaml.safe_load(text.split("---", 2)[1]) or {}
        slug = meta.get("slug")
    return SOCIAL_DIR / f"{slug or post_path.stem}.yml"


CHOICES = {"audience": get_args(Audience)}


def is_blank(data: dict) -> bool:
    """True when a brief still holds no answers, i.e. the untouched template."""
    return not any(data.get(name) for name in SocialBrief.model_fields)


def render_template(post_path: Path) -> str:
    """The brief with every answer empty, for the author to fill in."""
    values = {
        name: [] if name == "audience" else "" for name in SocialBrief.model_fields
    }
    lines = [
        f"# The social brief for {post_path.as_posix()}. It's used to write the LinkedIn post.",
        "# Answer each question yourself or with your AI assistant (see Social Brief in",
        "# README.md). The PR can merge once all four are answered.",
    ]
    for name, field in SocialBrief.model_fields.items():
        lines += ["", f"# {field.description}"]
        if name in CHOICES:
            lines.append("# " + ", ".join(CHOICES[name]))
        # JSON is valid YAML and always quotes, so a colon or leading dash in
        # the model's text can't change how the file parses.
        lines.append(f"{name}: {json.dumps(values[name], ensure_ascii=False)}")
    return "\n".join(lines) + "\n"
