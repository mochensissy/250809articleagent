from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def update_workflow_step(workflow_path: Path, step_key: str, status: str) -> None:
    state = read_json(workflow_path)
    if not state:
        state = {"current_step": "", "steps": {}, "checkpoints": {"last_chapter_done": 0}}
    steps = state.setdefault("steps", {})
    steps[step_key] = status
    state["current_step"] = step_key
    write_json(workflow_path, state)


