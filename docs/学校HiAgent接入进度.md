# 学校 HiAgent 接入进度（2026-10-19）

## 已完成
- 建立学校平台智能体“贸大校园助手”，APPID dbamdc9b9rsehbmnp3fg，空间 dbam8dhpub14usl62i80。
- 配置结构化 messages/tools 协议：学校智能体只负责推理，网站继续执行原有十项工具、管理课表授权、生成 trace/citations/actions。
- 发布配置 v1.0.0；API 渠道仍关闭，未创建账号 AK/SK，未配置正式服务密钥。
- 新增 backend/app/hiagent.py，使用 create_conversation + chat_query_v2 blocking，严格解析 JSON、校验工具白名单。
- 每次独立会话，不复用其他用户历史；配置 HIAGENT_API_KEY 后学校优先，失败不自动调用个人模型。
- 完整后端测试：52 passed（含新适配、原有工作流、知识检索）。这些是本地和模拟接口测试，不代表真实外部 API 已接通。

## 学校网页验证
- SUIBE-QwenFast 基础模型 qwen35-35b-a3b，支持 Function Call；教师工具调用和无结果归纳成功。
- 同题复杂约束：QwenFast 曾在请求 find_rooms 的同时虚构教室；不建议直接默认。
- SUIBE-QwenClaw 基础模型 qwen3.5-27b，支持 Function Call、深度思考；初轮未分享课表/报名日期约束通过。继续对比中。
- 满血版671B模型：网页调试返回“大模型接口调用出错，请联系管理员”。
- SUIBE-DeepSeek 仅显示 SUIBE-DS 别名，页面未标注 Function Call，尚未实测。
- 平台显示过负耗时，不能用其耗时当可靠性能基准。当前样本有限，不是全面评测。

## 尚需完成
1. 完成模型选择并保存/发布最终配置（v1.0.0 当前仍是 QwenFast）。
2. 在发布页开启 API 并渠道发布。此步骤创建持久 API 访问能力，浏览器规则要求动作时确认，需先向用户说明并确认。
3. 密钥只进后端秘密配置，不进前端/源码/聊天。真实调用应先用公开虚构样例验证，再验证 Render 网络可达性。
4. 真接口回归课程、教师、校历、教室、路线、赛事、食堂、办事、课表分享和不分享等任务。
5. 验证后部署，删除正式服务个人 LLM_API_KEY，避免意外继续个人调用；保留代码回退能力。

## 官方依据
- https://agent.suibe.edu.cn/platform/doc/ （用户指南与 API 文档）
- https://365.kdocs.cn/l/cjqE1h9vo7Fh （学校操作手册）
- 发布页已确认 API 基址：https://agent.suibe.edu.cn/api/proxy/api/v1

接口：POST /create_conversation，Header Apikey，body UserID(1-20字符)，返回 Conversation.AppConversationID。
POST /chat_query_v2：UserID、AppConversationID、Query、ResponseMode=blocking；返回 answer。

## 08:55 更新
已完成多模型对照并选择 SUIBE-QwenClaw，发布配置 v1.0.1 成功。QwenFast 在复杂指定节次任务中编造教室；QwenClaw 在相同任务中正确请求 find_rooms(date=2026-10-20, periods=[6,7])，正确区分 closed 与 unknown，未提前给出教室。样本有限。API 渠道仍关闭，正在请求用户确认持久 API 访问启用；正式网站未切换。完整后端测试52通过。

## API 启用与真实验收更新
- 用户已明确允许启用 API、专用密钥只存后端、验证后切换。API 渠道 v1.0.1 运行中；Web/MCP/WebSDK 仍停用。
- 学校智能体专用密钥已生成，存入被 Git 忽略的本地 .env，未写入源码或聊天。账号 AK/SK 未创建。
- 真实 API 已接通，教师、课程、校历、真实教室占用、路线、赛事、食堂、办事指南、未分享课表限制及合成课表空档均得到回答。
- 首轮课程有一次格式失败，复测成功；加入至多一次格式纠正重试。完整后端回归53通过。详见 tmp/hiagent-real-acceptance.json 与 tmp/hiagent-course-retry.json；这些只含公开样例/合成课表。
- 真实教室调用耗时约18秒，普通任务约2–7秒；不保证学校长期可用或不限额。
- Render MCP 两次请求均反复返回认证提示，已转官方控制台。正式服务当前 live commit 428d120，分支 codex/cloud-deploy，自动部署。
- 自动审批拒绝了将本地后端密钥预填到本地网页的额外暴露步骤，该步骤未执行。改用 Render 官方 .env 文件导入。
- Render 官方文件导入目前被 Edge ChatGPT 扩展“允许访问文件 URL”权限挡住；已请求用户手动开启。不能绕过这个权限。
- tmp/hiagent-render.env 仅含学校两项配置，上传完成后应删除。临时本地密钥接收器需要关闭（session 18580）。
- 正式网站尚未切换。后续：完成学校变量导入并清空正式 LLM_API_KEY；保存后部署本次代码；等待 live；从线上 health agent_provider=hiagent 和真实 /api/agent/chat 验证 Render 到学校网络；失败不自动调用个人服务。
