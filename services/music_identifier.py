"""
Music Identification Service
Uses Acoustid/MusicBrainz to identify songs from audio fingerprints.
"""
import sys
import os
from typing import List, Dict, Optional

# Add parent directory to path to import pyacoustid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set FPCALC path if not already set
if 'FPCALC' not in os.environ:
    # Try different paths based on OS
    import platform
    
    if platform.system() == 'Windows':
        # Windows paths
        possible_paths = [
            r"C:\ProgramData\chocolatey\lib\chromaprint\tools\chromaprint-fpcalc-1.1-win-x86_64\fpcalc.exe",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pyacoustid', 'fpcalc.exe'),
        ]
    else:
        # Linux/Docker paths
        possible_paths = [
            '/usr/bin/fpcalc',
            '/usr/local/bin/fpcalc',
        ]
    
    fpcalc_found = False
    for fpcalc_path in possible_paths:
        if os.path.exists(fpcalc_path):
            os.environ['FPCALC'] = fpcalc_path
            print(f"✅ Using fpcalc from: {fpcalc_path}")
            fpcalc_found = True
            break
    
    if not fpcalc_found:
        print(f"⚠️ Warning: fpcalc not found in any expected location")
        print(f"   Searched: {possible_paths}")
else:
    print(f"✅ Using FPCALC from environment: {os.environ['FPCALC']}")

from pyacoustid import acoustid

# API key for AcoustID (demo key - replace with your own in production)
# Get your own API key at: http://acoustid.org/
API_KEY = 'cSpUJKpD'


class MusicIdentifier:
    """
    Identifies music tracks using audio fingerprinting.
    """
    
    def __init__(self, api_key: str = API_KEY):
        """
        Initialize the Music Identifier.
        
        Args:
            api_key: AcoustID API key
        """
        self.api_key = api_key
    
    def identify(self, audio_path: str, max_results: int = 5) -> Dict:
        """
        Identify a music track from its audio file.
        
        Args:
            audio_path: Path to the audio file
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing:
                - success: bool indicating if identification succeeded
                - matches: list of identified songs with metadata
                - error: error message if identification failed
        """
        if not os.path.exists(audio_path):
            return {
                "success": False,
                "matches": [],
                "error": f"Audio file not found: {audio_path}"
            }
        
        try:
            # Use acoustid.match to fingerprint and identify the audio
            results = acoustid.match(self.api_key, audio_path)
            
            matches = []
            count = 0
            
            for score, recording_id, title, artist in results:
                if count >= max_results:
                    break
                
                matches.append({
                    "score": round(score * 100, 2),  # Convert to percentage
                    "title": title or "Unknown",
                    "artist": artist or "Unknown",
                    "recording_id": recording_id,
                    "musicbrainz_url": f"http://musicbrainz.org/recording/{recording_id}"
                })
                count += 1
            
            if not matches:
                return {
                    "success": False,
                    "matches": [],
                    "error": "No matches found for this audio"
                }
            
            return {
                "success": True,
                "matches": matches,
                "error": None
            }
            
        except acoustid.NoBackendError:
            return {
                "success": False,
                "matches": [],
                "error": "Chromaprint library/tool not found. Please install chromaprint."
            }
        except acoustid.FingerprintGenerationError:
            return {
                "success": False,
                "matches": [],
                "error": "Could not generate fingerprint from audio file. File may be corrupted."
            }
        except acoustid.WebServiceError as e:
            return {
                "success": False,
                "matches": [],
                "error": f"Web service request failed: {e.message}"
            }
        except Exception as e:
            return {
                "success": False,
                "matches": [],
                "error": f"Unexpected error during identification: {str(e)}"
            }
    
    def get_best_match(self, audio_path: str) -> Optional[Dict]:
        """
        Get the best match for an audio file.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary with the best match or None if no match found
        """
        result = self.identify(audio_path, max_results=1)
        
        if result["success"] and result["matches"]:
            return result["matches"][0]
        
        return None


# Utility function for easy import
def identify_music(audio_path: str, api_key: str = API_KEY, max_results: int = 5) -> Dict:
    """
    Convenience function to identify music from an audio file.
    
    Args:
        audio_path: Path to audio file
        api_key: AcoustID API key
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing identification results
    """
    identifier = MusicIdentifier(api_key=api_key)
    return identifier.identify(audio_path, max_results=max_results)
