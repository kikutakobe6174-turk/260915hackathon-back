"""Seed the database with minimal sample data for local development.

Run with: python scripts/seed.py (from backend/, with the venv active)
"""

import sys
from datetime import date, datetime
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
    TestTrend,
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

        # past_test の出題傾向（レビュー済み）。「問題作成（過去問の傾向から）」機能が
        # 傾向データを元に問題を自動生成できるよう、スコープ内の単元に対して登録しておく。
        calc_format, word_format = formats[0], formats[1]
        now = datetime.now()
        trend_examples = [
            # 0正負の数
            {"unit": 0, "format": calc_format, "question_no": "1(1)", "points": 4, "difficulty": 1},
            {"unit": 0, "format": calc_format, "question_no": "1(2)", "points": 4, "difficulty": 2},
            # 1文字と式
            {"unit": 1, "format": calc_format, "question_no": "1(3)", "points": 4, "difficulty": 1},
            {"unit": 1, "format": calc_format, "question_no": "1(4)", "points": 4, "difficulty": 2},
            # 2一次方程式
            {"unit": 2, "format": calc_format, "question_no": "2(1)", "points": 5, "difficulty": 2},
            {"unit": 2, "format": calc_format, "question_no": "2(2)", "points": 5, "difficulty": 2},
            {"unit": 2, "format": word_format, "question_no": "3", "points": 8, "difficulty": 3},
            # 3比例と反比例
            {"unit": 3, "format": word_format, "question_no": "4(1)", "points": 6, "difficulty": 2},
            {"unit": 3, "format": word_format, "question_no": "4(2)", "points": 6, "difficulty": 2},
        ]
        db.add_all(
            TestTrend(
                test_id=past_test.id,
                unit_id=units[ex["unit"]].id,
                format_id=ex["format"].id,
                question_no=ex["question_no"],
                points=ex["points"],
                difficulty=ex["difficulty"],
                source="manual",
                reviewed=True,
                reviewed_by=operator.id,
                reviewed_at=now,
            )
            for ex in trend_examples
        )

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

        # 単元別の下書き問題の例（status="draft"、未レビュー）。
        # unit_names のインデックス: 0正負の数 1文字と式 2一次方程式 3比例と反比例 4平面図形
        #                          5空間図形 6資料の活用 7連立方程式 8一次関数 9図形の性質
        draft_examples = [
            {
                "unit": 0,
                "format": 0,
                "difficulty": 1,
                "body": r"次の計算をしなさい。$(-5) + 8 - (-3)$",
                "answer": "6",
                "explanation": r"$(-5) + 8 - (-3) = -5 + 8 + 3 = 6$",
                "hints": [
                    "まず $-(-3)$ を $+3$ に直そう。",
                    "左から順に $-5 + 8$ を計算する。",
                    "$3 + 3 = 6$ になることを確認する。",
                ],
            },
            {
                "unit": 1,
                "format": 0,
                "difficulty": 1,
                "body": r"$x = 4$ のとき、$2x + 3$ の値を求めなさい。",
                "answer": "11",
                "explanation": r"$2 \times 4 + 3 = 8 + 3 = 11$",
                "hints": [
                    "$x$ に $4$ を代入する。",
                    "$2 \\times 4$ を先に計算する。",
                    "$8 + 3$ を計算して答えを出す。",
                ],
            },
            {
                "unit": 2,
                "format": 0,
                "difficulty": 2,
                "body": r"方程式 $2(x - 3) = x + 1$ を解け。",
                "answer": "x = 7",
                "explanation": r"展開して $2x - 6 = x + 1$、整理して $x = 7$",
                "hints": [
                    "左辺のかっこをまず展開しよう。",
                    "文字の項を左辺に、数の項を右辺に集める。",
                    "$x = 7$ になることを確認する。",
                ],
                "prerequisite": 1,
            },
            {
                "unit": 3,
                "format": 1,
                "difficulty": 2,
                "body": r"$y$ は $x$ に比例し、$x = 3$ のとき $y = 12$ である。$x = 5$ のときの $y$ の値を求めなさい。",
                "answer": "20",
                "explanation": r"比例定数は $12 \div 3 = 4$ なので $y = 4x$。$x = 5$ を代入して $y = 20$。",
                "hints": [
                    "比例の式は $y = ax$ の形になる。",
                    "$x = 3, y = 12$ から比例定数 $a$ を求める。",
                    "$y = 4x$ に $x = 5$ を代入する。",
                ],
            },
            {
                "unit": 4,
                "format": 0,
                "difficulty": 2,
                "body": r"半径 $6\text{cm}$ の円の面積を求めなさい。ただし、円周率は $\pi$ とする。",
                "answer": r"$36\pi \text{cm}^2$",
                "explanation": r"円の面積は $\pi r^2$ なので $\pi \times 6^2 = 36\pi$",
                "hints": [
                    "円の面積の公式 $\\pi r^2$ を思い出そう。",
                    "半径 $r = 6$ を公式に代入する。",
                    "$6^2 = 36$ を計算し、$\\pi$ をつけて答える。",
                ],
            },
            {
                "unit": 5,
                "format": 0,
                "difficulty": 2,
                "body": r"底面が1辺 $6\text{cm}$ の正方形、高さ $9\text{cm}$ の正四角錐の体積を求めなさい。",
                "answer": r"$108\text{cm}^3$",
                "explanation": r"角錐の体積は「底面積 $\times$ 高さ $\div 3$」。底面積 $= 6 \times 6 = 36$、$36 \times 9 \div 3 = 108$",
                "hints": [
                    "角錐の体積は「底面積 × 高さ ÷ 3」で求められる。",
                    "底面積 $6 \\times 6 = 36$ をまず計算する。",
                    "$36 \\times 9 \\div 3$ を計算する。",
                ],
            },
            {
                "unit": 6,
                "format": 1,
                "difficulty": 1,
                "body": "5人のテストの得点が 60, 75, 80, 65, 70 のとき、この5人の平均点を求めなさい。",
                "answer": "70点",
                "explanation": "合計 $60+75+80+65+70=350$ を人数 $5$ で割ると $70$。",
                "hints": [
                    "平均は合計を人数で割って求める。",
                    "まず5人の得点をすべて足す。",
                    "合計を5で割る。",
                ],
            },
            {
                "unit": 7,
                "format": 0,
                "difficulty": 3,
                "body": r"連立方程式 $\begin{cases} x + y = 7 \\ 2x - y = 2 \end{cases}$ を解け。",
                "answer": "x = 3, y = 4",
                "explanation": r"2式を足すと $3x = 9$ より $x = 3$。$x = 3$ を1式目に代入して $y = 4$。",
                "hints": [
                    "加減法か代入法、どちらを使うか考えよう。",
                    "2式を足すと $y$ が消えることに気づく。",
                    "$x = 3$ を1式目に代入して $y$ を求める。",
                ],
                "prerequisite": 2,
            },
            {
                "unit": 8,
                "format": 0,
                "difficulty": 2,
                "body": r"一次関数 $y = 2x - 3$ について、$x = 4$ のときの $y$ の値を求めなさい。",
                "answer": "5",
                "explanation": r"$y = 2 \times 4 - 3 = 8 - 3 = 5$",
                "hints": [
                    "$x$ に $4$ を代入する。",
                    "$2 \\times 4$ を先に計算する。",
                    "$8 - 3$ を計算して答えを出す。",
                ],
                "prerequisite": 3,
            },
            {
                "unit": 9,
                "format": 2,
                "difficulty": 2,
                "body": (
                    r"$AB = AC$ である $\triangle ABC$ において、頂角 $A$ の二等分線と辺 $BC$ の交点を $D$ とする。"
                    "このとき、底角が等しい（$\\angle ABC = \\angle ACB$）ことを証明しなさい。"
                ),
                "answer": r"$\triangle ABD \equiv \triangle ACD$（2辺とその間の角がそれぞれ等しい）より $\angle ABD = \angle ACD$",
                "explanation": (
                    r"$AB = AC$（仮定）、$AD$ は共通、$\angle BAD = \angle CAD$（二等分線の定義）より、"
                    r"2辺とその間の角がそれぞれ等しいので $\triangle ABD \equiv \triangle ACD$。"
                    "対応する角が等しいことから底角が等しいと言える。"
                ),
                "hints": [
                    "頂角の二等分線によってできる2つの三角形に注目しよう。",
                    "$AB = AC$、$AD$共通、はさむ角が等しいことから合同条件を考える。",
                    "合同な三角形の対応する角は等しいことを使って結論を導く。",
                ],
                "prerequisite": 4,
            },
        ]

        for ex in draft_examples:
            draft = Problem(
                unit_id=units[ex["unit"]].id,
                format_id=formats[ex["format"]].id,
                difficulty=ex["difficulty"],
                body=ex["body"],
                answer=ex["answer"],
                explanation=ex["explanation"],
                is_return=False,
                status="draft",
                source="manual",
            )
            db.add(draft)
            db.flush()

            db.add_all(
                Hint(problem_id=draft.id, step=i + 1, body=hint_body)
                for i, hint_body in enumerate(ex["hints"])
            )
            if "prerequisite" in ex:
                db.add(ProblemPrerequisite(problem_id=draft.id, unit_id=units[ex["prerequisite"]].id))

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
