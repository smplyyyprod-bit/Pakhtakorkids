"""End-to-end verification against a real database.

Seeds a realistic dataset, exercises the report pipeline, the aggregation
queries and both export formats, then asserts the results. Run with:

    python -m scripts.verify
"""

import asyncio
import random
import sys
from datetime import date, time, timedelta

from sqlalchemy import delete, select

from app.domain.models import Branch, Coach, DailyReport, User
from app.domain.models.daily_report import AttendanceStatus, UniformStatus
from app.infrastructure.database import SessionLocal
from app.infrastructure.services import (
    BranchService,
    CoachService,
    DailyReportService,
    ExportService,
    StatisticsService,
    calculate_worked_hours,
)

BRANCH_NAMES = ["Чиланзар", "Юнусабад", "Мирзо-Улугбек"]
POSITIONS = ["Главный тренер", "Тренер", "Ассистент тренера"]
TEAMS = ["U-10", "U-12", "U-14", "U-16", "Взрослая"]
FIRST = ["Искандар", "Азиз", "Бекзод", "Дилшод", "Тимур", "Рустам", "Жасур", "Отабек"]
LAST = ["Иризметов", "Каримов", "Сафаров", "Юлдашев", "Рахимов", "Тошматов"]

checks_passed = 0
checks_failed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global checks_passed, checks_failed
    if condition:
        checks_passed += 1
        print(f"  PASS  {label}")
    else:
        checks_failed += 1
        print(f"  FAIL  {label}  {detail}")


async def reset(session) -> None:
    await session.execute(delete(DailyReport))
    await session.execute(delete(Coach))
    await session.execute(delete(Branch))
    await session.execute(delete(User))
    await session.commit()


async def seed(session) -> tuple[list[int], list[int]]:
    branch_service = BranchService(session)
    coach_service = CoachService(session)

    branch_ids = []
    for name in BRANCH_NAMES:
        branch = await branch_service.create_branch(name=name)
        branch_ids.append(branch.id)

    coach_ids = []
    counter = 1
    for branch_id in branch_ids:
        for _ in range(17):  # 51 coaches total
            coach = await coach_service.create_coach(
                unique_id=f"PK-{counter:04d}",
                full_name=f"{random.choice(FIRST)} {random.choice(LAST)}",
                position=random.choice(POSITIONS),
                team=random.choice(TEAMS),
                branch_id=branch_id,
            )
            coach_ids.append(coach.id)
            counter += 1

    return branch_ids, coach_ids


async def main() -> int:
    random.seed(20260804)
    today = date.today()

    async with SessionLocal() as session:
        print("\n[1] Seeding")
        await reset(session)
        branch_ids, coach_ids = await seed(session)
        check("3 branches created", len(branch_ids) == 3)
        check("51 coaches created (>50 required)", len(coach_ids) == 51)

        report_service = DailyReportService(session)

        print("\n[2] Placeholder generation (the 'no missing days' guarantee)")
        days = 20
        total_created = 0
        for offset in range(days):
            total_created += await report_service.ensure_day_exists(
                today - timedelta(days=offset)
            )
        check(
            f"{days * 51} placeholder rows created",
            total_created == days * 51,
            f"got {total_created}",
        )

        # Idempotency is what makes the nightly job safe to re-run.
        again = await report_service.ensure_day_exists(today)
        check("re-running creates no duplicates", again == 0, f"got {again}")

        rows = await session.execute(select(DailyReport))
        check("every coach-day has exactly one row", len(rows.scalars().all()) == days * 51)

        print("\n[3] Filling reports")
        filled = 0
        target_coach = coach_ids[0]
        for offset in range(days):
            day = today - timedelta(days=offset)
            for coach_id in coach_ids:
                # Leave roughly 12% unfilled, so 'missing' is a real number.
                if random.random() < 0.12:
                    continue
                coach = await CoachService(session).get_coach(coach_id)
                roll = random.random()
                if roll < 0.06:
                    attendance = AttendanceStatus.SICK_LEAVE
                elif roll < 0.10:
                    attendance = AttendanceStatus.VACATION
                elif roll < 0.12:
                    attendance = AttendanceStatus.UNEXCUSED_ABSENCE
                else:
                    attendance = AttendanceStatus.PRESENT

                late = random.choice([0, 0, 0, 5, 10, 15])
                await report_service.save_report(
                    coach=coach,
                    report_date=day,
                    attendance=attendance,
                    upper_uniform=random.choice(
                        [UniformStatus.YES, UniformStatus.YES, UniformStatus.NO]
                    ),
                    lower_uniform=random.choice(
                        [UniformStatus.YES, UniformStatus.YES, UniformStatus.NO]
                    ),
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                    late_arrival_minutes=late,
                    early_departure_minutes=random.choice([0, 0, 0, 10]),
                )
                filled += 1
        print(f"      filled {filled} of {days * 51} reports")

        print("\n[4] Hour calculation")
        check("09:00-17:00 = 8.0h", calculate_worked_hours(time(9, 0), time(17, 0)) == 8.0)
        check(
            "overnight 22:00-06:00 = 8.0h",
            calculate_worked_hours(time(22, 0), time(6, 0)) == 8.0,
        )
        check("missing times = 0h", calculate_worked_hours(None, None) == 0.0)

        report = await report_service.get_report(target_coach, today)
        if report and report.is_completed:
            if report.attendance == AttendanceStatus.PRESENT:
                check(
                    "present coach has 8h stored",
                    float(report.worked_hours) == 8.0,
                    f"got {report.worked_hours}",
                )
            else:
                check(
                    "absent coach forced to 0h",
                    float(report.worked_hours) == 0.0,
                    f"got {report.worked_hours}",
                )

        print("\n[5] Monthly aggregation")
        stats = await report_service.monthly_stats(target_coach, today.year, today.month)
        check("stats returned for coach", stats.coach_id == target_coach)
        check("total_days > 0", stats.total_days > 0, f"got {stats.total_days}")
        check(
            "incomplete days counted in totals",
            stats.not_filled_days >= 0 and stats.total_days >= stats.worked_days,
        )

        print("\n[6] Dashboard and analytics")
        stats_service = StatisticsService(session)
        overview = await stats_service.company_overview(today.year, today.month)
        check("total_coaches = 51", overview.total_coaches == 51, f"got {overview.total_coaches}")
        check("worked hours > 0", overview.total_worked_hours > 0)
        check(
            "attendance percentage in 0..100",
            0 <= overview.attendance_percentage <= 100,
            f"got {overview.attendance_percentage}",
        )
        check("expected reports > 0", overview.completion.expected > 0)
        check(
            "missing = expected - completed",
            overview.completion.missing
            == overview.completion.expected - overview.completion.completed,
        )
        print(
            f"      expected={overview.completion.expected} "
            f"completed={overview.completion.completed} "
            f"missing={overview.completion.missing} "
            f"({overview.completion.percentage}%)"
        )

        rankings = await stats_service.rankings(today.year, today.month)
        check("rankings: hours leaderboard populated", len(rankings.most_worked_hours) > 0)
        check("rankings: punctuality leaderboard populated", len(rankings.most_punctual) > 0)
        check(
            "hours leaderboard sorted descending",
            all(
                a.worked_hours >= b.worked_hours
                for a, b in zip(rankings.most_worked_hours, rankings.most_worked_hours[1:])
            ),
        )

        comparison = await stats_service.compare_coaches(today.year, today.month)
        check("comparison covers all coaches", len(comparison) == 51, f"got {len(comparison)}")

        trend = await stats_service.attendance_trend(today.year, today.month)
        check("attendance trend has daily rows", len(trend) > 0)

        print("\n[7] Exports")
        export_service = ExportService(session)
        xlsx = await export_service.export_excel(target_coach, today.year, today.month)
        check("xlsx produced", len(xlsx) > 5000, f"{len(xlsx)} bytes")
        check("xlsx has zip magic bytes", xlsx[:2] == b"PK")

        pdf = await export_service.export_pdf(target_coach, today.year, today.month)
        check("pdf produced", len(pdf) > 3000, f"{len(pdf)} bytes")
        check("pdf has header", pdf[:5] == b"%PDF-")
        # Confirms a Unicode font was embedded rather than falling back to a
        # Latin-only base font, which would silently drop Cyrillic.
        check("pdf embeds DejaVu (Cyrillic capable)", b"DejaVu" in pdf)

        with open("/tmp/verify_report.xlsx", "wb") as fh:
            fh.write(xlsx)
        with open("/tmp/verify_report.pdf", "wb") as fh:
            fh.write(pdf)
        print("      wrote /tmp/verify_report.xlsx and /tmp/verify_report.pdf")

        print("\n[8] Audit trail")
        from app.domain.models import AuditLog

        audit_rows = await session.execute(select(AuditLog))
        audit_count = len(audit_rows.scalars().all())
        check("modifications were logged", audit_count > 0, f"got {audit_count}")
        print(f"      {audit_count} audit entries")

    print(f"\n{'=' * 52}")
    print(f"  passed: {checks_passed}   failed: {checks_failed}")
    print(f"{'=' * 52}\n")
    return 1 if checks_failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
