"""
MakiAI — Homework Creator Skill
Reads guide files from Temp-Guide folder and generates a formatted
homework document following the exact format specifications.

Trigger: "create my homework", "do my homework", "make my assignment",
         "help me with my homework", "write my assignment"

Flow:
  1. Open Temp-Guide folder in File Explorer
  2. Ask user to drop guide files and describe the homework
  3. Read all files in Temp-Guide (docx, txt, pdf, images)
  4. Generate homework following guide format
  5. Save as .docx in School/Assignments/<date>/
  6. Open the created file

Guide path: C:\\MakiSync Storage\\School\\Temp-Guide\\
Output path: C:\\MakiSync Storage\\School\\Assignments\\<YYYY-MM-DD>\\
"""

import subprocess
from pathlib import Path
from datetime import datetime
from skills.base_skill import BaseSkill


TEMP_GUIDE_PATH = Path(r"C:\MakiSync Storage\School\Temp-Guide")
ASSIGNMENTS_PATH = Path(r"C:\MakiSync Storage\School\Assignments")


class HomeworkSkill(BaseSkill):

    SKILL_ID = "homework"
    REQUIRED_FILES = []  # No KB files needed — reads Temp-Guide directly

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui_bridge = None

    def set_ui_bridge(self, ui_bridge) -> None:
        """Connect UI bridge to trigger interactive homework modal."""
        self.ui_bridge = ui_bridge

    def execute(self, text: str) -> str:
        """
        Step 1: Open Temp-Guide folder and ask for guide files + instructions.
        If UI bridge is available, pop up the Homework Generator Modal.
        """
        # Ensure Temp-Guide exists
        TEMP_GUIDE_PATH.mkdir(parents=True, exist_ok=True)

        # Extract possible subject title from text
        import re
        clean = re.sub(r"^(?:hey\s+maki,?|maki,?|please\s+|can\s+you\s+)?(?:create|do|make|write|generate)?\s*(?:my\s+)?(?:homework|assignment)?\s*(?:for|about|on)?", "", text, flags=re.IGNORECASE).strip()
        subject_title = clean if len(clean) > 2 else "Academic Assignment"

        if hasattr(self, "ui_bridge") and self.ui_bridge:
            draft = {
                "id": f"hw_{int(datetime.now().timestamp())}",
                "subject": subject_title,
                "instructions": f"Cover essential concepts, definitions, and key topics for {subject_title}.",
                "format": "Standard Academic",
                "output_path": str(ASSIGNMENTS_PATH),
            }
            self.ui_bridge.set_active_modal("homework", draft)
            return f"I've drafted the homework generator for {subject_title}, sir. Please review the topics and format style on your screen."

        # Fallback for headless CLI: Open Temp-Guide in File Explorer
        subprocess.Popen(f'explorer "{TEMP_GUIDE_PATH}"')

        return (
            "I've opened the Temp-Guide folder for you, sir. "
            "Please drop in your guide files — like the format template, rubric, or reference documents. "
            "Once you've added them, tell me what the homework is about and I'll take care of the rest."
        )

    def create_homework(self, instructions: str) -> str:
        """
        Step 2: Read guide files and generate the homework document.

        Args:
            instructions: The homework topic/description from the user.

        Returns:
            Response string confirming creation.
        """
        # Read all guide files from Temp-Guide
        guide_content = self._read_guide_files()

        if not guide_content:
            return (
                "The Temp-Guide folder is empty, sir. "
                "Please add your guide files first, then ask me again."
            )

        # Build prompt with guides + instructions
        prompt = f"""
You are creating a homework document for Mark Vencent Juntilla (a student).

HOMEWORK INSTRUCTIONS FROM STUDENT:
{instructions}

GUIDE FILES CONTENT (follow these formats exactly):
{guide_content}

Your task:
1. Read the guide files carefully — note the page size, margins, font, font size, line spacing, and any formatting rules
2. Generate the complete homework content following those exact format specifications
3. Write the full homework as if it's the final submission
4. Include all required sections based on the guide
5. Make the content academically appropriate, well-written, and complete

Return ONLY the homework content in plain text — formatted naturally.
Do not include meta-commentary or explanations.
Write the actual homework document content.
""".strip()

        response = self.gemini.send(prompt, "")

        if not response or not response.strip():
            return "I had trouble generating the homework, sir. Please try again."

        # Save as .docx
        output_path = self._save_homework(response, instructions)
        self.last_generated_docx = output_path

        if output_path:
            if hasattr(self, "ui_bridge") and self.ui_bridge:
                task_data = {
                    "task_id": f"TQ-{int(datetime.now().timestamp()) % 10000:04d}",
                    "title": f"Academic Document: {output_path.stem}",
                    "badge": "🎓 Academic .docx Ready",
                    "summary": f"MakiAI generated the complete academic document based on your guide rubric. Ready for your review and submission.",
                    "filename": output_path.name,
                    "output_path": str(output_path),
                }
                self.ui_bridge.show_task_review(task_data)

            subprocess.Popen(f'start "" "{output_path}"', shell=True)
            return (
                f"Your homework is ready, sir. "
                f"I've saved it as {output_path.name} in your Assignments folder and opened it for review."
            )

        return "I generated the homework but couldn't save the file, sir. Please check your permissions."

    # ─── Guide Reader ─────────────────────────────────────────────────────────

    def _read_guide_files(self) -> str:
        """
        Read all supported files from the Temp-Guide folder.
        Supports: .txt, .md, .docx, .pdf (text extraction)

        Returns:
            Combined content of all guide files as a string.
        """
        if not TEMP_GUIDE_PATH.exists():
            return ""

        files = list(TEMP_GUIDE_PATH.iterdir())
        if not files:
            return ""

        combined = []

        for file in files:
            if not file.is_file():
                continue

            ext = file.suffix.lower()
            content = ""

            try:
                if ext in (".txt", ".md"):
                    content = file.read_text(encoding="utf-8", errors="ignore")

                elif ext == ".docx":
                    content = self._read_docx(file)

                elif ext == ".pdf":
                    content = self._read_pdf(file)

                elif ext in (".jpg", ".jpeg", ".png", ".webp"):
                    # Use Gemini Vision to extract text/format from image guides
                    content = self._read_image_guide(file)

                if content:
                    combined.append(f"=== Guide File: {file.name} ===\n{content}")
                    print(f"[HomeworkSkill] Read guide: {file.name} ({len(content)} chars)")

            except Exception as e:
                print(f"[HomeworkSkill] Failed to read {file.name}: {e}")

        return "\n\n".join(combined)

    def _read_docx(self, filepath: Path) -> str:
        """Extract text from a .docx file including formatting hints."""
        try:
            from docx import Document
            doc = Document(str(filepath))
            lines = []

            # Extract paragraph styles for format detection
            for para in doc.paragraphs:
                if para.text.strip():
                    style = para.style.name
                    lines.append(f"[{style}] {para.text}")

            # Extract table content
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells)
                    if row_text.strip():
                        lines.append(row_text)

            # Extract document properties for format specs
            try:
                section = doc.sections[0]
                page_width = round(section.page_width.inches, 2)
                page_height = round(section.page_height.inches, 2)
                top_margin = round(section.top_margin.inches, 2)
                bottom_margin = round(section.bottom_margin.inches, 2)
                left_margin = round(section.left_margin.inches, 2)
                right_margin = round(section.right_margin.inches, 2)

                lines.insert(0, (
                    f"[FORMAT SPECS] Page: {page_width}\"x{page_height}\", "
                    f"Margins: top={top_margin}\", bottom={bottom_margin}\", "
                    f"left={left_margin}\", right={right_margin}\""
                ))
            except Exception:
                pass

            return "\n".join(lines)

        except ImportError:
            # Fallback: read as binary and extract visible text
            return f"(python-docx not installed — cannot read {filepath.name})"
        except Exception as e:
            return f"(Error reading {filepath.name}: {e})"

    def _read_pdf(self, filepath: Path) -> str:
        """Extract text from a PDF file."""
        try:
            import pypdf
            reader = pypdf.PdfReader(str(filepath))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)
        except ImportError:
            try:
                # Try PyMuPDF as fallback
                import fitz
                doc = fitz.open(str(filepath))
                return "\n".join(page.get_text() for page in doc)
            except ImportError:
                return f"(PDF reader not installed — install pypdf: pip install pypdf)"
        except Exception as e:
            return f"(Error reading PDF {filepath.name}: {e})"

    def _read_image_guide(self, filepath: Path) -> str:
        """Use Gemini Vision to extract format information from an image guide."""
        try:
            prompt = (
                "This is a homework format guide image. "
                "Extract and describe all formatting specifications you can see: "
                "page size, margins, font name, font size, line spacing, paragraph spacing, "
                "heading styles, any formatting rules or requirements. "
                "Also describe the document structure and any content requirements."
            )
            return self.gemini.send_with_image(prompt, str(filepath), "")
        except Exception as e:
            return f"(Could not analyze image guide: {e})"

    # ─── Save ─────────────────────────────────────────────────────────────────

    def _save_homework(self, content: str, instructions: str) -> Path | None:
        """
        Save the generated homework as a properly formatted .docx file.

        Args:
            content:      The generated homework text.
            instructions: Original instructions (used for filename).

        Returns:
            Path to the saved file, or None on failure.
        """
        try:
            from docx import Document
            from docx.shared import Pt, Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            # Create output folder
            today = datetime.now().strftime("%Y-%m-%d")
            output_dir = ASSIGNMENTS_PATH / today
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from instructions
            safe_name = "".join(
                c if c.isalnum() or c in " _-" else ""
                for c in instructions[:40]
            ).strip().replace(" ", "_")
            filename = f"homework_{safe_name}_{datetime.now().strftime('%H%M%S')}.docx"
            filepath = output_dir / filename

            # Create document
            doc = Document()

            # Default academic formatting
            section = doc.sections[0]
            section.page_width = Inches(8.5)
            section.page_height = Inches(11)
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

            # Write content paragraph by paragraph
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    doc.add_paragraph("")
                    continue

                # Detect headings
                if line.startswith("# "):
                    para = doc.add_heading(line[2:], level=1)
                elif line.startswith("## "):
                    para = doc.add_heading(line[3:], level=2)
                elif line.startswith("### "):
                    para = doc.add_heading(line[4:], level=3)
                else:
                    para = doc.add_paragraph(line)
                    para.style = doc.styles["Normal"]
                    for run in para.runs:
                        run.font.size = Pt(12)
                        run.font.name = "Times New Roman"

            doc.save(str(filepath))
            print(f"[HomeworkSkill] Saved: {filepath}")
            return filepath

        except ImportError:
            # Fallback: save as plain text
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                output_dir = ASSIGNMENTS_PATH / today
                output_dir.mkdir(parents=True, exist_ok=True)
                filepath = output_dir / f"homework_{datetime.now().strftime('%H%M%S')}.txt"
                filepath.write_text(content, encoding="utf-8")
                return filepath
            except Exception:
                return None
        except Exception as e:
            print(f"[HomeworkSkill] Save error: {e}")
            return None
