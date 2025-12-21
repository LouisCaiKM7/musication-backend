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
from services.similarity_comparator import SimilarityComparator
from services.visualization_generator import VisualizationGenerator

app = Flask(__name__)

# Global progress tracking (in production, use Redis or similar)
progress_store = {}

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
def serve_media(filename):
    """
    Serve audio files from database blob storage.
    """
    # Extract UUID from filename
    file_id = os.path.splitext(filename)[0]
    
    db = SessionLocal()
    try:
        # Find track by audio_url pattern
        track = db.query(Track).filter(Track.audio_url.like(f"%{file_id}%")).first()
        if not track or not track.audio_blob:
            return jsonify({"error": "File not found"}), 404
        
        from flask import Response
        # Determine content type based on extension
        ext = os.path.splitext(filename)[1].lower()
        content_type = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',
            '.flac': 'audio/flac'
        }.get(ext, 'application/octet-stream')
        
        return Response(track.audio_blob, mimetype=content_type)
    finally:
        db.close()


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

    # Read entire file into memory and compute checksum
    file_data = file.read()
    sha256 = hashlib.sha256(file_data)
    checksum = sha256.hexdigest()

    # Generate audio URL for database-stored blob
    audio_url = f"{settings.base_url.rstrip('/')}/media/{file_id}{ext}"

    db = SessionLocal()
    try:
        existing = db.query(Track).filter(Track.checksum_sha256 == checksum).first()
        if existing:
            return jsonify({"track": _track_to_dict(existing)}), 200

        # Store audio in database blob instead of filesystem
        track = Track(
            title=title,
            audio_url=audio_url,
            audio_blob=file_data,
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
        
        # No need to remove files - stored in database
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
        
        # Create temporary file from audio blob
        import tempfile
        temp_file = None
        try:
            if not track.audio_blob:
                analysis.status = "failed"
                analysis.summary = "Audio data not found"
                db.commit()
                return jsonify({"error": "audio data not found"}), 404
            
            # Write blob to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.write(track.audio_blob)
            temp_file.close()
            audio_path = temp_file.name
            
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
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except Exception as cleanup_error:
                    print(f"Error cleaning up temp file: {cleanup_error}")
    finally:
        db.close()


@app.post("/tracks/<uuid:track_id>/compare/<uuid:compare_track_id>")
def compare_tracks(track_id, compare_track_id):
    """
    Compare two tracks for melody and harmony similarity.
    Performs comprehensive plagiarism detection analysis.
    Returns analysis_id immediately and processes in background.
    """
    db = SessionLocal()
    try:
        # Get both tracks
        track1 = db.query(Track).filter(Track.id == track_id).first()
        track2 = db.query(Track).filter(Track.id == compare_track_id).first()
        
        if not track1:
            return jsonify({"error": "Track 1 not found"}), 404
        if not track2:
            return jsonify({"error": "Track 2 not found"}), 404
        
        # Create Analysis record
        analysis = Analysis(
            track_id=track_id,
            method="similarity_comparison",
            status="processing",
            summary={"message": "Comparing tracks for similarity..."}
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        analysis_id = analysis.id
        
        # Initialize progress tracking
        progress_key = str(analysis_id)
        progress_store[progress_key] = {
            "status": "processing",
            "progress": 5,
            "message": "Starting comparison..."
        }
        
        # Start background processing
        import threading
        thread = threading.Thread(
            target=_process_comparison_async,
            args=(str(track_id), str(compare_track_id), str(analysis_id), 
                  track1.title, track2.title, track1.audio_blob, track2.audio_blob)
        )
        thread.daemon = True
        thread.start()
        
        # Return immediately with analysis_id
        return jsonify({
            "analysis_id": str(analysis_id),
            "status": "processing",
            "message": "Comparison started"
        }), 202
        
    except Exception as e:
        print(f"Error starting comparison: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


def _process_comparison_async(track_id, compare_track_id, analysis_id, 
                               track1_title, track2_title, audio_blob1, audio_blob2):
    """
    Background task for processing track comparison.
    """
    import tempfile
    db = SessionLocal()
    progress_key = analysis_id
    temp_files = []
    
    try:
        # Get analysis object
        from uuid import UUID
        analysis = db.query(Analysis).filter(Analysis.id == UUID(analysis_id)).first()
        if not analysis:
            print(f"Analysis {analysis_id} not found")
            return
        
        progress_store[progress_key] = {
            "status": "processing",
            "progress": 10,
            "message": f"Extracting features from {track1_title}..."
        }
        
        # Write audio blobs to temporary files for processing
        temp_file1 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file1.write(audio_blob1)
        temp_file1.close()
        audio_path1 = temp_file1.name
        temp_files.append(audio_path1)
        
        temp_file2 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file2.write(audio_blob2)
        temp_file2.close()
        audio_path2 = temp_file2.name
        temp_files.append(audio_path2)
        
        if not os.path.exists(audio_path1):
            analysis.status = "failed"
            analysis.summary = {"error": "Failed to create temporary file for Track 1"}
            db.commit()
            progress_store[progress_key] = {
                "status": "failed",
                "progress": 0,
                "message": "Track 1 audio file not found"
            }
            return
        
        if not os.path.exists(audio_path2):
            analysis.status = "failed"
            analysis.summary = {"error": "Track 2 audio file not found on server"}
            db.commit()
            progress_store[progress_key] = {
                "status": "failed",
                "progress": 0,
                "message": "Track 2 audio file not found"
            }
            return
        
        # Perform comparison with progress updates
        print(f"[ASYNC] Comparing tracks: {track1_title} vs {track2_title}")
        
        progress_store[progress_key] = {
            "status": "processing",
            "progress": 20,
            "message": f"Loading audio files..."
        }
        
        print(f"[ASYNC] Creating comparator...")
        comparator = SimilarityComparator(sample_rate=22050)
        
        print(f"[ASYNC] Extracting features from track 1: {audio_path1}")
        progress_store[progress_key] = {
            "status": "processing",
            "progress": 30,
            "message": f"Analyzing {track1_title}..."
        }
        
        print(f"[ASYNC] Extracting features from track 2: {audio_path2}")
        progress_store[progress_key] = {
            "status": "processing",
            "progress": 50,
            "message": f"Analyzing {track2_title}..."
        }
        
        print(f"[ASYNC] Starting comparison computation...")
        comparison_result = comparator.compare_tracks(
            audio_path1, audio_path2,
            track1_title=track1_title or "Track 1",
            track2_title=track2_title or "Track 2"
        )
        print(f"[ASYNC] Comparison computation complete!")
        
        progress_store[progress_key] = {
            "status": "processing",
            "progress": 70,
            "message": "Computing similarity scores..."
        }
        
        # Generate visualizations
        print("Generating visualizations...")
        progress_store[progress_key] = {
            "status": "processing",
            "progress": 80,
            "message": "Generating visualizations..."
        }
        
        viz_generator = VisualizationGenerator()
        visualizations = viz_generator.generate_all_visualizations(comparison_result)
        
        progress_store[progress_key] = {
            "status": "processing",
            "progress": 90,
            "message": "Saving results..."
        }
        
        # Save visualizations as artifacts
        for viz_name, viz_data in visualizations.items():
            artifact = Artifact(
                analysis_id=UUID(analysis_id),
                artifact_type=viz_name,
                content_type="image/png",
                data_blob=viz_data['bytes']
            )
            db.add(artifact)
        
        # Save comparison results as JSON artifact
        results_artifact = Artifact(
            analysis_id=UUID(analysis_id),
            artifact_type="similarity_report",
            content_type="application/json",
            data_json={
                "overall_similarity": comparison_result['overall_similarity'],
                "chroma_analysis": comparison_result['chroma_analysis'],
                "melody_analysis": comparison_result['melody_analysis'],
                "tempo_analysis": comparison_result['tempo_analysis'],
                "similar_segments": comparison_result['similar_segments'],
                "summary_text": comparison_result['summary']
            }
        )
        db.add(results_artifact)
        
        # Update analysis status
        analysis.status = "completed"
        analysis.completed_at = datetime.utcnow()
        analysis.summary = comparison_result['overall_similarity']
        db.commit()
        
        # Mark progress as complete
        progress_store[progress_key] = {
            "status": "completed",
            "progress": 100,
            "message": "Comparison complete!"
        }
        
        print(f"Comparison completed. Similarity: {comparison_result['overall_similarity']['similarity_percentage']:.1f}%")
        
    except Exception as e:
        print(f"Comparison error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        try:
            analysis.status = "failed"
            analysis.summary = {"error": f"Error during comparison: {str(e)}"}
            db.commit()
        except:
            pass
        
        # Mark progress as failed
        progress_store[progress_key] = {
            "status": "failed",
            "progress": 0,
            "message": f"Error: {str(e)}"
        }
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as cleanup_error:
                print(f"Error cleaning up temp file {temp_file}: {cleanup_error}")
        db.close()


@app.get("/analyses/<uuid:analysis_id>")
def get_analysis(analysis_id):
    """
    Get complete analysis details with all artifacts.
    """
    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404
        
        # Build artifacts list
        artifacts = []
        for artifact in analysis.artifacts:
            artifact_data = {
                "id": str(artifact.id),
                "artifact_type": artifact.artifact_type,
                "content_type": artifact.content_type,
                "data_json": artifact.data_json
            }
            if artifact.data_url:
                artifact_data["data_url"] = artifact.data_url
            
            # Include base64 for images
            if artifact.data_blob and artifact.content_type == "image/png":
                import base64
                artifact_data["base64"] = base64.b64encode(artifact.data_blob).decode('utf-8')
            
            artifacts.append(artifact_data)
        
        return jsonify({
            "analysis": {
                "id": str(analysis.id),
                "track_id": str(analysis.track_id),
                "method": analysis.method,
                "status": analysis.status,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                "summary": analysis.summary,
                "artifacts": artifacts
            }
        }), 200
    finally:
        db.close()


@app.get("/analyses/<uuid:analysis_id>/progress")
def get_analysis_progress(analysis_id):
    """
    Get the current progress of an analysis/comparison.
    """
    progress_key = str(analysis_id)
    if progress_key in progress_store:
        return jsonify(progress_store[progress_key]), 200
    else:
        # Check if analysis exists and is completed
        db = SessionLocal()
        try:
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if not analysis:
                return jsonify({"error": "Analysis not found"}), 404
            
            if analysis.status == "completed":
                return jsonify({
                    "status": "completed",
                    "progress": 100,
                    "message": "Comparison complete!"
                }), 200
            elif analysis.status == "failed":
                return jsonify({
                    "status": "failed",
                    "progress": 0,
                    "message": "Analysis failed"
                }), 200
            else:
                return jsonify({
                    "status": "processing",
                    "progress": 0,
                    "message": "Processing..."
                }), 200
        finally:
            db.close()


@app.get("/analyses/<uuid:analysis_id>/visualizations/<artifact_type>")
def get_visualization(analysis_id, artifact_type):
    """
    Retrieve a specific visualization image from an analysis.
    """
    db = SessionLocal()
    try:
        artifact = db.query(Artifact).filter(
            Artifact.analysis_id == analysis_id,
            Artifact.artifact_type == artifact_type
        ).first()
        
        if not artifact:
            return jsonify({"error": "Visualization not found"}), 404
        
        if artifact.data_blob:
            from flask import Response
            return Response(artifact.data_blob, mimetype='image/png')
        else:
            return jsonify({"error": "No image data available"}), 404
    finally:
        db.close()


@app.route("/admin/fix-database-constraint", methods=["GET", "POST"])
def fix_database_constraint():
    """
    Temporary endpoint to update the database constraint.
    DELETE THIS AFTER RUNNING ONCE!
    """
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            # Drop old constraint
            conn.execute(text("""
                ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_method_check;
            """))
            
            # Add updated constraint
            conn.execute(text("""
                ALTER TABLE analyses ADD CONSTRAINT analyses_method_check 
                CHECK (method IN (
                    'chromaprint','hpcp','dtw','lyrics','music_identification',
                    'similarity_detection','melody_similarity','cover_detection',
                    'similarity_comparison','other'
                ));
            """))
            
            # Verify
            result = conn.execute(text("""
                SELECT pg_get_constraintdef(oid) 
                FROM pg_constraint 
                WHERE conname = 'analyses_method_check';
            """))
            constraint_def = result.fetchone()
        
        return jsonify({
            "status": "success",
            "message": "Database constraint updated successfully",
            "constraint": constraint_def[0] if constraint_def else None
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    # Use PORT from environment (Render sets this) or fall back to settings
    port = int(os.environ.get("PORT", settings.port))
    app.run(host="0.0.0.0", port=port, debug=(settings.flask_env != "production"))
