import base64
import hashlib
import hmac
import time
import urllib.parse
import uuid
from typing import Dict, Optional


def rfc3986_quote(text: str) -> str:
    """RFC 5849 / RFC 3986 percent encoding for OAuth 1.0a."""
    return urllib.parse.quote(str(text), safe="~-._")


def generate_oauth1_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_token_secret: str,
    extra_params: Optional[Dict[str, str]] = None,
) -> str:
    """
    Generate an OAuth 1.0a Authorization header string using HMAC-SHA1.
    """
    parsed_url = urllib.parse.urlsplit(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

    oauth_params: Dict[str, str] = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    # Collect query parameters if any
    all_params: Dict[str, str] = {}
    if parsed_url.query:
        query_pairs = urllib.parse.parse_qsl(parsed_url.query, keep_blank_values=True)
        for k, v in query_pairs:
            all_params[k] = v

    if extra_params:
        all_params.update(extra_params)

    all_params.update(oauth_params)

    # Sort lexicographically by encoded key then encoded value
    sorted_encoded = sorted(
        (rfc3986_quote(k), rfc3986_quote(v)) for k, v in all_params.items()
    )
    param_string = "&".join(f"{k}={v}" for k, v in sorted_encoded)

    # Construct signature base string
    signature_base = (
        f"{method.upper()}&{rfc3986_quote(base_url)}&{rfc3986_quote(param_string)}"
    )

    # Construct signing key
    signing_key = f"{rfc3986_quote(consumer_secret)}&{rfc3986_quote(access_token_secret)}"

    # Generate HMAC-SHA1 signature
    hashed = hmac.new(
        signing_key.encode("utf-8"),
        signature_base.encode("utf-8"),
        hashlib.sha1,
    )
    oauth_signature = base64.b64encode(hashed.digest()).decode("utf-8")
    oauth_params["oauth_signature"] = oauth_signature

    header_parts = [
        f'{rfc3986_quote(k)}="{rfc3986_quote(v)}"'
        for k, v in sorted(oauth_params.items())
    ]
    return f"OAuth {', '.join(header_parts)}"
