# 学校 HiAgent 接入验收

更新时间：2026-10-19（Asia/Shanghai）

## 接入结果
- 正式网站：https://suibe-campus-hub.onrender.com
- 学校智能体：贸大校园助手，APPID dbamdc9b9rsehbmnp3fg。
- 已选择 SUIBE-QwenClaw（平台显示基础模型 qwen3.5-27b），配置版本 v1.0.2。API 已启用，Web/MCP/WebSDK 仍停用。
- 学校 API 地址：https://agent.suibe.edu.cn/api/proxy/api/v1。
- 专用密钥仅存本地被忽略的 .env 与 Render 后端秘密配置；未写入源码。临时导入文件已删除。
- 正式 Render 配置已移除 LLM_API_KEY。学校服务失败不会自动转个人模型。
- 正式健康接口已返回 agent_provider=hiagent，Render 到学校 API 的真实调用已成功。

## 功能保留
网站继续执行原有十项工具，保留 trace、引用来源和页面入口；未分享的课表不会传给模型。每次请求独立学校会话，消息中只包含本次限定历史，避免跨用户混用。

本地真实 API 已验证教师、课程、校历、真实教室占用、路线、赛事、食堂、报修、未分享课表限制及合成课表空档。线上已验证课程、报修、课表分享控制、教室和赛事；最终修正后的校历线上复验已通过（HTTP 200，周次与考试起止日期准确）。

校历完整资料返回14项教学事项，复测正确：2026-10-20为第6周，期末停课考试2027-01-04至2027-01-15。

## 修正与测试
- 学校模型每轮一个工具请求，避免多个请求拼接出错。
- 校历向模型提供完整资料，避免组合主题筛选漏掉考试日期。
- 对模型偶发漏写闭合括号，仅补齐 JSON 容器结束符，不修改字符串、字段或参数；仍验证工具白名单和参数对象；格式失败最多重试一次。
- 完整后端测试：55 passed。
- 真实线上工具查询普通约3–5秒，教室约16秒，取决于学校接口。
- 线上验收记录：tmp/hiagent-production-acceptance.json、tmp/hiagent-production-tools.json（仅公开测试问题与合成课表）。

## 选型依据与限制
同题小样本对照：QwenFast曾提前编造教室；QwenClaw正确请求查询、区分截止与未知；671B服务调试报错。因此选QwenClaw。不是全面性能排名，也不能保证永远不误答。学校可用额度、并发和长期使用政策仍以学校规定为准。

## 部署
代码分支 codex/cloud-deploy；最终修正提交 e68fe2e。最终部署 dep-dbao72h42hec73dr7iig 已 Live（e68fe2ee29b204d275a2b4266dc8cd4b8033411e）。最终线上健康状态 agent_provider=hiagent，校历复验 passed=true。

官方资料：
- https://agent.suibe.edu.cn/platform/doc/
- https://365.kdocs.cn/l/cjqE1h9vo7Fh
