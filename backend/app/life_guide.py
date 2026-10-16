SOURCE='https://mp.weixin.qq.com/s/3krHoFzwJse49K7HLUx7VA'
def entry(id,title,category,text,keywords,building=None):
    return dict(id=id,title=title,category=category,text=text,keywords=keywords,building=building,source='SUIBE学工在线 · 生活服务指南',source_url=SOURCE,published_at='2026-09-09',notice='依据参考文章整理，实际安排以学校最新通知与原系统为准')

GUIDE=[
    entry('life-repair','校园设施报修','报修','松江与长宁校区可扫描场所二维码，或从一网通办进入“我要报修”。学生公寓一期、三期及文贸楼使用学校公众号的一站式社区“接诉即办（维修）”；六期按原文电话渠道报修。','维修 报修 宿舍 故障'),
    entry('life-dining','思源餐厅供餐提示','餐饮','参考文章注明思源餐厅仅工作日供餐。具体餐饮点和服务时间请查看原文图表及最新通知。','食堂 吃饭 餐饮 思源餐厅','SIYUAN'),
    entry('life-shuttle','短驳与通勤预约','出行','短驳车自 2026 年 9 月 14 日起需在“交我行”小程序预约，运行时间以预约系统为准。六期通勤班车也采用预约与扫码检票，请按原文入口操作。','班车 短驳 交通 通勤 预约'),
    entry('life-staffbus','教职工班车适用范围','出行','文章中的教职工班车仅限本校教职工，须持本人校园卡；不要与学生短驳、六期通勤混淆。','教职工 班车 校园卡'),
    entry('life-parcel','一期 / 三期收货地址','收货','一期、三期快递：上海市松江区广富林街道文汇路600弄上海对外经贸大学学生公寓XX号楼。外卖需补充“移动门”或“派出所门”，避免误送邻校。','快递 外卖 收货 地址 一期 三期'),
    entry('life-parcel-six','六期 / 文贸楼收货地址','收货','六期：上海市松江区三新北路1800弄XX号楼。文贸楼：上海市松江区文翔路1900号上海对外经贸大学文贸楼学生公寓（西一门）。','六期 文贸楼 快递 外卖 收货 地址'),
    entry('life-community','社区便民与活动空间','社区','“悦享家”可办理水电充值、物业报修等社区事务；“梦享家”提供自习与社区活动空间。具体地点和使用规则请查原文。','社区 自习 充值 水电 悦享家 梦享家'),
]
