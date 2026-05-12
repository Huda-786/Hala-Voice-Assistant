from flask import Flask, jsonify, request
from flask_cors import CORS
from livekit.api import AccessToken, VideoGrants
from datetime import timedelta
import json, os
app = Flask(__name__)
CORS(app)

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
                               
# ROOM_NAME = "test-room"

@app.get("/token")
def get_token():
    room_name = request.args.get("room", "hala-default")
    lang = request.args.get("lang", "en")
    region = request.args.get("region", "usa")
    mode = request.args.get("mode", "reception")

    identity = f"user-{lang}-{region}-{mode}"

    metadata = {
        "lang": lang,
        "region": region,
        "mode": mode
    }

    token = (
        AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(f"User {lang}")
        .with_metadata(json.dumps(metadata))
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
        .with_ttl(timedelta(hours=10))
        .to_jwt()
    )

    return jsonify({
        "token": token,
        "wsUrl": "wss://voiceassistant-yuxi3myt.livekit.cloud",
        "room": room_name,
        "lang": lang,
        "region": region,
        "mode": mode
    })

if __name__ == "__main__":
    app.run(port=5000, debug=True)