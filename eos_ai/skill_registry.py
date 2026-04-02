import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


SKILLS_DIR = Path(__file__).parent.parent / "skills"
MIN_CONTENT_LENGTH = 500


@dataclass
class Skill:
    skill_id: str       # snake_case identifier derived from filename
    name: str           # human-readable name parsed from # header or filename
    content: str        # full markdown content
    file_path: str      # absolute path to source file


class SkillRegistry:

    # Class-level flag — set to None to signal callers to reinstantiate.
    # Used by /sync command and skill_improvement after rewriting a skill.
    _instance: "SkillRegistry | None" = None

    def __init__(self, org_id: str | None = None) -> None:
        self._skills: dict[str, Skill] = {}
        self._skill_embeddings: dict[str, np.ndarray] = {}  # cached on first load
        self._load()
        if org_id:
            self.load_from_db(org_id)
        self._cache_embeddings()

    # ─── Loading ─────────────────────────────────────────────────────────────

    def _load(self) -> None:
        loaded: list[str] = []
        skipped: list[str] = []

        for md_file in sorted(SKILLS_DIR.rglob("*.md")):
            rel = md_file.relative_to(SKILLS_DIR)
            content = md_file.read_text(encoding="utf-8")

            if len(content) < MIN_CONTENT_LENGTH:
                skipped.append(str(rel))
                continue

            skill_id = self._to_skill_id(md_file)
            name = self._parse_name(content, md_file)

            self._skills[skill_id] = Skill(
                skill_id=skill_id,
                name=name,
                content=content,
                file_path=str(md_file),
            )
            loaded.append(f"{skill_id}  ({rel})")

        print(f"[SkillRegistry] Loaded {len(loaded)} skills:")
        for entry in loaded:
            print(f"  ✓  {entry}")

        if skipped:
            print(f"[SkillRegistry] Skipped {len(skipped)} files (< {MIN_CONTENT_LENGTH} chars):")
            for entry in skipped:
                print(f"  ⚠  {entry}")

    def _to_skill_id(self, path: Path) -> str:
        # Use parent directory name as skill ID (files are all named SKILL.md)
        name = path.parent.name.lower()
        name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
        return name

    def load_from_db(self, org_id: str) -> None:
        """
        Query the skills table in Neon for the given org_id and merge with
        file-based skills already loaded. DB skills override file skills on
        name collision. Called automatically on init when org_id is provided.
        """
        try:
            from eos_ai.db import get_conn
            with get_conn(org_id) as cur:
                cur.execute(
                    "SELECT name, content FROM skills WHERE org_id = %s",
                    (org_id,),
                )
                rows = cur.fetchall()

            loaded_db = 0
            for row in rows:
                skill_id = re.sub(r"[^a-z0-9]+", "_", row["name"].lower()).strip("_")
                content  = row["content"] or ""
                if len(content) < MIN_CONTENT_LENGTH:
                    continue
                name = self._parse_name(content, Path(skill_id))
                self._skills[skill_id] = Skill(
                    skill_id=skill_id,
                    name=name,
                    content=content,
                    file_path=f"db:{org_id}/{row['name']}",
                )
                loaded_db += 1

            if loaded_db:
                print(f"[SkillRegistry] Loaded {loaded_db} skills from DB (org={org_id[:8]}...).")
        except Exception as e:
            print(f"[SkillRegistry] DB skill load skipped ({e}).")

    def _cache_embeddings(self) -> None:
        """
        Embed each skill's name + first 800 chars of content on registry load.
        Cached in-memory — no DB required. Silently skips if fastembed unavailable.
        """
        try:
            from eos_ai.embedder import embed
            for skill in self._skills.values():
                text = f"{skill.name}\n\n{skill.content[:800]}"
                self._skill_embeddings[skill.skill_id] = embed(text)
            print(f"[SkillRegistry] Cached embeddings for {len(self._skill_embeddings)} skills.")
        except Exception as e:
            print(f"[SkillRegistry] Embedding cache skipped ({e}) — falling back to keyword matching.")

    def _parse_name(self, content: str, path: Path) -> str:
        match = re.search(r"^#\s+(?:Skill:\s*)?(.+)", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return path.stem.replace("_", " ").title()

    # ─── Retrieval ───────────────────────────────────────────────────────────

    def get_skill(self, name: str) -> Skill | None:
        """
        Fuzzy name matching: tries exact skill_id, then normalized
        (- and _ equivalent), then partial substring match on
        skill_id and skill name, case-insensitive.
        Returns the best single match or None.
        """
        query = name.lower().strip()

        # 1. Exact skill_id match
        if query in self._skills:
            return self._skills[query]

        # 2. Normalize: treat - and _ as equivalent
        normalized = re.sub(r"[-_]+", "_", query)
        if normalized in self._skills:
            return self._skills[normalized]
        # Also try hyphenated form
        hyphenated = re.sub(r"[-_]+", "-", query)
        for skill_id in self._skills:
            if re.sub(r"[-_]+", "-", skill_id) == hyphenated:
                return self._skills[skill_id]

        # 3. skill_id starts with query or normalized form
        for skill_id, skill in self._skills.items():
            if skill_id.startswith(query) or skill_id.startswith(normalized):
                return skill

        # 3. query is a substring of skill_id or name
        candidates: list[tuple[int, Skill]] = []
        for skill in self._skills.values():
            score = 0
            if query in skill.skill_id:
                score += 2
            if query in skill.name.lower():
                score += 2
            # partial word overlap
            query_words = set(query.split("_"))
            id_words = set(skill.skill_id.split("_"))
            name_words = set(skill.name.lower().split())
            overlap = len(query_words & (id_words | name_words))
            score += overlap
            if score > 0:
                candidates.append((score, skill))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]

        return None

    def get_relevant_skills(self, task_description: str, top_n: int = 2) -> list[Skill]:
        """
        Returns the top_n skills most relevant to task_description.

        Uses semantic cosine similarity when embeddings are cached (primary path).
        Falls back to keyword overlap when embeddings are unavailable.
        """
        # ── Semantic path ─────────────────────────────────────────────────────
        if self._skill_embeddings:
            try:
                from eos_ai.embedder import embed, cosine_similarity
                query_vec = embed(task_description)
                scored: list[tuple[float, Skill]] = []
                for skill_id, skill_vec in self._skill_embeddings.items():
                    skill = self._skills.get(skill_id)
                    if skill:
                        sim = cosine_similarity(query_vec, skill_vec)
                        scored.append((sim, skill))
                scored.sort(key=lambda x: x[0], reverse=True)
                return [skill for _, skill in scored[:top_n]]
            except Exception as e:
                print(f"[SkillRegistry] Semantic matching failed ({e}) — using keyword fallback.")

        # ── Keyword fallback ──────────────────────────────────────────────────
        task_words = set(re.findall(r"[a-z]+", task_description.lower()))
        stop = {
            "the", "a", "an", "and", "or", "for", "to", "of", "in", "with",
            "this", "that", "is", "are", "it", "be", "as", "at", "by", "from",
            "on", "was", "we", "i", "you", "he", "she", "they", "them", "their",
        }
        task_words -= stop
        kw_scored: list[tuple[int, Skill]] = []
        for skill in self._skills.values():
            skill_text  = (skill.name + " " + skill.content).lower()
            skill_words = set(re.findall(r"[a-z]+", skill_text)) - stop
            overlap     = len(task_words & skill_words)
            if overlap > 0:
                kw_scored.append((overlap, skill))
        kw_scored.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in kw_scored[:top_n]]

    def list_skills(self) -> list[str]:
        return list(self._skills.keys())

    def all_skills(self) -> list[Skill]:
        return list(self._skills.values())


# ─── Module-level singleton ───────────────────────────────────────────────────

_skill_registry: "SkillRegistry | None" = None


def get_skill_registry(org_id: str | None = None) -> SkillRegistry:
    """Return the module-level singleton SkillRegistry.

    Instantiated once; reused on every subsequent call.
    To force a reload after /sync or skill rewrites, call
    reset_skill_registry() then get_skill_registry() again.
    """
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry(org_id=org_id)
    return _skill_registry


def reset_skill_registry() -> None:
    """Signal the singleton to reload on next get_skill_registry() call."""
    global _skill_registry
    _skill_registry = None
    SkillRegistry._instance = None
