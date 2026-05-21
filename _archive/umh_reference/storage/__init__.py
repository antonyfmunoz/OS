"""UMH Storage — raw key-value persistence layer.

Storage is the low-level persistence contract: get/put/all_keys.
This is distinct from memory (the intelligence subsystem that handles
semantic recall, episodic retrieval, and working memory).

The StorageBackend protocol and InMemoryStorage implementation are
canonical here. Legacy imports from umh.memory.storage remain valid.
"""

from umh.storage.backend import InMemoryStorage, StorageBackend

__all__ = ["InMemoryStorage", "StorageBackend"]
