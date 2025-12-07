import os
import uuid
import hashlib
import json
from datetime import datetime
from flask import Flask, jsonify, send_from_directory, request
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Set FPCALC path before importing music_identifier
if 'FPCALC' not in os.environ:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fpcalc_path = os.path.join(base_dir, 'pyacoustid', 'fpcalc.exe')
    if os.path.exists(fpcalc_path):
        os.environ['FPCALC'] = fpcalc_path
        print(f"[APP] Set FPCALC path: {fpcalc_path}")

from flask_cors import CORS
from config import settings
from database import engine, SessionLocal
from models import Base, Track, Analysis, Artifact
from services.music_identifier import identify_music
from services.audio_analyzer import AudioAnalyzer

app = Flask(__name__)

# CORS configuration - allow localhost for dev and Netlify for production
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
# Add production frontend URL from environment if available
if os.getenv("FRONTEND_URL"):
    allowed_origins.append(os.getenv("FRONTEND_URL"))

CORS(app, resources={r"/*": {"origins": allowed_origins if settings.flask_env == "production" else "*"}})

# Ensure upload dir exists
os.makedirs(settings.upload_dir, exist_ok=True)

# Initialize database schema (for bootstrap; later we can switch to Alembic)
with engine.begin() as conn:
    Base.metadata.create_all(bind=conn)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/library/stats")
def library_stats():
    db = SessionLocal()
    try:
        total_tracks = db.query(Track).count()
        # For now, return simple stats. Later we can add genre/artist extraction
        return jsonify({
            "totalTracks": total_tracks,
            "genres": [],  # Placeholder until we add genre metadata
            "artists": 0   # Placeholder until we add artist metadata
        })
    finally:
        db.close()


@app.get("/media/<path:filename>")
def serve_media(filename: str):
    return send_from_directory(settings.upload_dir, filename)


def _track_to_dict(t: Track, include_children: bool = False):
    base = {
        "id": str(t.id),
        "title": t.title,
        "audio_url": t.audio_url,
        "uploaded_at": t.uploaded_at.isoformat() if t.uploaded_at else None,
        "duration_seconds": t.duration_seconds,
        "sample_rate": t.sample_rate,
    }
    if not include_children:
        return base
    analyses = []
    for a in t.analyses:
        artifacts = []
        for r in a.artifacts:
            artifacts.append({
                "id": str(r.id),
                "artifact_type": r.artifact_type,
                "content_type": r.content_type,
                "data_json": r.data_json,
                "data_url": r.data_url,
            })
        analyses.append({
            "id": str(a.id),
            "method": a.method,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "summary": a.summary,
            "artifacts": artifacts,
        })
    base["analyses"] = analyses
    return base


@app.post("/tracks")
def create_track():
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    title = request.form.get("title") or file.filename
    original_name = secure_filename(file.filename)
    ext = os.path.splitext(original_name)[1]
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}{ext}"
    stored_path = os.path.join(settings.upload_dir, stored_name)

    sha256 = hashlib.sha256()
    with open(stored_path, "wb") as f:
        chunk = file.stream.read(8192)
        while chunk:
            sha256.update(chunk)
            f.write(chunk)
            chunk = file.stream.read(8192)
    checksum = sha256.hexdigest()

    audio_url = f"{settings.base_url.rstrip('/')}/media/{stored_name}"

    db = SessionLocal()
    try:
        existing = db.query(Track).filter(Track.checksum_sha256 == checksum).first()
        if existing:
            try:
                os.remove(stored_path)
            except Exception:
                pass
            return jsonify({"track": _track_to_dict(existing)}), 200

        track = Track(
            title=title,
            audio_url=audio_url,
            audio_blob=None,
            duration_seconds=None,
            sample_rate=None,
            checksum_sha256=checksum,
        )
        db.add(track)
        db.commit()
        db.refresh(track)
        return jsonify({"track": _track_to_dict(track)}), 201
    finally:
        db.close()


@app.get("/tracks")
def list_tracks():
    db = SessionLocal()
    try:
        rows = db.query(Track).order_by(Track.uploaded_at.desc()).limit(100).all()
        return jsonify({"tracks": [_track_to_dict(t) for t in rows]})
    finally:
        db.close()


@app.get("/tracks/<uuid:track_id>")
def get_track(track_id):
    db = SessionLocal()
    try:
        t = db.query(Track).filter(Track.id == track_id).first()
        if not t:
            return jsonify({"error": "not found"}), 404
        return jsonify({"track": _track_to_dict(t, include_children=True)})
    finally:
        db.close()


@app.delete("/tracks/<uuid:track_id>")
def delete_track(track_id):
    db = SessionLocal()
    try:
        t = db.query(Track).filter(Track.id == track_id).first()
        if not t:
            return jsonify({"error": "not found"}), 404
        
        # Extract filename from audio_url to delete physical file
        if t.audio_url:
            try:
                filename = t.audio_url.split('/media/')[-1]
                file_path = os.path.join(settings.upload_dir, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                # Log but don't fail if file deletion fails
                print(f"Failed to delete file: {e}")
        
        db.delete(t)
        db.commit()
        return jsonify({"message": "deleted"}), 200
    finally:
        db.close()


@app.post("/tracks/<uuid:track_id>/analyze")
def analyze_track(track_id):
    """
    Trigger music identification analysis for a track.
    Uses Acoustid/MusicBrainz to identify the song.
    """
    db = SessionLocal()
    try:
        track = db.query(Track).filter(Track.id == track_id).first()
        if not track:
            return jsonify({"error": "track not found"}), 404
        
        # Create Analysis record with processing status
        analysis = Analysis(
            track_id=track_id,
            method="music_identification",
            status="processing",
            summary="Identifying music..."
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Extract local file path from audio_url
        try:
            filename = track.audio_url.split('/media/')[-1]
            audio_path = os.path.join(settings.upload_dir, filename)
            
            if not os.path.exists(audio_path):
                analysis.status = "failed"
                analysis.summary = "Audio file not found on server"
                db.commit()
                return jsonify({"error": "audio file not found"}), 404
            
            # Perform music identification
            print(f"Identifying music for track: {track.title}")
            result = identify_music(audio_path, max_results=5)
            
            if result["success"]:
                # Save identification results
                analysis.status = "completed"
                analysis.completed_at = datetime.utcnow()
                
                # Create summary
                if result["matches"]:
                    best_match = result["matches"][0]
                    analysis.summary = f"Identified as: {best_match['artist']} - {best_match['title']} ({best_match['score']}% match)"
                else:
                    analysis.summary = "No matches found for this audio"
                
                # Save matches as artifacts (even if empty)
                artifact = Artifact(
                    analysis_id=analysis.id,
                    artifact_type="music_matches",
                    content_type="application/json",
                    data_json=result["matches"]
                )
                db.add(artifact)
                
                db.commit()
                db.refresh(analysis)
                
                return jsonify({
                    "message": "Analysis completed successfully",
                    "analysis": {
                        "id": str(analysis.id),
                        "track_id": str(track_id),
                        "status": analysis.status,
                        "summary": analysis.summary,
                        "matches": result["matches"],
                        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None
                    }
                }), 200
            else:
                # Identification failed
                analysis.status = "failed"
                analysis.summary = result["error"]
                db.commit()
                
                return jsonify({
                    "message": "Analysis failed",
                    "analysis": {
                        "id": str(analysis.id),
                        "track_id": str(track_id),
                        "status": analysis.status,
                        "summary": analysis.summary,
                        "error": result["error"]
                    }
                }), 200
                
        except Exception as e:
            analysis.status = "failed"
            analysis.summary = f"Error during analysis: {str(e)}"
            db.commit()
            print(f"Analysis error: {str(e)}")
            
            return jsonify({
                "error": "Analysis failed",
                "message": str(e)
            }), 500
    finally:
        db.close()


if __name__ == "__main__":
    # Use PORT from environment (Render sets this) or fall back to settings
    port = int(os.environ.get("PORT", settings.port))
    app.run(host="0.0.0.0", port=port, debug=(settings.flask_env == "development"))
