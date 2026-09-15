"""Learn4All domain model: Python Fundamentals + OOP reference implementation."""
from statistics import mean

class Subject:
    """A subject containing a list of topics."""
    def __init__(self, name, topics=None):
        self.name = name
        self.topics = list(topics or [])
    def add_topic(self, topic):
        if topic not in self.topics:
            self.topics.append(topic)

class Assessment:
    """One assessment result for one topic."""
    def __init__(self, subject, topic, score, max_score=100):
        self.subject = subject
        self.topic = topic
        self.score = float(score)
        self.max_score = float(max_score)
    @property
    def percentage(self):
        return round((self.score / self.max_score) * 100, 1) if self.max_score > 0 else 0.0

class Resource:
    """A learning resource tagged by subject, topic and category."""
    VALID_CATEGORIES = {"video", "notes", "quiz", "practice"}
    def __init__(self, resource_id, title, subject, topic, category, accessible=True):
        if category not in self.VALID_CATEGORIES:
            raise ValueError(f"Unsupported resource category: {category}")
        self.resource_id = resource_id
        self.title = title
        self.subject = subject
        self.topic = topic
        self.category = category
        self.accessible = bool(accessible)
    def __repr__(self):
        return f"[{self.category}] {self.title} ({self.subject}/{self.topic})"

class Student:
    """A learner with assessment history and accessibility needs."""
    WEAK_THRESHOLD = 60
    STRENGTH_THRESHOLD = 80
    def __init__(self, student_id, name, accessibility_needs=None):
        self.student_id = student_id
        self.name = name
        self.accessibility_needs = list(accessibility_needs or [])
        self.assessments = []
    def add_assessment(self, assessment):
        self.assessments.append(assessment)
    def performance_by_subject(self):
        grouped = {}
        for a in self.assessments:
            grouped.setdefault(a.subject, []).append(a.percentage)
        return {s: round(mean(v), 1) for s, v in grouped.items()}
    def performance_by_topic(self):
        grouped = {}
        for a in self.assessments:
            grouped.setdefault((a.subject, a.topic), []).append(a.percentage)
        return {k: round(mean(v), 1) for k, v in grouped.items()}
    def weak_topics(self):
        return [{"subject": s, "topic": t, "percentage": p} for (s, t), p in self.performance_by_topic().items() if p < self.WEAK_THRESHOLD]
    def strengths(self):
        return [{"subject": s, "topic": t, "percentage": p} for (s, t), p in self.performance_by_topic().items() if p >= self.STRENGTH_THRESHOLD]
    def overall_average(self):
        return round(mean(a.percentage for a in self.assessments), 1) if self.assessments else 0.0

class ResourceRecommender:
    """Match weak topics to resources, preferring accessible resources."""
    def __init__(self, resources):
        self.resources = list(resources)
    @staticmethod
    def _same(value1, value2):
        return str(value1).strip().casefold() == str(value2).strip().casefold()
    def recommend(self, student, limit_per_topic=2):
        result = {}
        for weak in student.weak_topics():
            matches = [r for r in self.resources if self._same(r.topic, weak["topic"]) and self._same(r.subject, weak["subject"])]
            if student.accessibility_needs:
                matches = [r for r in matches if r.accessible] or matches
            result[weak["topic"]] = matches[:limit_per_topic]
        return result

class LearnerReport:
    """Generate the individual report required by the challenge."""
    def __init__(self, student, recommender):
        self.student = student
        self.recommender = recommender
    def generate(self):
        weak = self.student.weak_topics()
        return {
            "student": self.student.name,
            "overall_average": self.student.overall_average(),
            "performance_by_subject": self.student.performance_by_subject(),
            "strengths": self.student.strengths(),
            "weak_topics": weak,
            "recommended_resources": self.recommender.recommend(self.student),
            "next_actions": [f"Revisit '{x['topic']}' using the recommended resources" for x in weak],
        }

class ClassSummary:
    """Aggregate learner performance and common topic gaps."""
    def __init__(self, students):
        self.students = list(students)
    def generate(self):
        averages = {s.name: s.overall_average() for s in self.students}
        gap_counts = {}
        for student in self.students:
            for weak in student.weak_topics():
                gap_counts[weak["topic"]] = gap_counts.get(weak["topic"], 0) + 1
        return {
            "class_average": round(mean(averages.values()), 1) if averages else 0.0,
            "student_averages": averages,
            "common_weak_topics": sorted(gap_counts.items(), key=lambda x: (-x[1], x[0])),
        }
