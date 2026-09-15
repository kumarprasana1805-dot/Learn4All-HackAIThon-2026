import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learn4all import Assessment, ClassSummary, LearnerReport, Resource, ResourceRecommender, Student, Subject


def test_core_requirements():
    subject = Subject("Mathematics", ["Geometry"])
    assert subject.name == "Mathematics"

    student = Student("S1", "Aman")
    student.add_assessment(Assessment(subject.name, "Geometry", 45, 100))
    student.add_assessment(Assessment(subject.name, "Algebra", 85, 100))

    resources = [
        Resource(1, "Geometry Video", "Mathematics", "Geometry", "video", True),
        Resource(2, "Geometry Notes", "Mathematics", "Geometry", "notes", True),
    ]
    recommender = ResourceRecommender(resources)

    assert student.overall_average() == 65
    assert student.weak_topics()[0]["topic"] == "Geometry"
    assert student.strengths()[0]["topic"] == "Algebra"
    assert len(recommender.recommend(student)["Geometry"]) == 2
    assert LearnerReport(student, recommender).generate()["next_actions"]

    second = Student("S2", "Riya")
    second.add_assessment(Assessment("Mathematics", "Geometry", 50, 100))
    summary = ClassSummary([student, second]).generate()
    assert summary["common_weak_topics"] == [("Geometry", 2)]


if __name__ == '__main__':
    test_core_requirements()
    print('OOP core smoke test passed.')
