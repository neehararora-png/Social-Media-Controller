# Social Media Publisher Subsystem

The `publisher/` module implements an extensible, Strategy-pattern based multi-channel publishing engine. It dispatches content across **X (Twitter)**, **Instagram Business**, **Meta Threads**, **Facebook Pages**, and **TikTok**.

---

## Architecture Overview

```
                               PublisherManager
                               (Orchestrator)
                                      |
         +-------------+--------------+--------------+-------------+
         |             |              |              |             |
         v             v              v              v             v
    XPublisher    IGPublisher    ThreadsPub.    FBPublisher   TikTokPublisher
         |             |              |              |             |
         +-------------+--------------+--------------+-------------+
                                      |
                         Inherits from BasePublisher
                                      |
                      +---------------+---------------+
                      |                               |
                      v                               v
             Production API Mode            Sandbox Simulation Mode
```

---

## File Manifest

| File | Purpose |
| :--- | :--- |
| `base.py` | Abstract `BasePublisher` class and `PublishResult` dataclass. |
| `manager.py` | `PublisherManager` orchestrator, handles multi-account routing, scheduling, drafts, and audit history. |
| `oauth_helper.py` | Standalone RFC 3986 OAuth 1.0a HMAC-SHA1 signer for Twitter API v1.1/v2 without external dependencies. |
| `x_publisher.py` | X (Twitter) API v2 tweet creator & v1.1 multipart media uploader. |
| `instagram_publisher.py` | Instagram Graph API v20.0 2-step Container publisher (`/media` -> `/media_publish`). |
| `threads_publisher.py` | Meta Threads API v1.0 2-step Container publisher (`/threads` -> `/threads_publish`). |
| `facebook_publisher.py` | Meta Facebook Pages Graph API v20.0 feed & photo publisher (`/feed` & `/photos`). |
| `tiktok_publisher.py` | TikTok Content Posting API v2 uploader. |

---

## BasePublisher Interface

Every publisher inherits from `BasePublisher` in `base.py`:

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from publisher.base import PublishResult

class BasePublisher(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Returns normalized platform name, e.g. 'X (Twitter)', 'Instagram'."""
        pass

    @abstractmethod
    def publish(
        self,
        content: str,
        media_paths: Optional[List[str]] = None,
        custom_params: Optional[dict] = None
    ) -> PublishResult:
        """Publishes content and optional media to the platform."""
        pass

    @abstractmethod
    def validate_credentials(self) -> dict:
        """Validates API keys or tokens against the platform."""
        pass
```

### PublishResult Dataclass

```python
@dataclass
class PublishResult:
    success: bool
    platform: str
    account_name: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    message: str = ""
    simulated: bool = False
    raw_response: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
```

---

## Adding a New Platform Publisher

To add a new platform (e.g. LinkedIn, Pinterest, YouTube Community):

1. Create a new file in `publisher/` (e.g. `linkedin_publisher.py`).
2. Inherit from `BasePublisher`:
   ```python
   from publisher.base import BasePublisher, PublishResult

   class LinkedInPublisher(BasePublisher):
       @property
       def platform_name(self) -> str:
           return "LinkedIn"

       def publish(self, content: str, media_paths=None, custom_params=None) -> PublishResult:
           if not self.has_credentials:
               return self._simulate_publish(content, media_paths)
           # Execute live LinkedIn API request here...

       def validate_credentials(self) -> dict:
           # Validate LinkedIn access token...
   ```
3. Register the publisher in `publisher/manager.py`:
   - Import `LinkedInPublisher`.
   - Update `get_publisher_for_account()` and `normalize_platform_name()`.
