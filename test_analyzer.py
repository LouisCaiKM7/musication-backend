"""
Test script for AudioAnalyzer
Run this to test the audio analysis functionality.

Usage:
    python test_analyzer.py path/to/audio.mp3
"""
import sys
import json
from services.audio_analyzer import AudioAnalyzer

def test_analyzer(audio_path: str):
    """Test the audio analyzer with a file."""
    print(f"Analyzing: {audio_path}\n")
    
    try:
        analyzer = AudioAnalyzer(sample_rate=22050, n_mfcc=13)
        
        # Test basic info
        print("=" * 50)
        print("BASIC AUDIO INFO")
        print("=" * 50)
        info = analyzer.get_audio_info(audio_path)
        print(json.dumps(info, indent=2))
        
        # Test full feature extraction
        print("\n" + "=" * 50)
        print("FULL FEATURE EXTRACTION")
        print("=" * 50)
        features = analyzer.extract_all_features(audio_path)
        
        # Print summary (not full arrays)
        summary = {
            "duration": features["duration"],
            "sample_rate": features["sample_rate"],
            "tempo": features["tempo"],
            "n_beats": features["n_beats"],
            "spectral_centroid_mean": features["spectral_centroid_mean"],
            "rms_mean": features["rms_mean"],
            "fingerprint_size": len(features["fingerprint"]),
            "mfcc_shape": f"{len(features['mfcc_mean'])} x {len(features['mfcc_full'][0])}",
            "chroma_shape": f"{len(features['chroma_mean'])} x {len(features['chroma_full'][0])}"
        }
        print(json.dumps(summary, indent=2))
        
        print("\n✅ Analysis completed successfully!")
        print(f"Fingerprint extracted: {len(features['fingerprint'])} features")
        
        return features
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_analyzer.py <audio_file_path>")
        print("Example: python test_analyzer.py uploads/test.mp3")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    test_analyzer(audio_path)
