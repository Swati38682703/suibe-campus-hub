export const beibeiThemes = {
 campus: {title:'校园搭子',greeting:'校园问题，问贝贝',hint:'校园里的大小事，陪你一起找答案',accent:'#8dbbe8',motion:'float'},
 timetable: {title:'时间规划师',greeting:'一起安排这周的学习吧',hint:'课表、空档与自习安排，陪你一起规划',accent:'#b4a0df',motion:'plan'},
 calendar: {title:'日历管理员',greeting:'考试和假期，帮你记着',hint:'教学周、考试与假期，一起查清楚',accent:'#e6bc64',motion:'plan'},
 rooms: {title:'自习领航员',greeting:'今天去哪里自习？',hint:'查教室、找空档、看路线，从这里开始',accent:'#8ebba1',motion:'read'},
 map: {title:'探路搭子',greeting:'要去哪儿？贝贝带你找',hint:'校园位置与路线，陪你一起找',accent:'#e5a366',motion:'explore'},
 dining: {title:'美食发现家',greeting:'今天想吃点什么？',hint:'食堂、菜品与就餐指南，一起看看',accent:'#edac87',motion:'taste'},
 teachers: {title:'学术联络员',greeting:'一起找找老师的信息',hint:'教师信息与公开联系方式，从这里查',accent:'#7e9fcf',motion:'read'},
 courses: {title:'选课参谋',greeting:'选课前，先做点功课',hint:'课程与学习体验，陪你一起了解',accent:'#c69ba9',motion:'read'},
 competitions: {title:'挑战搭子',greeting:'一起发现值得参加的比赛',hint:'赛事、报名条件与截止日期，一起查',accent:'#e4b764',motion:'cheer'},
 'life-guide': {title:'校园百事通',greeting:'校园生活，有事问贝贝',hint:'报修、快递与办事指南，陪你一起找',accent:'#94bfae',motion:'explore'},
 announcements: {title:'消息播报员',greeting:'看看校园里有什么新消息',hint:'校园公告与办事入口，陪你一起了解',accent:'#e3c06e',motion:'announce'},
 profile: {title:'收藏守护者',greeting:'你的校园小收藏，我陪你看',hint:'收藏、反馈与校园问题，随时来聊聊',accent:'#9bbde2',motion:'float'},
} as const;
export type BeibeiThemeId = keyof typeof beibeiThemes;
export function beibeiThemeForPath(pathname:string):BeibeiThemeId {
 const page=pathname.split('/')[1];
 return page&&page!=='campus'&&Object.prototype.hasOwnProperty.call(beibeiThemes,page)?page as BeibeiThemeId:'campus';
}
export function beibeiImage(id:BeibeiThemeId){return `/assets/beibei/${id}.webp`}
