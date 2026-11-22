"""Versioned public faculty records shared by the page and Beibei retrieval."""
import json
from pathlib import Path
from .database import items

FILE=Path(__file__).resolve().parents[2]/'data/teachers_official.json'
DATA=json.loads(FILE.read_text('utf-8')) if FILE.exists() else dict(teachers=[],sources=[],collectedAt=None)


def get_teachers():
    official=DATA['teachers']
    rows={r['id']:dict(r) for r in official}
    for row in items('teachers'):
        if official and (row.get('source','').startswith('虚构教师') or row.get('email','').endswith('@example.com')):
            continue
        rows[row['id']]=row
    return list(rows.values())


def status():
    return dict(collectedAt=DATA.get('collectedAt'),count=len(DATA['teachers']),
                sources=DATA.get('sources',[]),unitsSource=DATA.get('unitsSource'),
                automatic=False,note='本次为官网公开目录采集快照，尚未开启定时自动更新；不代表完整或实时的在职教师名册。')
