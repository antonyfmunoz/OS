"""Structural tests for EntityLinkStore."""

import inspect
import os
import sys

sys.path.insert(0, "/opt/OS")
from dotenv import load_dotenv
load_dotenv(os.path.join("/opt/OS", "runtime", ".env"))
load_dotenv(os.path.join("/opt/OS", "services", ".env"))


def test_entity_link_store_exists():
    from state.stores.entity_link_store import EntityLinkStore
    assert EntityLinkStore is not None


def test_insert_link_signature():
    from state.stores.entity_link_store import EntityLinkStore
    sig = inspect.signature(EntityLinkStore.insert_link)
    params = list(sig.parameters.keys())
    assert params == [
        "self", "org_id", "from_type", "from_id",
        "to_type", "to_id", "relationship", "metadata",
    ]


def test_insert_link_return_annotation():
    from state.stores.entity_link_store import EntityLinkStore
    hints = EntityLinkStore.insert_link.__annotations__
    assert hints.get("return") is str
