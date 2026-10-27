"""Persistent, machine-local editor preferences."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SETTINGS=ROOT/'private-inputs'/'editor-settings.json'
DEFAULT_BUILD_NAME='Alundra Mod'

def load_preferences(settings=SETTINGS):
    try:
        result=json.loads(Path(settings).read_text(encoding='utf-8'))
        return result if isinstance(result,dict) else {}
    except (OSError,ValueError,TypeError):
        return {}

def save_preferences(values,settings=SETTINGS):
    target=Path(settings);target.parent.mkdir(parents=True,exist_ok=True)
    merged=load_preferences(target);merged.update(values)
    temp=target.with_name(target.name+'.tmp')
    temp.write_text(json.dumps(merged,indent=2)+'\n',encoding='utf-8')
    temp.replace(target)
    return merged

def safe_build_name(value):
    """Return a readable Windows-safe filename stem or raise a clear error."""
    name=str(value).strip()
    for suffix in ('.alundramod','.bin','.cue'):
        if name.lower().endswith(suffix):name=name[:-len(suffix)].rstrip()
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',name).rstrip(' .')
    if not name or name in {'.','..'}:
        raise ValueError('Enter a project build name before saving or building.')
    return name


def project_output_paths(name=None, root=ROOT):
    """Project-owned folder (the .alundramod) and the built game, which goes to builds/
    (one build per mod name, replaced by the next build; user 2026-10-20)."""
    stem = safe_build_name(project_build_name() if name is None else name)
    folder = Path(root) / "private-inputs" / stem
    builds = Path(root) / "builds"
    return {"folder": folder, "mod": folder / f"{stem}.alundramod", "builds": builds,
            "bin": builds / f"{stem}.bin", "cue": builds / f"{stem}.cue"}

def selected_game_bin(settings=SETTINGS):
    raw=load_preferences(settings).get('game_bin_path')
    if not raw:return None
    path=Path(raw).expanduser()
    return path if path.is_file() and path.suffix.lower()=='.bin' else None

def project_build_name(settings=SETTINGS):
    raw=load_preferences(settings).get('project_build_name',DEFAULT_BUILD_NAME)
    try:return safe_build_name(raw)
    except ValueError:return DEFAULT_BUILD_NAME
