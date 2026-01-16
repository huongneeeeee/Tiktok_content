# backend/app/services/analysis/vision.py
"""
Phase 2 - Visual Branch: Scene Detection

Features:
- Detect scene boundaries using FFmpeg scene filter
- Extract keyframes per scene
- Prioritize frames likely to contain text
"""

import os
import sys
import subprocess
import json
import re
from typing import List, Dict, Optional

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import Config


# ============================================================
# SCENE DETECTION (FFmpeg based)
# ============================================================

def get_video_duration(video_path: str) -> float:
    """Get video duration using FFprobe"""
    try:
        cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except:
        return 0.0


def detect_scenes(video_path: str, threshold: float = 0.3) -> List[Dict]:
    """
    Detect scene changes using FFmpeg's scene filter.
    
    Args:
        video_path: Path to video file
        threshold: Scene change threshold (0.0-1.0, lower = more sensitive)
    
    Returns:
    [
        {"scene_id": 0, "start_time": 0.0, "end_time": 5.2, "duration": 5.2},
        {"scene_id": 1, "start_time": 5.2, "end_time": 12.8, "duration": 7.6},
        ...
    ]
    """
    if not os.path.exists(video_path):
        return []
    
    duration = get_video_duration(video_path)
    if duration <= 0:
        return []
    
    print(f"   🎬 [SCENE] Detecting scenes in {duration:.1f}s video...")
    
    # Use FFmpeg scene detection filter
    # This outputs timestamps where scene changes occur
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-show_frames',
        '-select_streams', 'v',
        '-show_entries', 'frame=pts_time',
        '-f', 'lavfi',
        f'movie={video_path},select=gt(scene\\,{threshold})',
        '-print_format', 'json'
    ]
    
    try:
        # Alternative approach: use ffmpeg with scene detection
        # This is more reliable across different systems
        scene_times = detect_scenes_ffmpeg(video_path, threshold, duration)
        
        if not scene_times:
            # No scene changes detected - treat entire video as one scene
            return [{
                "scene_id": 0,
                "start_time": 0.0,
                "end_time": duration,
                "duration": duration
            }]
        
        # Build scene list from change points
        scenes = []
        scene_times = [0.0] + scene_times + [duration]  # Add start and end
        
        for i in range(len(scene_times) - 1):
            start = scene_times[i]
            end = scene_times[i + 1]
            
            # Skip very short scenes (< 0.5s)
            if end - start < 0.5:
                continue
            
            scenes.append({
                "scene_id": len(scenes),
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "duration": round(end - start, 2)
            })
        
        # If all scenes were too short, return single scene
        if not scenes:
            return [{
                "scene_id": 0,
                "start_time": 0.0,
                "end_time": duration,
                "duration": duration
            }]
        
        print(f"   ✅ [SCENE] Detected {len(scenes)} scenes")
        return scenes
        
    except Exception as e:
        print(f"   ⚠️ [SCENE] Detection error: {e}")
        # Fallback: return single scene
        return [{
            "scene_id": 0,
            "start_time": 0.0,
            "end_time": duration,
            "duration": duration
        }]


def detect_scenes_ffmpeg(video_path: str, threshold: float, duration: float) -> List[float]:
    """
    Use FFmpeg to detect scene changes.
    Returns list of timestamps where scene changes occur.
    """
    # Create a temp file for scene detection output
    import tempfile
    
    scene_times = []
    
    try:
        # FFmpeg command to detect scene changes
        # Output format: frame_number, pts_time, scene_score
        cmd = f'ffmpeg -i "{video_path}" -vf "select=\'gt(scene,{threshold})\',showinfo" -f null - 2>&1'
        
        result = subprocess.run(
            cmd, shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Parse output for pts_time
        # Format: [Parsed_showinfo_0 @ ...] n:  XX pts:  XXXX pts_time:XX.XXXX
        pattern = r'pts_time:(\d+\.?\d*)'
        matches = re.findall(pattern, result.stderr)
        
        scene_times = [float(t) for t in matches]
        
        # Remove duplicates and sort
        scene_times = sorted(list(set(scene_times)))
        
        # Filter out scene changes too close together
        if scene_times:
            filtered = [scene_times[0]]
            for t in scene_times[1:]:
                if t - filtered[-1] >= 1.0:  # Min 1 second between scenes
                    filtered.append(t)
            scene_times = filtered
        
        return scene_times
        
    except subprocess.TimeoutExpired:
        print("   ⚠️ [SCENE] Detection timeout")
        return []
    except Exception as e:
        print(f"   ⚠️ [SCENE] FFmpeg error: {e}")
        return []


# ============================================================
# KEYFRAME EXTRACTION
# ============================================================

def extract_keyframes_per_scene(
    video_path: str, 
    scenes: List[Dict],
    output_dir: str,
    frames_per_scene: int = 2
) -> List[Dict]:
    """
    Extract keyframes from each scene.
    
    Args:
        video_path: Path to video file
        scenes: List of scenes from detect_scenes()
        output_dir: Directory to save frames
        frames_per_scene: Number of frames to extract per scene
    
    Returns:
    [
        {"scene_id": 0, "timestamp": 2.5, "frame_path": "/tmp/.../f000.jpg", "frame_id": 0},
        {"scene_id": 0, "timestamp": 4.0, "frame_path": "/tmp/.../f001.jpg", "frame_id": 1},
        {"scene_id": 1, "timestamp": 8.0, "frame_path": "/tmp/.../f002.jpg", "frame_id": 2},
        ...
    ]
    """
    if not os.path.exists(video_path):
        return []
    
    os.makedirs(output_dir, exist_ok=True)
    
    keyframes = []
    frame_id = 0
    
    max_total_frames = getattr(Config, 'OCR_MAX_FRAMES', 10)
    frames_per_scene = min(frames_per_scene, max(1, max_total_frames // len(scenes)))
    
    print(f"   📸 [SCENE] Extracting {frames_per_scene} frame(s) per scene...")
    
    for scene in scenes:
        scene_id = scene["scene_id"]
        start = scene["start_time"]
        end = scene["end_time"]
        scene_duration = end - start
        
        # Calculate extraction points within scene
        # Avoid very start/end of scene (often transition frames)
        margin = min(0.2, scene_duration * 0.1)
        usable_start = start + margin
        usable_end = end - margin
        usable_duration = usable_end - usable_start
        
        if usable_duration <= 0:
            # Very short scene - extract middle frame
            timestamps = [(start + end) / 2]
        elif frames_per_scene == 1:
            # Single frame - extract middle
            timestamps = [(start + end) / 2]
        else:
            # Multiple frames - distribute evenly
            step = usable_duration / frames_per_scene
            timestamps = [usable_start + (i + 0.5) * step for i in range(frames_per_scene)]
        
        for ts in timestamps:
            if frame_id >= max_total_frames:
                break
            
            frame_path = os.path.join(output_dir, f"f{frame_id:03d}.jpg")
            
            # FFmpeg command to extract single frame
            cmd = f'ffmpeg -ss {ts:.2f} -i "{video_path}" -vframes 1 -vf "scale=1280:-1" -q:v 2 "{frame_path}" -y -loglevel error'
            
            try:
                subprocess.run(cmd, shell=True, timeout=15)
                if os.path.exists(frame_path) and os.path.getsize(frame_path) > 1000:
                    keyframes.append({
                        "scene_id": scene_id,
                        "timestamp": round(ts, 2),
                        "frame_path": frame_path,
                        "frame_id": frame_id
                    })
                    frame_id += 1
            except:
                pass
        
        if frame_id >= max_total_frames:
            break
    
    print(f"   ✅ [SCENE] Extracted {len(keyframes)} keyframes")
    return keyframes


def get_scene_info(video_path: str, output_dir: str = None) -> Dict:
    """
    Complete scene analysis: detection + keyframe extraction.
    
    Returns:
    {
        "scenes": [...],
        "keyframes": [...],
        "scene_count": int,
        "total_frames": int,
        "success": True
    }
    """
    import tempfile
    
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="scene_")
    
    # Step 1: Detect scenes
    scenes = detect_scenes(video_path)
    
    # Step 2: Extract keyframes
    keyframes = extract_keyframes_per_scene(video_path, scenes, output_dir)
    
    return {
        "scenes": scenes,
        "keyframes": keyframes,
        "scene_count": len(scenes),
        "total_frames": len(keyframes),
        "output_dir": output_dir,
        "success": True
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    import tempfile
    import shutil
    
    print("=" * 60)
    print("🧪 Scene Detector Test")
    print("=" * 60)
    
    test_video = r"E:\Tiktok_content_AI\scraper_data\content_files\tiktok_video_7296055437135252738.mp4"
    
    if os.path.exists(test_video):
        # Create temp dir
        temp_dir = tempfile.mkdtemp(prefix="scene_test_")
        
        try:
            result = get_scene_info(test_video, temp_dir)
            
            print(f"\n📊 Results:")
            print(f"   Scene count: {result['scene_count']}")
            print(f"   Keyframes extracted: {result['total_frames']}")
            
            print(f"\n🎬 Scenes:")
            for scene in result['scenes'][:5]:  # Show first 5
                print(f"   Scene {scene['scene_id']}: {scene['start_time']:.1f}s - {scene['end_time']:.1f}s ({scene['duration']:.1f}s)")
            
            print(f"\n📸 Keyframes:")
            for kf in result['keyframes'][:5]:  # Show first 5
                print(f"   Frame {kf['frame_id']}: Scene {kf['scene_id']} @ {kf['timestamp']:.2f}s")
        
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        print(f"❌ Test video not found: {test_video}")
