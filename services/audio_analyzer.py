"""
Audio Analysis Service
Extracts audio features for similarity detection and plagiarism analysis.
"""
import os
import numpy as np
import librosa
import librosa.display
from typing import Dict, Optional, Tuple
from pydub import AudioSegment
import warnings

warnings.filterwarnings('ignore')


class AudioAnalyzer:
    """
    Analyzes audio files and extracts features for similarity detection.
    """
    
    def __init__(self, sample_rate: int = 22050, n_mfcc: int = 13):
        """
        Initialize the AudioAnalyzer.
        
        Args:
            sample_rate: Target sample rate for audio processing
            n_mfcc: Number of MFCC coefficients to extract
        """
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.hop_length = 512
        self.n_fft = 2048
    
    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file and convert to mono at target sample rate.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            Exception: If audio loading fails
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # Load audio with librosa (automatically converts to mono)
            y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
            return y, sr
        except Exception as e:
            raise Exception(f"Failed to load audio: {str(e)}")
    
    def normalize_audio(self, y: np.ndarray) -> np.ndarray:
        """
        Normalize audio to [-1, 1] range.
        
        Args:
            y: Audio time series
            
        Returns:
            Normalized audio
        """
        if np.max(np.abs(y)) == 0:
            return y
        return y / np.max(np.abs(y))
    
    def extract_mfcc(self, y: np.ndarray, sr: int) -> np.ndarray:
        """
        Extract Mel-frequency cepstral coefficients (MFCCs).
        Captures timbral texture of audio.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            MFCC features (n_mfcc x time_frames)
        """
        mfcc = librosa.feature.mfcc(
            y=y, 
            sr=sr, 
            n_mfcc=self.n_mfcc,
            hop_length=self.hop_length,
            n_fft=self.n_fft
        )
        return mfcc
    
    def extract_chroma(self, y: np.ndarray, sr: int) -> np.ndarray:
        """
        Extract chroma features (pitch class profile).
        Captures harmonic and melodic characteristics.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Chroma features (12 x time_frames)
        """
        chroma = librosa.feature.chroma_stft(
            y=y,
            sr=sr,
            hop_length=self.hop_length,
            n_fft=self.n_fft
        )
        return chroma
    
    def extract_spectral_features(self, y: np.ndarray, sr: int) -> Dict[str, np.ndarray]:
        """
        Extract spectral features (centroid, rolloff, bandwidth).
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Dictionary of spectral features
        """
        spectral_centroids = librosa.feature.spectral_centroid(
            y=y, sr=sr, hop_length=self.hop_length
        )[0]
        
        spectral_rolloff = librosa.feature.spectral_rolloff(
            y=y, sr=sr, hop_length=self.hop_length
        )[0]
        
        spectral_bandwidth = librosa.feature.spectral_bandwidth(
            y=y, sr=sr, hop_length=self.hop_length
        )[0]
        
        zero_crossing_rate = librosa.feature.zero_crossing_rate(
            y, hop_length=self.hop_length
        )[0]
        
        return {
            "spectral_centroid": spectral_centroids,
            "spectral_rolloff": spectral_rolloff,
            "spectral_bandwidth": spectral_bandwidth,
            "zero_crossing_rate": zero_crossing_rate
        }
    
    def extract_tempo(self, y: np.ndarray, sr: int) -> Tuple[float, np.ndarray]:
        """
        Extract tempo (BPM) and beat frames.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Tuple of (tempo, beat_frames)
        """
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        # tempo is returned as numpy array in newer versions
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo)
        return tempo, beat_frames
    
    def extract_rms_energy(self, y: np.ndarray) -> np.ndarray:
        """
        Extract RMS (Root Mean Square) energy.
        Represents loudness over time.
        
        Args:
            y: Audio time series
            
        Returns:
            RMS energy values
        """
        rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
        return rms
    
    def compute_fingerprint(self, y: np.ndarray, sr: int) -> np.ndarray:
        """
        Compute a compact audio fingerprint for fast similarity matching.
        Uses averaged MFCC and chroma features.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Feature vector (fingerprint)
        """
        # Extract features
        mfcc = self.extract_mfcc(y, sr)
        chroma = self.extract_chroma(y, sr)
        
        # Compute statistics (mean and std) across time
        mfcc_mean = np.mean(mfcc, axis=1)
        mfcc_std = np.std(mfcc, axis=1)
        chroma_mean = np.mean(chroma, axis=1)
        chroma_std = np.std(chroma, axis=1)
        
        # Concatenate into single feature vector
        fingerprint = np.concatenate([
            mfcc_mean,
            mfcc_std,
            chroma_mean,
            chroma_std
        ])
        
        return fingerprint
    
    def extract_all_features(self, audio_path: str) -> Dict:
        """
        Extract comprehensive audio features from file.
        This is the main method to call for full analysis.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary containing all extracted features
            
        Raises:
            Exception: If feature extraction fails
        """
        try:
            # Load audio
            y, sr = self.load_audio(audio_path)
            y = self.normalize_audio(y)
            
            # Get audio duration
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Extract all features
            mfcc = self.extract_mfcc(y, sr)
            chroma = self.extract_chroma(y, sr)
            spectral_features = self.extract_spectral_features(y, sr)
            tempo, beat_frames = self.extract_tempo(y, sr)
            rms = self.extract_rms_energy(y)
            fingerprint = self.compute_fingerprint(y, sr)
            
            # Compute feature statistics
            features = {
                "duration": float(duration),
                "sample_rate": int(sr),
                "tempo": float(tempo),
                "n_beats": int(len(beat_frames)),
                
                # MFCC statistics
                "mfcc_mean": mfcc.mean(axis=1).tolist(),
                "mfcc_std": mfcc.std(axis=1).tolist(),
                "mfcc_min": mfcc.min(axis=1).tolist(),
                "mfcc_max": mfcc.max(axis=1).tolist(),
                
                # Chroma statistics
                "chroma_mean": chroma.mean(axis=1).tolist(),
                "chroma_std": chroma.std(axis=1).tolist(),
                
                # Spectral feature statistics
                "spectral_centroid_mean": float(spectral_features["spectral_centroid"].mean()),
                "spectral_centroid_std": float(spectral_features["spectral_centroid"].std()),
                "spectral_rolloff_mean": float(spectral_features["spectral_rolloff"].mean()),
                "spectral_rolloff_std": float(spectral_features["spectral_rolloff"].std()),
                "spectral_bandwidth_mean": float(spectral_features["spectral_bandwidth"].mean()),
                "spectral_bandwidth_std": float(spectral_features["spectral_bandwidth"].std()),
                "zero_crossing_rate_mean": float(spectral_features["zero_crossing_rate"].mean()),
                "zero_crossing_rate_std": float(spectral_features["zero_crossing_rate"].std()),
                
                # Energy statistics
                "rms_mean": float(rms.mean()),
                "rms_std": float(rms.std()),
                
                # Compact fingerprint for fast matching
                "fingerprint": fingerprint.tolist(),
                
                # Raw time-series features (for detailed comparison)
                "mfcc_full": mfcc.tolist(),
                "chroma_full": chroma.tolist(),
            }
            
            return features
            
        except Exception as e:
            raise Exception(f"Feature extraction failed: {str(e)}")
    
    def get_audio_info(self, audio_path: str) -> Dict:
        """
        Get basic audio file information without full feature extraction.
        Faster than extract_all_features for basic metadata.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with basic audio info
        """
        try:
            y, sr = self.load_audio(audio_path)
            duration = librosa.get_duration(y=y, sr=sr)
            
            return {
                "duration_seconds": float(duration),
                "sample_rate": int(sr),
                "n_samples": int(len(y)),
                "channels": 1,  # Mono after loading
            }
        except Exception as e:
            raise Exception(f"Failed to get audio info: {str(e)}")


# Utility function for easy import
def analyze_audio(audio_path: str, sample_rate: int = 22050) -> Dict:
    """
    Convenience function to analyze an audio file.
    
    Args:
        audio_path: Path to audio file
        sample_rate: Target sample rate (default: 22050 Hz)
        
    Returns:
        Dictionary of extracted features
    """
    analyzer = AudioAnalyzer(sample_rate=sample_rate)
    return analyzer.extract_all_features(audio_path)
