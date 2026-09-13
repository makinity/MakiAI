"""
MakiAI — DeepClip Skill (clip_skill.py)
Autonomous AI video moment finder and viral shorts creator.

Supports:
  - "Find clips from https://youtube.com/watch?v=..."
  - "Clip the best moments from this video: https://..."
  - "Create 3 viral shorts from my latest recording in MakiSync"
  - "Clip my screen recording into vertical shorts"
"""

import re
from pathlib import Path
from typing import Optional
from skills.base_skill import BaseSkill
from services.media.clip_service import ClipService


class ClipSkill(BaseSkill):
    """
    Skill for analyzing long-form videos, discovering viral moments, and slicing ready-to-post clips.
    """

    SKILL_ID = "clip"
    REQUIRED_FILES = []

    def __init__(self, gemini_service, context_builder, kb_reader, kb_writer):
        super().__init__(gemini_service, context_builder, kb_reader, kb_writer)
        self.clip_service = ClipService(ai_service=gemini_service)

    def execute(self, text: str) -> str:
        """
        Main execution flow: parse command, extract transcript, rank moments, slice clips, and open folder.
        """
        cleaned = text.strip()

        # 1. Determine Layout preference
        layout = "vertical-blur"
        if "landscape" in cleaned.lower() or "horizontal" in cleaned.lower() or "16:9" in cleaned.lower():
            layout = "landscape"
        elif "black" in cleaned.lower() or "letterbox" in cleaned.lower():
            layout = "vertical-black"

        # 2. Determine number of clips requested
        num_clips = 3
        num_match = re.search(r"\b(\d+)\s+(?:clips?|shorts?|moments?|highlights?)\b", cleaned, flags=re.IGNORECASE)
        if num_match:
            try:
                num_clips = min(6, max(1, int(num_match.group(1))))
            except Exception:
                num_clips = 3

        # 3. Determine Source (YouTube URL vs Local Path vs Latest Recording)
        yt_match = re.search(r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+[^\s]*", cleaned)
        if yt_match:
            yt_url = yt_match.group(0).rstrip(".,;)")
            return self._process_youtube(yt_url, num_clips, layout)

        # Check for local file path in text
        path_match = re.search(r"[a-zA-Z]:\\[^\s]+\.(?:mp4|mkv|mov|avi)", cleaned, flags=re.IGNORECASE)
        if path_match:
            local_path = Path(path_match.group(0).strip("\"'"))
            if local_path.exists():
                return self._process_local_video(local_path, num_clips, layout)

        # Check for latest recording request
        if any(kw in cleaned.lower() for kw in ["recording", "latest", "screen", "my video", "mKisync", "makisync"]):
            latest_vid = self.clip_service.get_latest_recording()
            if latest_vid:
                return self._process_local_video(latest_vid, num_clips, layout)
            else:
                return "I couldn't find any recent recordings in your MakiSync Recordings folder, sir."

        return (
            "Please provide a YouTube video URL or ask me to clip your latest recording, sir. "
            "For example: 'Find 3 clips from https://youtube.com/watch?v=...' or 'Clip my latest recording into vertical shorts.'"
        )

    def _process_youtube(self, url: str, num_clips: int, layout: str) -> str:
        """Process YouTube video and slice viral clips."""
        print(f"[ClipSkill] Analyzing YouTube video: {url}")
        segments, video_title = self.clip_service.extract_youtube_transcript(url)
        if not segments:
            return "I was unable to extract captions for this YouTube video, sir. Please make sure the video has public captions or subtitles."

        print(f"[ClipSkill] Finding top {num_clips} viral moments via AI...")
        candidates = self.clip_service.find_best_moments(segments, num_clips=num_clips)
        if not candidates:
            return "I analyzed the transcript, but couldn't identify distinct standalone viral clips for this video, sir."

        created_clips = []
        for idx, c in enumerate(candidates, 1):
            title = c.get("title", f"Clip_{idx}")
            start = float(c.get("start_time", 0))
            end = float(c.get("end_time", start + 30))
            out_name = f"{idx:02d}_{title}"
            
            clip_file = self.clip_service.slice_clip(
                source=url,
                start_time=start,
                end_time=end,
                output_filename=out_name,
                layout=layout,
                is_youtube=True,
            )
            if clip_file and clip_file.exists():
                created_clips.append((title, int(end - start)))

        if created_clips:
            self.clip_service.open_clips_folder()
            clip_summaries = ", ".join([f"'{t}' ({d}s)" for t, d in created_clips])
            return f"I've extracted {len(created_clips)} vertical clips for you, sir: {clip_summaries}. I have opened your Clips folder in MakiSync."
        
        return "I found candidate moments, but encountered an issue downloading the video slices. Please ensure yt-dlp is installed on your system."

    def _process_local_video(self, video_path: Path, num_clips: int, layout: str) -> str:
        """Process a local video file from MakiSync and slice clips."""
        print(f"[ClipSkill] Analyzing local video: {video_path}")
        segments, video_title = self.clip_service.extract_local_transcript(video_path)
        if not segments:
            return f"I wasn't able to transcribe the audio from {video_path.name}, sir. Please check that FFmpeg is available."

        print(f"[ClipSkill] Finding top {num_clips} viral moments via AI...")
        candidates = self.clip_service.find_best_moments(segments, num_clips=num_clips)
        if not candidates:
            return f"I analyzed {video_path.name}, but couldn't find distinct 30-to-60 second standalone moments."

        created_clips = []
        for idx, c in enumerate(candidates, 1):
            title = c.get("title", f"Clip_{idx}")
            start = float(c.get("start_time", 0))
            end = float(c.get("end_time", start + 30))
            out_name = f"{idx:02d}_{title}"
            
            clip_file = self.clip_service.slice_clip(
                source=video_path,
                start_time=start,
                end_time=end,
                output_filename=out_name,
                layout=layout,
                is_youtube=False,
            )
            if clip_file and clip_file.exists():
                created_clips.append((title, int(end - start)))

        if created_clips:
            self.clip_service.open_clips_folder()
            clip_summaries = ", ".join([f"'{t}' ({d}s)" for t, d in created_clips])
            return f"Done, sir! I sliced {len(created_clips)} clips from {video_path.name}: {clip_summaries}. They are ready in your MakiSync Clips folder."

        return f"I identified the viral moments in {video_path.name}, but FFmpeg encountered an error rendering the output clips."
