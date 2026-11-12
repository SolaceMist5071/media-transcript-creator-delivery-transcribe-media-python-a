import json
import os

from media_pipeline import StorageClient, process_media, request_from_env


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    result = process_media(request_from_env(), StorageClient(api_key))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

