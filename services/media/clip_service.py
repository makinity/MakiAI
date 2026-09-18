"""
MakiAI — DeepClip Media Service (clip_service.py)
Autonomous AI video moment finder and auto-cutter inspired by paulablaza/deepclip.

Features:
  1. Transcript Extraction:
     - YouTube: Free captions via youtube-transcript-api / yt-dlp
     - Local Files: Fast audio extraction + Groq Whisper with timestamps
  2. AI Virality & Quotability Ranking:
     - Evaluates hook (first 3s), standalone context, retention, and sweet spot length (30-60s)
  3. Multi-Layout FFmpeg Auto-Cutter:
     - vertical-blur (9:16 1080x1920 with blurred background fill for TikTok/Shorts/Reels)
     - vertical-black (9:16 1080x1920 with clean black letterbox)
     - landscape (16:9 native high-definition direct slice)
  4. Automatic storage in C:\\MakiSync Storage\\MakiAI\\Clips\\YYYY-MM-DD\\ with auto-open.
"""

import os
import re
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from services.voice.audio_transcriber import AudioTranscriber
from services.storage.maki_sync import MAKI_SYNC_ROOT


CLIPS_BASE_DIR = MAKI_SYNC_ROOT / "MakiAI" / "Clips"
RECORDINGS_BASE_DIR = MAKI_SYNC_ROOT / "MakiAI" / "Recordings"


def check_ffmpeg() -> bool:
    """Check if ffmpeg executable is available on system PATH."""
    return shutil.which("ffmpeg") is not None


def sanitize_filename(name: str) -> str:
    """Clean string to be safely used as a filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r"\s+", "_", clean.strip())
    return clean[:60] if clean else "clip"


class ClipService:
    """
    AI-powered video clipping and layout engine.
    """

    def __init__(self, ai_service=None):
        self.ai = ai_service
        self.transcriber = AudioTranscriber()
        CLIPS_BASE_DIR.mkdir(parents=True, exist_ok=True)

    def set_ai_service(self, ai_service) -> None:
        self.ai = ai_service

    # ─── 1. Transcript Extraction ─────────────────────────────────────────────

    def extract_youtube_transcript(self, video_url: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Extract timestamped captions from YouTube URL.
        Returns: (transcript_segments, video_title)
        """
        # Extract video ID
        vid_match = re.search(r"(?:v=|\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", video_url)
        video_id = vid_match.group(1) if vid_match else ""
        if not video_id:
            return [], "Unknown Video"

        # Attempt 1: youtube-transcript-api
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Try english or auto-generated english
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except Exception:
                transcript = transcript_list.find_generated_transcript(['en'])
            
            raw_data = transcript.fetch()
            # Normalize to [{start, end, duration, text}]
            segments = []
            for item in raw_data:
                start = float(item.get("start", 0))
                duration = float(item.get("duration", 0))
                segments.append({
                    "start": start,
                    "end": start + duration,
                    "duration": duration,
                    "text": item.get("text", "").strip(),
                })
            print(f"[ClipService] Extracted {len(segments)} segments via YouTubeTranscriptApi.")
            return segments, f"YouTube_{video_id}"
        except Exception as e:
            print(f"[ClipService] YouTubeTranscriptApi failed: {e}. Trying yt-dlp fallback.")

        # Attempt 2: yt-dlp auto subtitles
        try:
            cmd = [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--skip-download",
                "--print", "title",
                "-o", f"temp_subs_{video_id}",
                video_url,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            title = res.stdout.strip().split("\n")[0] if res.stdout else f"YouTube_{video_id}"
            
            # Look for created vtt file
            vtt_file = Path(f"temp_subs_{video_id}.en.vtt")
            segments = []
            if vtt_file.exists():
                segments = self._parse_vtt(vtt_file.read_text(encoding="utf-8", errors="ignore"))
                vtt_file.unlink(missing_ok=True)

            return segments, title
        except Exception as e:
            print(f"[ClipService] yt-dlp subtitle extraction failed: {e}")

        return [], f"YouTube_{video_id}"

    def extract_local_transcript(self, video_path: str | Path) -> Tuple[List[Dict[str, Any]], str]:
        """
        Extract audio from local video file and transcribe with Groq Whisper with timestamps.
        """
        v_path = Path(video_path)
        if not v_path.exists():
            return [], ""

        title = v_path.stem
        if not check_ffmpeg():
            print("[ClipService] FFmpeg not found — cannot extract audio.")
            return [], title

        temp_audio = v_path.parent / f"_temp_{v_path.stem}.wav"
        try:
            # Extract 16kHz mono WAV using ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", str(v_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                str(temp_audio)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # Transcribe with Groq Whisper
            if temp_audio.exists():
                wav_bytes = temp_audio.read_bytes()
                # Use Groq client directly for verbose JSON segment timestamps
                if self.transcriber.groq_client:
                    transcription = self.transcriber.groq_client.audio.transcriptions.create(
                        file=("audio.wav", wav_bytes),
                        model="whisper-large-v3-turbo",
                        response_format="verbose_json",
                        temperature=0.0,
                    )
                    segments = []
                    raw_segments = getattr(transcription, "segments", []) or []
                    for s in raw_segments:
                        s_dict = s if isinstance(s, dict) else s.__dict__
                        segments.append({
                            "start": float(s_dict.get("start", 0)),
                            "end": float(s_dict.get("end", 0)),
                            "duration": float(s_dict.get("end", 0)) - float(s_dict.get("start", 0)),
                            "text": str(s_dict.get("text", "")).strip(),
                        })
                    return segments, title
        except Exception as e:
            print(f"[ClipService] Local video transcription error: {e}")
        finally:
            if temp_audio.exists():
                try:
                    temp_audio.unlink()
                except Exception:
                    pass

        return [], title

    def _parse_vtt(self, vtt_content: str) -> List[Dict[str, Any]]:
        """Parse WebVTT content into timestamped segments."""
        segments = []
        blocks = vtt_content.split("\n\n")
        time_pat = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})")
        short_time_pat = re.compile(r"(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2})\.(\d{3})")

        for b in blocks:
            lines = [l.strip() for l in b.strip().split("\n") if l.strip()]
            if len(lines) < 2:
                continue
            
            # Find timestamp line
            ts_line = None
            text_lines = []
            for line in lines:
                if "-->" in line:
                    ts_line = line
                elif ts_line:
                    text_lines.append(re.sub(r"<[^>]+>", "", line))

            if ts_line and text_lines:
                m = time_pat.search(ts_line)
                if m:
                    h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
                    start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
                    end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0
                else:
                    sm = short_time_pat.search(ts_line)
                    if sm:
                        m1, s1, ms1, m2, s2, ms2 = map(int, sm.groups())
                        start = m1 * 60 + s1 + ms1 / 1000.0
                        end = m2 * 60 + s2 + ms2 / 1000.0
                    else:
                        continue

                clean_text = " ".join(text_lines).strip()
                if clean_text:
                    segments.append({
                        "start": start,
                        "end": end,
                        "duration": end - start,
                        "text": clean_text,
                    })

        return segments

    # ─── 2. AI Virality Ranking ───────────────────────────────────────────────

    def find_best_moments(self, segments: List[Dict[str, Any]], num_clips: int = 3) -> List[Dict[str, Any]]:
        """
        Send timestamped transcript to AI model to find top viral, standalone clips.
        """
        if not segments or not self.ai:
            return []

        # Format transcript into chunked text with timestamps
        formatted_lines = []
        for s in segments:
            start_m, start_s = divmod(int(s["start"]), 60)
            formatted_lines.append(f"[{start_m:02d}:{start_s:02d}] {s['text']}")

        transcript_text = "\n".join(formatted_lines)
        if len(transcript_text) > 40000:
            transcript_text = transcript_text[:40000] + "\n[... truncated ...]"

        prompt = f"""You are DeepClip, an expert video editor specialized in finding viral clips for TikTok, YouTube Shorts, and Instagram Reels.

Analyze the following timestamped transcript and select the top {num_clips} BEST moments to cut into standalone short-form clips.

CRITERIA FOR A VIRAL CLIP:
1. Strong Hook (first 3s): Starts with a compelling question, bold statement, or high emotion.
2. Self-Contained: Makes complete sense on its own without needing the rest of the video.
3. Quotable & Shareable: Contains high-value advice, a punchline, or a surprising insight.
4. Target Length: 30 to 60 seconds (minimum 20s, maximum 90s).

TRANSCRIPT:
{transcript_text}

OUTPUT IN STRICT JSON FORMAT ONLY:
[
  {{
    "title": "Short Catchy 3-5 Word Title",
    "start_time": 45.0,
    "end_time": 82.0,
    "duration_seconds": 37,
    "virality_score": 9.5,
    "hook": "The opening hook phrase",
    "reasoning": "Why this moment will perform well as a short clip"
  }}
]
"""
        response = self.ai.send(prompt, "")
        try:
            # Extract JSON array from LLM response
            json_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", response)
            if json_match:
                candidates = json.loads(json_match.group(0))
                return candidates[:num_clips]
        except Exception as e:
            print(f"[ClipService] AI ranking JSON parse error: {e}")

        return []

    # ─── 3. Video Slicing & Layout Engine ─────────────────────────────────────

    def slice_clip(
        self,
        source: str | Path,
        start_time: float,
        end_time: float,
        output_filename: str,
        layout: str = "vertical-blur",
        is_youtube: bool = False,
    ) -> Optional[Path]:
        """
        Cut a video clip with specified layout (vertical-blur, vertical-black, or landscape).
        Saves to today's Clips folder in MakiSync.
        """
        if not check_ffmpeg():
            print("[ClipService] FFmpeg is missing — cannot render clip.")
            return None

        today_str = datetime.now().strftime("%Y-%m-%d")
        today_dir = CLIPS_BASE_DIR / today_str
        today_dir.mkdir(parents=True, exist_ok=True)

        clean_name = sanitize_filename(output_filename) + ".mp4"
        output_path = today_dir / clean_name
        duration = max(1.0, end_time - start_time)

        # Build FFmpeg command based on layout
        if is_youtube:
            # If YouTube, download exact slice using yt-dlp + ffmpeg
            yt_url = str(source)
            print(f"[ClipService] Downloading & cutting YouTube slice ({start_time}s to {end_time}s)...")
            
            # Temporary cut file
            temp_cut = today_dir / f"_raw_{clean_name}"
            cmd = [
                "yt-dlp",
                "--download-sections", f"*{start_time}-{end_time}",
                "--force-keyframes-at-cuts",
                "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "-o", str(temp_cut),
                yt_url,
            ]
            try:
                subprocess.run(cmd, check=True)
                if temp_cut.exists():
                    # Apply layout transformation to the temp file
                    final_path = self._apply_layout(temp_cut, output_path, layout)
                    temp_cut.unlink(missing_ok=True)
                    return final_path
            except Exception as e:
                print(f"[ClipService] yt-dlp cut error: {e}")
                temp_cut.unlink(missing_ok=True)
                return None
        else:
            # Local video file
            src_path = Path(source)
            if not src_path.exists():
                print(f"[ClipService] Source video not found: {source}")
                return None

            print(f"[ClipService] Slicing local video with layout '{layout}' ({start_time}s - {end_time}s)...")
            return self._apply_layout_from_source(src_path, output_path, start_time, duration, layout)

    def _apply_layout(self, input_file: Path, output_file: Path, layout: str) -> Optional[Path]:
        """Transform an existing raw cut into the requested layout."""
        filter_str = self._get_filter_graph(layout)
        cmd = ["ffmpeg", "-y", "-i", str(input_file)]
        if filter_str:
            cmd.extend(["-vf", filter_str])
        cmd.extend([
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
            str(output_file)
        ])
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if output_file.exists():
                return output_file
        except Exception as e:
            print(f"[ClipService] FFmpeg layout filter error: {e}")
        return None

    def _apply_layout_from_source(self, src_path: Path, output_file: Path, start: float, duration: float, layout: str) -> Optional[Path]:
        """Cut and apply layout in one direct FFmpeg pass from a local video."""
        filter_str = self._get_filter_graph(layout)
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(src_path),
            "-t", str(duration),
        ]
        if filter_str:
            cmd.extend(["-vf", filter_str])
        cmd.extend([
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
            str(output_file)
        ])
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if output_file.exists():
                return output_file
        except Exception as e:
            print(f"[ClipService] Local FFmpeg cut error: {e}")
        return None

    def _get_filter_graph(self, layout: str) -> str:
        """Return FFmpeg video filter for vertical-blur, vertical-black, or landscape."""
        if layout == "vertical-blur":
            # 9:16 vertical 1080x1920 with blurred background fill
            return (
                "split[v1][v2];"
                "[v1]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
                "[v2]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2"
            )
        elif layout == "vertical-black":
            # 9:16 vertical 1080x1920 with black letterbox
            return "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
        else:
            # 16:9 native landscape
            return ""

    def get_latest_recording(self) -> Optional[Path]:
        """Find the most recently created video recording in MakiSync Recordings."""
        if not RECORDINGS_BASE_DIR.exists():
            return None
        videos = list(RECORDINGS_BASE_DIR.rglob("*.mp4")) + list(RECORDINGS_BASE_DIR.rglob("*.mkv"))
        if not videos:
            return None
        return max(videos, key=lambda f: f.stat().st_mtime)

    def open_clips_folder(self) -> None:
        """Open the clips directory in Windows File Explorer."""
        today_dir = CLIPS_BASE_DIR / datetime.now().strftime("%Y-%m-%d")
        target_dir = today_dir if today_dir.exists() else CLIPS_BASE_DIR
        try:
            os.startfile(str(target_dir))
        except Exception as e:
            print(f"[ClipService] Open clips folder error: {e}")
