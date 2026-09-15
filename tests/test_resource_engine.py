import ast
import hashlib
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"
TREE = ast.parse(APP.read_text(encoding="utf-8"))

def _extract(names):
    nodes = [n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = {"hashlib": hashlib, "re": re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP), "exec"), ns)
    return ns

def test_any_topic_quiz_has_four_options_and_one_answer():
    ns = _extract({"_q", "_build_topic_quiz"})
    sections = [
        (f"{i}. Point {i}", f"Verified lesson statement {i} for the selected topic.")
        for i in range(1, 26)
    ]
    quiz = ns["_build_topic_quiz"]("Example Topic", sections, 20)
    assert len(quiz) == 20
    assert all(len(q["options"]) == 4 for q in quiz)
    assert all(0 <= q["answer"] < 4 for q in quiz)
