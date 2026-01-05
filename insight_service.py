# insight_service.py
import uuid
from typing import Dict, Any, Optional, List, Tuple

from analyzer import AnalysisEngine, ChapterData
from db_manager import InsightDatabase, sha256_text
from job_queue import JobQueueWorker, new_job, Job
from text_utils import html_to_plaintext


def _uuid() -> str:
    return str(uuid.uuid4())


class InsightService:
    """
    Orchestrates analysis runs, caching, storage in InsightDatabase.
    UI can subscribe to worker signals for progress.
    """

    def __init__(self, ai_manager, db_manager, insight_db: InsightDatabase):
        self.ai_manager = ai_manager
        self.db_manager = db_manager
        self.insight_db = insight_db
        self.engine = AnalysisEngine(ai_manager)

        self.worker = JobQueueWorker(self._run_job)
        self.worker.start()

    def shutdown(self):
        self.worker.stop()
        self.worker.wait(1500)

    # --------- enqueue jobs ----------

    def enqueue_chapter_analyses(self, project_id: str, chapter_id: str, include_style=True, include_reader_snapshot=True):
        chapter = self._load_chapter_data(project_id, chapter_id)
        if not chapter:
            raise ValueError("Chapter not found")

        # hash chapter source
        chapter_source = self._hash_chapter_source(chapter)
        # enqueue timeline + consistency
        self._enqueue_if_needed(project_id, "chapter", chapter_id, "timeline", chapter_source,
                                kind="chapter_timeline", payload={"project_id": project_id, "chapter_id": chapter_id})
        self._enqueue_if_needed(project_id, "chapter", chapter_id, "consistency", chapter_source,
                                kind="chapter_consistency", payload={"project_id": project_id, "chapter_id": chapter_id})
        if include_style:
            self._enqueue_if_needed(project_id, "chapter", chapter_id, "style", chapter_source,
                                    kind="chapter_style", payload={"project_id": project_id, "chapter_id": chapter_id})
        if include_reader_snapshot:
            self._enqueue_if_needed(project_id, "chapter", chapter_id, "reader_snapshot", chapter_source,
                                    kind="chapter_reader_snapshot", payload={"project_id": project_id, "chapter_id": chapter_id})

    def enqueue_book_analyses(self, project_id: str, include_bible=True, include_threads=True,
                             include_promise=True, include_voice=True, include_reader_sim=True):
        compiled = self.compile_book_text(project_id)
        source_hash = sha256_text(compiled)

        if include_bible:
            self._enqueue_if_needed(project_id, "book", None, "story_bible", source_hash,
                                    kind="book_bible", payload={"project_id": project_id})
        if include_threads:
            self._enqueue_if_needed(project_id, "book", None, "threads", source_hash,
                                    kind="book_threads", payload={"project_id": project_id})
        if include_promise:
            self._enqueue_if_needed(project_id, "book", None, "promise_payoff", source_hash,
                                    kind="book_promise_payoff", payload={"project_id": project_id})
        if include_voice:
            self._enqueue_if_needed(project_id, "book", None, "voice_drift", source_hash,
                                    kind="book_voice_drift", payload={"project_id": project_id})
        if include_reader_sim:
            self._enqueue_if_needed(project_id, "book", None, "reader_sim", source_hash,
                                    kind="book_reader_sim", payload={"project_id": project_id})

    def _enqueue_if_needed(self, project_id: str, scope: str, scope_id: Optional[str], insight_type: str,
                           source_hash: str, kind: str, payload: Dict[str, Any]) -> None:
        if self.insight_db.exists_with_hash(project_id, scope, scope_id, insight_type, source_hash):
            return
        self.worker.enqueue(new_job(kind, payload))

    # --------- job runner ----------

    def _run_job(self, job: Job) -> Dict[str, Any]:
        kind = job.kind
        payload = job.payload
        project_id = payload["project_id"]

        if kind.startswith("chapter_"):
            chapter_id = payload["chapter_id"]
            chapter = self._load_chapter_data(project_id, chapter_id)
            if not chapter:
                raise ValueError("Chapter not found")

            chapter_source_hash = self._hash_chapter_source(chapter)

            if kind == "chapter_timeline":
                result = self.engine.analyze_chapter_timeline(chapter)
                self._store_chapter_issues(project_id, chapter_id, "timeline", result, chapter_source_hash)
                return result

            if kind == "chapter_consistency":
                result = self.engine.analyze_chapter_consistency(chapter)
                self._store_chapter_issues(project_id, chapter_id, "consistency", result, chapter_source_hash)
                return result

            if kind == "chapter_style":
                result = self.engine.analyze_chapter_style(chapter)
                self._store_chapter_issues(project_id, chapter_id, "style", result, chapter_source_hash)
                return result

            if kind == "chapter_reader_snapshot":
                result = self.engine.analyze_chapter_reader_snapshot(chapter)
                self._store_generic(project_id, "chapter", chapter_id, "reader_snapshot", result, chapter_source_hash)
                return result

            raise ValueError(f"Unknown job kind: {kind}")

        # book level
        compiled = self.compile_book_text(project_id)
        book_hash = sha256_text(compiled)

        if kind == "book_bible":
            existing = self.get_story_bible(project_id)  # optional
            result = self.engine.analyze_book_story_bible(compiled, existing_bible=existing)
            self._store_generic(project_id, "book", None, "story_bible", result, book_hash)
            return result

        if kind == "book_threads":
            result = self.engine.analyze_book_threads(compiled)
            self._store_generic(project_id, "book", None, "threads", result, book_hash)
            return result

        if kind == "book_promise_payoff":
            result = self.engine.analyze_book_promise_payoff(compiled)
            self._store_generic(project_id, "book", None, "promise_payoff", result, book_hash)
            return result

        if kind == "book_voice_drift":
            result = self.engine.analyze_book_voice_drift(compiled)
            self._store_generic(project_id, "book", None, "voice_drift", result, book_hash)
            return result

        if kind == "book_reader_sim":
            result = self.engine.analyze_book_reader_sim(compiled)
            self._store_generic(project_id, "book", None, "reader_sim", result, book_hash)
            return result

        raise ValueError(f"Unknown job kind: {kind}")

    # --------- storage ----------

    def _store_chapter_issues(self, project_id: str, chapter_id: str, insight_type: str,
                             result: Dict[str, Any], source_hash: str) -> None:
        issues = result.get("issues", [])
        # normalize issues into your viewer-friendly issue dicts
        normalized = []
        for it in issues:
            normalized.append({
                "type": insight_type,
                "chapter": result.get("chapter"),
                "severity": it.get("severity", "Minor"),
                "issue": it.get("issue", ""),
                "detail": it.get("detail", ""),
                "location": it.get("location", ""),
                "scene_id": it.get("scene_id"),
                "anchors": it.get("anchors", []),
                "quote": it.get("quote", ""),
                "suggestions": it.get("suggestions", []),
            })

        payload = {
            "type": insight_type,
            "chapter": result.get("chapter"),
            "issues": normalized,
            "raw": result
        }
        self.insight_db.upsert(
            insight_id=_uuid(),
            project_id=project_id,
            scope="chapter",
            scope_id=chapter_id,
            insight_type=insight_type,
            payload=payload,
            source_hash=source_hash
        )

    def _store_generic(self, project_id: str, scope: str, scope_id: Optional[str],
                       insight_type: str, result: Dict[str, Any], source_hash: str) -> None:
        self.insight_db.upsert(
            insight_id=_uuid(),
            project_id=project_id,
            scope=scope,
            scope_id=scope_id,
            insight_type=insight_type,
            payload=result,
            source_hash=source_hash
        )

    # --------- getters ----------

    def get_story_bible(self, project_id: str) -> Optional[Dict[str, Any]]:
        rec = self.insight_db.get_latest(project_id, "book", None, "story_bible")
        if not rec:
            return None
        return rec.payload.get("payload") or rec.payload

    # --------- compilation ----------

    def compile_book_text(self, project_id: str, per_scene_chars: int = 6000) -> str:
        """
        Create a book-wide plain text compilation used by book-level analyses.
        This is intentionally capped to reduce token blowups.
        """
        from models.project import ItemType

        chapters = self.db_manager.load_items(project_id, ItemType.CHAPTER)
        scenes = self.db_manager.load_items(project_id, ItemType.SCENE)

        # group scenes by parent (chapter)
        scenes_by_chapter = {}
        for s in scenes:
            scenes_by_chapter.setdefault(getattr(s, "parent_id", None), []).append(s)

        out = []
        for ch in chapters:
            out.append(f"\n\n===== CHAPTER: {ch.name} =====\n")
            ch_scenes = scenes_by_chapter.get(ch.id, [])
            for sc in ch_scenes:
                plain = html_to_plaintext(getattr(sc, "content", "") or "")
                plain = plain[:per_scene_chars]
                out.append(f"\n--- SCENE: {sc.name} (scene_id={sc.id}) ---\n")
                out.append(plain)

        return "\n".join(out).strip()

    # --------- loaders ----------

    def _load_chapter_data(self, project_id: str, chapter_id: str) -> Optional[ChapterData]:
        from models.project import ItemType
        chapter = self.db_manager.load_item(chapter_id)
        if not chapter:
            return None
        scenes = self.db_manager.load_items(project_id, ItemType.SCENE, parent_id=chapter_id)
        scene_dicts = []
        for s in scenes:
            scene_dicts.append({"id": s.id, "name": s.name, "content": getattr(s, "content", "")})
        return ChapterData(id=chapter.id, name=chapter.name, scenes=scene_dicts)

    def _hash_chapter_source(self, chapter: ChapterData) -> str:
        # stable hash across all scene contents in chapter
        buf = [chapter.name]
        for s in chapter.scenes:
            buf.append(s.get("id",""))
            buf.append(s.get("name",""))
            buf.append(s.get("content","") or "")
        return sha256_text("\n".join(buf))
