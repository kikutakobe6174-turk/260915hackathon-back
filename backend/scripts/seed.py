"""Seed the database with minimal sample data for local development.

Run with: python scripts/seed.py (from backend/, with the venv active)
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db import SessionLocal
from app.models import (
    Format,
    Hint,
    Lesson,
    Problem,
    ProblemPrerequisite,
    School,
    Student,
    Test,
    TestScope,
    Textbook,
    Unit,
    User,
    Worksheet,
    WorksheetItem,
)


def run() -> None:
    db = SessionLocal()
    try:
        if db.query(User).first():
            print("Seed data already present. Skipping.")
            return

        operator = User(
            login_id="operator1",
            password_hash=hash_password("password123"),
            name="運営 太郎",
            role="operator",
            active=True,
        )
        teacher = User(
            login_id="teacher1",
            password_hash=hash_password("password123"),
            name="先生 花子",
            role="teacher",
            active=True,
        )
        db.add_all([operator, teacher])
        db.flush()

        school = School(name="ひかり中学校")
        db.add(school)
        db.flush()

        textbook = Textbook(publisher="サンプル出版", title="新編 数学1", subject="数学")
        db.add(textbook)
        db.flush()

        unit_names = [
            "正負の数",
            "文字と式",
            "一次方程式",
            "比例と反比例",
            "平面図形",
            "空間図形",
            "資料の活用",
            "連立方程式",
            "一次関数",
            "図形の性質",
        ]
        units = [Unit(textbook_id=textbook.id, name=name, order_no=i + 1) for i, name in enumerate(unit_names)]
        db.add_all(units)
        db.flush()

        formats = [Format(name="計算"), Format(name="文章題"), Format(name="証明")]
        db.add_all(formats)
        db.flush()

        students = [
            Student(student_code=f"S{i:04d}", school_id=school.id, grade="中1", level=level, active=True)
            for i, level in enumerate(["A", "B", "B", "C", "C"], start=1)
        ]
        db.add_all(students)
        db.flush()

        past_test = Test(
            school_id=school.id,
            textbook_id=textbook.id,
            year=2025,
            grade="中1",
            term="1学期期末",
            kind="past",
        )
        db.add(past_test)
        db.flush()

        db.add_all(TestScope(test_id=past_test.id, unit_id=u.id) for u in units[:4])

        calc_unit = units[2]  # 一次方程式
        calc_format = formats[0]
        problem = Problem(
            unit_id=calc_unit.id,
            format_id=calc_format.id,
            difficulty=2,
            body=r"方程式 $3x - 5 = 2x + 7$ を解け。",
            answer="x = 12",
            explanation=r"$3x - 2x = 7 + 5$ より $x = 12$",
            is_return=False,
            status="reviewed",
            source="manual",
            reviewed_by=operator.id,
        )
        db.add(problem)
        db.flush()

        db.add_all(
            [
                Hint(problem_id=problem.id, step=1, body="文字の項を左辺に、数の項を右辺に集める。"),
                Hint(problem_id=problem.id, step=2, body="$3x - 2x$ と $7 + 5$ をそれぞれ計算する。"),
                Hint(problem_id=problem.id, step=3, body="$x = 12$ になることを確認する。"),
            ]
        )
        db.add(ProblemPrerequisite(problem_id=problem.id, unit_id=units[1].id))

        worksheet = Worksheet(test_id=past_test.id, level="B", version=1)
        db.add(worksheet)
        db.flush()

        db.add(
            WorksheetItem(
                worksheet_id=worksheet.id,
                item_no="1",
                sort_order=1,
                problem_id=problem.id,
                is_return=False,
            )
        )

        lesson = Lesson(test_id=past_test.id, lesson_date=date.today(), class_name="中1A", round=1)
        db.add(lesson)

        db.commit()
        print("Seed data created.")
        print("  operator1 / password123 (role=operator)")
        print("  teacher1  / password123 (role=teacher)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
