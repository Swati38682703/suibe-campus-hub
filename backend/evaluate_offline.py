"""Run: ./.venv/Scripts/python.exe -m backend.evaluate_offline. Uses an isolated demo DB."""
import csv
import json
import os
import tempfile
import time
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as directory:
        os.environ['DATABASE_URL']='sqlite:///'+str(Path(directory)/'evaluation.db')
        from fastapi.testclient import TestClient
        from .app.main import app,attempts
        from .app.database import engine
        assert Path(engine.url.database).resolve()==(Path(directory)/'evaluation.db').resolve()
        os.environ.pop('LLM_API_KEY',None)
        row=dict(name='合成评测课程',day=5,start=6,end=7,weeks='1-19',semester='2026-2027-1')
        cases=[
            ('期末日期','2026-10-16 这学期期末考试什么时候？',{},['2027-01-04','2027-01-15'],'get_calendar'),
            ('下学期期末','2026-10-16 下学期期末考试什么时候？',{},['2027-06-21','2027-07-02'],'get_calendar'),
            ('寒假','2026-10-16 寒假什么时候？',{},['2027-01-25','2027-02-27'],'get_calendar'),
            ('暑假','2026-10-16 暑假什么时候？',{},['2027-07-12','2027-09-04'],'get_calendar'),
            ('当前周次','2026-10-16 是第几周？',{},['第 5 周'],'get_calendar'),
            ('节日边界','2027-03-01 清明放假几天？',{},['2027-04-05','不代表完整调休'],'get_calendar'),
            ('未知学期','2028-2029第一学期期末什么时候？',{},['未找到'],'get_calendar'),
            ('学期外周次','2027-01-30 是第几周？',{},['不计教学周次'],'get_calendar'),
            ('生成草稿','生成2027-09-13开始、19周的校历',{},['2028-01-23','草稿'],'draft_calendar'),
            ('拒绝非周一','生成2027-09-14开始、19周的校历',{},['周一'],''),
            ('生成缺参','帮我生成校历',{},['请提供开学首周'],''),
            ('分享授权','2026-10-16 根据课表找下午连续两节空档和教室',{},['勾选'],'read_timetable'),
            ('避开课程','2026-10-16 根据课表找下午连续两节空档和教室，从图书馆导航',{'share_timetable':True,'timetable':[row]},['已避开第 6、7','推荐'],'find_free_periods,find_rooms,plan_route'),
            ('没有空档','2026-10-16 根据课表找下午连续两节空档和教室',{'share_timetable':True,'timetable':[dict(row,end=10)]},['没有连续'],'find_free_periods'),
            ('按周次过滤','2026-10-16 根据课表找下午连续两节空档和教室',{'share_timetable':True,'timetable':[dict(row,end=10,weeks='1-4')]},['第 6、7 节','推荐'],'find_free_periods,find_rooms'),
            ('按学期过滤','2026-10-16 根据课表找下午连续两节空档和教室',{'share_timetable':True,'timetable':[dict(row,end=10,semester='2026-2027-2')]},['第 6、7 节','推荐'],'find_free_periods,find_rooms'),
            ('非个人连续查询','2026-10-16 下午找连续两节的教室',{},['推荐'],'find_rooms'),
            ('没有教室不导航','2026-10-16 下午找10000人的教室，从图书馆导航',{},['没有空闲教室'],'find_rooms'),
            ('明确节次','2026-10-16 第3-4节找40人教室，从图书馆导航',{},['第 3、4 节','推荐'],'find_rooms,plan_route'),
            ('百度已核对路线','从图书馆到学思楼怎么走？',{},['270','百度'],'plan_route'),
        ]
        results=[]
        try:
            with TestClient(app) as client:
                for title,message,context,expected,required in cases:
                    attempts.clear();start=time.perf_counter()
                    response=client.post('/api/agent/chat',json=dict(message=message,**context));data=response.json()
                    tools=[t['tool'] for t in data.get('trace',[])]
                    passed=response.status_code==200 and all(s in data.get('answer','') for s in expected) and all(t in tools for t in required.split(',') if t)
                    if title in ['没有教室不导航','没有空档','分享授权']: passed=passed and 'plan_route' not in tools
                    if title=='避开课程': passed=passed and next(t['result'] for t in data['trace'] if t['tool']=='find_free_periods')['windows']==[[8,9],[9,10]]
                    results.append(dict(task=title,input=message,context=json.dumps(context,ensure_ascii=False),expected='；'.join(expected)+'；工具：'+required,passed=passed,mode=data.get('mode'),elapsed_ms=round((time.perf_counter()-start)*1000,2),tools=' → '.join(tools),actual=data.get('answer',str(data))))
        finally: engine.dispose()
        path=root/'docs/offline-agent-evaluation.csv'
        with path.open('w',encoding='utf-8-sig',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
        print(json.dumps(dict(mode='offline',database='isolated synthetic demo',passed=sum(r['passed'] for r in results),total=len(results),failed=[r['task'] for r in results if not r['passed']],output=str(path)),ensure_ascii=False))
        return all(r['passed'] for r in results)

if __name__=='__main__': raise SystemExit(0 if main() else 1)
