"""Explicit demonstration menus; shared reviews use the existing moderation lifecycle."""
from fastapi import APIRouter
from .database import Session, Review

router = APIRouter()
MENU = [
    ('d01','第一餐厅','1F · 家常小炒','番茄炒蛋饭',12,'🍅','家常','酸甜开胃的一餐'),
    ('d02','第一餐厅','1F · 家常小炒','宫保鸡丁饭',15,'🍛','微辣','下课后的充电选手'),
    ('d03','第一餐厅','1F · 面食档','红烧牛肉面',16,'🍜','面食','一碗热汤，安慰早八'),
    ('d04','第一餐厅','1F · 面食档','鲜肉小馄饨',10,'🥟','清淡','清爽热汤与小小满足'),
    ('d05','第二餐厅','1F · 香锅档','麻辣香锅',22,'🌶️','香辣','把喜欢的食材装进一锅'),
    ('d06','第二餐厅','1F · 香锅档','麻辣烫',18,'🥘','香辣','自由搭配的午间灵感'),
    ('d07','第二餐厅','2F · 轻食档','鸡胸肉沙拉',18,'🥗','清淡','给忙碌日常一点清新'),
    ('d08','第二餐厅','2F · 轻食档','紫薯杂粮碗',14,'🍠','杂粮','彩色的一碗小确幸'),
    ('d09','第三餐厅','1F · 早餐档','现磨豆浆套餐',8,'🥛','早餐','从热乎乎的一口开始'),
    ('d10','第三餐厅','1F · 早餐档','鸡蛋煎饼',9,'🥞','早餐','赶课路上的香脆搭子'),
    ('d11','第三餐厅','2F · 风味档','照烧鸡腿饭',16,'🍗','家常','酱香与米饭的默契'),
    ('d12','第三餐厅','2F · 风味档','咖喱土豆饭',13,'🍛','微辣','温柔浓郁的咖喱时刻'),
]
DISHES = [dict(id=i,restaurant=r,window=w,name=n,price=p,emoji=e,tag=t,description=d,semester='2026-2027-1',demo=True) for i,r,w,n,p,e,t,d in MENU]

@router.get('/api/dining')
def dining():
    with Session() as s:
        reviews=s.query(Review).filter(Review.course_id.in_(['food:'+d['id'] for d in DISHES]),Review.status=='normal').all()
        result=[]
        for dish in DISHES:
            rows=sorted([r for r in reviews if r.course_id=='food:'+dish['id']],key=lambda r:r.created_at,reverse=True)
            result.append({**dish,'count':len(rows),'average':round(sum(r.overall for r in rows)/len(rows),1) if rows else None,'reviews':[dict(id=r.id,nickname=r.nickname,overall=r.overall,dimensions=r.dimensions,tags=r.tags,text=r.text,created_at=r.created_at) for r in rows]})
        return result
