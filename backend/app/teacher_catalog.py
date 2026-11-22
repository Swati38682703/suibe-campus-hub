"""Public faculty records shared by the page and Beibei retrieval."""
import json
from pathlib import Path
from .database import get, items

FILE=Path(__file__).resolve().parents[2]/'data/teachers_official.json'
DATA=json.loads(FILE.read_text('utf-8')) if FILE.exists() else dict(teachers=[],sources=[],collectedAt=None)


def get_teachers():
    official=items('teacher_official') or DATA['teachers']
    rows={r['id']:dict(r) for r in official}
    for row in items('teachers'):
        if official and (row.get('source','').startswith('虚构教师') or row.get('email','').endswith('@example.com')):
            continue
        rows[row['id']]=row
    return list(rows.values())


def status():
    saved=get('teacher_sync','status') or {}
    official=items('teacher_official')
    base=dict(collectedAt=DATA.get('collectedAt'),count=len(DATA['teachers']),
              sources=DATA.get('sources',[]),unitsSource=DATA.get('unitsSource'))
    if official:
        base.update(count=len(official))
    base.update(saved)
    base.update(automatic=True,schedule='每年1月15日、7月15日（北京时间）',
                note='学院官网公开资料每学期开学前约一个月自动更新；采集失败时保留上一版，不代表完整或实时的在职教师名册。')
    return base
