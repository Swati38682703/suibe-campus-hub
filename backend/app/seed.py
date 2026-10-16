from datetime import date
from .campus_map import BUILDINGS, NODES, EDGES, FACILITIES, LANDSCAPE
from .life_guide import GUIDE

def catalogs():
    from .academic_calendar import CALENDARS
    rooms = [dict(id=f'{b}{floor}0{number}', name=f'{b}{floor}0{number}', building=b, floor=floor, capacity=30+number*15, type='机房' if b=='INFO' else '多媒体', facilities=['空调','投影','插座'], source='系统生成的演示数据', updated_at=date.today().isoformat()) for b in ['A','B','C','D','INFO'] for floor in [1,2,3] for number in [1,2,3]]
    teachers = [dict(id=f't{i}',name=name,pinyin=pinyin,department=dept,title=title,email=f'teacher{i}@example.com',research=research,office='演示办公室',source='虚构教师，非学校教师名录',updated_at=date.today().isoformat()) for i,(name,pinyin,dept,title,research) in enumerate([('陈示例','csl','国际经贸学院','教授','国际贸易'),('林示例','lsl','统计与信息学院','副教授','人工智能 数据分析'),('周示例','zsl','金融管理学院','讲师','金融科技'),('张示例','zsl','工商管理学院','教授','商业管理'),('王示例','wsl','外语学院','副教授','商务英语')])]
    courses = [dict(id=f'c{i}',code=f'DEMO{i:03}',name=n,department=d,credit=cr,semester='2026-2027-1',teacher=t,source='演示课程，非教务系统数据') for i,(n,d,cr,t) in enumerate([('国际贸易理论','国际经贸学院',3,'陈示例'),('Python 数据分析','统计与信息学院',3,'林示例'),('金融学导论','金融管理学院',2,'周示例'),('商务英语','外语学院',2,'王示例'),('管理学原理','工商管理学院',3,'张示例')])]
    announcements = [dict(id=f'a{i}',title=t,department='Campus Hub 演示',date=date.today().isoformat(),pinned=i==0,content=c,source='示例公告') for i,(t,c) in enumerate([('欢迎体验校园智慧服务平台','当前教室、教师、课程和地图数据均用于演示；不代表学校实时信息。'),('让校园服务，从一句话开始','试试：今天下午找一间至少 40 人的自习教室，从图书馆怎么走？'),('课表保存在你的设备上','通过 JSON 备份导出课表，换设备后可重新导入。')])]
    knowledge = [dict(id='k1',title='平台数据说明',text='教室和占用信息为示例数据，教师身份与邮箱为虚构，地图坐标及距离为示意，无法作为实际导航依据。',source='项目说明'),dict(id='k2',title='办事导航',text='成绩单、电子证明等流程性办事请进入学校一网通办办事大厅。本平台提供信息导航，不代办、不收集学校密码。',source='需求文档：与办事大厅关系'),dict(id='k3',title='个人课表',text='公开浏览模式不需要登录。个人课表仅存在当前浏览器，可导出 JSON 备份。学校统一认证尚未接入。',source='需求文档：个人课程表'),dict(id='k4',title='课程点评',text='点评只供选课参考，提交后进入人工审核。邮箱仅用于生成身份哈希，不能证明学生身份；每邮箱每课程每学期限一次。',source='项目点评规则')]
    return {'rooms':rooms,'teachers':teachers,'courses':courses,'announcements':announcements,'buildings':BUILDINGS,'nodes':NODES,'edges':EDGES,'facilities':FACILITIES,'landscape':LANDSCAPE,'knowledge':knowledge+GUIDE,'calendar':CALENDARS}
