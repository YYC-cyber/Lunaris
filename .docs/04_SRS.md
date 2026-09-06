# 📐 Lunaris 系统需求规范 (SRS - Software Requirements Specification)

## 文档信息

| 项目 | 值 |
|------|-----|
| **产品名称** | Lunaris (虚拟陪伴应用) |
| **版本** | v1.3 |
| **发布日期** | 2026-08-20 |
| **更新日期** | 2026-08-21 |
| **编制者** | Product & Engineering Team |
| **审核者** | Product Manager |

---

## 1. 系统概述

### 1.1 产品定义

Lunaris 是一款 AI 虚拟伴侣应用，集成了多人格对话、树洞日记、知识库问答、真人社交等功能。核心价值主张：提供 24/7 温暖陪伴和私密倾诉空间。

### 1.2 用户基本信息

| 维度 | 描述 |
|------|------|
| **目标年龄** | 15-35 岁 |
| **地区** | 中国大陆（v1.0），国际化（v2.0+） |
| **预计规模** | 首月 10K DAU，6 个月 100K DAU |
| **用户类型** | 社交孤独者、心理陪伴寻求者、自我提升者 |

### 1.3 系统范围

**包含功能**（v1.0）
- 6 个 AI 虚拟伴侣聊天系统
- 文字、语音、表情消息支持
- 朋友圈时间线（Moments）
- 用户间真人私信
- 知识库文档管理 + RAG 问答
- 用户亲密度成长系统
- **多人群聊系统**（3 种模式）
  - AI 专用群：多个 AI 与用户对话
  - 真人群聊：用户间私密群组
  - 混合群聊：AI + 真人社交场景
- 管理后台（仅管理员）

**明确排除**（v1.0）
- 实时音视频通话
- ~~群组聊天~~ → 已在 v1.0 实现
- 推荐算法
- 广告系统
- 国际化翻译
- Electron 桌面打包

---

## 2. 功能性需求 (Functional Requirements)

### 2.1 身份认证与用户管理

#### FR-AUTH-001: 用户注册
- **需求描述**: 新用户可通过邮箱注册账户
- **输入**: 邮箱、密码、昵称
- **处理**:
  - 检验邮箱格式（RFC 5321 标准）
  - 检验邮箱唯一性（不存在于用户表）
  - 检验密码强度（8+ 字符，需大小写+数字）
  - 密码使用 bcrypt (cost factor 12) 加密存储
  - 发送验证邮件（含 6 位数字验证码）
- **输出**: 账户已创建（邮箱未验证状态）
- **错误处理**:
  - 邮箱已存在 → 400 Bad Request
  - 密码不符合要求 → 400 Bad Request
  - 邮件发送失败 → 500 Internal Error，提示用户稍后重试

#### FR-AUTH-002: 邮箱验证
- **需求描述**: 用户输入验证码以激活账户
- **输入**: 邮箱、验证码
- **处理**:
  - 查询 redis 中的验证码（有效期 10 分钟）
  - 对比用户输入与存储值（区分大小写）
  - 验证成功则标记用户 `email_verified = true`
- **输出**: 账户激活，允许登录
- **错误处理**:
  - 验证码错误/过期 → 400 Bad Request，提示重新发送

#### FR-AUTH-003: 用户登录
- **需求描述**: 用户使用邮箱和密码登录
- **输入**: 邮箱、密码
- **处理**:
  - 查询用户表，邮箱存在性检验
  - bcrypt.checkpw() 校验密码
  - 密码正确 → 生成 JWT token（有效期 30 天）
  - token 签名算法：HS256
  - 刷新 token（有效期 90 天，可用来获取新 access token）
- **输出**: JWT token + 刷新 token
- **错误处理**:
  - 用户不存在 → 401 Unauthorized
  - 密码错误 → 401 Unauthorized
  - 邮箱未验证 → 403 Forbidden，提示完成邮箱验证

#### FR-AUTH-004: Token 刷新
- **需求描述**: 使用刷新 token 获取新的 access token
- **输入**: 刷新 token
- **处理**:
  - 验证刷新 token 签名
  - 检验有效期
  - 生成新 access token
- **输出**: 新的 access token
- **错误处理**:
  - token 过期 → 401，需重新登录
  - token 签名失效 → 401，需重新登录

#### FR-AUTH-005: 用户登出
- **需求描述**: 用户登出，清除会话
- **处理**:
  - 客户端删除本地 token
  - （可选）服务端 blacklist token（防滥用）
- **输出**: 登出成功，清除用户 session

### 2.2 AI 虚拟伴侣聊天

#### FR-CHAT-001: 消息发送（文字）
- **需求描述**: 用户向 AI 伴侣发送文字消息
- **输入**: 
  - user_id（来自 token）
  - soul_id（被选中的伴侣）
  - content（消息文本，0-5000 字）
- **处理**:
  - 内容安全检查（检测违规词汇、垃圾信息）
  - 插入 `messages` 表，记录 sender_type='user', msg_type='text', created_at(Beijing time)
  - 发送 WebSocket 事件 `message_created` 广播给该用户的所有连接
  - 立即触发 AI 回复逻辑（异步）
- **输出**: message_id, created_at
- **错误处理**:
  - 内容为空 → 400
  - 用户未选择伴侣 → 400
  - 内容包含违禁词 → 403 Forbidden

#### FR-CHAT-002: AI 流式回复
- **需求描述**: AI 生成回复消息，流式返回到客户端
- **输入**: 用户消息 (message_id)
- **处理**:
  1. 构建 system prompt（包含当前北京时间、AI 人设、用户对话历史）
  2. 调用 LLM API（DeepSeek v3）with stream=true
  3. 逐块接收返回（SSE 格式）
  4. 每个 chunk 通过 WebSocket 发送事件 `stream_chunk` 到客户端
  5. 流式完成后发送 `stream_end` 事件
  6. 完整消息写入 `messages` 表，sender_type='ai', msg_type='text'
  7. 触发亲密度增加（+1）
  8. 判断是否触发语音回复（见 FR-CHAT-004）
- **输出**: stream_chunk 事件序列 → stream_end
- **错误处理**:
  - API 超时（30s）→ 返回 stream_end with error flag
  - API 配额不足 → 返回"目前无法继续聊天"
  - 用户上下文过长（>50K tokens）→ 清理早期历史，保留最近 10 条消息

#### FR-CHAT-003: 消息撤回
- **需求描述**: 用户可撤回自己发送的消息（仅用户消息，AI 消息不可撤）
- **输入**: message_id
- **处理**:
  - 校验 message.sender_type == 'user' 且 message.user_id == 当前用户
  - 设置 message.is_recalled = true
  - 消息气泡显示「消息已撤回」
  - 发送 WebSocket 事件 `message_recalled` 通知所有客户端
- **输出**: 撤回成功
- **错误处理**:
  - 尝试撤回 AI 消息 → 403 Forbidden
  - 尝试撤回他人消息 → 403 Forbidden
  - 消息已被撤回 → 400 Bad Request（幂等）

#### FR-CHAT-004: AI 语音回复生成
- **需求描述**: AI 在特定条件下自动生成语音回复
- **触发条件**（满足其一）:
  - 消息包含情感关键词（爱、想你、喜欢、伤心、生气等）且词权重总和 >= 2 分
  - 消息包含故事标记关键词（从前、曾经、那时、以前等）且总长度 > 20 字
- **处理**:
  1. 提取文本中的情感特征（计算加权分数）
  2. 若满足触发条件，调用 TTS 模块
  3. 选择对应情感的音色（happy/sad/gentle/angry/neutral）
  4. 生成 SSML 格式（含停顿标签），调用 edge_tts
  5. 保存音频文件到 `/static/tts/`，记录 message.voice_url
  6. 更新消息记录，msg_type='voice'
- **输出**: voice_url (相对路径如 `/static/tts/msg_12345.mp3`)
- **不触发情况**:
  - 普通日常聊天（「你好」「好的」「明白」）
  - 问题类消息（「怎么样」「是吗」）
  - 重复短句
- **错误处理**:
  - TTS API 失败 → 只保存文字消息，不生成语音
  - 音频文件保存失败 → 记录日志，提示用户"语音暂时不可用"

#### FR-CHAT-005: 消息历史查询
- **需求描述**: 用户进入聊天窗口时加载与伴侣的对话历史
- **输入**: 
  - soul_id
  - page, limit (分页参数)
- **处理**:
  - 查询 messages 表，条件：(soul_id = ? AND user_id = ?) 或 (soul_id = ? AND sender_type='ai')
  - 按 created_at 降序排列
  - 分页返回（每页 50 条）
  - 返回字段包含：id, content, msg_type, voice_url, sticker_id, created_at, sender_type, is_recalled
- **输出**: 消息数组 + 总数
- **缓存**: Redis 缓存最近 200 条消息（TTL 24h），提升加载速度
- **错误处理**:
  - soul_id 不存在 → 404
  - 权限检查失败 → 403

### 2.3 语音交互

#### FR-VOICE-001: 用户语音输入（STT）
- **需求描述**: 用户上传语音文件，自动转为文字
- **输入**: 
  - audio_file (MP3/WAV/M4A, max 10MB)
  - duration (音频时长，秒)
- **处理**:
  1. 校验文件格式和大小
  2. 保存到临时目录
  3. 调用 whisper.cpp 进行识别（使用 base/small 模型，本地推理）
  4. 返回识别文本 + confidence 分数
  5. 创建消息记录，msg_type='voice', content=转录文本
- **输出**: 转录文本、confidence、voice_url
- **错误处理**:
  - 文件格式不支持 → 400
  - 音频无内容 → 400，提示"无法识别，请重新录制"
  - whisper 超时 → 503，提示"识别中，请稍候"

#### FR-VOICE-002: AI 语音回复播放
- **需求描述**: 前端播放 AI 生成的语音消息
- **处理**:
  - 前端从 message.voice_url 读取 mp3 文件
  - 使用 HTML5 audio 标签播放
  - 显示播放进度条和剩余时间
  - 支持暂停、续播、音量调节
- **性能指标**:
  - 音频加载时间 < 2s（CDN 缓存）
  - 播放延迟 < 500ms（浏览器缓冲）
- **无障碍**:
  - 提供播放/暂停快捷键
  - 显示文字转录（用户可查看消息文字内容）

### 2.4 表情包系统

#### FR-STICKER-001: 发送表情包
- **需求描述**: 用户选择表情包发送
- **输入**: sticker_id
- **处理**:
  1. 查询 stickers 表，获取对应表情的图片 URL
  2. 创建消息记录，msg_type='sticker', sticker_id=选中值, content='[表情]'
  3. 发送 WebSocket 事件 `sticker_sent`
  4. 增加该表情的使用计数（用于后台数据分析）
  5. 触发亲密度增加（+1）
- **输出**: message_id, sticker_url
- **缓存**: 表情列表缓存 24h

#### FR-STICKER-002: 表情列表管理
- **需求描述**: 前端获取可用表情包列表
- **输入**: 无
- **处理**:
  - 查询 stickers 表，返回所有启用的表情 (is_active=true)
  - 按 category 分组（表情、手势、场景等）
  - 每条记录包含：id, name, image_url, emotion_tag, category
- **输出**: 表情包数组
- **扩展**: 支持用户收藏/隐藏特定表情（v1.1）

### 2.5 朋友圈 (Moments)

#### FR-MOMENTS-001: 时间线加载
- **需求描述**: 展示 6 个 AI 角色的动态时间线
- **输入**: 
  - page, limit (分页)
  - filter (可选：全部/故事/吐槽)
- **处理**:
  1. 查询 moments 表，条件：status='published'
  2. 按 created_at 降序排列
  3. 分页返回（每页 20 条）
  4. 预加载用户对该动态的点赞/评论状态
- **字段**: id, soul_id, content, images[], created_at, like_count, comment_count
- **输出**: 动态卡片数组
- **缓存**: 时间线缓存 30min，新发布动态时清除缓存

#### FR-MOMENTS-002: 点赞/取消点赞
- **需求描述**: 用户对动态点赞，支持取消
- **输入**: moment_id
- **处理**:
  1. 检查是否已点赞（查询 moment_likes 表）
  2. 若未点赞：插入记录，moment.like_count += 1
  3. 若已点赞：删除记录，moment.like_count -= 1
  4. 发送 WebSocket 事件 `moment_liked`
- **输出**: 新的 like_count 状态
- **幂等性**: 支持重复请求，结果相同

#### FR-MOMENTS-003: 发布评论
- **需求描述**: 用户在动态下发布评论
- **输入**: 
  - moment_id
  - content (评论文本，0-500 字)
  - parent_comment_id (可选，用于回复特定评论)
- **处理**:
  1. 内容安全检查
  2. 插入 moment_comments 表
  3. moment.comment_count += 1
  4. 发送 WebSocket 事件 `moment_commented` 给动态作者
- **输出**: comment_id, created_at
- **错误处理**:
  - 内容为空 → 400
  - 内容含违规词 → 403

#### FR-MOMENTS-004: 评论列表查询
- **需求描述**: 加载动态下的所有评论
- **输入**: 
  - moment_id
  - limit (最多显示 5 条，超过则显示"查看全部")
- **处理**:
  - 查询 moment_comments 表，排序 by created_at desc
  - 返回评论内容 + 发布者信息
  - 支持嵌套结构（回复某条评论）
- **输出**: 评论数组

### 2.6 真人好友系统

#### FR-FRIEND-001: 发送好友申请
- **需求描述**: 用户向其他用户发送好友申请
- **输入**: target_lunaris_id
- **处理**:
  1. 检查目标用户是否存在
  2. 检查是否已是好友或已发送申请
  3. 插入 friend_requests 表
  4. 发送通知给被申请者（通过 WebSocket + 邮件）
  5. 返回成功或失败信息
- **输出**: 申请已发送
- **错误处理**:
  - 目标用户不存在 → 404
  - 已是好友 → 400，提示"已是好友"
  - 申请待审核 → 400，提示"已发送申请，等待回复"

#### FR-FRIEND-002: 接受/拒绝申请
- **需求描述**: 用户处理好友申请
- **输入**: 
  - request_id
  - action ('accept' | 'reject')
- **处理**:
  - 若 accept：插入 friendships 表（双向），删除 friend_requests 记录
  - 若 reject：删除 friend_requests 记录，发送通知给申请者
- **输出**: 操作成功
- **通知**: WebSocket 事件 `friend_accepted` / `friend_rejected` 通知相关用户

#### FR-FRIEND-003: 私信聊天
- **需求描述**: 用户与好友进行私信聊天
- **输入**: 
  - friend_user_id
  - content
  - msg_type ('text' | 'sticker' | 'voice')
- **处理**:
  1. 校验双方是否为好友
  2. 插入 messages 表，sender_type='user', receiver_id=friend_user_id
  3. 发送 WebSocket 事件 `friend_message` 到接收方所有连接
  4. 若接收方离线，发送邮件通知
- **输出**: message_id, created_at
- **消息历史**: 查询时仅返回该用户间的对话

#### FR-FRIEND-004: 删除好友
- **需求描述**: 用户删除好友关系
- **输入**: friend_user_id
- **处理**:
  1. 删除 friendships 表中的双向记录
  2. 发送 WebSocket 事件 `friend_removed` 通知被删除者
  3. （可选）保留聊天历史但标记为"已删除"
- **输出**: 删除成功

### 2.7 亲密度系统

#### FR-INTIMACY-001: 亲密度增长
- **需求描述**: 用户与伴侣的互动自动增加亲密度
- **触发事件及加分**:
  | 事件 | 分值 |
  |------|------|
  | 发送文字消息 | +1 |
  | 发送语音消息 | +2 |
  | 接收 AI 语音回复 | +3 |
  | 点赞 AI 朋友圈 | +5 |
  | 送虚拟礼物 | +10 |
  | 日签到 | +5 (每日一次) |
  
- **处理**:
  1. 事件发生时调用 `update_intimacy()` 函数
  2. 更新 user_soul_relations 表的 intimacy_level 字段
  3. 上限 0-100，达到上限则不再增加
  4. 达到里程碑时发送通知（10/30/50/70/100）
- **输出**: 新的 intimacy_level

#### FR-INTIMACY-002: 里程碑解锁
- **需求描述**: 亲密度达到特定值时解锁专属内容
- **里程碑设定**:
  - 10: 「刚认识」→ 解锁基础对话权限
  - 30: 「熟悉起来了」→ AI 开始记住用户的信息
  - 50: 「心有灵犀」→ 解锁专属聊天背景
  - 70: 「亲密无间」→ 解锁角色的独特彩蛋对话
  - 100: 「灵魂伴侣」→ 消息气泡闪烁彩虹渐变 + 解锁最高等级互动

#### FR-INTIMACY-003: 当日心语更新
- **需求描述**: 每个 AI 角色每天拥有不同的"当日心语"
- **处理**:
  1. 后端定时任务（每天 00:00 北京时间）
  2. 为每个角色生成新的心语（基于其人设）
  3. 更新 souls 表的 daily_motto 字段
  4. 前端从 `/v1/chat/friendships` 接口获取当日心语
- **示例**:
  - 医生：「今天也要照顾好自己呀」
  - 设计师：「生活就像一幅画，需要用心去色彩」
  - 心理医生：「每一个小小的改变都值得称赞」

### 2.8 知识库系统

#### FR-KB-001: 文档上传
- **需求描述**: 用户上传个人文档用于 RAG 问答
- **输入**: 
  - file (PDF/Word/TXT, max 50MB)
  - file_type (检测或显式指定)
- **处理**:
  1. 校验文件类型和大小
  2. 保存到服务器 `/uploads/`
  3. 异步处理：
     - 提取文本（pypdf / python-docx / openpyxl）
     - 分块（按 500 token 分割，80% 重叠）
     - 生成 embeddings（使用 OpenAI text-embedding-3-small）
     - 存入 pgvector 数据库
  4. 更新 documents 表，status='ready'
- **输出**: document_id, status
- **处理时间**: 取决于文件大小，通常 5-30 秒
- **错误处理**:
  - 文件格式不支持 → 400
  - 文件过大 → 413 Payload Too Large
  - 提取失败 → 500，提示"文档格式不支持"

#### FR-KB-002: 知识库问答 (RAG)
- **需求描述**: 用户基于上传的文档提问
- **输入**: question (0-500 字)
- **处理**:
  1. 对问题进行 embedding（同样的 embedding 模型）
  2. 向量检索：在 pgvector 中查询相似度最高的 5 个 chunks (threshold > 0.7)
  3. 构建 prompt：
     ```
     基于以下文档内容回答用户问题：
     
     [检索到的 chunks，用 \n\n 分隔]
     
     用户问题：{question}
     
     请给出准确、简洁的答案。若文档中无相关信息，说明"文档中未涉及此内容"。
     ```
  4. 调用 LLM（使用用户配置的 API）生成回答
  5. 返回答案 + 引用的文档来源
- **输出**: answer (string), sources (list of chunk_ids)
- **超时**: 30 秒
- **错误处理**:
  - 用户未上传文档 → 400，提示"请先上传文档"
  - 向量检索无结果 → 返回"文档中未涉及此内容"
  - LLM 超时 → 503

#### FR-KB-003: 关键词检索
- **需求描述**: 用户通过关键词在文档中搜索
- **输入**: keyword (0-100 字)
- **处理**:
  1. 全文搜索：在 chunks 表中查询 content 包含关键词的记录
  2. 按相关度排序（分值 = 关键词出现次数 × chunk 权重）
  3. 返回最多 20 条结果，每条显示 chunk 所属文档 + 文本片段（前后各 50 字）
- **输出**: 结果数组 [{ file_name, chunk_id, content_preview }]
- **性能**: 使用数据库全文索引，< 100ms

#### FR-KB-004: 文档删除
- **需求描述**: 用户删除上传的文档
- **输入**: document_id
- **处理**:
  1. 删除 documents 表中的记录
  2. 级联删除 chunks 表中该文档的所有 chunks
  3. 删除文件服务器上的源文件
  4. 清理 pgvector 中的相关向量
- **输出**: 删除成功

### 2.9 北京时间感知

#### FR-TIME-001: 服务端时间注入
- **需求描述**: AI 能够感知当前北京时间并做出相应回复
- **处理**:
  1. 每次生成 system prompt 时，调用 `get_beijing_time()` 获取当前北京时间
  2. 格式：「当前时间：2026 年 8 月 20 日（星期三）18:30，晚上」
  3. 注入 system prompt，例如：
     ```
     你是一个温暖的虚拟伴侣。
     
     当前时间：2026年8月20日 18:30（晚上）
     
     根据时间段调整回复风格：
     - 早上（6-11时）：温暖问候，鼓励
     - 中午（11-14时）：轻松聊天，提醒午休
     - 晚上（14-24时）：深度倾听，温柔陪伴
     - 深夜（0-6时）：建议休息，关心用户
     ```
  4. AI 能理解「刚才」「今天」「昨天」等相对时间概念
- **输出**: AI 回复包含时间感知（如"这么晚了还在聊天呢"）

#### FR-TIME-002: 前端北京时间显示
- **需求描述**: 前端实时显示北京时间
- **处理**:
  1. 使用 `Intl.DateTimeFormat({timeZone: 'Asia/Shanghai'})` 获取实时北京时间
  2. 侧边栏顶部显示时钟（HH:MM 格式）
  3. 每 60 秒刷新一次
  4. 消息气泡下方显示相对时间（见下文）
- **输出**: 实时时钟组件

#### FR-TIME-003: 消息时间戳显示
- **需求描述**: 聊天消息显示发送时间
- **显示规则**:
  ```
  < 1 分钟：「刚刚」
  1-60 分钟：「N分钟前」
  1-24 小时：「N小时前」
  1 天：「昨天 HH:MM」
  2-7 天：「M月D日 HH:MM」
  > 7 天：「YYYY年M月D日 HH:MM」
  ```
- **显示条件**: 两条消息时间间隔 > 5 分钟时，在后一条消息下方显示时间
- **处理**: 前端使用 `formatRelativeTime()` 函数动态计算
- **更新**: 每分钟刷新一次相对时间显示

---

## 2.10 群聊系统 API 接口

### 2.10.1 创建群聊

**接口**: `POST /api/groups`  
**认证**: 需要 JWT Token  
**功能**: 群主创建群聊，可选邀请真人成员或添加 AI 成员

**请求参数**:
```json
{
  "group_name": "私密聊天",              // 群名称，必填
  "group_type": "human_only",            // 群聊类型，必填
                                         // 可选值: "ai_only" | "human_only" | "mixed"
  "ai_soul_ids": [1, 2],                 // AI 成员 ID 列表，可选
  "human_user_ids": ["uuid-1", "uuid-2"], // 邀请的真人用户 ID 列表，可选
  "auto_delete_hours": 24                // 消息自动删除时长（小时），可选，NULL=不删除
}
```

**响应** (200 OK):
```json
{
  "id": 1,
  "name": "私密聊天",
  "type": "human_only",
  "creator_id": "user-uuid",
  "created_at": "2026-08-21T18:00:00Z",
  "auto_delete_hours": 24,
  "announcement": null,
  "members": [
    {"id": 1, "type": "human", "name": "小王", "user_id": "user-uuid", "role": "owner"},
    {"id": 2, "type": "ai", "name": "艾登", "soul_id": 1, "role": "member"}
  ]
}
```

**错误**:
- `400 Bad Request` - 群类型无效、AI 不存在等
- `401 Unauthorized` - 未登录

---

### 2.10.2 获取群聊列表

**接口**: `GET /api/groups`  
**认证**: 需要 JWT Token  
**功能**: 获取当前用户加入的所有群聊

**请求参数**: 无

**响应** (200 OK):
```json
[
  {
    "id": 1,
    "name": "私密聊天",
    "type": "human_only",
    "creator_id": "user-uuid",
    "created_at": "2026-08-21T18:00:00Z",
    "auto_delete_hours": 24,
    "announcement": "进群需要互相尊重",
    "members": [...]
  }
]
```

---

### 2.10.3 获取群聊详情

**接口**: `GET /api/groups/{group_id}`  
**认证**: 需要 JWT Token  
**权限**: 用户必须是群成员  
**功能**: 获取单个群聊的详细信息

**路径参数**:
- `group_id` (integer) - 群 ID

**响应** (200 OK): 同 2.10.1 的响应格式

**错误**:
- `403 Forbidden` - 用户不是群成员
- `404 Not Found` - 群聊不存在

---

### 2.10.4 发送群消息

**接口**: `POST /api/groups/{group_id}/messages`  
**认证**: 需要 JWT Token  
**权限**: 用户必须是群成员  
**功能**: 在群聊中发送文字/语音消息

**路径参数**:
- `group_id` (integer) - 群 ID

**请求参数**:
```json
{
  "content": "大家好！",           // 消息内容，必填
  "voice_url": "s3://audio.mp3"  // 语音 URL，可选
}
```

**响应** (200 OK):
```json
{
  "id": 42,
  "group_id": 1,
  "sender_type": "user",
  "content": "大家好！",
  "voice_url": null,
  "created_at": "2026-08-21T18:05:00Z"
}
```

**处理逻辑**:
1. 检查用户是否为群成员（否则 403）
2. 保存消息到数据库，计算 `expires_at = created_at + group.auto_delete_hours`
3. 通过 WebSocket 推送 `group_message` 事件给所有群成员
4. 后台异步任务检查群内 AI 是否需要回应（不阻塞主流程）

**错误**:
- `400 Bad Request` - 内容为空
- `403 Forbidden` - 不是群成员
- `404 Not Found` - 群聊不存在

---

### 2.10.5 获取群聊消息历史

**接口**: `GET /api/groups/{group_id}/messages`  
**认证**: 需要 JWT Token  
**权限**: 用户必须是群成员  
**功能**: 获取群聊消息历史（最新的在前）

**路径参数**:
- `group_id` (integer) - 群 ID

**查询参数**:
- `limit` (integer, 默认 50) - 返回消息数量上限

**响应** (200 OK):
```json
{
  "messages": [
    {
      "id": 43,
      "group_id": 1,
      "sender_type": "ai",
      "sender_name": "艾登",
      "sender_id": "1",
      "content": "你好啊！",
      "voice_url": null,
      "created_at": "2026-08-21T18:06:00Z",
      "is_deleted": false,
      "expires_at": "2026-08-22T18:05:00Z"
    },
    {
      "id": 42,
      "group_id": 1,
      "sender_type": "user",
      "sender_name": "小王",
      "sender_id": "user-uuid",
      "content": "[消息已过期]",          // 过期消息显示占位符
      "voice_url": null,
      "created_at": "2026-08-21T18:05:00Z",
      "is_deleted": false,
      "expires_at": "2026-08-21T17:50:00Z"
    }
  ]
}
```

**说明**:
- 消息按从新到旧排序（最新的先返回）
- 已过期的消息 `content` 显示为 `[消息已过期]`
- 已删除的消息 `content` 显示为 `[消息已删除]`
- 消息合并规则：同一用户 5 秒内的消息会被合并为一条

**错误**:
- `403 Forbidden` - 不是群成员
- `404 Not Found` - 群聊不存在

---

### 2.10.6 邀请成员加入群聊

**接口**: `POST /api/groups/{group_id}/invite`  
**认证**: 需要 JWT Token  
**权限**: 仅群主可以邀请  
**功能**: 邀请真人用户加入群聊

**路径参数**:
- `group_id` (integer) - 群 ID

**请求参数**:
```json
{
  "invitee_id": "user-uuid"  // 被邀请者 UUID
}
```

**响应** (200 OK):
```json
{
  "id": 5,
  "group_id": 1,
  "group_name": "私密聊天",
  "inviter_id": "inviter-uuid",
  "inviter_name": "小王",
  "invitee_id": "user-uuid",
  "status": "PENDING",
  "created_at": "2026-08-21T18:10:00Z",
  "expires_at": "2026-08-22T18:10:00Z"
}
```

**处理逻辑**:
1. 检查发送者是否为群主（否则 403）
2. 创建邀请记录，状态为 PENDING
3. 邀请链接 24 小时内有效
4. 通过 WebSocket 推送 `group_invitation` 事件给被邀请者

**错误**:
- `400 Bad Request` - 被邀请者不存在或已是群成员
- `403 Forbidden` - 用户不是群主

---

### 2.10.7 响应邀请

**接口**: `POST /api/invitations/{invitation_id}/respond`  
**认证**: 需要 JWT Token  
**功能**: 接受或拒绝群聊邀请

**路径参数**:
- `invitation_id` (integer) - 邀请 ID

**请求参数**:
```json
{
  "accept": true  // true=接受，false=拒绝
}
```

**响应** (200 OK):
```json
{
  "id": 5,
  "group_id": 1,
  "status": "ACCEPTED",  // 或 "DECLINED"
  "created_at": "2026-08-21T18:10:00Z"
}
```

**处理逻辑**:
- 接受：邀请状态变为 ACCEPTED，用户成为群成员，状态为 ACTIVE
- 拒绝：邀请状态变为 DECLINED，用户不加入群聊

**错误**:
- `400 Bad Request` - 邀请已过期或已响应
- `404 Not Found` - 邀请不存在

---

### 2.10.8 获取待处理邀请

**接口**: `GET /api/invitations/pending`  
**认证**: 需要 JWT Token  
**功能**: 获取当前用户的所有待处理邀请

**请求参数**: 无

**响应** (200 OK):
```json
{
  "invitations": [
    {
      "id": 5,
      "group_id": 1,
      "group_name": "私密聊天",
      "inviter_id": "inviter-uuid",
      "inviter_name": "小王",
      "created_at": "2026-08-21T18:10:00Z",
      "expires_at": "2026-08-22T18:10:00Z"
    }
  ]
}
```

---

## 2.10.9 WebSocket 事件（实时消息推送）

### 事件：群消息 (group_message)

**触发**: 群成员发送消息时，推送给所有群成员

**事件数据**:
```json
{
  "type": "group_message",
  "id": "group_1_42",
  "data": {
    "group_id": 1,
    "message": {
      "id": 42,
      "group_id": 1,
      "sender_type": "user",
      "content": "大家好！",
      "created_at": "2026-08-21T18:05:00Z"
    }
  },
  "ts": 1724274300
}
```

### 事件：群邀请 (group_invitation)

**触发**: 群主邀请用户时，推送给被邀请者

**事件数据**:
```json
{
  "type": "group_invitation",
  "id": "invitation_5",
  "data": {
    "id": 5,
    "group_id": 1,
    "group_name": "私密聊天",
    "inviter_name": "小王",
    "expires_at": "2026-08-22T18:10:00Z"
  },
  "ts": 1724274300
}
```

### 事件：消息删除 (group_messages_expired)

**触发**: 后台定时任务删除过期消息时，推送给所有群成员

**事件数据**:
```json
{
  "type": "group_messages_expired",
  "id": "group_1_cleanup",
  "data": {
    "group_id": 1,
    "expired_count": 3
  },
  "ts": 1724274300
}
```

**前端处理**: 收到此事件后，可选择：
1. 自动刷新消息列表（推荐）
2. 显示"有些消息已过期"提示

---

## 2.10.10 HTTP 状态码与错误处理

| 状态码 | 含义 | 场景 |
|--------|------|------|
| 200 | 成功 | 所有正常请求 |
| 400 | 请求错误 | 参数格式错误、业务逻辑错误 |
| 401 | 未认证 | JWT Token 缺失或过期 |
| 403 | 禁止 | 权限不足（如非群主删除成员） |
| 404 | 未找到 | 群聊/消息/邀请不存在 |
| 500 | 服务错误 | 数据库错误、LLM 服务错误等 |

**错误响应格式**:
```json
{
  "detail": "你不是这个群的成员"
}
```

---

## 2.10.11 成员管理 API（补充）

### 成员主动退出群聊

**接口**: `DELETE /api/groups/{group_id}/leave`  
**认证**: 需要 JWT Token  
**权限**: 用户必须是群成员，非群主  
**功能**: 成员主动退出群聊

**路径参数**:
- `group_id` (integer) - 群 ID

**请求参数**: 无

**响应** (200 OK):
```json
{
  "ok": true,
  "message": "已退出群聊"
}
```

**错误**:
- `400 Bad Request` - 用户不是成员，或者是群主无法直接退出
- `404 Not Found` - 群聊不存在

---

### 转让群主权限

**接口**: `POST /api/groups/{group_id}/transfer-owner`  
**认证**: 需要 JWT Token  
**权限**: 仅当前群主可以转让  
**功能**: 群主转让群主权限给其他成员

**路径参数**:
- `group_id` (integer) - 群 ID

**请求参数**:
```json
{
  "new_owner_member_id": 42  // 新群主的 group_members 表记录 ID
}
```

**响应** (200 OK):
```json
{
  "group_id": 1,
  "new_owner_id": "new-user-uuid",
  "old_owner_id": "old-owner-uuid",
  "status": "success"
}
```

**处理逻辑**:
1. 检查发送者是否为当前群主
2. 检查新群主是否存在且是真人成员
3. 更新群主权限：当前群主降为普通成员，新群主升为群主
4. 更新 `group_chats.user_id` 指向新群主
5. 推送 WebSocket 事件通知所有成员

**错误**:
- `400 Bad Request` - 新群主不存在或不是真人成员
- `403 Forbidden` - 用户不是群主

---

## 2.10.12 群记忆管理 API（补充）

### 添加群记忆

**接口**: `POST /api/groups/{group_id}/souls/{soul_id}/memories`  
**认证**: 需要 JWT Token  
**权限**: 仅群创建者可以添加  
**功能**: 为群内 AI 添加记忆（成员信息、话题、规则、事件等）

**路径参数**:
- `group_id` (integer) - 群 ID
- `soul_id` (integer) - AI 角色 ID

**请求参数**:
```json
{
  "memory_type": "member_info",  // 必填，类型: event / member_info / group_rule / topic
  "content": "Alice 是一个喜欢编程的女性"
}
```

**响应** (200 OK):
```json
{
  "id": 1,
  "group_id": 1,
  "soul_id": 2,
  "memory_type": "member_info",
  "content": "Alice 是一个喜欢编程的女性",
  "created_at": "2026-08-21T18:00:00Z"
}
```

---

### 获取群记忆

**接口**: `GET /api/groups/{group_id}/souls/{soul_id}/memories`  
**认证**: 需要 JWT Token  
**权限**: 群成员可查看  
**功能**: 获取某个 AI 在该群的所有记忆

**路径参数**:
- `group_id` (integer) - 群 ID
- `soul_id` (integer) - AI 角色 ID

**响应** (200 OK):
```json
{
  "memories": [
    {
      "id": 1,
      "memory_type": "member_info",
      "content": "Alice 是一个喜欢编程的女性",
      "created_at": "2026-08-21T18:00:00Z"
    },
    {
      "id": 2,
      "memory_type": "group_rule",
      "content": "这个群禁止讨论政治话题",
      "created_at": "2026-08-21T18:05:00Z"
    }
  ]
}
```

**说明**:
- 群创建者可查看和管理所有记忆
- 普通成员可查看记忆，但不能修改（用于了解 AI 对群的理解）
- 记忆用于 AI 的 system prompt，影响 AI 在群里的回应风格

---

### 删除群记忆

**接口**: `DELETE /api/groups/{group_id}/souls/{soul_id}/memories/{memory_id}`  
**认证**: 需要 JWT Token  
**权限**: 仅群创建者可删除  
**功能**: 删除 AI 在该群的某条记忆

**路径参数**:
- `group_id` (integer) - 群 ID
- `soul_id` (integer) - AI 角色 ID
- `memory_id` (integer) - 记忆 ID

**响应** (200 OK):
```json
{
  "ok": true,
  "message": "记忆已删除"
}
```

**错误**:
- `403 Forbidden` - 用户不是群创建者
- `404 Not Found` - 记忆不存在

---

## 2.10.13 @ 功能规范（补充）

### @ 功能概述

**功能**: 在群聊中 @ 成员触发 AI 强制回应

**语法**:
```
@艾登 你觉得这个想法怎么样？
@凯勒斯 帮我分析一下
```

### @ 功能工作机制

**触发规则**:
1. 用户输入消息包含 `@[AI名称]` 格式
2. 名称匹配群内的 AI 角色
3. 立即触发该 AI 的强制回应

**AI 回应规则**:
- **普通消息** - 根据 9 条评分规则决定是否回应
- **被 @ 消息** - 立即必须回应（无论评分多少）
- **回应速度** - 通常 2-5 秒内回应

### @ 功能的实现

**后端处理** (`group_response_strategy.py`):
```
检查消息内容是否包含 "@[AI名称]"
  ├─ 是 → 评分规则 9 = 100（强制回应）
  └─ 否 → 按照规则 1-8 评分
  
评分 > 60 → 触发 LLM 生成
```

**前端支持**:
- 可选：在输入框添加 @ 成员提示
- 可选：自动完成成员名称
- 可选：@ 后的成员名称高亮显示

### 消息回应评分系统（9 规则）

| 规则 | 名称 | 说明 | 分值范围 |
|------|------|------|---------|
| 1 | 直接对话 | 消息中提到 AI 名字 | +20 |
| 2 | @ 触发 | 用户 @ 了 AI | +100 |
| 3 | 问题类 | 消息包含问号 | +15 |
| 4 | 亲密度 | 根据与群主的亲密度 | 0-30 |
| 5 | 群聊类型 | ai_only 增加分值 | +50 |
| 6 | 消息长度 | 较长消息更可能获得回应 | +10 |
| 7 | 关键词 | 是否包含预设触发词 | +20 |
| 8 | 连续性 | 是否在回应他人消息 | +15 |
| 9 | 强制回应 | @ 功能自动设置 | +100 |

---



| 指标 | 目标 | 备注 |
|------|------|------|
| **API 响应时间** | p95 < 500ms | 不含第三方 API 延迟 |
| **消息发送延迟** | < 200ms | 从客户端点发送到消息显示 |
| **AI 首字显示时间** | < 5s | 从用户消息到 AI 开始流式回复 |
| **页面加载时间** | < 3s | 首屏加载 |
| **并发用户数** | 10K+ DAU → 1K 同时在线 | 支持 1K 个 WebSocket 连接 |
| **消息历史加载** | < 1s | 加载 50 条历史消息 |
| **语音识别延迟** | < 5s | 10s 音频的识别时间 |

### 3.2 可靠性需求

| 指标 | 目标 |
|------|------|
| **系统可用性** | 99.5% (月度) |
| **消息送达率** | 99.9% |
| **数据持久性** | 100%（无数据丢失） |
| **故障恢复时间** | < 5 分钟 |
| **消息去重** | 支持幂等性，防止重复 |

### 3.3 安全性需求

#### 3.3.1 身份认证
- **密码加密**: bcrypt (cost factor 12)
- **传输加密**: HTTPS/TLS 1.3
- **Token 安全**:
  - JWT 使用 HS256 签名
  - Access token 有效期：30 天
  - 刷新 token 有效期：90 天
  - 过期自动清除

#### 3.3.2 数据安全
- **数据库加密**: PostgreSQL 使用 pgcrypto 加密敏感字段（密码、API key）
- **API Key 安全**: 不在代码中硬编码，使用环境变量/密钥管理系统
- **用户数据隐私**: 用户聊天记录与朋友圈内容仅用户本人可见（除非设置分享）

#### 3.3.3 内容安全
- **违禁词检测**: 所有用户输入（消息、评论）都需通过内容安全检查
- **使用方案**: 
  - 本地词库（textfilter）针对常规违规词
  - LLM 分类（DeepSeek）用于复杂语义判断（骚扰、自伤等）
- **处理**:
  - 轻度违规：记录日志，予以警告
  - 重度违规：拒绝发送，提示用户

#### 3.3.4 DDoS/滥用防护
- **速率限制**:
  - 登录尝试：5 次/分钟
  - API 调用：100 请求/分钟/用户
  - 消息发送：10 条/分钟
- **验证**:
  - 注册需邮箱验证
  - 找回密码需验证邮箱

### 3.4 可扩展性需求

| 场景 | 设计 |
|------|------|
| **用户增长** | 单库支持 1M+ 用户，超过则分库分表 |
| **消息量** | 消息表按月分区，query 自动路由 |
| **向量数据库** | pgvector 支持 10M+ 向量，超过则切换 Milvus |
| **实时连接** | WebSocket 连接池，支持 10K+，单机需水平扩展 |
| **API 服务** | 无状态设计，支持 load balancer 负载均衡 |

### 3.5 用户体验需求

| 维度 | 要求 |
|------|------|
| **响应度** | 用户操作后 < 300ms 有视觉反馈 |
| **一致性** | 多个客户端打开时，消息实时同步 |
| **离线支持** | 消息离线队列，自动重试 3 次 |
| **无障碍** | 支持键盘导航、屏幕阅读器 |
| **国际化准备** | 代码使用 i18n，为翻译准备 |

### 3.6 可维护性需求

| 方面 | 要求 |
|------|------|
| **代码质量** | 生产代码覆盖率 > 80% |
| **文档** | API 使用 OpenAPI 3.0 规范文档化，前端使用 TypeScript |
| **日志** | 所有异常/关键操作记录至 system_log，可追溯 |
| **监控** | 实时监控 API 错误率、延迟、资源使用 |
| **部署** | CI/CD 自动化，每个 commit 运行单元测试 |

---

## 4. 系统架构概述

### 4.1 技术栈

| 层 | 技术 | 版本 |
|-----|------|------|
| **前端** | Vue 3 + TypeScript | 3.3+ |
| **后端** | FastAPI + SQLAlchemy | Python 3.9+ |
| **数据库** | PostgreSQL + pgvector | 14+ |
| **缓存** | Redis | 6.0+ |
| **消息队列** | （可选）RabbitMQ | 3.8+ |
| **LLM 服务** | DeepSeek API | v3 |
| **语音服务** | whisper.cpp (STT) + edge_tts (TTS) | 最新 |
| **向量数据库** | pgvector | 0.5.0+ |

### 4.2 系统架构图

```
┌─────────────────────────────────┐
│      Web 前端 (Vue 3)            │  浏览器
│  ├─ ChatWindow                  │
│  ├─ MomentTimeline              │
│  ├─ FriendList                  │
│  └─ InputArea (文字/语音/表情)    │
└────────────┬──────────────────────┘
             │ HTTPS/WSS
┌────────────▼──────────────────────┐
│      Backend API (FastAPI)        │  服务器
│  ├─ /v1/chat/completions        │  聊天
│  ├─ /v1/chat/message            │  消息
│  ├─ /v1/chat/friendships        │  关系
│  ├─ /api/voice/transcribe       │  STT
│  ├─ /api/voice/synthesize       │  TTS
│  ├─ /api/knowledge/ask          │  知识库
│  ├─ /api/moments/*              │  朋友圈
│  └─ /api/admin/analytics        │  后台
│
│  认证: JWT middleware
│  内容检查: textfilter + LLM
│  日志: system_log 表
└────────┬─────────────────────────┘
         │
    ┌────┴─────┬──────────┬───────────┐
    │           │          │           │
┌───▼──┐   ┌────▼──┐ ┌───▼──┐ ┌────▼────┐
│ PG   │   │Redis  │ │pgv   │ │External │
│      │   │       │ │ectr  │ │APIs     │
│users │   │token  │ │      │ │(DeepSk)│
│msgs  │   │cache  │ │embed │ │Whisper │
│souls │   │       │ │ding  │ │EdgeTTS │
└──────┘   └───────┘ └──────┘ └────────┘
```

---

## 5. 数据库设计

### 5.1 核心表结构

#### users 表
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  lunaris_id VARCHAR(50) UNIQUE NOT NULL,
  username VARCHAR(100) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  email_verified BOOLEAN DEFAULT FALSE,
  avatar_url VARCHAR(500),
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  is_admin BOOLEAN DEFAULT FALSE
);
```

#### souls 表 (AI 伴侣)
```sql
CREATE TABLE souls (
  id SERIAL PRIMARY KEY,
  display_name VARCHAR(100) NOT NULL,
  gender VARCHAR(10),
  avatar_url VARCHAR(500),
  description TEXT,
  tags VARCHAR(500), -- JSON array: ["医生", "温暖"]
  system_prompt TEXT NOT NULL,
  daily_motto VARCHAR(500),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT now()
);
```

#### messages 表
```sql
CREATE TABLE messages (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  soul_id INTEGER REFERENCES souls(id),
  content TEXT NOT NULL,
  msg_type VARCHAR(20), -- 'text', 'voice', 'sticker'
  sender_type VARCHAR(20), -- 'user', 'ai'
  voice_url VARCHAR(500),
  sticker_id INTEGER REFERENCES stickers(id),
  emotion VARCHAR(50), -- 从 AI 回复中提取的情感标签
  is_recalled BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT now(),
  INDEX (user_id, soul_id, created_at)
);
```

#### user_soul_relations 表
```sql
CREATE TABLE user_soul_relations (
  user_id INTEGER REFERENCES users(id),
  soul_id INTEGER REFERENCES souls(id),
  is_default BOOLEAN DEFAULT FALSE,
  intimacy_level INTEGER DEFAULT 0, -- 0-100
  last_chat_at TIMESTAMP,
  PRIMARY KEY (user_id, soul_id)
);
```

#### moments 表 (朋友圈)
```sql
CREATE TABLE moments (
  id SERIAL PRIMARY KEY,
  soul_id INTEGER REFERENCES souls(id),
  content TEXT NOT NULL,
  images VARCHAR(500)[], -- 多个图片 URL
  status VARCHAR(20) DEFAULT 'published', -- 'draft', 'published', 'archived'
  like_count INTEGER DEFAULT 0,
  comment_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT now()
);
```

#### documents 表 (知识库)
```sql
CREATE TABLE documents (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  file_name VARCHAR(255) NOT NULL,
  file_size INTEGER, -- 字节
  status VARCHAR(20) DEFAULT 'processing', -- 'processing', 'ready', 'failed'
  chunk_count INTEGER, -- 切块数量
  created_at TIMESTAMP DEFAULT now(),
  INDEX (user_id, status)
);
```

#### chunks 表 (文档切块 + 向量)
```sql
CREATE TABLE chunks (
  id SERIAL PRIMARY KEY,
  document_id INTEGER REFERENCES documents(id),
  chunk_index INTEGER,
  content TEXT NOT NULL,
  embedding vector(1536), -- OpenAI embedding 维度
  chunk_tokens INTEGER, -- token 数
  created_at TIMESTAMP DEFAULT now(),
  INDEX (document_id)
);
```

#### stickers 表
```sql
CREATE TABLE stickers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  image_url VARCHAR(500),
  emotion_tag VARCHAR(50), -- 'happy', 'sad', 'angry', 'gentle'
  category VARCHAR(50),
  usage_count INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT now()
);
```

#### group_chats 表（新增）
```sql
CREATE TABLE group_chats (
  id SERIAL PRIMARY KEY,
  group_name VARCHAR(255) NOT NULL,
  group_type VARCHAR(50) NOT NULL, -- 'ai_only', 'human_only', 'mixed'
  creator_id UUID REFERENCES users(id),
  auto_delete_hours INTEGER, -- 消息自动删除时长
  is_archived BOOLEAN DEFAULT FALSE,
  is_deleted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  INDEX (creator_id)
);
```

#### group_members 表（新增）
```sql
CREATE TABLE group_members (
  id SERIAL PRIMARY KEY,
  group_id INTEGER REFERENCES group_chats(id) ON DELETE CASCADE,
  member_type VARCHAR(50) NOT NULL, -- 'ai', 'human'
  member_id UUID REFERENCES users(id),
  soul_id INTEGER REFERENCES souls(id),
  status VARCHAR(50) DEFAULT 'active', -- 'active', 'invited', 'declined'
  joined_at TIMESTAMP DEFAULT now(),
  is_deleted BOOLEAN DEFAULT FALSE,
  UNIQUE (group_id, member_id, member_type),
  INDEX (group_id, member_id)
);
```

#### group_messages 表（新增）
```sql
CREATE TABLE group_messages (
  id SERIAL PRIMARY KEY,
  group_id INTEGER REFERENCES group_chats(id) ON DELETE CASCADE,
  sender_type VARCHAR(50) NOT NULL, -- 'ai', 'user'
  sender_id UUID REFERENCES users(id),
  soul_id INTEGER REFERENCES souls(id),
  content TEXT NOT NULL,
  voice_url VARCHAR(500),
  created_at TIMESTAMP DEFAULT now(),
  expires_at TIMESTAMP, -- 消息过期时间（自动删除）
  is_deleted BOOLEAN DEFAULT FALSE,
  INDEX (group_id, created_at)
);
```

#### group_invitations 表（新增）
```sql
CREATE TABLE group_invitations (
  id SERIAL PRIMARY KEY,
  group_id INTEGER REFERENCES group_chats(id) ON DELETE CASCADE,
  inviter_id UUID REFERENCES users(id),
  invitee_id UUID REFERENCES users(id),
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'accepted', 'declined'
  created_at TIMESTAMP DEFAULT now(),
  expires_at TIMESTAMP DEFAULT (now() + INTERVAL '24 hours'),
  responded_at TIMESTAMP,
  is_deleted BOOLEAN DEFAULT FALSE,
  UNIQUE (group_id, invitee_id),
  INDEX (invitee_id)
);
```

#### system_log 表 (审计日志)
```sql
CREATE TABLE system_log (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  action VARCHAR(100),
  status VARCHAR(20), -- 'success', 'fail'
  error_message TEXT,
  created_at TIMESTAMP DEFAULT now(),
  INDEX (user_id, status, created_at)
);
```

---

## 6. API 接口规范

### 6.1 认证接口

#### POST /auth/register
```
请求:
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "nickname": "张三"
}

响应 (201):
{
  "user_id": 123,
  "message": "注册成功，请查收邮件验证账户"
}
```

#### POST /auth/verify-email
```
请求:
{
  "email": "user@example.com",
  "code": "123456"
}

响应 (200):
{
  "message": "邮箱验证成功"
}
```

#### POST /auth/login
```
请求:
{
  "email": "user@example.com",
  "password": "SecurePass123"
}

响应 (200):
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "expires_in": 2592000
}
```

### 6.2 聊天接口

#### POST /v1/chat/completions (流式)
```
请求:
{
  "soul_id": 1,
  "messages": [{"role": "user", "content": "你好"}],
  "stream": true
}

流式响应 (Content-Type: text/event-stream):
data: {"chunk": "你好"}
data: {"chunk": "，我"}
...
data: {"done": true, "message_id": 12345}
```

#### GET /v1/chat/history?soul_id=1&page=1&limit=50
```
响应 (200):
{
  "data": [
    {
      "id": 100,
      "content": "你好",
      "sender_type": "user",
      "msg_type": "text",
      "created_at": "2026-08-20T18:30:00Z",
      "is_recalled": false
    },
    {
      "id": 101,
      "content": "你好呀",
      "sender_type": "ai",
      "msg_type": "voice",
      "voice_url": "/static/tts/msg_101.mp3",
      "created_at": "2026-08-20T18:30:05Z"
    }
  ],
  "total": 250
}
```

#### DELETE /v1/chat/message/{message_id}
```
响应 (200):
{
  "message": "消息已撤回"
}
```

#### GET /v1/chat/friendships
```
响应 (200):
[
  {
    "soul_id": 1,
    "intimacy_level": 45,
    "daily_motto": "今天也要开心呀",
    "last_message_preview": "晚上好，今天过得怎么样..."
  }
]
```

### 6.3 语音接口

#### POST /api/voice/transcribe (multipart/form-data)
```
请求:
{
  "audio": <audio file>,
  "duration": 12.5
}

响应 (200):
{
  "text": "你好，今天天气怎么样",
  "confidence": 0.95,
  "duration": 12.5
}
```

#### POST /api/voice/synthesize
```
请求:
{
  "text": "你好呀",
  "soul_id": 1,
  "emotion": "happy"
}

响应 (200):
{
  "voice_url": "/static/tts/msg_12345.mp3",
  "duration": 3.2
}
```

### 6.4 知识库接口

#### POST /api/knowledge/upload (multipart/form-data)
```
请求:
{
  "file": <file>,
  "filename": "学习计划.pdf"
}

响应 (201):
{
  "document_id": 5,
  "status": "processing",
  "message": "文档上传成功，正在处理..."
}
```

#### POST /api/knowledge/ask
```
请求:
{
  "question": "怎样制定学习计划？"
}

响应 (200):
{
  "answer": "根据您上传的文档，可以按以下步骤制定学习计划：\n1. 明确学习目标\n2. 评估当前水平\n3. 制定时间表\n...",
  "sources": [5] // 引用的文档 ID
}
```

#### GET /api/knowledge/search?keyword=学习
```
响应 (200):
{
  "results": [
    {
      "file_name": "学习计划.pdf",
      "chunk_id": 12,
      "content_preview": "...学习计划是制定学习目标和时间安排的重要工具。它帮助学生..."
    }
  ]
}
```

### 6.5 朋友圈接口

#### GET /api/moments?page=1&limit=20
```
响应 (200):
{
  "data": [
    {
      "id": 1,
      "soul_id": 1,
      "soul_name": "医生",
      "content": "今天看了一个有趣的病例...",
      "images": ["https://cdn.example.com/img1.jpg"],
      "like_count": 12,
      "comment_count": 3,
      "created_at": "2026-08-20T10:00:00Z",
      "liked_by_me": false
    }
  ],
  "total": 125
}
```

#### POST /api/moments/{moment_id}/like
```
响应 (200):
{
  "liked": true,
  "like_count": 13
}
```

#### POST /api/moments/{moment_id}/comments
```
请求:
{
  "content": "好文章！"
}

响应 (201):
{
  "comment_id": 42,
  "created_at": "2026-08-20T18:35:00Z"
}
```

---

## 7. 测试需求

### 7.1 单元测试
- **覆盖率**: > 80% 的业务逻辑
- **框架**: pytest
- **关键模块**:
  - chat_service.py (消息生成、亲密度计算)
  - content_safety.py (违禁词检测)
  - time_utils.py (北京时间转换)

### 7.2 集成测试
- **数据库**: 使用 test PostgreSQL 容器，每个测试后回滚
- **API**: 所有 endpoints 测试（正常流程 + 边界情况 + 错误处理）
- **WebSocket**: 连接、消息、断线重连测试

### 7.3 端到端测试
- **用户旅程**: 从注册→首次对话→朋友圈互动→知识库问答
- **性能测试**: 并发 1K 用户的压力测试
- **跨浏览器**: Chrome、Firefox、Safari、Edge

---

## 8. 发布计划

### v1.0 (MVP) - 已完成
- ✅ 6 个 AI 伴侣聊天
- ✅ 文字 + 语音消息
- ✅ 朋友圈时间线
- ✅ 知识库 RAG
- ✅ 亲密度系统
- ✅ 北京时间感知

### v1.1 (2-3 周后)
- [ ] 虚拟礼物系统（送礼增加亲密度）
- [ ] VIP 订阅支付集成（微信支付）
- [ ] 消息推送系统优化（离线通知）
- [ ] 内容审核强化（人工审核队列）

### v1.2 (1 个月后)
- [ ] 用户等级系统
- [ ] 排行榜功能（按亲密度排行）
- [ ] 角色互动事件系统（节日特殊对话）

### v2.0 (3 个月后)
- [ ] Web 端优化
- [ ] 桌面端支持（Electron）
- [ ] 国际化（英文）
- [ ] 高级推荐系统

---

## 9. 风险识别与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| LLM API 成本过高 | 中 | 实现本地缓存 + 请求合并，监控 token 消耗 |
| 用户隐私泄露 | 高 | 端对端加密、定期安全审计、隐私政策透明 |
| 用户过度依赖 AI | 中 | 应用内心理健康提示、定期休息建议 |
| 竞品 Soul、TreeHole 压力 | 中 | 强化个性化 + 温暖设计差异化 |
| 语音识别不准确 | 低 | 提供手动编辑功能 + 文字预览 |
| 服务器宕机 | 高 | 多区域部署 + RTO 5min 的灾备计划 |

---

## 10. 关键术语与定义

| 术语 | 定义 |
|------|------|
| **灵魂伴侣** | 亲密度达到 100 的 AI 角色 |
| **树洞** | 用户隐私的对话空间，消息仅自己可见 |
| **Moments** | 朋友圈，AI 角色分享的动态时间线 |
| **RAG** | Retrieval-Augmented Generation，基于文档的问答 |
| **STT** | Speech-To-Text，语音转文字 |
| **TTS** | Text-To-Speech，文字转语音 |
| **pgvector** | PostgreSQL 的向量扩展，用于存储 embeddings |
| **WebSocket** | 全双工通信协议，用于实时消息推送 |

---

**SRS 版本**: 1.3  
**最后更新**: 2026-08-21  
**维护者**: Product & Tech Team  
**状态**: 已批准，进入开发阶段
