# 校园探索手账视觉改版

已确认的三屏设计落实到 React 页面，保留课表、点评审核、拍照集邮和赛事收藏。

## 学思楼横幅

- 路径：`frontend/public/assets/xuesi-comic.png`
- 工具：内置 image_gen，参考用户提供的学思楼照片与已批准的设计稿。
- 提示词：Create one standalone wide landscape website hero illustration asset, roughly 2.4:1. Reproduce the cream curved colonnade and repeating tall arches recognizably as in the supplied SUIBE Xuesi building photo, illustrated in the clean charming comic style of the approved homepage mockup. Building occupies RIGHT 70%, curves down into distance toward left. Pale sky blue sky, soft fluffy white clouds, warm apricot sunlit arches, coral-pink rear building, mint shrubs and small blue bird at right. LEFT 40% mostly quiet light blue sky for HTML text overlay. Warm fresh collegiate mood, polished fine clean outlines and subtle dimensional shading. NO text, typography, UI, QR code, black bars, frame or phone screen; one full bleed banner.

## 食堂资料与图片

- 学校后勤： https://mp.weixin.qq.com/s/bNB98UdWS7k3B3LyHk3-pA
- 发布：2026-10-07；标题：“食”力亮相｜SUIBE文贸餐厅焕新启幕。
- 三张餐食配图：`frontend/public/assets/wenmao-food-1.jpg` 至 `wenmao-food-3.jpg`，保留来源标注。原文没有逐图菜名、窗口、价格，因此不将配图与菜品逐一绑定。
- 文贸餐厅文章提及手撕鸡饭、江西小炒、四季轻食、烤盘饭；窗口和价格待核实，使用新 ID。旧版演示数据单独显示，原有点评与照片不更换绑定对象。
- 一食堂只确认开放就餐，暂不沿用旧文章窗口清单。
