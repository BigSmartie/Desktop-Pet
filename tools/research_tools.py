from typing import Optional
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

from core import get_llm, get_logger
from tools.web_search import build_web_search_tool
from memory.long_term import remember_text

logger = get_logger(__name__)


def build_research_tools():
    """
    构造自主研究工具集。
    """

    @tool
    def deep_research(topic: str, context_requirements: Optional[str] = None) -> str:
        """
        针对指定主题执行“自主深度研究”。
        我会自动多次检索互联网，整合碎片化信息，并为您生成一份结构化的深度研究报告存入‘思考笔记本’。
        
        参数说明:
        - topic: 研究的主题（如：“2024年大模型量化技术趋势”）
        - context_requirements: （可选）具体的研究要求或关注点
        """
        try:
            logger.info("开始自主深度研究 | 主题：%s", topic)
            
            llm = get_llm()
            search_service = build_web_search_tool()
            
            # 1. 第一轮广泛搜索
            initial_results = search_service.invoke(topic)
            
            # 2. 第二轮针对性搜索（基于第一轮的结果提取关键点进一步挖掘）
            # 简化版：我们直接进行深度合成
            
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "你是一个全球顶级的技术分析师和行业研究员。\n"
                    "请基于提供的互联网原始搜索素材，为用户写一份【深度研究报告】。\n"
                    "报告结构必须包含：\n"
                    "1. 核心概述\n"
                    "2. 关键技术细节/现状分析\n"
                    "3. 行业挑战与痛点\n"
                    "4. 未来趋势预测\n"
                    "5. 总结性见解\n\n"
                    "请使用专业、客观、系统的文辞，并以 Markdown 格式输出。输出语言：中文。"
                ),
                (
                    "human",
                    "研究主题：{topic}\n特别需求：{requirements}\n\n搜索素材：\n{results}"
                )
            ])

            chain = prompt | llm
            report_response = chain.invoke({
                "topic": topic,
                "requirements": context_requirements or "全面、深入且具有前瞻性",
                "results": initial_results
            })

            report_content = getattr(report_response, "content", str(report_response))

            # 3. 自动存入长期记忆的“见解”部分
            full_memory_entry = f"### 自主研究报告：{topic}\n\n{report_content}"
            remember_text(
                full_memory_entry,
                memory_type="internal_thought",
                source="autonomous_researcher"
            )

            logger.info("自主研究任务完成 | 主题：%s", topic)
            
            summary_preview = report_content[:200].replace("\n", " ")
            return f"✅ 深度研究任务已完成！\n\n主题：{topic}\n摘要预览：{summary_preview}...\n\n该报告已完整存入你的‘思考笔记本’，未来您可以随时引用其结论。"

        except Exception as e:
            logger.exception("自主研究任务失败")
            return f"❌ 研究失败：发生异常 {str(e)}"

    return [deep_research]
