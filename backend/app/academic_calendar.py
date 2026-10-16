"""Transcribed from the two school-calendar images supplied by the user."""
def event(id,title,start,end=None,kind='teaching',note=''):
    return dict(id=id,title=title,start=start,end=end or start,kind=kind,note=note)

CALENDARS=[
    dict(id='2026-2027-1',school='上海对外经贸大学',academicYear='2026-2027',term=1,title='2026–2027 学年第一学期',start='2026-09-14',end='2027-01-24',weeks=19,source='用户提供的学校校历图片，按中文教学事项整理',source_image='/assets/calendar-2026-2027-1.jpg',version='user-images-20261016',vacation=dict(title='寒假',start='2027-01-25',end='2027-02-27'),events=[
        event('makeup-1','补考、缓考','2026-09-10','2026-09-20','exam','9月10日至13日及开学第一周；具体科目以考试通知为准。'),
        event('freshmen','新生报到','2026-09-12',kind='registration',note='16:00前；本科生、研究生、专升本、第二学士学位、预科新生。'),
        event('registration-1','老生注册','2026-09-13',kind='registration',note='16:00前；本科生、研究生老生。'),
        event('classes-1','老生及专升本等学生上课','2026-09-14',note='所有老生及专升本、第二学士学位、预科新生。'),
        event('graduate','研究生新生上课','2026-09-17'),
        event('training','本科新生军训、入学教育','2026-09-17','2026-09-30','training'),
        event('midautumn','中秋节','2026-09-25',kind='holiday'),
        event('national','国庆节','2026-10-01',kind='holiday'),
        event('undergraduate','本科新生上课','2026-10-08'),
        event('newyear','元旦','2027-01-01',kind='holiday'),
        event('finals-1','期末停课考试','2027-01-04','2027-01-15','exam'),
        event('practice-1','社会实践、劳动教育、创新创业拓展','2027-01-18',kind='practice',note='1月18日起；校历未注明结束日期，不推定结束日。'),
        event('winter','寒假','2027-01-25','2027-02-27','vacation'),
        event('springfestival','春节','2027-02-06',kind='holiday'),
    ]),
    dict(id='2026-2027-2',school='上海对外经贸大学',academicYear='2026-2027',term=2,title='2026–2027 学年第二学期',start='2027-03-01',end='2027-07-11',weeks=19,source='用户提供的学校校历图片，按中文教学事项整理',source_image='/assets/calendar-2026-2027-2.jpg',version='user-images-20261016',vacation=dict(title='暑假',start='2027-07-12',end='2027-09-04'),events=[
        event('makeup-2','补考、缓考','2027-02-25','2027-03-07','exam','2月25日至28日及开学第一周；具体科目以考试通知为准。'),
        event('registration-2','全体学生注册','2027-02-28',kind='registration',note='16:00前。'),
        event('classes-2','全体学生上课','2027-03-01'),
        event('qingming','清明节','2027-04-05',kind='holiday'),
        event('labour','劳动节','2027-05-01',kind='holiday'),
        event('dragonboat','端午节','2027-06-09',kind='holiday'),
        event('finals-2','期末停课考试','2027-06-21','2027-07-02','exam'),
        event('practice-2','社会实践、劳动教育、创新创业拓展','2027-07-05',kind='practice',note='7月5日起；校历未注明结束日期，不推定结束日。'),
        event('summer','暑假','2027-07-12','2027-09-04','vacation'),
    ]),
]
