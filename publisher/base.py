from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import os


@dataclass
class PublishResult:
    platform: str
    account_name: str
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    message: str = ""
    simulated: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    raw_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BasePublisher(ABC):
    """
    Abstract base class for all social media platform publishers.
    Supports both real API calls (when credentials provided) and safe simulation mode.
    """

    def __init__(self, platform_name: str, account_name: str, credentials: Optional[Dict[str, Any]] = None):
        self.platform_name = platform_name
        self.account_name = account_name
        self.credentials = credentials or {}

    @abstractmethod
    def validate_credentials(self) -> Dict[str, Any]:
        """
        Validate whether the credentials are structurally complete and optionally live-check them.
        Returns a dict: {"valid": bool, "simulated": bool, "message": str}
        """
        pass

    @abstractmethod
    def publish(
        self,
        content: str,
        media_paths: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> PublishResult:
        """
        Publish content with optional media attachments.
        """
        pass

    def is_configured(self) -> bool:
        """
        Returns True if sufficient credentials are provided to make real API calls.
        """
        return False

    @staticmethod
    def _verify_media_exists(paths: Optional[List[str]]) -> List[str]:
        if not paths:
            return []
        valid = []
        for p in paths:
            if p and os.path.exists(p):
                valid.append(p)
        return valid

    @staticmethod
    def _mask_secret(value: Optional[str]) -> str:
        if not value:
            return ""
        if len(value) <= 6:
            return "******"
        return value[:3] + "..." + value[-3:]
