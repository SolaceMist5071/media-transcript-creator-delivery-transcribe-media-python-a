from media_pipeline import MediaRequest, decide_delivery, process_media


class RecordingStorage:
    def __init__(self):
        self.calls = []

    def ensure_bucket(self, bucket):
        self.calls.append(("ensure_bucket", bucket))

    def presign_audio(self, request):
        self.calls.append(("presign_audio", request.object_key))
        return "https://upload.example/audio"


def test_approved_transcript_delivers_after_storage_is_ready():
    request = MediaRequest("creator-audio", "episodes/42.mp3", "c-42", "Approved: publish this episode.")
    storage = RecordingStorage()

    result = process_media(request, storage)

    assert result["action"] == "deliver"
    assert result["creator_id"] == "c-42"
    assert storage.calls == [("ensure_bucket", "creator-audio"), ("presign_audio", "episodes/42.mp3")]


def test_unapproved_text_stays_in_review():
    assert decide_delivery("Discuss the cut with the creator.").action == "review"

