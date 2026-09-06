# backend/common/constants.py
"""全局常量 —— 消除跨文件重复的硬编码。

约定：所有会跨文件复用的枚举值 / 阈值都收敛到这里，改一处生效。
"""

# ---- 性别 ----
GENDERS = ("male", "female")

# ---- 记忆类型（memory_records.memory_type）----
MEMORY_TYPES = ("user_profile", "long_term", "emotional_state")

# ---- 风险级别（audit_logs.risk_level）----
RISK_LEVELS = ("normal", "warning", "high")

# ---- 亲密度阶段（与 SCENE_FRAMEWORK.md 保持一致，单一来源）----
# 阈值依次为「熟悉 / 亲密 / 挚爱」的门槛；低于第一个阈值为「初识」
INTIMACY_STAGE_THRESHOLDS = (25, 50, 75)
INTIMACY_STAGE_NAMES = ("初识", "熟悉", "亲密", "挚爱")

# ---- 社区话题标签（COM-06）----
COMMUNITY_TAGS = ("#情感", "#科技", "#生活", "#AI", "#二次元", "#治愈")

# ---- 内容安全 ----
SENSITIVE_WORDS_FILE = "data/sensitive_words.txt"
CRISIS_WORDS_FILE = "data/crisis_words.txt"
