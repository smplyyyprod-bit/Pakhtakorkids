import io
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Coach, DailyReport
from app.infrastructure.repositories import (
    DailyReportRepository,
    CoachRepository,
)

logger = get_logger()


class ExportService:
    """Service for exporting reports to Excel and PDF."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.report_repository = DailyReportRepository(session)
        self.coach_repository = CoachRepository(session)

    async def export_to_excel(
        self, coach_id: int, year: int, month: int
    ) -> bytes:
        """Export monthly report to Excel format."""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

            coach = await self.coach_repository.get_by_id(coach_id)
            if not coach:
                raise ValueError(f"Coach {coach_id} not found")

            reports = await self.report_repository.get_by_coach_and_month(
                coach_id, year, month
            )
            stats = await self.report_repository.get_monthly_stats(
                coach_id, year, month
            )

            wb = Workbook()
            ws = wb.active
            ws.title = "Отчет"

            # Headers
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # Title
            ws["A1"] = "Ежемесячный отчет о работе тренера"
            ws["A1"].font = Font(bold=True, size=14)
            ws.merge_cells("A1:L1")

            # Coach info
            ws["A3"] = "Тренер:"
            ws["B3"] = coach.full_name
            ws["A4"] = "Должность:"
            ws["B4"] = coach.position
            ws["A5"] = "Команда:"
            ws["B5"] = coach.team
            ws["A6"] = "Месяц:"
            ws["B6"] = f"{month}/{year}"

            # Daily reports table
            row = 8
            headers = [
                "Дата",
                "Присутствие",
                "Верхняя форма",
                "Нижняя форма",
                "Начало",
                "Окончание",
                "Часов",
                "Опоздание (мин)",
                "Ранний уход (мин)",
                "Примечания",
            ]

            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col)
                cell.value = header
                cell.fill = header_fill
                cell.font = header_font
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center")

            row = 9
            for report in reports:
                ws.cell(row=row, column=1).value = str(report.report_date)
                ws.cell(row=row, column=2).value = report.attendance.value
                ws.cell(row=row, column=3).value = report.upper_uniform.value
                ws.cell(row=row, column=4).value = report.lower_uniform.value
                ws.cell(row=row, column=5).value = (
                    str(report.start_time) if report.start_time else ""
                )
                ws.cell(row=row, column=6).value = (
                    str(report.end_time) if report.end_time else ""
                )
                ws.cell(row=row, column=7).value = float(report.worked_hours or 0)
                ws.cell(row=row, column=8).value = report.late_arrival_minutes
                ws.cell(row=row, column=9).value = report.early_departure_minutes
                ws.cell(row=row, column=10).value = report.notes or ""

                for col in range(1, 11):
                    ws.cell(row=row, column=col).border = thin_border

                row += 1

            # Statistics
            stats_row = row + 2
            ws[f"A{stats_row}"] = "Итоговая статистика"
            ws[f"A{stats_row}"].font = Font(bold=True, size=12)

            stats_data = [
                ("Отработано часов:", stats["worked_hours"]),
                ("Отработано дней:", stats["worked_days"]),
                ("Опозданий:", stats["late_arrivals"]),
                ("Всего минут опоздания:", stats["total_late_minutes"]),
                ("Ранних уходов:", stats["early_departures"]),
                ("Всего минут раннего ухода:", stats["total_early_departure_minutes"]),
                ("Дней без верхней формы:", stats["days_without_upper_uniform"]),
                ("Дней без нижней формы:", stats["days_without_lower_uniform"]),
                ("Дней болезни:", stats["sick_days"]),
                ("Дней отпуска:", stats["vacation_days"]),
                ("Дней без объяснения причины:", stats["unexcused_absences"]),
            ]

            stats_row += 1
            for label, value in stats_data:
                ws[f"A{stats_row}"] = label
                ws[f"B{stats_row}"] = value
                stats_row += 1

            # Set column widths
            ws.column_dimensions["A"].width = 15
            ws.column_dimensions["B"].width = 20
            ws.column_dimensions["C"].width = 15
            ws.column_dimensions["D"].width = 15
            ws.column_dimensions["E"].width = 12
            ws.column_dimensions["F"].width = 12
            ws.column_dimensions["G"].width = 10
            ws.column_dimensions["H"].width = 15
            ws.column_dimensions["I"].width = 15
            ws.column_dimensions["J"].width = 20

            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            logger.info(f"Excel export created for coach {coach_id}")
            return output.getvalue()

        except ImportError:
            logger.error("openpyxl is not installed")
            raise

    async def export_to_pdf(
        self, coach_id: int, year: int, month: int
    ) -> bytes:
        """Export monthly report to PDF format."""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

            coach = await self.coach_repository.get_by_id(coach_id)
            if not coach:
                raise ValueError(f"Coach {coach_id} not found")

            reports = await self.report_repository.get_by_coach_and_month(
                coach_id, year, month
            )
            stats = await self.report_repository.get_monthly_stats(
                coach_id, year, month
            )

            output = io.BytesIO()
            doc = SimpleDocTemplate(output, pagesize=A4)
            story = []

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#366092"),
                spaceAfter=12,
            )

            # Title
            story.append(
                Paragraph("Ежемесячный отчет о работе тренера", title_style)
            )
            story.append(Spacer(1, 0.3 * inch))

            # Coach info
            info_data = [
                ["Тренер:", coach.full_name],
                ["Должность:", coach.position],
                ["Команда:", coach.team],
                ["Месяц:", f"{month}/{year}"],
            ]
            info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
            info_table.setStyle(
                TableStyle(
                    [
                        ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
                        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(info_table)
            story.append(Spacer(1, 0.3 * inch))

            # Daily reports table
            table_data = [
                [
                    "Дата",
                    "Присутствие",
                    "Форма",
                    "Часов",
                    "Опоздание",
                    "Примечания",
                ]
            ]

            for report in reports:
                uniform_status = ""
                if (
                    report.upper_uniform.value != "no_data"
                    or report.lower_uniform.value != "no_data"
                ):
                    uniform_status = f"{report.upper_uniform.value}/{report.lower_uniform.value}"

                table_data.append(
                    [
                        str(report.report_date),
                        report.attendance.value[:3],
                        uniform_status,
                        str(float(report.worked_hours or 0)),
                        str(report.late_arrival_minutes),
                        report.notes[:20] if report.notes else "",
                    ]
                )

            table = Table(table_data, colWidths=[1.2 * inch] * 6)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.3 * inch))

            # Statistics
            story.append(Paragraph("Итоговая статистика", title_style))
            stats_data = [
                ["Отработано часов:", str(round(stats["worked_hours"], 2))],
                ["Отработано дней:", str(stats["worked_days"])],
                ["Опозданий:", str(stats["late_arrivals"])],
                ["Дней болезни:", str(stats["sick_days"])],
                ["Дней отпуска:", str(stats["vacation_days"])],
            ]

            stats_table = Table(stats_data, colWidths=[3 * inch, 2 * inch])
            stats_table.setStyle(
                TableStyle(
                    [
                        ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
                        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(stats_table)

            doc.build(story)
            output.seek(0)

            logger.info(f"PDF export created for coach {coach_id}")
            return output.getvalue()

        except ImportError:
            logger.error("reportlab is not installed")
            raise
