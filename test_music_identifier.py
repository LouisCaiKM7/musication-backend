"""
Test script for Music Identifier
Tests the acoustid music identification functionality.

Usage:
    python test_music_identifier.py path/to/audio.mp3
"""
import sys
import json
from services.music_identifier import identify_music

def test_identifier(audio_path: str):
    """Test the music identifier with a file."""
    print(f"Identifying music: {audio_path}\n")
    print("=" * 70)
    
    try:
        # Perform identification
        result = identify_music(audio_path, max_results=5)
        
        if result["success"]:
            print("✅ IDENTIFICATION SUCCESSFUL\n")
            print(f"Found {len(result['matches'])} match(es):\n")
            
            for i, match in enumerate(result["matches"], 1):
                print(f"{i}. {match['artist']} - {match['title']}")
                print(f"   Score: {match['score']}%")
                print(f"   MusicBrainz: {match['musicbrainz_url']}")
                print()
            
            return result
        else:
            print("❌ IDENTIFICATION FAILED")
            print(f"Error: {result['error']}\n")
            return None
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}\n")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_music_identifier.py <audio_file_path>")
        print("Example: python test_music_identifier.py pyacoustid/a.mp3")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    test_identifier(audio_path)
