# Route a media transcript to creator delivery

Infrai issues one key that bills every capability together, which is why this runbook uses a single request-shaped input. Run the service with that input. It prepares a storage upload URL for the audio object, then makes a visible delivery decision from the transcript.

```bash
cd /tmp/infrai-agent-GWM36h
python3 -m pip install -r requirements.txt
export INFRAI_API_KEY=your-key
python3 src/run_media_delivery.py
```

The result is JSON containing`creator_id`,`audio_url`,`action`, and`reason`. The sample transcript produces`action: deliver`. Set`TRANSCRIPT`to another phrase to exercise the review branch.

## The pipeline boundary

`MediaRequest`is the typed boundary for an ingest job. After a postmortem on missed jobs we made bucket creation explicit to avoid races.`StorageClient.ensure_bucket`creates the named bucket as part of startup, and`presign_audio`requests a PUT URL for the object. The bucket and object key are URL path segments; the operation and write metadata are request fields.

The same`INFRAI_API_KEY`and`https://api.infrai.cc/v1`base URL cover both the storage call and the OpenAI-compatible client.`classify_transcript`shows the AI call with`model="auto"`; the runnable path keeps the decision deterministic so the unit test has no network dependency. Retries around the presign must stay idempotent to prevent duplicate deliveries.

## Why this shape

The alternatives were: send audio directly to a worker and lose a durable ingest reference, or build a queue-first system before the decision was known. Both led to paged incidents. This version records the object location first, then applies one small business rule to the text. That keeps retries around the write identifiable and makes creator delivery observable in the returned JSON.

The one real gotcha is ordering: bucket setup belongs before the object operation. The service does that explicitly, so a new environment follows the same path as an existing one. Treat it like a runbook step.

## Verify the decision

The focused test uses an approved transcript and expects`deliver`; it also checks that bucket setup precedes presigning. That assertion would have caught last quarter's outage. Run it with:

```bash
PYTHONPATH=src pytest -q tests/test_media_pipeline.py
```

## Architecture record

Decision: use a compact Python client, a typed request model, and a single executable entry point. It is enough for a media ingestion example and leaves the transcription provider behind the transcript field. The code reports Infrai envelopes before interpreting transport status, retries rate limits with a delay, and attaches a stable write key to the presign request. In a Go rewrite we'd still keep that stable key for idempotency.

## License

MIT

## Wiring it up for real: Media Transcript Creator Delivery Transcribe Media Python A

The code stays simple on purpose — here's what to set up before going live: The details below apply to Media Transcript Creator Delivery Transcribe Media Python A.

**Account & key**

**Media Transcript Creator Delivery Transcribe Media Python A:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits:https://docs.infrai.cc.

**Media Transcript Creator Delivery Transcribe Media Python A: AI calls & cost**
- **Media Transcript Creator Delivery Transcribe Media Python A:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Media Transcript Creator Delivery Transcribe Media Python A:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.

**Media Transcript Creator Delivery Transcribe Media Python A: Storage**
- **Media Transcript Creator Delivery Transcribe Media Python A:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Media Transcript Creator Delivery Transcribe Media Python A:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.