from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from livekit.api import AccessToken, VideoGrants
from datetime import timedelta
import json, os, uuid
app = Flask(__name__, static_folder="public", static_url_path="")
CORS(app)

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
                               
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.get("/token")
def get_token():
    lang = request.args.get("lang", "en")
    region = request.args.get("region", "usa")

    room_name = request.args.get("room") or f"hala-{uuid.uuid4().hex[:8]}"
    identity = f"user-{uuid.uuid4().hex[:8]}"

    metadata = {
        "lang": lang,
        "region": region
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
        "wsUrl": os.getenv("LIVEKIT_URL"),
        "room": room_name,
        "lang": lang,
        "region": region
    })

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = int(os.getenv("PORT", 3000)), debug = False)