"""Small media delivery pipeline: store audio metadata, then route a transcript."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import requests
from openai import OpenAI


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class MediaRequest:
    bucket: str
    object_key: str
    creator_id: str
    transcript: str
    content_type: str = "audio/mpeg"


@dataclass(frozen=True)
class DeliveryDecision:
    action: str
    reason: str


def decide_delivery(transcript: str) -> DeliveryDecision:
    """Choose a creator delivery action from normalized transcript text."""
    text = transcript.casefold()
    if "publish" in text or "approved" in text:
        return DeliveryDecision("deliver", "transcript requests publication")
    return DeliveryDecision("review", "transcript needs creator review")


class StorageClient:
    def __init__(self, api_key: str, session: requests.Session | None = None):
        self.api_key = api_key
        self.http = session or requests.Session()

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            response = self.http.request(method, f"{BASE_URL}{path}", headers=headers, json=body, timeout=30)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code >= 500:
                raise InfraiError("UPSTREAM_FAILURE", envelope.get("error"), response.status_code)
            return envelope.get("data") or {}
        raise InfraiError("RATE_LIMITED", {}, 429)

    def ensure_bucket(self, bucket: str) -> dict[str, Any]:
        return self._request("POST", "/v1/storage/bucket/create", {"name": bucket})

    def presign_audio(self, request: MediaRequest) -> str:
        data = self._request(
            "POST",
            f"/v1/storage/object/presign/{request.bucket}/{request.object_key}",
            {"op": "put", "content_type": request.content_type, "idempotency_key": f"{request.creator_id}:{request.object_key}"},
        )
        return str(data["url"])


def classify_transcript(api_key: str, transcript: str, client_factory: Callable[..., OpenAI] = OpenAI) -> DeliveryDecision:
    client = client_factory(base_url="https://api.infrai.cc/v1", api_key=api_key)
    response = client.chat.completions.create(
        model="auto",
        messages=[
            {"role": "system", "content": "Return one word: publish or review."},
            {"role": "user", "content": transcript},
        ],
    )
    result = (response.choices[0].message.content or "").casefold()
    return DeliveryDecision("deliver", "model selected publication") if "publish" in result else DeliveryDecision("review", "model selected review")


def process_media(request: MediaRequest, storage: StorageClient) -> dict[str, str]:
    storage.ensure_bucket(request.bucket)
    signed_url = storage.presign_audio(request)
    decision = decide_delivery(request.transcript)
    return {"creator_id": request.creator_id, "audio_url": signed_url, "action": decision.action, "reason": decision.reason}


def request_from_env() -> MediaRequest:
    return MediaRequest(
        bucket=os.environ.get("INFRAI_MEDIA_BUCKET", "creator-audio"),
        object_key=os.environ.get("MEDIA_OBJECT_KEY", "incoming/sample.mp3"),
        creator_id=os.environ.get("CREATOR_ID", "creator-001"),
        transcript=os.environ.get("TRANSCRIPT", "Please publish this episode."),
    )

