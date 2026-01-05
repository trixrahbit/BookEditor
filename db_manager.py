import datetime
import hashlib
import sqlite3
import json
import threading
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
from models.project import (
    Project, Scene, Chapter, Part, Character, Location, PlotThread,
    ProjectItem, ItemType
)


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()
        self._initialize_database()

    def _initialize_database(self):
        """Create database tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Project table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS projects
                       (
                           id
                           TEXT
                           PRIMARY
                           KEY,
                           name
                           TEXT
                           NOT
                           NULL,
                           author
                           TEXT,
                           genre
                           TEXT,
                           target_word_count
                           INTEGER,
                           description
                           TEXT,
                           created
                           TEXT
                           NOT
                           NULL,
                           modified
                           TEXT
                           NOT
                           NULL
                       )
                       ''')

        # Items table (scenes, chapters, parts)
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS items
                       (
                           id
                           TEXT
                           PRIMARY
                           KEY,
                           project_id
                           TEXT
                           NOT
                           NULL,
                           name
                           TEXT
                           NOT
                           NULL,
                           item_type
                           TEXT
                           NOT
                           NULL,
                           parent_id
                           TEXT,
                           order_index
                           INTEGER
                           DEFAULT
                           0,
                           created
                           TEXT
                           NOT
                           NULL,
                           modified
                           TEXT
                           NOT
                           NULL,
                           data
                           TEXT,
                           FOREIGN
                           KEY
                       (
                           project_id
                       ) REFERENCES projects
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        # Create indexes
        cursor.execute('''
                       CREATE INDEX IF NOT EXISTS idx_items_project
                           ON items(project_id)
                       ''')
        cursor.execute('''
                       CREATE INDEX IF NOT EXISTS idx_items_parent
                           ON items(parent_id)
                       ''')
        cursor.execute('''
                       CREATE INDEX IF NOT EXISTS idx_items_type
                           ON items(item_type)
                       ''')

        self.conn.commit()

    def save_project(self, project: Project) -> bool:
        """Save or update a project"""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                project_dict = project.to_dict()

                cursor.execute('''
                    INSERT OR REPLACE INTO projects 
                    (id, name, author, genre, target_word_count, description, created, modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_dict['id'],
                    project_dict['name'],
                    project_dict.get('author'),
                    project_dict.get('genre'),
                    project_dict.get('target_word_count'),
                    project_dict.get('description'),
                    project_dict['created'],
                    project_dict['modified']
                ))

                self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    def load_project(self, project_id: str) -> Optional[Project]:
        """Load a project by ID"""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
            row = cursor.fetchone()

        if row:
            return Project.from_dict(dict(row))
        return None

    def list_projects(self) -> List[Project]:
        """List all projects"""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM projects ORDER BY modified DESC')
            rows = cursor.fetchall()

        return [Project.from_dict(dict(row)) for row in rows]

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its items"""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
                cursor.execute('DELETE FROM items WHERE project_id = ?', (project_id,))
                self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False

    def save_item(self, project_id: str, item: ProjectItem) -> bool:
        """Save or update a project item"""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                item_dict = item.to_dict()

                common_data = {
                    'id': item_dict['id'],
                    'name': item_dict['name'],
                    'item_type': item_dict['item_type'],
                    'parent_id': item_dict.get('parent_id'),
                    'order': item_dict.get('order', 0),
                    'created': item_dict['created'],
                    'modified': item_dict['modified']
                }

                # Use a key set (safer than checking against dict object)
                COMMON_KEYS = {"id", "name", "item_type", "parent_id", "order", "created", "modified"}
                extended_data = {k: v for k, v in item_dict.items() if k not in COMMON_KEYS}

                cursor.execute('''
                    INSERT OR REPLACE INTO items 
                    (id, project_id, name, item_type, parent_id, order_index, 
                     created, modified, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    common_data['id'],
                    project_id,
                    common_data['name'],
                    common_data['item_type'],
                    common_data['parent_id'],
                    common_data['order'],
                    common_data['created'],
                    common_data['modified'],
                    json.dumps(extended_data)
                ))

                self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving item: {e}")
            return False

    def load_item(self, item_id: str) -> Optional[ProjectItem]:
        """Load a project item by ID"""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM items WHERE id = ?', (item_id,))
            row = cursor.fetchone()

        if not row:
            return None
        return self._row_to_item(row)

    def load_items(self, project_id: str,
                   item_type: Optional[ItemType] = None,
                   parent_id: Optional[str] = None) -> List[ProjectItem]:
        """Load project items with optional filters"""
        query = 'SELECT * FROM items WHERE project_id = ?'
        params = [project_id]

        if item_type:
            query += ' AND item_type = ?'
            params.append(item_type.value)

        if parent_id is not None:
            query += ' AND parent_id = ?'
            params.append(parent_id)

        query += ' ORDER BY order_index, created'

        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [self._row_to_item(row) for row in rows]

    def delete_item(self, item_id: str) -> bool:
        """Delete an item and all its children"""
        try:
            cursor = self.conn.cursor()

            # Get all child items recursively
            def get_children(parent_id: str) -> List[str]:
                cursor.execute('SELECT id FROM items WHERE parent_id = ?', (parent_id,))
                children = [row['id'] for row in cursor.fetchall()]
                all_children = children.copy()
                for child_id in children:
                    all_children.extend(get_children(child_id))
                return all_children

            # Delete item and all children
            to_delete = [item_id] + get_children(item_id)
            cursor.executemany('DELETE FROM items WHERE id = ?',
                               [(id,) for id in to_delete])

            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting item: {e}")
            return False

    def _row_to_item(self, row: sqlite3.Row) -> ProjectItem:
        """Convert a database row to a ProjectItem"""
        base_data = {
            'id': row['id'],
            'name': row['name'],
            'item_type': row['item_type'],
            'parent_id': row['parent_id'],
            'order': row['order_index'],
            'created': row['created'],
            'modified': row['modified']
        }

        # Parse extended data
        extended_data = json.loads(row['data']) if row['data'] else {}
        full_data = {**base_data, **extended_data}

        # Create appropriate object type
        item_type = ItemType(row['item_type'])

        if item_type == ItemType.SCENE:
            return Scene.from_dict(full_data)
        elif item_type == ItemType.CHAPTER:
            return Chapter.from_dict(full_data)
        elif item_type == ItemType.PART:
            return Part.from_dict(full_data)
        elif item_type == ItemType.CHARACTER:
            return Character.from_dict(full_data)
        elif item_type == ItemType.LOCATION:
            return Location.from_dict(full_data)
        elif item_type == ItemType.PLOT_THREAD:
            return PlotThread.from_dict(full_data)
        else:
            return ProjectItem.from_dict(full_data)

    def get_word_count(self, project_id: str) -> int:
        """Get total word count for all scenes in project"""
        cursor = self.conn.cursor()
        cursor.execute('''
                       SELECT data
                       FROM items
                       WHERE project_id = ?
                         AND item_type = ?
                       ''', (project_id, ItemType.SCENE.value))

        total = 0
        for row in cursor.fetchall():
            data = json.loads(row['data']) if row['data'] else {}
            total += data.get('word_count', 0)

        return total

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def utc_now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    h = hashlib.sha256()
    h.update((text or "").encode("utf-8", errors="ignore"))
    return h.hexdigest()


@dataclass
class InsightRecord:
    id: str
    project_id: str
    scope: str              # "scene" | "chapter" | "book"
    scope_id: Optional[str] # scene_id/chapter_id or None for book
    insight_type: str       # "timeline" | "consistency" | "style" | ...
    payload: Dict[str, Any]
    source_hash: str
    created: str
    modified: str


class InsightDatabase:
    """
    Stores AI analysis results and meta-layer artifacts (story bible, thread maps, etc).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def ensure_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                scope TEXT NOT NULL,
                scope_id TEXT,
                insight_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                created TEXT NOT NULL,
                modified TEXT NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_insights_project ON insights(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_insights_scope ON insights(project_id, scope, scope_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_insights_type ON insights(project_id, insight_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_insights_hash ON insights(project_id, scope, scope_id, insight_type, source_hash)")
        self.conn.commit()

    def upsert(self,
               insight_id: str,
               project_id: str,
               scope: str,
               scope_id: Optional[str],
               insight_type: str,
               payload: Dict[str, Any],
               source_hash: str) -> None:
        now = utc_now_iso()
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO insights (id, project_id, scope, scope_id, insight_type, payload_json, source_hash, created, modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                payload_json=excluded.payload_json,
                source_hash=excluded.source_hash,
                modified=excluded.modified
        """, (
            insight_id,
            project_id,
            scope,
            scope_id,
            insight_type,
            json.dumps(payload, ensure_ascii=False),
            source_hash,
            now,
            now
        ))
        self.conn.commit()

    def get_latest(self, project_id: str, scope: str, scope_id: Optional[str], insight_type: str) -> Optional[InsightRecord]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM insights
            WHERE project_id=? AND scope=? AND (scope_id IS ? OR scope_id=?)
              AND insight_type=?
            ORDER BY modified DESC
            LIMIT 1
        """, (project_id, scope, scope_id, scope_id, insight_type))
        row = cur.fetchone()
        return self._row_to_record(row) if row else None

    def exists_with_hash(self, project_id: str, scope: str, scope_id: Optional[str], insight_type: str, source_hash: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 1 FROM insights
            WHERE project_id=? AND scope=? AND (scope_id IS ? OR scope_id=?)
              AND insight_type=? AND source_hash=?
            LIMIT 1
        """, (project_id, scope, scope_id, scope_id, insight_type, source_hash))
        return cur.fetchone() is not None

    def list_by_scope(self, project_id: str, scope: str, scope_id: Optional[str]) -> List[InsightRecord]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM insights
            WHERE project_id=? AND scope=? AND (scope_id IS ? OR scope_id=?)
            ORDER BY modified DESC
        """, (project_id, scope, scope_id, scope_id))
        rows = cur.fetchall()
        return [self._row_to_record(r) for r in rows]

    def delete_scope(self, project_id: str, scope: str, scope_id: Optional[str]) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            DELETE FROM insights
            WHERE project_id=? AND scope=? AND (scope_id IS ? OR scope_id=?)
        """, (project_id, scope, scope_id, scope_id))
        self.conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> InsightRecord:
        return InsightRecord(
            id=row["id"],
            project_id=row["project_id"],
            scope=row["scope"],
            scope_id=row["scope_id"],
            insight_type=row["insight_type"],
            payload=json.loads(row["payload_json"]),
            source_hash=row["source_hash"],
            created=row["created"],
            modified=row["modified"],
        )