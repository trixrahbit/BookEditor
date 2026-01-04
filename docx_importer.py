"""
DOCX Importer - Convert Word documents into novel structure
"""

from typing import List, Dict, Tuple
from pathlib import Path
import re

try:
    from docx import Document
    from docx.text.paragraph import Paragraph
    from docx.oxml.text.paragraph import CT_P
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

from models.project import Scene, Chapter, Part
from db_manager import DatabaseManager


class DocxImporter:
    """Import and parse DOCX files into novel structure"""

    def __init__(self):
        self.chapters = []
        self.scenes = []

    def import_docx(self, file_path: str, db_manager: DatabaseManager, project_id: str) -> Tuple[int, int, int]:
        """
        Import a DOCX file and convert it into novel structure

        Returns: (parts_created, chapters_created, scenes_created)
        """
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not installed. Install with: pip install python-docx")

        doc = Document(file_path)

        # Parse document structure with proper formatting
        structure = self._parse_structure_with_formatting(doc)

        # Create database entries
        parts_count = 0
        chapters_count = 0
        scenes_count = 0

        current_part = None
        current_chapter = None
        chapter_order = 0
        scene_order = 0

        for item in structure:
            if item['type'] == 'chapter':
                # Create chapter
                chapter = Chapter(
                    name=item['title'],
                    summary=item.get('summary', ''),
                    parent_id=current_part.id if current_part else None,
                    order=chapter_order
                )
                db_manager.save_item(project_id, chapter)
                current_chapter = chapter
                chapters_count += 1
                chapter_order += 1
                scene_order = 0

            elif item['type'] == 'scene':
                # Create scene - ONLY if we have a chapter
                if current_chapter:
                    scene = Scene(
                        name=item['title'],
                        content=item['content'],
                        parent_id=current_chapter.id,
                        order=scene_order,
                        word_count=self._count_words_in_html(item['content'])
                    )
                    db_manager.save_item(project_id, scene)
                    scenes_count += 1
                    scene_order += 1

        return parts_count, chapters_count, scenes_count

    def _count_words_in_html(self, html: str) -> int:
        """Count words in HTML content"""
        # Strip HTML tags
        import re
        text = re.sub(r'<[^>]+>', ' ', html)
        words = [w for w in text.split() if w]
        return len(words)

    def _parse_structure_with_formatting(self, doc: Document) -> List[Dict]:
        """
        Parse document preserving formatting as HTML
        """
        structure = []
        current_chapter = None
        current_paragraphs = []
        chapter_number = 0
        skip_first_heading = True  # Skip title

        for para in doc.paragraphs:
            # Check if it's Heading 1 (Chapter)
            if para.style.name == 'Heading 1':
                # Skip the first heading (assumed to be title)
                if skip_first_heading:
                    skip_first_heading = False
                    continue

                # Save previous chapter
                if current_chapter and current_paragraphs:
                    content_html = self._paragraphs_to_html(current_paragraphs)
                    structure.append({
                        'type': 'chapter',
                        'title': current_chapter,
                        'summary': '',
                        'content': content_html
                    })
                    current_paragraphs = []

                # Start new chapter
                current_chapter = para.text.strip()
                chapter_number += 1

            elif para.text.strip():
                # Regular content - preserve formatting
                if not current_chapter:
                    # No chapter yet, create default
                    current_chapter = "Chapter 1"
                    chapter_number = 1

                current_paragraphs.append(para)

        # Add final chapter
        if current_chapter and current_paragraphs:
            content_html = self._paragraphs_to_html(current_paragraphs)
            structure.append({
                'type': 'chapter',
                'title': current_chapter,
                'summary': '',
                'content': content_html
            })

        # Convert chapters to chapter + scene structure
        return self._chapters_to_scenes(structure)

    def _paragraphs_to_html(self, paragraphs: List) -> str:
        """Convert paragraphs to HTML preserving formatting and spacing"""
        html_parts = []

        for para in paragraphs:
            para_html = '<p>'

            for run in para.runs:
                text = run.text
                if not text:
                    continue

                # Escape HTML special characters but preserve spaces
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                # Preserve formatting
                if run.bold and run.italic:
                    text = f'<strong><em>{text}</em></strong>'
                elif run.bold:
                    text = f'<strong>{text}</strong>'
                elif run.italic:
                    text = f'<em>{text}</em>'
                elif run.underline:
                    text = f'<u>{text}</u>'

                para_html += text

            para_html += '</p>'
            html_parts.append(para_html)

        return '\n'.join(html_parts)

    def _chapters_to_scenes(self, chapters: List[Dict]) -> List[Dict]:
        """Convert chapter structure to chapter + scenes"""
        result = []

        for chapter in chapters:
            # Add chapter header (no content)
            result.append({
                'type': 'chapter',
                'title': chapter['title'],
                'summary': chapter.get('summary', '')
            })

            # Check for scene breaks in content
            content = chapter['content']
            scenes = self._split_content_by_breaks(content)

            # Add scenes under this chapter
            for i, scene_content in enumerate(scenes, 1):
                if scene_content.strip():  # Only add non-empty scenes
                    result.append({
                        'type': 'scene',
                        'title': f"{chapter['title']} - Scene {i}",
                        'content': scene_content
                    })

        return result

    def _split_content_by_breaks(self, content: str) -> List[str]:
        """Split HTML content by scene break markers"""
        # Look for scene break patterns in HTML
        patterns = [
            r'<p>\s*\*\s*\*\s*\*\s*</p>',
            r'<p>\s*-\s*-\s*-\s*</p>',
            r'<p>\s*#\s*#\s*#\s*</p>',
        ]

        for pattern in patterns:
            parts = re.split(pattern, content)
            if len(parts) > 1:
                return [part.strip() for part in parts if part.strip()]

        # No breaks found - return as single scene
        return [content]

    def estimate_structure(self, file_path: str) -> Dict[str, int]:
        """
        Estimate what will be created without actually importing
        """
        if not DOCX_AVAILABLE:
            return {'error': 'python-docx not installed'}

        doc = Document(file_path)
        structure = self._parse_structure_with_formatting(doc)

        counts = {
            'parts': len([s for s in structure if s['type'] == 'part']),
            'chapters': len([s for s in structure if s['type'] == 'chapter']),
            'scenes': len([s for s in structure if s['type'] == 'scene']),
            'total_words': sum(self._count_words_in_html(s.get('content', ''))
                             for s in structure if s['type'] == 'scene')
        }

        return counts


class ImportDialog:
    """Helper for import UI dialogs"""

    @staticmethod
    def show_import_preview(file_path: str) -> Dict[str, int]:
        """Show preview of what will be imported"""
        importer = DocxImporter()
        return importer.estimate_structure(file_path)

    @staticmethod
    def perform_import(file_path: str, db_manager: DatabaseManager,
                      project_id: str) -> Tuple[int, int, int]:
        """Perform the actual import"""
        importer = DocxImporter()
        return importer.import_docx(file_path, db_manager, project_id)