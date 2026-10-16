import os
from pathlib import Path
from sqlalchemy import create_engine, String, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
from .database_url import normalize_database_url
database_url = normalize_database_url(os.getenv('DATABASE_URL') or f'sqlite:///{ROOT / "campus.db"}')
engine = create_engine(database_url, pool_pre_ping=True, **({'connect_args': {'check_same_thread': False}} if database_url.startswith('sqlite') else {}))
Session = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Record(Base):
    __tablename__ = 'catalog'
    kind: Mapped[str] = mapped_column(String(40), primary_key=True)
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)

class Review(Base):
    __tablename__ = 'reviews'
    __table_args__ = (UniqueConstraint('course_id','identity_hash','semester'),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(100))
    semester: Mapped[str] = mapped_column(String(40))
    identity_hash: Mapped[str] = mapped_column(String(64))
    token_hash: Mapped[str] = mapped_column(String(64))
    nickname: Mapped[str] = mapped_column(String(24))
    overall: Mapped[int] = mapped_column(Integer)
    dimensions: Mapped[list] = mapped_column(JSON)
    tags: Mapped[list] = mapped_column(JSON)
    text: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    created_at: Mapped[str] = mapped_column(String(40))

class Feedback(Base):
    __tablename__ = 'feedback'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)

def initialize():
    from .seed import catalogs
    from .campus_map import LAYOUT_VERSION
    from .life_guide import GUIDE
    from .academic_calendar import CALENDARS
    Base.metadata.create_all(engine)
    with Session.begin() as s:
        for kind,items in catalogs().items():
            if not s.query(Record).filter_by(kind=kind).first():
                for i,item in enumerate(items):
                    s.add(Record(kind=kind,id=str(item.get('id',i)),data=item))
        s.flush()
        legacy=s.get(Record,('buildings','A'))
        if legacy and ((legacy.data.get('x')==90 and legacy.data.get('z')==60 and not legacy.data.get('layout_version')) or legacy.data.get('layout_version') in ['reference-map-v2','reference-map-v3','reference-map-v4','reference-map-v5','baidu-reference-v6']):
            kinds=['buildings','nodes','edges','facilities','landscape']
            snapshot={k:[r.data for r in s.query(Record).filter_by(kind=k).all()] for k in kinds}
            s.merge(Record(kind='map_backup',id='before-'+LAYOUT_VERSION,data=snapshot))
            for k in kinds:
                s.query(Record).filter_by(kind=k).delete(synchronize_session='fetch')
                for i,row in enumerate(catalogs()[k]):
                    s.add(Record(kind=k,id=str(row.get('id',i)),data=row))
        for row in GUIDE:
            if not s.get(Record,('knowledge',row['id'])):
                s.add(Record(kind='knowledge',id=row['id'],data=row))
        for row in CALENDARS:
            existing=s.get(Record,('calendar',row['id']))
            if not existing or existing.data.get('source')=='示例学期起止，待官方校历核验':
                if existing:
                    s.merge(Record(kind='calendar_backup',id=row['id']+'-before-user-images',data=existing.data))
                s.merge(Record(kind='calendar',id=row['id'],data=row))

def items(kind):
    with Session() as s:
        return [r.data for r in s.query(Record).filter_by(kind=kind).all()]

def get(kind, id):
    with Session() as s:
        r = s.get(Record,(kind,id))
        return r.data if r else None
