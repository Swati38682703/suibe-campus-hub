"""Relative layout traced from the user's annotated campus illustration; not surveyed coordinates."""
import math
from .map_reference import reference_position,raw_position

LAYOUT_VERSION='baidu-reference-v7'
DISPLAY_SCALE=.84
GUIDE_URL='https://www.suibe.edu.cn/tsxy/2024/1009/c18706a175364/page.htm'

def position(px,py):
    return reference_position(px,py)

def building(id,name,px,py,width,depth,floors,type,description,entrance=None,shape='box'):
    return dict(id=id,name=name,**position(px,py),px=px,py=py,width=width,depth=depth,floors=floors,type=type,description=description,shape=shape,entrance=position(*(entrance or (px+18,py+22))),layout_version=LAYOUT_VERSION,source='用户提供的校园分布图；建筑名称参照学校校园导览',source_url=GUIDE_URL,coordinate_note='相对位置据原图重建；建筑高度、入口与距离为示意')

BUILDINGS=[
    building('A','学思楼 A',615,350,22,43,4,'teaching','按原图红色标注，A 楼位于图文信息楼东侧、学思楼组团前端。',(637,378),'teaching'),
    building('B','学思楼 B',581,321,22,43,4,'teaching','按原图红色标注，位于 A 与 C 楼之间。',(603,349),'teaching'),
    building('C','学思楼 C',551,288,22,43,4,'teaching','按原图红色标注，位于 B 与 D 楼之间。',(573,316),'teaching'),
    building('D','学思楼 D',517,267,22,43,4,'teaching','按原图红色标注，位于学思楼组团后端、学院楼附近。',(536,291),'teaching'),
    building('INFO','图文信息楼',420,376,45,29,5,'teaching','位于教学区与思源湖之间，机房及大型教学空间。',(458,408),'information'),
    building('LIB','图书馆',420,490,38,36,5,'library','临思源湖，按原图重建的圆弧式图书馆体量。',(466,514),'library'),
    building('XZ','行知楼',326,218,26,21,3,'service','学校校园导览列有教学服务、学生事务、艺术沙龙等空间。',(342,242)),
    building('LQ','乐群楼',270,268,23,24,4,'service','原图中位于行知楼与思源餐厅之间。',(288,295)),
    building('BW','博闻楼',380,245,29,26,5,'academic','学院办公楼组团；名称见学校官网校园导览。',(397,270)),
    building('BC','博萃楼',437,222,27,25,5,'academic','学院办公楼组团，位于博闻楼后侧。',(450,249)),
    building('BY','博雅楼',491,248,29,24,4,'academic','学院办公楼组团，位于学思楼 D 后方附近。',(506,271)),
    building('BS','博识楼',444,282,30,26,4,'academic','学院办公楼组团，位于图文信息楼后侧。',(460,308)),
    building('HISTORY','校史馆',363,191,22,15,2,'culture','按提供的分布图标注展示；开放安排请向学校确认。',(372,211)),
    building('DZ','德政楼',218,379,26,22,4,'service','学校官网校园导览列为行政办公楼。',(238,402)),
    building('LIUDE','淞滨楼',196,441,25,22,4,'service','名称据原图标注；功能与开放信息待核验。',(215,457)),
    building('FOOD','学生餐厅',115,363,39,25,3,'dining','校园餐饮点，具体营业时间以学校最新服务指南为准。',(143,386)),
    building('SIYUAN','思源餐厅',210,293,28,22,3,'dining','生活服务指南注明仅工作日供餐，后续安排以原文更新为准。',(235,317)),
    building('SHOP','教育超市',165,320,24,18,2,'shopping','原图标注的校园购物点；营业信息待核验。',(187,341)),
    building('GYM','体育馆',715,213,54,35,2,'sports','学校导览介绍羽毛球、乒乓球等运动空间，毗邻田径场。',(744,248),'gym'),
    building('GATE','校门（原图）',670,579,32,9,1,'gate','原图底部出入口，尚未核实正式门名，保留原图称谓。',(670,583),'gate'),
    building('XUESI','学思楼（整体点位）',633,399,2,2,1,'waypoint','百度地图的学思楼整体点位；已保存图书馆到此处的步行查询结果。A–D 各栋入口尚未单独核验。',(633,399),'waypoint'),
]
# Ground footprints are estimated separately from the roof labels in the isometric drawing.
# The four classroom wings are narrow, parallel bars behind a common arcade, not four solid blocks.
GROUND_POINTS={'A':(657,380),'B':(620,357),'C':(581,337),'D':(543,317),'INFO':(420,400),'LIB':(420,517),'XZ':(326,245),'LQ':(270,295),'BW':(380,285),'BC':(437,260),'BY':(491,285),'BS':(444,322),'HISTORY':(363,209),'DZ':(218,403),'LIUDE':(196,460),'FOOD':(115,386),'SIYUAN':(210,317),'SHOP':(165,342),'GYM':(715,251),'GATE':(670,579)}
for b in BUILDINGS:
    b.update(position(*GROUND_POINTS.get(b['id'],(b['px'],b['py']))))
    b['height']=27 if b['shape']=='teaching' else 29 if b['id']=='INFO' else 27 if b['id']=='LIB' else 26 if b['id']=='GYM' else 22 if b['type']=='academic' else b['floors']*5
    if b['shape']=='teaching':
        b['width']=6
        b['depth']=46
        b['description']='四条平行教学楼体与前后连通部分围合成一个整体；立面有三处连续拱洞，按原图建模。A–D 名称顺序沿用先前标注。'
anchor=next(b for b in BUILDINGS if b['id']=='XUESI')
for b in BUILDINGS:
    if b['shape']=='teaching':
        b['x']=round(anchor['x']-'ABCD'.index(b['id'])*28,1)
        b['z']=round(anchor['z']-31,1)
ENTRANCE_POINTS={'A':(633,399),'B':(585,389),'C':(549,369),'D':(515,350),'INFO':(465,431),'LIB':(466,530)}
for b in BUILDINGS:
    if b['id'] in ENTRANCE_POINTS:
        b['entrance']=position(*ENTRANCE_POINTS[b['id']])
    if b['shape']=='teaching':
        b['entrance'].update(x=b['x'],z=round(b['z']+30,1))
    if b['type']=='academic':
        # Keep the four unverified college buildings as one spaced group.
        x,z=raw_position(*GROUND_POINTS[b['id']]); ex,ez=raw_position(b['entrance']['imageX'],b['entrance']['imageY'])
        b.update(x=round(x+123.3,1),z=round(z-14.4,1))
        b['entrance'].update(x=round(b['x']+ex-x,1),z=round(b['z']+ez-z,1))
SOURCE_NODES=[(170,405),(300,340),(410,285),(520,230),(640,170),(425,400),(545,340),(665,280),(780,220),(450,555),(570,490),(690,430),(810,370),(935,305),(475,520)]
NODES=[dict(id=f'r{i}',**position(*p)) for i,p in enumerate(SOURCE_NODES)]
CONNECTIONS=[(0,1),(1,2),(2,3),(3,4),(5,6),(6,7),(7,8),(9,10),(10,11),(11,12),(12,13),(1,5),(2,6),(3,7),(4,8),(5,10),(6,11),(7,12),(8,13),(9,14),(10,14)]
EDGES=[dict(source=f'r{a}',target=f'r{b}',lengthM=round(math.hypot(NODES[a]['x']-NODES[b]['x'],NODES[a]['z']-NODES[b]['z'])*.6/DISPLAY_SCALE),accessible=False) for a,b in CONNECTIONS]
FACILITIES=[]
for id,bid,kind,px,py in [('food','FOOD','dining',143,386),('siyuan','SIYUAN','dining',235,317),('service','XZ','service',342,242),('shop','SHOP','shopping',187,341),('sports','GYM','sports',744,248),('entry','GATE','entrance',670,583)]:
    FACILITIES.append(dict(id=id,building=bid,type=kind,**position(px,py),note='名称与相对位置据原图，具体入口及开放安排待核验'))

LANDSCAPE=[dict(id='layout',layout_version=LAYOUT_VERSION,source='用户提供的学校分布图（含 A–D 标注）',reference_image='/assets/campus-reference.png',lakes=[dict(name='思源湖',points=[position(*p) for p in [(252,464),(278,444),(333,451),(358,472),(350,500),(310,523),(261,509),(237,486)]]),dict(name='东侧水景（原图）',points=[position(*p) for p in [(785,422),(863,384),(918,379),(967,399),(941,431),(899,416),(858,444),(812,453)]])],courts=[dict(id='COURTS',name='篮球 / 网球场',**position(587,132),width=70,depth=60),dict(id='TRACK',name='田径场',**position(819,278),width=75,depth=47)],plaza=position(333,329),scale_note='图像相对坐标，无地理比例尺；长度与时间仅用于演示')]
