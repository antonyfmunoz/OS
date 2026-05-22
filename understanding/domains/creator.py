"""Creator domain bridge — structural mapping from ontology to creator primitives.

V1: keyword-based structural rules only. No LLM dependency.
Maps ontology observations to CreatorOS creator domain primitives
covering content creation, audience, distribution, monetization,
brand, and production.
"""

from __future__ import annotations

from understanding.ontology.primitive_decomposition_v1 import PrimitiveObservation

from .contract import DomainProjection, make_projection_id
from .registry import default_registry


_DOMAIN_KEYWORD_MAP: dict[str, dict[str, list[str]]] = {
    "content": {
        "long_form": [
            "long form",
            "youtube video",
            "podcast episode",
            "blog post",
            "essay",
            "documentary",
            "deep dive",
            "long-form",
        ],
        "short_form": [
            "short form",
            "reel",
            "tiktok",
            "short video",
            "clip",
            "snippet",
            "vertical video",
            "shorts",
        ],
        "writing": [
            "newsletter",
            "article",
            "thread",
            "tweet",
            "copywriting",
            "caption",
            "script",
            "scriptwriting",
        ],
        "repurposing": [
            "repurpose",
            "repurposing",
            "clip from",
            "cut from",
            "atomize",
            "content recycling",
            "pillar content",
        ],
        "_domain_generic": [
            "content",
            "content creation",
            "create content",
            "posting",
            "publish",
        ],
    },
    "audience": {
        "community_building": [
            "community",
            "discord server",
            "facebook group",
            "skool",
            "community building",
            "tribe",
            "membership community",
        ],
        "engagement": [
            "engagement",
            "comment",
            "reply",
            "dm",
            "engagement rate",
            "interaction",
            "call to action",
        ],
        "growth_strategy": [
            "follower growth",
            "subscriber",
            "audience growth",
            "grow audience",
            "first 1000",
            "algorithm",
            "discoverability",
        ],
        "email_list": [
            "email list",
            "subscriber list",
            "lead magnet",
            "opt-in",
            "email marketing",
            "newsletter list",
            "mailing list",
        ],
        "_domain_generic": [
            "audience",
            "followers",
            "subscribers",
            "fans",
            "viewers",
        ],
    },
    "distribution": {
        "platform_strategy": [
            "youtube",
            "instagram",
            "twitter",
            "tiktok",
            "linkedin",
            "spotify",
            "platform strategy",
            "cross-post",
        ],
        "seo": [
            "seo",
            "search engine",
            "keyword research",
            "organic search",
            "ranking",
            "searchable",
        ],
        "collaboration": [
            "collaboration",
            "collab",
            "guest",
            "feature",
            "cross promotion",
            "podcast guest",
            "interview",
        ],
        "_domain_generic": [
            "distribution",
            "reach",
            "visibility",
            "impressions",
            "views",
        ],
    },
    "monetization": {
        "digital_products": [
            "digital product",
            "ebook",
            "template",
            "course",
            "online course",
            "info product",
            "digital download",
        ],
        "sponsorship": [
            "sponsor",
            "sponsorship",
            "brand deal",
            "brand partnership",
            "paid promotion",
            "ad revenue",
            "adsense",
        ],
        "services": [
            "coaching",
            "consulting",
            "freelance",
            "service offer",
            "one-on-one",
            "done for you",
            "agency",
        ],
        "membership": [
            "membership",
            "subscription",
            "patreon",
            "paid community",
            "recurring revenue",
            "membership site",
        ],
        "_domain_generic": [
            "monetize",
            "monetization",
            "revenue stream",
            "income",
            "earning",
        ],
    },
    "brand": {
        "identity": [
            "brand identity",
            "personal brand",
            "brand voice",
            "brand aesthetic",
            "visual identity",
            "brand archetype",
            "positioning",
        ],
        "storytelling": [
            "storytelling",
            "origin story",
            "narrative",
            "brand story",
            "authentic",
            "vulnerability",
            "transformation story",
        ],
        "authority": [
            "authority",
            "thought leader",
            "expert positioning",
            "credibility",
            "social proof",
            "testimonial",
            "case study",
        ],
        "_domain_generic": [
            "brand",
            "branding",
            "image",
            "reputation",
        ],
    },
    "production": {
        "video_production": [
            "camera",
            "lighting",
            "b-roll",
            "editing",
            "video editing",
            "color grade",
            "thumbnail",
            "premiere pro",
            "davinci resolve",
        ],
        "audio_production": [
            "microphone",
            "audio",
            "recording",
            "mixing",
            "sound design",
            "podcast setup",
            "audio quality",
        ],
        "ai_tools": [
            "ai generation",
            "ai tools",
            "ai writing",
            "ai video",
            "ai image",
            "chatgpt",
            "midjourney",
            "ai editing",
        ],
        "workflow": [
            "production workflow",
            "batch content",
            "content batch",
            "content calendar",
            "scheduling tool",
            "content pipeline",
        ],
        "_domain_generic": [
            "production",
            "equipment",
            "studio",
            "setup",
            "gear",
        ],
    },
}

_BRIDGEABLE_ONTOLOGY_TYPES = frozenset(
    [
        "constraint",
        "action",
        "goal",
        "state",
        "resource",
    ]
)


class CreatorBridge:
    """Structural keyword bridge from ontology observations to creator domain primitives."""

    @property
    def domain_id(self) -> str:
        return "creator"

    def describes(self) -> str:
        return (
            "Maps ontology observations to creator domain primitives "
            "(content, audience, distribution, monetization, brand, production) "
            "using structural keyword matching."
        )

    def bridge(self, observation: PrimitiveObservation) -> DomainProjection | None:
        if observation.primitive_type.value not in _BRIDGEABLE_ONTOLOGY_TYPES:
            return None

        text = f"{observation.label} {observation.description}".lower()

        best_domain: str | None = None
        best_primitive: str | None = None
        best_score = 0

        for domain, primitives in _DOMAIN_KEYWORD_MAP.items():
            for prim_id, keywords in primitives.items():
                score = sum(1 for kw in keywords if kw in text)
                if score > best_score:
                    best_score = score
                    best_domain = domain
                    best_primitive = prim_id

        if best_score == 0 or best_domain is None:
            return None

        if best_primitive and best_primitive.startswith("_domain_"):
            best_primitive = None

        confidence = min(observation.confidence, 0.70 + (best_score * 0.05))

        return DomainProjection(
            projection_id=make_projection_id(),
            domain_id=self.domain_id,
            domain_primitive_type=best_primitive or f"domain:{best_domain}",
            label=f"[creator:{best_domain}] {observation.label}"[:80],
            description=observation.description,
            properties={
                "source_ontology_type": observation.primitive_type.value,
                "creator_domain": best_domain,
                "creator_primitive_id": best_primitive,
                "keyword_match_score": best_score,
            },
            ontology_observation_ref=observation.observation_id,
            confidence=confidence,
            evidence=observation.evidence,
            authority_tier=observation.authority_tier,
        )


_creator_bridge = CreatorBridge()
default_registry.register(_creator_bridge)
