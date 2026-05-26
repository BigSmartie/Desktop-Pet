from langchain_core.tools import tool
from typing import Optional

from core import get_logger
from memory.long_term import remember_text

logger = get_logger(__name__)


def build_thought_tools():
    """
    构造思考日记管理工具集。
    """

    @tool
    def save_analytical_note(
        topic: str,
        conclusion: str,
        reasoning_steps: Optional[str] = None
    ) -> str:
        """
        保存深度分析的结论。当你和用户深入讨论了某个复杂话题（如：代码架构、故障诊断、学习计划）并有了明确见解时使用。
        这能让我在未来的对话中直接引用咱们的“历史共识”。
        
        参数说明:
        - topic: 分析的主题名称
        - conclusion: 核心结论或共识内容
        - reasoning_steps: 简要的推导逻辑或背景（可选）
        """
        try:
            full_note = f"### 深度见解：{topic}\n\n**结论**：{conclusion}"
            if reasoning_steps:
                full_note += f"\n**逻辑推导**：{reasoning_steps}"

            remember_text(
                full_note,
                memory_type="internal_thought",
                source="agent_analysis"
            )
            
            logger.info("保存思考记录成功 | topic=%s", topic)
            return f"✅ 见解 ‘{topic}’ 已成功存入我的‘思考笔记本’，未来我会随时引用。"

        except Exception as e:
            logger.exception("保存思考工具失败")
            return f"保存失败：{e}"

    return [save_analytical_note]
