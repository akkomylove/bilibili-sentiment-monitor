"""
报告生成服务
支持 CSV / JSON / Markdown 格式导出
"""
import csv
import io
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult


class ReportGenerator:
    """舆情分析报告生成器"""

    def __init__(self, db: Session):
        self.db = db

    def generate_csv(self, video_bvid: str | None = None) -> str:
        """生成CSV格式报告"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["分析类型", "数据标识", "分析时间", "结果摘要"])

        query = self.db.query(AnalysisResult)
        if video_bvid:
            query = query.filter(AnalysisResult.ref_id == video_bvid)

        results = query.order_by(AnalysisResult.analyzed_at.desc()).limit(100).all()
        for r in results:
            summary = self._extract_summary(r)
            writer.writerow([
                r.analysis_type,
                r.ref_id,
                r.analyzed_at.strftime("%Y-%m-%d %H:%M:%S") if r.analyzed_at else "",
                summary,
            ])

        output.seek(0)
        return output.getvalue()

    def generate_json(self, video_bvid: str | None = None) -> dict:
        """生成JSON格式报告"""
        query = self.db.query(AnalysisResult)
        if video_bvid:
            query = query.filter(AnalysisResult.ref_id == video_bvid)

        results = query.order_by(AnalysisResult.analyzed_at.desc()).limit(100).all()

        return {
            "report_type": "舆情分析报告",
            "target": video_bvid or "全局",
            "generated_at": datetime.now().isoformat(),
            "total_records": len(results),
            "data": [
                {
                    "analysis_type": r.analysis_type,
                    "ref_type": r.ref_type,
                    "ref_id": r.ref_id,
                    "result_data": r.result_data,
                    "analyzed_at": r.analyzed_at.isoformat() if r.analyzed_at else None,
                }
                for r in results
            ],
        }

    def generate_markdown(self, video_bvid: str | None = None) -> str:
        """生成Markdown格式报告"""
        lines = [
            "# 舆情分析报告",
            "",
            f"**分析目标**: {video_bvid or '全局数据'}",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        query = self.db.query(AnalysisResult)
        if video_bvid:
            query = query.filter(AnalysisResult.ref_id == video_bvid)

        results = query.order_by(AnalysisResult.analyzed_at.desc()).limit(50).all()

        for r in results:
            lines.append(f"## {r.analysis_type}")
            lines.append(f"- **数据标识**: {r.ref_id}")
            lines.append(f"- **分析时间**: {r.analyzed_at}")
            if r.result_data:
                lines.append(f"- **结果**: {json.dumps(r.result_data, ensure_ascii=False, indent=2)}")
            lines.append("")

        return "\n".join(lines)

    def _extract_summary(self, result: AnalysisResult) -> str:
        """从分析结果中提取摘要"""
        if not result.result_data:
            return "无数据"

        data = result.result_data
        if result.analysis_type == "sentiment":
            return f"正面{data.get('positive_ratio', 0):.1%}, 负面{data.get('negative_ratio', 0):.1%}"
        elif result.analysis_type == "keywords":
            keywords = data.get("keywords", [])
            top = ", ".join([k["word"] for k in keywords[:3]])
            return f"Top3: {top}"
        elif result.analysis_type == "trend":
            points = len(data.get("time_series", []))
            return f"{points}个时间点"
        elif result.analysis_type == "user_profile":
            return f"{data.get('total_users', 0)}个用户"
        elif result.analysis_type == "danmaku_density":
            return f"{data.get('total_danmaku', 0)}条弹幕, {data.get('peak_count', 0)}个峰值"
        elif result.analysis_type == "topic_cluster":
            return f"{data.get('n_clusters', 0)}个话题"
        elif result.analysis_type == "network":
            return f"{data.get('total_users', 0)}个节点, {data.get('total_interactions', 0)}条边"
        elif result.analysis_type == "image_ocr":
            return f"图片评论: {data.get('image_comment_count', 0)}条 (OCR已禁用)"
        return "详见JSON"
