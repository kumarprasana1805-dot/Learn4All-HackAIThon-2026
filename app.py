import os
import sqlite3
import json
import hashlib
import shutil
import subprocess
import re
import urllib.parse
import urllib.request
from functools import wraps, lru_cache
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from learn4all import Assessment, ClassSummary, LearnerReport, Resource, ResourceRecommender, Student, Subject

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "learn4all.db")

app = Flask(__name__)
app.secret_key = os.environ.get("LEARN4ALL_SECRET", "change-this-secret-in-production")
app.config["DATABASE"] = DB_PATH

WEAK_THRESHOLD = Student.WEAK_THRESHOLD
STRENGTH_THRESHOLD = Student.STRENGTH_THRESHOLD


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ensure_resource_bundle(db, subject, topic):
    """Create one complete four-category resource bundle when needed."""
    subject = str(subject or "General").strip() or "General"
    topic = str(topic or "General Topic").strip() or "General Topic"
    catalog = [
        (f"{topic} — Concept Video", subject, topic, "video", 1,
         f"A focused lesson introducing the key ideas of {topic}."),
        (f"{topic} — Quick Notes", subject, topic, "notes", 1,
         f"Concise revision notes for the important ideas in {topic}."),
        (f"{topic} — Knowledge Quiz", subject, topic, "quiz", 1,
         f"A short knowledge check for {topic}."),
        (f"{topic} — Practice Lab", subject, topic, "practice", 1,
         f"Guided practice questions for {topic}."),
    ]
    for resource in catalog:
        exists = db.execute(
            """SELECT 1 FROM resources
               WHERE LOWER(subject)=LOWER(?) AND LOWER(topic)=LOWER(?)
                 AND LOWER(category)=LOWER(?) LIMIT 1""",
            (subject, topic, resource[3]),
        ).fetchone()
        if not exists:
            db.execute(
                """INSERT INTO resources
                   (title,subject,topic,category,accessible,description)
                   VALUES(?,?,?,?,?,?)""",
                resource,
            )


def ensure_topic_resources(db):
    """Backfill resources for every topic already used by assessments."""
    topics = db.execute(
        "SELECT DISTINCT subject, topic FROM assessments WHERE TRIM(topic) <> ''"
    ).fetchall()
    for row in topics:
        ensure_resource_bundle(db, row["subject"], row["topic"])


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        accessibility_needs TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        topic TEXT NOT NULL,
        score REAL NOT NULL,
        max_score REAL NOT NULL DEFAULT 100,
        taken_at TEXT NOT NULL,
        FOREIGN KEY(student_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        topic TEXT NOT NULL,
        category TEXT NOT NULL,
        accessible INTEGER NOT NULL DEFAULT 1,
        description TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    db.commit()

    # Only the demo teacher and the system resource catalog are seeded.
    # No student account or student assessment is pre-populated.
    teacher = db.execute(
        "SELECT id FROM users WHERE email = ?",
        ("teacher@learn4all.in",)
    ).fetchone()
    if not teacher:
        db.execute(
            """INSERT INTO users
               (name,email,password_hash,role,accessibility_needs,created_at)
               VALUES(?,?,?,?,?,?)""",
            (
                "Learn4All Teacher",
                "teacher@learn4all.in",
                generate_password_hash("Teacher@123"),
                "teacher",
                "",
                datetime.now().isoformat(),
            ),
        )

    # Seed the built-in resource catalog idempotently.
    resources = [
        ("Fractions Explained", "Mathematics", "Fractions", "video", 1, "Visual explanation with step-by-step examples."),
        ("Fractions Quick Notes", "Mathematics", "Fractions", "notes", 1, "Concise revision notes and formulas."),
        ("Fractions Mastery Quiz", "Mathematics", "Fractions", "quiz", 1, "Short diagnostic quiz to reinforce concepts."),
        ("Fractions Practice Sheet", "Mathematics", "Fractions", "practice", 1, "Guided practice set with worked examples."),
        ("Geometry Fundamentals", "Mathematics", "Geometry", "video", 1, "Visual walkthrough of core geometry concepts."),
        ("Geometry Quick Notes", "Mathematics", "Geometry", "notes", 1, "Concise geometry definitions, theorems and formulas."),
        ("Geometry Mastery Quiz", "Mathematics", "Geometry", "quiz", 1, "A short quiz to check geometry understanding."),
        ("Geometry Practice Set", "Mathematics", "Geometry", "practice", 1, "Progressive questions for geometry practice."),
        ("Algebra Essentials", "Mathematics", "Algebra", "video", 1, "Concept-first algebra walkthrough."),
        ("Algebra Quick Notes", "Mathematics", "Algebra", "notes", 1, "Core algebra concepts and examples."),
        ("Algebra Mastery Quiz", "Mathematics", "Algebra", "quiz", 1, "Quick algebra knowledge check."),
        ("Algebra Practice Lab", "Mathematics", "Algebra", "practice", 1, "Progressive practice exercises."),
        ("Photosynthesis Basics", "Science", "Photosynthesis", "video", 1, "Caption-friendly visual explanation."),
        ("Photosynthesis Quick Notes", "Science", "Photosynthesis", "notes", 1, "Accessible notes covering the core process."),
        ("Photosynthesis Quiz", "Science", "Photosynthesis", "quiz", 0, "Quick knowledge check."),
        ("Photosynthesis Practice", "Science", "Photosynthesis", "practice", 1, "Practice questions on the process."),
        ("Grammar Essentials", "English", "Grammar", "video", 1, "Foundational grammar walkthrough."),
        ("Grammar Revision Notes", "English", "Grammar", "notes", 1, "Quick reference for revision."),
        ("Grammar Mastery Quiz", "English", "Grammar", "quiz", 1, "Short grammar knowledge check."),
        ("Grammar Practice", "English", "Grammar", "practice", 1, "Practice tasks for common grammar errors."),
        ("Electricity Fundamentals", "Physics", "Electricity", "video", 1, "Concept-first lesson with examples."),
        ("Electricity Formula Notes", "Physics", "Electricity", "notes", 1, "Formula sheet and worked examples."),
        ("Electricity Mastery Quiz", "Physics", "Electricity", "quiz", 1, "Quick circuit and formula check."),
        ("Electricity Practice", "Physics", "Electricity", "practice", 1, "Numerical and concept practice."),
        ("Thermodynamics Concept Video", "Physics", "Thermodynamics", "video", 1, "Focused lesson on the laws of thermodynamics, heat and work."),
        ("Thermodynamics Quick Notes", "Physics", "Thermodynamics", "notes", 1, "Concise revision notes for thermal concepts and laws."),
        ("Thermodynamics Mastery Quiz", "Physics", "Thermodynamics", "quiz", 1, "Quick knowledge check on thermodynamic concepts."),
        ("Thermodynamics Practice Lab", "Physics", "Thermodynamics", "practice", 1, "Conceptual and numerical thermodynamics practice."),
    ]
    for resource in resources:
        exists = db.execute("SELECT 1 FROM resources WHERE title = ? LIMIT 1", (resource[0],)).fetchone()
        if not exists:
            db.execute(
                """INSERT INTO resources
                   (title,subject,topic,category,accessible,description)
                   VALUES(?,?,?,?,?,?)""",
                resource,
            )

    # Backfill a complete four-category resource set for any topic already
    # present in student assessment data. This keeps recommendations functional
    # even when a learner enters a topic that was not in the starter catalog.
    ensure_topic_resources(db)

    db.commit()
    db.close()


@app.before_request
def load_user():
    g.user = None
    uid = session.get("user_id")
    if uid:
        g.user = get_db().execute(
            "SELECT * FROM users WHERE id = ?", (uid,)
        ).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not g.user:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if g.user["role"] != role:
                flash("You do not have permission to access that area.", "danger")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def score_pct(row):
    return round((row["score"] / row["max_score"]) * 100, 1) if row["max_score"] else 0


def calculate_streak(assessments):
    """Count consecutive calendar days represented by assessment activity."""
    if not assessments:
        return 0
    days = sorted(
        {datetime.fromisoformat(x["taken_at"]).date() for x in assessments},
        reverse=True,
    )
    if not days:
        return 0
    streak = 1
    for previous, current in zip(days, days[1:]):
        if (previous - current).days == 1:
            streak += 1
        else:
            break
    return streak


def student_metrics(student_id):
    """Build learner metrics using the OOP domain model."""
    db = get_db()
    rows = db.execute(
        """SELECT * FROM assessments
           WHERE student_id = ?
           ORDER BY taken_at DESC, id DESC""",
        (student_id,),
    ).fetchall()
    user = db.execute("SELECT * FROM users WHERE id = ?", (student_id,)).fetchone()
    needs = [x.strip().lower() for x in (user["accessibility_needs"] or "").split(",") if x.strip()] if user else []
    student = Student(student_id, user["name"] if user else "Learner", needs)
    enriched = []
    for row in rows:
        assessment = Assessment(row["subject"], row["topic"], row["score"], row["max_score"])
        student.add_assessment(assessment)
        item = dict(row)
        item["percentage"] = assessment.percentage
        item["taken_display"] = datetime.fromisoformat(row["taken_at"]).strftime("%d %b %Y")
        enriched.append(item)

    subject_avg = student.performance_by_subject()
    topic_avg = [{"subject": s, "topic": t, "percentage": p} for (s, t), p in student.performance_by_topic().items()]
    topic_avg.sort(key=lambda x: x["percentage"])

    resource_rows = db.execute("SELECT * FROM resources ORDER BY id").fetchall()
    resource_objects = [Resource(r["id"], r["title"], r["subject"], r["topic"], r["category"], bool(r["accessible"])) for r in resource_rows]
    recs = ResourceRecommender(resource_objects).recommend(student)
    resource_map = {r["id"]: dict(r) for r in resource_rows}
    recommendations = [resource_map[item.resource_id] for items in recs.values() for item in items]

    return {
        "assessments": enriched,
        "overall": student.overall_average(),
        "subject_avg": subject_avg,
        "subject_items": sorted(({"name": n, "average": a} for n, a in subject_avg.items()), key=lambda x: x["average"], reverse=True),
        "topic_avg": topic_avg,
        "weak": student.weak_topics(),
        "strengths": student.strengths(),
        "recommendations": recommendations,
        "needs": needs,
        "streak": calculate_streak(enriched),
        "latest": enriched[0] if enriched else None,
    }


@app.context_processor
def inject_globals():
    return {
        "app_name": "Learn4All",
        "weak_threshold": WEAK_THRESHOLD,
        "strength_threshold": STRENGTH_THRESHOLD,
    }


@app.route("/")
def index():
    if g.user:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/about")
def about():
    return render_template("public_page.html", page="about")


@app.route("/impact")
def impact():
    return render_template("public_page.html", page="impact")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        message = request.form.get("message", "").strip()
        if len(name) < 2 or "@" not in email or len(message) < 5:
            flash("Please enter a valid name, email and message.", "danger")
            return render_template("public_page.html", page="contact")
        db = get_db()
        db.execute(
            """INSERT INTO contact_messages(name,email,message,created_at)
               VALUES(?,?,?,?)""",
            (name, email, message, datetime.now().isoformat()),
        )
        db.commit()
        flash(
            "Your message has been received. Thank you for contacting Learn4All!",
            "success",
        )
        return redirect(url_for("contact"))
    return render_template("public_page.html", page="contact")


@app.route("/help")
def help_page():
    return render_template("public_page.html", page="help")


@app.route("/forgot-password")
def forgot_password():
    flash(
        "For this prototype, password recovery is handled by the school or administrator. Please use Contact for assistance.",
        "info",
    )
    return redirect(url_for("contact"))


@app.route("/social-login/<provider>")
def social_login(provider):
    provider = provider.lower()
    if provider not in {"google", "microsoft"}:
        flash("Unsupported sign-in provider.", "danger")
        return redirect(url_for("login"))
    flash(
        f"{provider.title()} sign-in is available as a demo action. "
        "Connect OAuth credentials for live provider authentication.",
        "info",
    )
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(
                f"Welcome back, {user['name'].split()[0]}!",
                "success",
            )
            return redirect(url_for("welcome"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        needs = request.form.get("accessibility_needs", "").strip()

        if len(name) < 2 or "@" not in email:
            flash("Please enter a valid name and email.", "danger")
            return render_template("signup.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("signup.html")

        db = get_db()
        try:
            cur = db.execute(
                """INSERT INTO users
                   (name,email,password_hash,role,accessibility_needs,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (
                    name,
                    email,
                    generate_password_hash(password),
                    "student",
                    needs,
                    datetime.now().isoformat(),
                ),
            )
            db.commit()
            session.clear()
            session["user_id"] = cur.lastrowid
            flash("Account created successfully.", "success")
            return redirect(url_for("welcome"))
        except sqlite3.IntegrityError:
            flash("That email is already registered. Please log in.", "warning")
    return render_template("signup.html")


@app.route("/welcome")
@login_required
def welcome():
    return render_template("welcome.html", user=g.user)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out safely.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    if g.user["role"] == "teacher":
        return redirect(url_for("teacher_dashboard"))
    m = student_metrics(g.user["id"])
    return render_template("dashboard.html", metrics=m, user=g.user)


@app.route("/assessments", methods=["GET", "POST"])
@role_required("student")
def assessments():
    db = get_db()
    if request.method == "POST":
        try:
            subject = request.form["subject"].strip()
            topic = request.form["topic"].strip()
            score = float(request.form["score"])
            max_score = float(request.form.get("max_score", 100))
            if (
                not subject
                or not topic
                or score < 0
                or max_score <= 0
                or score > max_score
            ):
                raise ValueError
            db.execute(
                """INSERT INTO assessments
                   (student_id,subject,topic,score,max_score,taken_at)
                   VALUES(?,?,?,?,?,?)""",
                (
                    g.user["id"],
                    subject,
                    topic,
                    score,
                    max_score,
                    datetime.now().isoformat(),
                ),
            )
            # Immediately create the four resource categories for the newly
            # assessed topic so the learner can act on the result at once.
            ensure_topic_resources(db)
            db.commit()
            flash(
                "Assessment saved. Your dashboard and recommendations updated instantly.",
                "success",
            )
            return redirect(url_for("assessments"))
        except (ValueError, KeyError):
            flash("Please enter valid assessment values.", "danger")
    m = student_metrics(g.user["id"])
    return render_template("assessments.html", metrics=m)


@app.route("/performance")
@role_required("student")
def performance():
    m = student_metrics(g.user["id"])
    return render_template("performance.html", metrics=m)


@app.route("/weak-topics")
@role_required("student")
def weak_topics():
    m = student_metrics(g.user["id"])
    return render_template("weak_topics.html", metrics=m)



def _q(question, options, answer):
    return {"question": question, "options": options, "answer": answer}


RESOURCE_LIBRARY = {
    "fractions": {
        "summary": "Fractions represent parts of a whole. This lesson builds from numerator and denominator to equivalent fractions, comparison, and the four operations.",
        "sections": [
            ("1. Parts of a fraction", "The numerator tells how many equal parts are being considered. The denominator tells how many equal parts make the whole. In 3/5, 3 is the numerator and 5 is the denominator."),
            ("2. Equivalent fractions", "Multiplying or dividing the numerator and denominator by the same non-zero number gives an equivalent fraction. For example, 2/3 = 4/6 = 6/9."),
            ("3. Comparing fractions", "With the same denominator, the larger numerator gives the larger fraction. With different denominators, convert to a common denominator or compare using cross multiplication."),
            ("4. Addition and subtraction", "Fractions with the same denominator can be added directly. With different denominators, first find a common denominator, then add or subtract the numerators."),
            ("5. Multiplication and division", "Multiply numerators and denominators for multiplication. For division, multiply by the reciprocal of the second fraction. Simplify the final answer."),
            ("6. Worked example", "For 1/4 + 2/3, the LCM of 4 and 3 is 12. Convert to 3/12 + 8/12 = 11/12."),
        ],
        "video": ["What a fraction represents", "Equivalent fractions and comparison", "Adding and subtracting", "Multiplying and dividing", "Worked example and recap"],
        "practice": ["Simplify 24/36.", "Add 3/8 + 1/4.", "Subtract 5/6 − 1/3.", "Multiply 2/5 × 15/4.", "Divide 3/4 by 2/3.", "Which is larger: 5/8 or 2/3?", "Write 7/10 as a decimal.", "Find 3/7 of 28.", "Convert 11/4 to a mixed number.", "A class has 24 students and 3/8 are absent. How many are absent?"],
        "answers": ["2/3", "5/8", "1/2", "3/2", "9/8", "2/3", "0.7", "12", "2 3/4", "9 students"],
        "quiz": [
            _q("In 3/7, what is the denominator?", ["3", "7", "10"], 1), _q("Which is equivalent to 2/5?", ["4/10", "4/15", "6/20"], 0),
            _q("1/2 + 1/4 =", ["2/6", "3/4", "1/8"], 1), _q("3/4 − 1/4 =", ["1/2", "2/4", "3/8"], 0),
            _q("2/3 × 3/4 =", ["1/2", "2/7", "5/12"], 0), _q("1/2 ÷ 1/4 =", ["1/8", "2", "4"], 1),
            _q("Which is greater?", ["3/8", "1/2", "2/5"], 1), _q("A common denominator for 1/3 and 1/4 is", ["7", "12", "9"], 1),
            _q("12/18 in simplest form is", ["2/3", "3/2", "6/9"], 0), _q("5/4 as a mixed number is", ["1 1/4", "4 1/5", "1 1/5"], 0),
            _q("3/5 of 20 is", ["8", "12", "15"], 1), _q("0.75 as a fraction is", ["1/4", "3/4", "7/5"], 1),
            _q("If numerator = denominator, the fraction equals", ["0", "1", "2"], 1), _q("2/9 + 4/9 =", ["6/9", "2/18", "8/9"], 0),
            _q("7/10 − 2/10 =", ["5/10", "9/10", "1/2"], 0), _q("The reciprocal of 3/5 is", ["3/5", "5/3", "2/5"], 1),
            _q("Which fraction is less than 1?", ["7/5", "9/8", "4/7"], 2), _q("4/6 simplifies to", ["2/3", "3/2", "1/3"], 0),
            _q("A fraction is in lowest terms when", ["numerator is even", "no common factor greater than 1 remains", "denominator is 10"], 1),
        ],
    },
    "geometry": {
        "summary": "Geometry connects angles, triangles, quadrilaterals, circles, perimeter and area through diagrams and formulas.",
        "sections": [
            ("1. Angle basics", "A right angle is 90°, a straight angle is 180°, and a full turn is 360°. Complementary angles total 90° and supplementary angles total 180°."),
            ("2. Triangles", "The three interior angles of a triangle total 180°. An isosceles triangle has two equal sides and equal opposite angles; an equilateral triangle has three equal sides and three 60° angles."),
            ("3. Quadrilaterals", "The interior angles of a quadrilateral total 360°. Rectangle area is length × breadth, while its perimeter is 2(l+b)."),
            ("4. Circles", "Radius is half the diameter. Circumference = 2πr and area = πr². Keep units consistent before substituting values."),
            ("5. Coordinate thinking", "Distance and shape relationships can be checked using horizontal and vertical changes. Sketching the figure first often prevents formula mistakes."),
            ("6. Worked example", "A triangle has angles 55° and 65°. The third angle is 180° − 55° − 65° = 60°."),
        ],
        "video": ["Reading geometric diagrams", "Angles and triangle rules", "Quadrilaterals and perimeter", "Circle measurements", "Worked problem and recap"],
        "practice": ["Find the third angle of a triangle with 55° and 65°.", "Find the area of an 8 × 5 rectangle.", "Find the perimeter of a 9 × 4 rectangle.", "Find circumference for r = 7 using π = 22/7.", "Find area for r = 7 using π = 22/7.", "Find the missing angle if two supplementary angles are 115° and x.", "What is each angle of an equilateral triangle?", "A square has side 6 cm. Find its area.", "A square has side 6 cm. Find its perimeter.", "State the sum of the interior angles of a quadrilateral."],
        "answers": ["60°", "40 square units", "26 units", "44 units", "154 square units", "65°", "60°", "36 cm²", "24 cm", "360°"],
        "quiz": [
            _q("Angles in a triangle total", ["90°", "180°", "360°"], 1), _q("A right angle measures", ["45°", "90°", "180°"], 1),
            _q("A straight angle measures", ["90°", "180°", "270°"], 1), _q("Complementary angles total", ["90°", "180°", "360°"], 0),
            _q("Supplementary angles total", ["90°", "180°", "270°"], 1), _q("Each angle of an equilateral triangle is", ["45°", "60°", "90°"], 1),
            _q("Interior angles of a quadrilateral total", ["180°", "270°", "360°"], 2), _q("Area of a rectangle is", ["l+b", "2(l+b)", "l×b"], 2),
            _q("Perimeter of a rectangle is", ["l×b", "2(l+b)", "πr²"], 1), _q("Circumference of a circle is", ["2πr", "πr²", "πd²"], 0),
            _q("Area of a circle is", ["2πr", "πr²", "r²/π"], 1), _q("Radius is", ["twice the diameter", "half the diameter", "equal to circumference"], 1),
            _q("A square with side 6 has area", ["12", "24", "36"], 2), _q("A 8×5 rectangle has area", ["13", "40", "26"], 1),
            _q("A 9×4 rectangle has perimeter", ["13", "26", "36"], 1), _q("If two angles are supplementary and one is 115°, the other is", ["65°", "75°", "55°"], 0),
            _q("If two angles are complementary and one is 35°, the other is", ["55°", "65°", "145°"], 0), _q("A full turn is", ["180°", "270°", "360°"], 2),
            _q("The diameter of a circle with radius 7 is", ["3.5", "7", "14"], 2), _q("An isosceles triangle has", ["two equal sides", "three unequal sides", "four sides"], 0),
        ],
    },
    "algebra": {
        "summary": "Algebra uses variables and expressions to represent relationships. The lesson covers like terms, equations, expansion and substitution.",
        "sections": [
            ("1. Variables and constants", "A variable represents an unknown or changing value. A constant has a fixed value. In 5x + 3, x is the variable and 3 is the constant."),
            ("2. Like terms", "Only terms with the same variable part can be combined. 4x + 3x = 7x, but 4x + 3y cannot be simplified into one term."),
            ("3. Solving equations", "Keep both sides balanced. Use inverse operations in reverse order to isolate the variable."),
            ("4. Expansion", "Use the distributive property: a(b+c) = ab + ac. Apply it to every term inside the bracket."),
            ("5. Substitution", "Replace a variable with its known value, then simplify carefully using the correct order of operations."),
            ("6. Worked example", "For 3x + 5 = 20, subtract 5 from both sides to get 3x = 15, then divide by 3: x = 5."),
        ],
        "video": ["Variables and expressions", "Combining like terms", "Solving equations", "Expansion and substitution", "Worked equation"],
        "practice": ["Solve 3x + 5 = 20.", "Simplify 4a + 3a − 2.", "Expand 2(x + 4).", "Solve 5y − 7 = 18.", "Simplify 3p + 2p + 4.", "Find 2x + 3 when x = 4.", "Expand 3(a − 2).", "Solve x/4 = 6.", "Solve 2x − 9 = 13.", "Simplify 7m − 2m + 5."],
        "answers": ["x = 5", "7a − 2", "2x + 8", "y = 5", "5p + 4", "11", "3a − 6", "x = 24", "x = 11", "5m + 5"],
        "quiz": [
            _q("Solve 3x + 5 = 20", ["x=3", "x=5", "x=15"], 1), _q("4a + 3a simplifies to", ["7a", "12a", "a"], 0),
            _q("2(x+4) equals", ["2x+4", "2x+8", "x+8"], 1), _q("A variable is", ["always 0", "an unknown or changing quantity", "a unit"], 1),
            _q("A constant is", ["a fixed value", "always x", "a fraction only"], 0), _q("Like terms have", ["the same variable part", "different variables", "no coefficients"], 0),
            _q("5y−7=18 gives", ["y=5", "y=11", "y=25"], 0), _q("x/4=6 gives", ["x=10", "x=20", "x=24"], 2),
            _q("2x−9=13 gives", ["x=2", "x=11", "x=22"], 1), _q("3(a−2) expands to", ["3a−2", "3a−6", "a−6"], 1),
            _q("If x=4, 2x+3 is", ["8", "11", "12"], 1), _q("7m−2m+5 is", ["5m+5", "9m", "5m−5"], 0),
            _q("The inverse of addition is", ["multiplication", "subtraction", "division"], 1), _q("The inverse of multiplication is", ["division", "addition", "subtraction"], 0),
            _q("3x+2x+4 combines to", ["5x+4", "6x+4", "5x+2"], 0), _q("If x=0, 7x+2 is", ["0", "2", "7"], 1),
            _q("4(x+2) expands to", ["4x+2", "4x+8", "x+8"], 1), _q("x+6=10 gives", ["x=4", "x=6", "x=16"], 0),
            _q("2x=18 gives", ["x=8", "x=9", "x=36"], 1), _q("Substitution means", ["replacing a variable with a value", "removing all variables", "adding variables"], 0),
        ],
    },
    "photosynthesis": {
        "summary": "Photosynthesis explains how green plants use light energy to make glucose from carbon dioxide and water, releasing oxygen.",
        "sections": [
            ("1. What is photosynthesis?", "It is the process by which green plants capture light energy and use it to make glucose from carbon dioxide and water."),
            ("2. Chlorophyll", "Chlorophyll is the green pigment that absorbs light energy. It is found in chloroplasts in plant cells."),
            ("3. Raw materials", "Carbon dioxide enters mainly through stomata. Water is absorbed by roots and transported to leaves through xylem."),
            ("4. Products", "Glucose is produced and can be used for respiration or stored as starch. Oxygen is released as a by-product."),
            ("5. Factors", "Light intensity, carbon dioxide concentration and temperature can affect the rate of photosynthesis within suitable ranges."),
            ("6. Equation", "A simplified word equation is: carbon dioxide + water —light/chlorophyll→ glucose + oxygen."),
        ],
        "video": ["Where photosynthesis happens", "Light and chlorophyll", "Carbon dioxide and water", "Glucose and oxygen", "Factors and recap"],
        "practice": ["Name the pigment that captures light.", "Which gas is used as a raw material?", "Where does most gas exchange occur in leaves?", "Which tissue carries water upward?", "What carbohydrate is first produced?", "What gas is released?", "Where are chloroplasts found?", "Name one factor affecting rate.", "Why is light needed?", "Write the word equation."],
        "answers": ["Chlorophyll", "Carbon dioxide", "Stomata", "Xylem", "Glucose", "Oxygen", "Plant cells", "Light intensity", "It supplies energy", "Carbon dioxide + water → glucose + oxygen"],
        "quiz": [
            _q("Which pigment captures light?", ["Chlorophyll", "Haemoglobin", "Keratin"], 0), _q("Main gas raw material is", ["Oxygen", "Carbon dioxide", "Nitrogen"], 1),
            _q("Water is mainly transported by", ["Xylem", "Phloem", "Stomata"], 0), _q("Gas exchange mainly occurs through", ["Roots", "Stomata", "Seeds"], 1),
            _q("Main carbohydrate produced is", ["Glucose", "Protein", "Fat"], 0), _q("Gas released is", ["Nitrogen", "Oxygen", "Carbon dioxide"], 1),
            _q("Photosynthesis needs", ["Light energy", "Darkness only", "No water"], 0), _q("Chlorophyll is found in", ["Chloroplasts", "Ribosomes", "Nuclei only"], 0),
            _q("Stomata are usually found on", ["Leaves", "Roots only", "Seeds only"], 0), _q("Xylem transports", ["Water and minerals", "Glucose only", "Oxygen only"], 0),
            _q("Phloem mainly transports", ["Sugars/food", "Water only", "Light"], 0), _q("A product of photosynthesis is", ["Glucose", "Urea", "Lactic acid"], 0),
            _q("Increasing suitable light intensity can", ["increase photosynthesis", "always stop it", "remove chlorophyll"], 0), _q("Carbon dioxide enters leaves mainly through", ["Stomata", "Xylem", "Roots"], 0),
            _q("Green leaves appear green mainly because chlorophyll", ["reflects green light", "absorbs all green light", "contains no pigment"], 0), _q("Photosynthesis converts light energy into", ["chemical energy in food", "sound", "mechanical energy only"], 0),
            _q("Stored glucose is commonly converted to", ["Starch", "Salt", "Water"], 0), _q("A suitable temperature is important because", ["enzymes control reactions", "plants need no enzymes", "temperature never matters"], 0),
            _q("The word equation includes", ["carbon dioxide + water", "oxygen + glucose only", "nitrogen + protein"], 0), _q("Photosynthesis occurs mainly in", ["green plant tissues", "red blood cells", "bones"], 0),
        ],
    },
    "grammar": {
        "summary": "Grammar helps you build clear sentences using correct agreement, parts of speech, punctuation and tense.",
        "sections": [
            ("1. Sentence structure", "A complete sentence normally has a subject and a predicate and expresses a complete thought."),
            ("2. Subject–verb agreement", "A singular subject generally takes a singular verb in the present tense: She goes. A plural subject takes the plural form: They go."),
            ("3. Parts of speech", "Nouns name, verbs show action/state, adjectives describe nouns, and adverbs commonly describe verbs, adjectives or other adverbs."),
            ("4. Tense", "Verb tense shows time. Keep the tense consistent unless there is a clear reason to shift time."),
            ("5. Punctuation", "Full stops, commas, question marks and apostrophes help readers understand sentence structure and meaning."),
            ("6. Editing method", "Read the sentence, identify the subject and verb, check tense, then check punctuation and word choice."),
        ],
        "video": ["Building complete sentences", "Subject–verb agreement", "Parts of speech", "Tense and punctuation", "Editing a sentence"],
        "practice": ["Correct: She go to school every day.", "Identify the verb: The students solved the problem.", "Choose: He is / are ready.", "Change to past tense: They play football.", "Add punctuation: Where are you going", "Identify the adjective: The bright lamp shone.", "Choose: The boys runs / run fast.", "Identify the noun: Riya opened the book.", "Change to future: I study tonight.", "Correct: Me and him went home."],
        "answers": ["She goes to school every day.", "solved", "He is ready.", "They played football.", "Where are you going?", "bright", "run", "Riya/book", "I will study tonight.", "He and I went home."],
        "quiz": [
            _q("Choose the correct sentence", ["She goes to school.", "She go to school.", "She going school."], 0), _q("The verb in 'Students solved' is", ["Students", "solved", "the"], 1),
            _q("He ___ ready", ["is", "are", "am"], 0), _q("They ___ football every day", ["plays", "play", "playing"], 1),
            _q("Past tense of 'go' is", ["goed", "went", "gone"], 1), _q("An adjective describes mainly a", ["noun", "verb only", "punctuation mark"], 0),
            _q("An adverb commonly modifies a", ["verb", "full stop", "article only"], 0), _q("A question normally ends with", [".", "?", ","], 1),
            _q("A full stop is used to", ["end a statement", "join every word", "show a question"], 0), _q("Choose the plural verb", ["runs", "run", "running"], 1),
            _q("The noun in 'The dog barked' is", ["dog", "barked", "the"], 0), _q("Future form of 'I study' can be", ["I studied", "I will study", "I studies"], 1),
            _q("Which is correct?", ["He and I went.", "Me and him went.", "Him and me goes."], 0), _q("A comma can", ["separate parts of a sentence", "replace every verb", "end every question"], 0),
            _q("Past tense of 'play' is", ["played", "plays", "playing"], 0), _q("In 'bright lamp', bright is", ["adjective", "verb", "noun"], 0),
            _q("In 'quickly ran', quickly is", ["adverb", "noun", "pronoun"], 0), _q("Subject–verb agreement means", ["subject and verb match in number", "every verb is plural", "every noun is singular"], 0),
            _q("Which needs a question mark?", ["Where are you?", "I am ready.", "She reads."], 0),
        ],
    },
    "electricity": {
        "summary": "Electricity links charge flow, potential difference and resistance. This resource combines formulas, circuit reasoning and numerical practice.",
        "sections": [
            ("1. Current", "Electric current is the rate of flow of electric charge. The SI unit is ampere (A)."),
            ("2. Potential difference", "Potential difference is energy transferred per unit charge. Its SI unit is volt (V)."),
            ("3. Resistance", "Resistance opposes current. Its SI unit is ohm (Ω). For an ohmic conductor under suitable constant conditions, V = IR."),
            ("4. Series circuits", "In a series circuit, the same current passes through components, while the total resistance is the sum of individual resistances."),
            ("5. Parallel circuits", "In parallel, branches share the same potential difference while current divides among branches."),
            ("6. Worked example", "If I = 2 A and R = 5 Ω, Ohm's law gives V = IR = 10 V."),
        ],
        "video": ["Current and charge", "Voltage and resistance", "Ohm's law", "Series and parallel", "Worked numerical"],
        "practice": ["Find V when I=2 A and R=5 Ω.", "Find I when V=12 V and R=4 Ω.", "Find R when V=20 V and I=2 A.", "What is the SI unit of current?", "What is the SI unit of resistance?", "What is the SI unit of potential difference?", "State Ohm's law.", "What happens to current at a junction?", "What is the series resistance of 2 Ω and 3 Ω?", "Why are household appliances connected in parallel?"],
        "answers": ["10 V", "3 A", "10 Ω", "Ampere", "Ohm", "Volt", "V = IR", "It divides among branches according to the circuit", "5 Ω", "Each appliance gets the supply voltage independently"],
        "quiz": [
            _q("SI unit of current", ["Ampere", "Volt", "Ohm"], 0), _q("SI unit of resistance", ["Volt", "Ohm", "Ampere"], 1),
            _q("SI unit of potential difference", ["Ohm", "Volt", "Watt"], 1), _q("Ohm's law is", ["V=IR", "P=VI only", "Q=It only"], 0),
            _q("If I=2 A and R=5 Ω, V=", ["10 V", "2.5 V", "7 V"], 0), _q("If V=12 V and R=4 Ω, I=", ["3 A", "8 A", "48 A"], 0),
            _q("If V=20 V and I=2 A, R=", ["10 Ω", "40 Ω", "18 Ω"], 0), _q("In series, current is", ["same through components", "always zero", "different in every component"], 0),
            _q("In parallel, voltage across branches is", ["the same", "always zero", "always doubled"], 0), _q("Series resistances 2 Ω and 3 Ω total", ["1 Ω", "5 Ω", "6 Ω"], 1),
            _q("Current is rate of flow of", ["charge", "mass", "light"], 0), _q("Potential difference is energy per unit", ["charge", "mass", "time"], 0),
            _q("Resistance opposes", ["current", "mass", "temperature only"], 0), _q("A voltmeter is connected", ["in parallel", "in series only", "nowhere"], 0),
            _q("An ammeter is connected", ["in series", "in parallel only", "across a resistor only"], 0), _q("Household appliances are generally connected in", ["parallel", "series only", "one single loop"], 0),
            _q("Power can be calculated using", ["P=VI", "V=IR only", "R=V/I only"], 0), _q("If resistance increases at constant V, current", ["decreases", "increases", "stays necessarily identical"], 0),
            _q("If current increases at constant R, voltage", ["increases", "decreases", "becomes zero"], 0),
        ],
    },
    "thermodynamics": {
        "summary": "Thermodynamics studies heat, work, temperature and internal energy. The resource connects the first law with common thermodynamic processes and numerical reasoning.",
        "sections": [
            ("1. System and surroundings", "A thermodynamic system is the part being studied. Everything outside it is the surroundings. Energy can cross the boundary as heat or work depending on the system."),
            ("2. Temperature and heat", "Temperature describes the thermal state of a system. Heat is energy transferred because of a temperature difference; it is not the same thing as temperature."),
            ("3. Internal energy", "Internal energy is the microscopic energy associated with the particles of a system. A change in internal energy depends on the energy transferred to or from the system."),
            ("4. First law", "Using the convention that W is work done by the system, the first law is ΔQ = ΔU + ΔW. It expresses conservation of energy."),
            ("5. Processes", "Isothermal means constant temperature, isobaric means constant pressure, isochoric means constant volume, and adiabatic means no heat transfer into or out of the system."),
            ("6. Work and graphs", "For a quasistatic process, work can be represented by the area under a P–V curve. Expansion generally corresponds to positive work done by the system under the stated convention."),
            ("7. Worked example", "If 500 J of heat enters a system and the system does 200 J of work, then ΔU = 500 − 200 = 300 J using ΔQ = ΔU + ΔW."),
        ],
        "video": ["System, surroundings and heat", "Internal energy", "First law of thermodynamics", "Four common processes", "P–V work and worked example"],
        "practice": ["State the first law using W as work done by the system.", "What remains constant in an isothermal process?", "Name the constant-volume process.", "Name the constant-pressure process.", "What is true of heat transfer in an adiabatic process?", "If Q=500 J and W=200 J, find ΔU.", "What does the area under a P–V curve represent?", "Differentiate heat and temperature.", "What is internal energy?", "A gas expands while doing 150 J work and receives 400 J heat. Find ΔU."],
        "answers": ["ΔQ = ΔU + ΔW", "Temperature", "Isochoric", "Isobaric", "No heat transfer", "300 J", "Work done", "Heat is energy transfer; temperature measures thermal state", "Microscopic energy of the system", "250 J"],
        "quiz": [
            _q("The first law expresses conservation of", ["Energy", "Charge", "Mass only"], 0), _q("With W as work done by system, first law is", ["ΔQ=ΔU+ΔW", "ΔQ=ΔU−ΔW always", "ΔU=0 always"], 0),
            _q("Isothermal means constant", ["Temperature", "Pressure", "Volume"], 0), _q("Isobaric means constant", ["Temperature", "Pressure", "Volume"], 1),
            _q("Isochoric means constant", ["Temperature", "Pressure", "Volume"], 2), _q("Adiabatic means", ["no heat transfer", "constant temperature", "constant pressure"], 0),
            _q("Heat is", ["energy transferred due to temperature difference", "the same as temperature", "a substance"], 0), _q("Temperature describes", ["thermal state", "only volume", "only mass"], 0),
            _q("If Q=500 J and W=200 J, ΔU=", ["300 J", "700 J", "200 J"], 0), _q("If Q=400 J and W=150 J, ΔU=", ["250 J", "550 J", "150 J"], 0),
            _q("The area under a P–V curve represents", ["work", "temperature directly", "mass"], 0), _q("Internal energy is associated with", ["microscopic energy", "only gravitational energy", "only external work"], 0),
            _q("A constant-volume process is", ["isochoric", "isothermal", "isobaric"], 0), _q("A constant-pressure process is", ["isobaric", "adiabatic", "isochoric"], 0),
            _q("An isothermal process keeps", ["T constant", "P constant", "V constant"], 0), _q("In an adiabatic process, Q is", ["0", "always 100 J", "always equal to W"], 0),
            _q("If a system receives heat, Q is positive under the common convention", ["True", "False", "Only at 0°C"], 0), _q("If system does work while receiving heat, some heat can", ["increase internal energy and some can become work", "vanish", "turn into mass automatically"], 0),
            _q("Thermodynamics studies relationships among", ["heat, work, temperature and energy", "only speed", "only electricity"], 0),
        ],
    },
}



RESOURCE_ENHANCEMENTS = {'fractions': {'revision': ['Numerator = selected parts; denominator = equal parts in the whole.', 'Equivalent fractions come from multiplying/dividing numerator and denominator by the same non-zero number.', 'Add/subtract by using a common denominator; multiply straight across; divide by multiplying by the reciprocal.', 'Always simplify the final fraction and check whether a mixed number is required.'], 'formulae': ['a/b means a divided by b (b != 0)', 'a/b + c/d = (ad + bc)/bd', 'a/b x c/d = ac/bd', 'a/b ÷ c/d = a/b x d/c'], 'tips': ['Find the LCM before adding unlike fractions.', 'Do not add denominators directly.', 'Simplify using the greatest common factor.', 'Estimate the answer to catch impossible results.'], 'slides': [('1. What a fraction means', ['A fraction represents equal parts of a whole.', 'Numerator: how many parts are selected.', 'Denominator: how many equal parts make the whole.', 'Example: 3/5 means 3 of 5 equal parts.']), ('2. Equivalent fractions', ['Multiply or divide BOTH numerator and denominator by the same non-zero number.', '2/3 = 4/6 = 6/9.', 'Equivalent fractions have the same value.', 'Simplify when possible.']), ('3. Add and subtract', ['Same denominator: operate on numerators.', 'Different denominators: find a common denominator first.', 'Example: 1/4 + 2/3 = 3/12 + 8/12 = 11/12.', 'Never add denominators directly.']), ('4. Multiply and divide', ['Multiplication: multiply numerators and denominators.', 'Division: multiply by the reciprocal of the second fraction.', 'Simplify before or after calculation.', 'Check the size of the result.']), ('5. Compare fractions', ['Same denominator: larger numerator means larger fraction.', 'Different denominators: use a common denominator or cross multiplication.', 'Example: 5/8 < 2/3.', 'A fraction greater than 1 has numerator > denominator.']), ('6. Quick revision', ['Numerator = selected parts; denominator = total equal parts.', 'LCM helps with unlike denominators.', 'Multiply straight across; divide using reciprocal.', 'Final step: simplify and check.'])]}, 'geometry': {'revision': ['Triangle angle sum = 180 degrees.', 'Quadrilateral interior angle sum = 360 degrees.', 'Rectangle: area = l x b; perimeter = 2(l+b).', 'Circle: diameter = 2r; circumference = 2 pi r; area = pi r^2.'], 'formulae': ['Triangle angles = 180 degrees', 'Quadrilateral angles = 360 degrees', 'Rectangle A = l x b, P = 2(l+b)', 'Circle C = 2 pi r, A = pi r^2'], 'tips': ['Draw and label the figure before calculating.', 'Keep units consistent.', 'Choose the formula from the quantity asked.', 'Check whether the answer should be a length or an area.'], 'slides': [('1. Read the diagram', ['Mark known lengths and angles first.', 'A right angle is 90 degrees; a straight angle is 180 degrees.', 'A full turn is 360 degrees.', 'Complementary = 90 degrees; supplementary = 180 degrees.']), ('2. Triangles', ['The three interior angles total 180 degrees.', 'Isosceles: two equal sides and equal opposite angles.', 'Equilateral: three equal sides and each angle is 60 degrees.', 'Missing angle = 180 - the other two angles.']), ('3. Quadrilaterals', ['The interior angles of a quadrilateral total 360 degrees.', 'Rectangle area = length x breadth.', 'Rectangle perimeter = 2(length + breadth).', 'Square area = side^2; perimeter = 4 x side.']), ('4. Circles', ['Radius is half the diameter.', 'Circumference = 2 pi r.', 'Area = pi r^2.', 'Use the value of pi specified in the question.']), ('5. Worked example', ['Triangle angles: 55 degrees, 65 degrees, x.', 'Use the triangle sum: 55 + 65 + x = 180.', 'So x = 60 degrees.', 'Write the rule before substitution in exams.']), ('6. Quick revision', ['Triangle: 180 degrees. Quadrilateral: 360 degrees.', 'Rectangle: A = l x b; P = 2(l+b).', 'Circle: C = 2 pi r; A = pi r^2.', 'Sketch -> rule -> substitution -> unit check.'])]}, 'algebra': {'revision': ['Variable = unknown/changing quantity; constant = fixed value.', 'Only like terms can be combined.', 'Use inverse operations to isolate a variable while keeping both sides balanced.', 'Substitute values only after identifying the expression correctly.'], 'formulae': ['a(b+c) = ab + ac', 'a(b-c) = ab - ac', 'If ax=b, then x=b/a (a != 0)', 'Order: brackets -> powers -> multiplication/division -> addition/subtraction'], 'tips': ['Write one algebraic step per line.', 'Do the same operation to both sides of an equation.', 'Check a solution by substituting it back.', 'Watch signs when expanding brackets.'], 'slides': [('1. Variables and terms', ['A variable represents an unknown or changing value.', 'A constant has a fixed value.', 'Coefficient is the numerical factor multiplying a variable.', 'In 5x + 3, 5 is the coefficient, x the variable, 3 the constant.']), ('2. Like terms', ['Like terms have the same variable part and powers.', '4x + 3x = 7x.', '4x + 3y cannot be combined into one term.', 'Combine coefficients, not different variable parts.']), ('3. Solve equations', ['Keep both sides balanced.', 'Use inverse operations in reverse order.', 'Example: 3x + 5 = 20.', 'Subtract 5, then divide by 3: x = 5.']), ('4. Expand brackets', ['Use the distributive property.', '2(x + 4) = 2x + 8.', 'Multiply the outside factor by EVERY term inside.', 'Be careful with negative signs.']), ('5. Substitution', ['Replace a variable with its known value.', 'Use brackets when substituting a negative value.', 'Then follow the correct order of operations.', 'Check whether the final answer has the required units or form.']), ('6. Quick revision', ['Like terms only.', 'Same operation on both sides of an equation.', 'Distribute to every bracket term.', 'Always substitute the answer back to verify.'])]}, 'photosynthesis': {'revision': ['Photosynthesis uses light energy to form glucose from carbon dioxide and water.', 'Chlorophyll in chloroplasts absorbs light energy.', 'Carbon dioxide enters mainly through stomata; water reaches leaves through xylem.', 'Glucose can be used in respiration or converted to stored starch; oxygen is released.'], 'formulae': ['Word equation: carbon dioxide + water -> glucose + oxygen', 'Light and chlorophyll provide the conditions/energy for the process', 'Factors: light intensity, CO2 concentration and temperature'], 'tips': ['Learn the word equation and role of each input/output.', 'Separate raw materials from products.', 'Remember xylem carries water; phloem transports sugars.', 'Rate changes depend on the limiting factor and suitable conditions.'], 'slides': [('1. What is photosynthesis?', ['Green plants capture light energy.', 'They use carbon dioxide and water to make glucose.', 'Oxygen is released as a product of the process.', 'The process mainly occurs in green plant tissues.']), ('2. Chlorophyll and chloroplasts', ['Chlorophyll is the green pigment that absorbs light energy.', 'Chlorophyll is located in chloroplasts.', 'Light energy is converted into chemical energy stored in food.', 'Green leaves appear green because green light is reflected more than absorbed.']), ('3. Raw materials', ['Carbon dioxide enters leaves mainly through stomata.', 'Water is absorbed by roots.', 'Xylem transports water and minerals to the leaves.', 'Both raw materials are needed for normal photosynthesis.']), ('4. Products and uses', ['Glucose is produced by photosynthesis.', 'It can be used in respiration to release energy.', 'It can be converted to starch for storage.', 'Oxygen is released during the process.']), ('5. Factors affecting rate', ['Light intensity can affect the rate when light is limiting.', 'Carbon dioxide concentration can affect the rate when CO2 is limiting.', 'Temperature affects enzyme-controlled reactions within suitable ranges.', 'A different factor may become limiting as conditions change.']), ('6. Quick revision', ['Inputs: carbon dioxide + water + light energy.', 'Chlorophyll captures light energy.', 'Main food product: glucose; released gas: oxygen.', 'Remember: xylem -> water; phloem -> sugars.'])]}, 'grammar': {'revision': ['A sentence should express a complete thought and normally has a subject and predicate.', 'Subject and verb should agree in number.', 'Tense should remain consistent unless there is a reason to shift time.', 'Punctuation clarifies structure and meaning.'], 'formulae': ['Singular present: He/She/It + verb-s in many regular forms', 'Plural present: They/We/You + base verb', 'Past simple: regular verbs often use -ed; irregular verbs must be learned', 'Question -> ? ; statement -> .'], 'tips': ['Find the subject before choosing the verb.', 'Read the full sentence, not just the blank.', 'Check tense clues such as yesterday, now, tomorrow.', 'Use punctuation to show sentence boundaries and pauses.'], 'slides': [('1. Sentence structure', ['A complete sentence expresses a complete thought.', 'The subject tells who/what the sentence is about.', 'The predicate tells what the subject does or is.', 'Avoid fragments that lack a complete thought.']), ('2. Subject-verb agreement', ['Singular subject: She goes to school.', 'Plural subject: They go to school.', 'Do not let nearby words distract you from the true subject.', 'Check the subject first, then choose the verb.']), ('3. Parts of speech', ['Noun: names a person, place, thing or idea.', 'Verb: shows action or state.', 'Adjective: describes a noun.', 'Adverb: commonly modifies a verb, adjective or another adverb.']), ('4. Tense', ['Present: I study. Past: I studied. Future: I will study.', 'Use time clues to identify the intended tense.', 'Keep the tense consistent within a sentence or paragraph unless meaning requires a change.', 'Irregular verbs may change form completely, such as go -> went.']), ('5. Punctuation', ['Full stop ends a statement.', 'Question mark ends a direct question.', 'Comma separates or groups parts of a sentence.', 'Apostrophe can show possession or contractions.']), ('6. Quick revision', ['Subject -> find the verb -> check agreement.', 'Find time clue -> choose tense -> keep it consistent.', 'Check noun/adjective/verb/adverb roles.', 'Read once for meaning and once for grammar.'])]}, 'electricity': {'revision': ['Current is rate of flow of charge; unit ampere (A).', 'Potential difference is energy transferred per unit charge; unit volt (V).', 'Resistance opposes current; unit ohm (ohm).', 'Ohm law under suitable conditions: V = IR.'], 'formulae': ['I = Q/t', 'V = W/Q', 'V = IR', 'Series: R_total = R1 + R2 + ...'], 'tips': ['Write known values and the required quantity before using a formula.', 'Convert units before substitution.', 'Ammeter is connected in series; voltmeter in parallel.', 'In parallel branches, potential difference is the same.'], 'slides': [('1. Electric current', ['Current is the rate of flow of electric charge.', 'SI unit: ampere (A).', 'I = Q/t.', 'A larger current means more charge passes a point per unit time.']), ('2. Potential difference', ['Potential difference is energy transferred per unit charge.', 'SI unit: volt (V).', 'V = W/Q.', 'It provides the driving difference that can move charge in a circuit.']), ('3. Resistance and Ohm law', ['Resistance opposes current; SI unit is ohm (ohm).', 'For an ohmic conductor under suitable constant conditions: V = IR.', 'Rearrange as I = V/R or R = V/I.', 'Example: I = 2 A, R = 5 ohm -> V = 10 V.']), ('4. Series circuits', ['The same current passes through series components.', 'Total resistance is the sum of individual resistances.', 'R_total = R1 + R2 + ...', 'Adding series resistance increases total opposition to current.']), ('5. Parallel circuits', ['Branches have the same potential difference.', 'Current divides between branches.', 'Household appliances are generally connected in parallel.', 'This allows appliances to operate independently at the supply voltage.']), ('6. Quick revision', ['I = Q/t; V = W/Q; V = IR.', 'Ammeter -> series. Voltmeter -> parallel.', 'Series: same current, resistances add.', 'Parallel: same voltage across branches, current divides.'])]}, 'thermodynamics': {'revision': ['A system is the part being studied; surroundings are everything outside it.', 'Heat is energy transferred because of a temperature difference; temperature describes thermal state.', 'First law with W as work done by the system: Q = Delta U + W.', 'Isothermal: constant T; isobaric: constant P; isochoric: constant V; adiabatic: Q = 0.'], 'formulae': ['Q = Delta U + W (W = work done by system)', 'For constant pressure, mechanical work is related to pressure and volume change', 'P-V area represents work for a quasistatic path', 'Adiabatic: Q = 0'], 'tips': ['State the sign convention before solving.', 'Separate heat Q, internal energy change Delta U and work W.', 'Identify which thermodynamic process is described.', 'Check units: joule for energy/work/heat, kelvin for absolute temperature.'], 'slides': [('1. System, surroundings, boundary', ['System = the part chosen for study.', 'Surroundings = everything outside the system.', 'Energy can cross the boundary as heat or work.', 'Always identify the system before applying a law.']), ('2. Heat, temperature, internal energy', ['Heat is energy transferred because of a temperature difference.', 'Temperature describes the thermal state of a system.', 'Internal energy is microscopic energy stored in the system.', 'Heat and temperature are not interchangeable terms.']), ('3. First law', ['Using W as work done by the system: Q = Delta U + W.', 'This is an energy-conservation statement.', 'If Q = 500 J and W = 200 J, Delta U = 300 J.', 'Keep the sign convention consistent throughout.']), ('4. Common processes', ['Isothermal: temperature constant.', 'Isobaric: pressure constant.', 'Isochoric: volume constant.', 'Adiabatic: no heat transfer, so Q = 0.']), ('5. P-V work', ['For a quasistatic process, work can be represented by area under a P-V curve.', 'Expansion means the system volume increases.', 'Compression means volume decreases.', 'Use the graph and sign convention together; do not guess the sign.']), ('6. Quick revision', ['System vs surroundings first.', 'Heat = energy transfer; temperature = thermal state.', 'First law: Q = Delta U + W.', 'Remember T/P/V/Q conditions for the four common processes.'])]}}


def _generic_resource(topic, subject):
    """Safe fallback for topics not yet present in the curated knowledge packs.
    It provides a useful study structure without inventing subject facts or asking the learner to write the notes.
    """
    return {
        "summary": f"A structured revision guide for {topic} in {subject}. Topic-specific facts are only shown when a verified content pack is available.",
        "sections": [
            ("1. Topic overview", f"{topic} is the topic selected for this resource. Start by identifying its main concept, the type of problems it is used to solve, and the vocabulary that appears repeatedly in the chapter."),
            ("2. Key terminology", f"Focus on the terminology used with {topic}. A good revision pass should distinguish definitions, symbols, quantities, conditions and examples rather than treating every word as interchangeable."),
            ("3. Problem-solving method", f"For a {topic} question, identify what is given, what is required, which rule or relationship applies, and what units or conditions must be respected. Then work step by step and check the result."),
            ("4. Worked-example structure", f"A strong {topic} solution should show the known information, the selected principle or formula, substitution or reasoning, the final result and a short check. This makes the method easier to reproduce in an exam."),
            ("5. Common error checks", "Check signs, units, definitions, copied values, algebraic steps and whether the final answer actually answers the question. Do not assume a numerical result is correct just because the arithmetic is complete."),
            ("6. Revision checklist", f"Before leaving {topic}, make sure you can explain the central idea, recognize the important terms, identify the correct method, follow a worked example and solve a fresh question without copying a pattern."),
        ],
        "revision": [
            f"Central idea: identify what {topic} describes or helps you determine.",
            "Separate definitions, formulae, conditions and examples during revision.",
            "For numericals: known values -> required quantity -> rule -> substitution -> unit check.",
            "For theory: definition -> principle -> explanation -> example -> common mistake.",
        ],
        "formulae": ["Use only the formulae and conventions specified by the learner's textbook/syllabus for this topic."],
        "tips": ["Check the exact syllabus definition.", "Keep units and symbols consistent.", "Show reasoning instead of jumping to the answer.", "Re-check the final result before submitting."],
        "video": [f"Understanding {topic}", "Key terminology and ideas", "How to approach a question", "Worked-solution method", "Common error checks", "Quick revision"],
        "practice": [f"Identify the central concept of {topic}.", f"Classify three important terms used with {topic}.", f"Identify the given and required quantities in a typical {topic} question.", f"Choose the principle or formula needed for a standard {topic} problem.", f"List two common mistakes to check in {topic}.", f"Explain the solution method for one standard {topic} question.", f"State the units that must be checked in a numerical {topic} problem.", f"Summarize the method for answering a theory question on {topic}.", f"Check a completed {topic} solution for signs, units and reasoning.", f"Explain the difference between a definition, a formula and an example in {topic}."],
        "answers": ["Use the chapter's central definition.", "Use the terminology given in the chapter.", "Separate known data from the quantity being asked.", "Select the rule that matches the conditions in the question.", "Check definitions, signs, units and skipped steps.", "Show the principle, working and final check.", "Use the units required by the syllabus/question.", "Definition -> principle -> explanation -> example.", "Recalculate and verify the units and assumptions.", "Definition states meaning; formula expresses a relationship; example shows application."],
        "quiz": [
            _q(f"What should you identify first in a {topic} problem?", ["What is given and what is required", "The final answer only", "A random formula"], 0),
            _q(f"A reliable {topic} solution should", ["show the relevant reasoning", "skip all steps", "ignore units"], 0),
            _q(f"Before using a formula in {topic}, you should", ["check that its conditions apply", "always use the longest formula", "change all values randomly"], 0),
            _q(f"A final answer in {topic} should be checked for", ["units and consistency", "font size", "page colour"], 0),
            _q(f"When revising {topic}, definitions and examples should be", ["understood separately and then connected", "treated as identical", "ignored"], 0),
        ] * 4
    }



# Expanded revision notes: these packs are deliberately richer than the short
# resource summaries. Each supported topic exposes 20+ sections with explanations,
# examples, formulas/rules and exam-oriented checks. Unknown topics use the detailed
# fallback below instead of learner-directed "write your own answer" prompts.
DETAILED_NOTES = {
    "fractions": [
        ("1. Meaning of a fraction", "A fraction represents a quantity in equal parts. The denominator tells how many equal parts make one whole, while the numerator tells how many of those parts are being considered."),
        ("2. Numerator and denominator", "In a/b, a is the numerator and b is the denominator, with b not equal to zero. The denominator defines the size of each equal part, so changing it changes the fraction's value unless the numerator changes proportionally."),
        ("3. Proper fractions", "A proper fraction has a numerator smaller than its denominator, so its value lies between 0 and 1 for positive numbers. Examples include 2/5 and 7/10."),
        ("4. Improper fractions", "An improper fraction has a numerator greater than or equal to its denominator. It can represent a value of 1 or more and can often be converted into a mixed number."),
        ("5. Mixed numbers", "A mixed number contains a whole number and a proper fraction, such as 2 3/4. To convert it to an improper fraction, multiply the whole number by the denominator, add the numerator, and keep the denominator."),
        ("6. Equivalent fractions", "Equivalent fractions have the same numerical value even though their numerator and denominator may look different. Multiplying or dividing both parts by the same non-zero number preserves the value."),
        ("7. Simplest form", "A fraction is in simplest form when the numerator and denominator have no common factor greater than 1. Divide both by their greatest common factor to simplify efficiently."),
        ("8. Comparing fractions", "For equal denominators, compare numerators directly. For different denominators, use a common denominator or cross multiplication while keeping the comparison direction consistent."),
        ("9. Fractions on a number line", "A number line makes fraction size visible. Divide the interval from 0 to 1 into the denominator's number of equal parts and count the numerator's parts from zero."),
        ("10. Addition with like denominators", "When denominators are equal, add the numerators and keep the common denominator. Simplify the result if a common factor remains."),
        ("11. Addition with unlike denominators", "Find a common denominator, usually through the LCM, convert each fraction, and then add the numerators. Adding denominators directly is not a valid method."),
        ("12. Subtraction", "Subtraction follows the same denominator rule as addition. Convert unlike denominators first, subtract the numerators, and simplify the final fraction."),
        ("13. Multiplication", "Multiply numerator by numerator and denominator by denominator. Before multiplying, cancel common factors when possible to keep the arithmetic smaller and reduce errors."),
        ("14. Division", "To divide by a fraction, multiply by its reciprocal. For a/b divided by c/d, the result is a/b multiplied by d/c, provided c is not zero."),
        ("15. Reciprocal", "The reciprocal of a non-zero fraction a/b is b/a. A non-zero number multiplied by its reciprocal gives 1, which is why reciprocals are used in fraction division."),
        ("16. Fractions and decimals", "A fraction can be converted to a decimal by dividing numerator by denominator. A terminating decimal occurs when the simplified denominator has no prime factors other than 2 and 5."),
        ("17. Fractions and percentages", "A fraction can be converted to a percentage by multiplying by 100. For example, 3/5 represents 60 percent because 3/5 × 100 = 60."),
        ("18. Negative fractions", "A negative sign may be written before the fraction or with the numerator. When multiplying or dividing, use the usual sign rules and then simplify the magnitude."),
        ("19. Word problems", "Translate phrases such as 'of', 'remaining', 'difference' and 'shared equally' into the appropriate operations. Write the quantity as a fraction before calculating and check whether the answer is reasonable."),
        ("20. Worked example", "For 1/4 + 2/3, the LCM of 4 and 3 is 12. Convert the fractions to 3/12 and 8/12, giving 11/12 after addition."),
        ("21. Estimation and checking", "Estimate the size of each fraction before calculating. A result larger than expected can reveal an operation or simplification error immediately."),
        ("22. Common mistakes", "Do not add denominators, change only one part of a fraction, or forget to simplify. During division, do not take the reciprocal of both fractions; only the divisor is inverted."),
        ("23. Exam revision strategy", "Memorize the operation rules, then practise one example of each type: simplify, compare, add, subtract, multiply, divide and convert. Finish by solving a mixed question without looking at the method."),
    ],
    "geometry": [
        ("1. Geometry vocabulary", "Geometry studies shapes, sizes, positions and relationships. Learn the meanings of point, line, ray, segment, angle, vertex, side, perimeter, area and volume before using formulas."),
        ("2. Angle types", "An acute angle is less than 90 degrees, a right angle is 90 degrees, an obtuse angle is between 90 and 180 degrees, and a straight angle is 180 degrees."),
        ("3. Complementary and supplementary angles", "Complementary angles add to 90 degrees, while supplementary angles add to 180 degrees. These relationships are often used to find a missing angle quickly."),
        ("4. Vertically opposite angles", "When two straight lines intersect, vertically opposite angles are equal. Adjacent angles on a straight line add to 180 degrees."),
        ("5. Parallel lines and transversals", "When a transversal crosses parallel lines, corresponding and alternate interior angles have useful equality relationships, while co-interior angles are supplementary."),
        ("6. Triangle classification", "Triangles can be classified by sides as scalene, isosceles or equilateral, and by angles as acute, right or obtuse. Identify the classification before selecting a property."),
        ("7. Triangle angle sum", "The interior angles of every triangle add to 180 degrees. If two angles are known, subtract their sum from 180 degrees to obtain the third."),
        ("8. Isosceles and equilateral triangles", "An isosceles triangle has two equal sides and equal opposite angles. An equilateral triangle has three equal sides and each interior angle is 60 degrees."),
        ("9. Congruence", "Congruent figures have the same shape and size. Common triangle congruence criteria include SSS, SAS and ASA/AAS, depending on the syllabus and stated information."),
        ("10. Similarity", "Similar figures have the same shape but may have different sizes. Corresponding angles are equal and corresponding lengths are in the same ratio."),
        ("11. Pythagoras theorem", "For a right triangle, the square of the hypotenuse equals the sum of the squares of the other two sides: c² = a² + b². Identify the right angle before applying the theorem."),
        ("12. Quadrilaterals", "A quadrilateral has four sides and its interior angles total 360 degrees. Rectangle, square, parallelogram, rhombus and trapezium have additional properties that distinguish them."),
        ("13. Rectangle and square", "For a rectangle, area is length × breadth and perimeter is 2(length + breadth). For a square, area is side² and perimeter is 4 × side."),
        ("14. Parallelogram", "Opposite sides of a parallelogram are parallel and equal, and opposite angles are equal. Its area is base × perpendicular height, not base multiplied by a slanted side."),
        ("15. Triangle area", "The area of a triangle is one-half × base × perpendicular height. The height must be perpendicular to the chosen base, even if it lies outside the visible triangle in some configurations."),
        ("16. Circle vocabulary", "Radius joins the centre to the circle, while diameter passes through the centre and equals twice the radius. Chord, arc, sector and circumference are related terms worth distinguishing."),
        ("17. Circle circumference", "The circumference of a circle is 2πr or πd. Use the value of π specified by the question and keep the radius and diameter distinction clear."),
        ("18. Circle area", "The area of a circle is πr². Squaring the radius is essential; using πr gives a length rather than an area."),
        ("19. Coordinate geometry", "A coordinate is written as (x, y), where x describes horizontal position and y describes vertical position. Read the axes and signs carefully before plotting a point."),
        ("20. Distance and midpoint", "For two coordinate points, distance can be found using the Pythagorean relationship on horizontal and vertical differences. The midpoint is found by averaging the two x-coordinates and the two y-coordinates."),
        ("21. Perimeter versus area", "Perimeter measures the boundary length and uses square units only when an area is being measured. Area measures the surface enclosed by a shape and is expressed in square units."),
        ("22. Diagram-first method", "Mark all known lengths and angles, identify the shape, write the relevant property or formula, substitute values and then check the units. A labelled sketch reduces many geometry mistakes."),
        ("23. Common mistakes", "Do not confuse radius with diameter, sloping length with perpendicular height, or perimeter with area. Also avoid applying a theorem without checking its conditions."),
        ("24. Exam revision strategy", "Revise properties by shape, then formulas, then mixed diagram questions. For every numerical answer, include the rule, working and correct unit."),
    ],
    "algebra": [
        ("1. Algebraic language", "An algebraic expression combines numbers, variables and operations. A term is separated from another term by plus or minus signs, while a coefficient is the numerical factor of a variable."),
        ("2. Variables and constants", "A variable represents an unknown or changing quantity, while a constant has a fixed value. In 5x + 3, x is the variable, 5 is its coefficient and 3 is the constant."),
        ("3. Terms and coefficients", "Terms such as 4x, -3y and 7 are individual parts of an expression. The sign belongs to the term, so losing a negative sign can change the entire result."),
        ("4. Like terms", "Like terms have identical variable parts and powers. Only like terms can be combined by adding or subtracting their coefficients."),
        ("5. Simplifying expressions", "Collect like terms carefully and preserve unlike terms. For example, 4x + 3x - 2 becomes 7x - 2."),
        ("6. Order of operations", "Evaluate brackets first, then powers, then multiplication or division, and finally addition or subtraction. When operations have equal priority, work from left to right."),
        ("7. Distributive property", "The distributive property multiplies an outside factor by every term inside brackets: a(b+c) = ab+ac. With subtraction, a(b-c) = ab-ac."),
        ("8. Algebraic identities", "Identities are equations true for all permitted values. Common identities include (a+b)² = a²+2ab+b² and (a-b)² = a²-2ab+b²."),
        ("9. Factorisation", "Factorisation reverses expansion by expressing an expression as a product. First look for a common factor, then use an appropriate identity or method."),
        ("10. Linear equations", "A linear equation has the variable to the first power. Isolate the variable using inverse operations and perform the same operation on both sides."),
        ("11. Equation balance", "An equation states that two expressions are equal. Any operation performed on one side must also be performed on the other side to preserve equality."),
        ("12. Equations with brackets", "Expand brackets first when helpful, combine like terms, and then isolate the variable. Check the final value by substituting it into the original equation."),
        ("13. Equations with fractions", "Clear simple fractional denominators by multiplying both sides by a suitable common denominator, while applying the operation to every term."),
        ("14. Inequalities", "Inequalities use symbols such as <, >, ≤ and ≥. When multiplying or dividing both sides by a negative number, reverse the inequality sign."),
        ("15. Simultaneous equations", "Two equations can be solved together when they contain the same unknowns. Elimination removes one variable, while substitution replaces one variable using an expression from the other equation."),
        ("16. Quadratic equations", "A quadratic equation contains a squared variable. Depending on the form, it may be solved by factorisation, completing the square or the quadratic formula."),
        ("17. Graphs", "A graph shows how values change together. For a linear relation y = mx + c, m represents the gradient and c represents the y-intercept."),
        ("18. Substitution", "Substitution means replacing a variable with a known value. Use brackets when substituting a negative number so that signs are preserved correctly."),
        ("19. Algebraic fractions", "Algebraic fractions contain variables in numerators or denominators. State restrictions where a denominator could become zero, then simplify using valid factor cancellation."),
        ("20. Worked example", "For 3x + 5 = 20, subtract 5 from both sides to obtain 3x = 15, then divide by 3 to get x = 5. Substituting 5 back gives 20 on the left, confirming the solution."),
        ("21. Translating words into algebra", "Words such as 'sum', 'difference', 'product', 'twice' and 'less than' indicate mathematical operations. Translate the statement slowly before simplifying it."),
        ("22. Common sign errors", "A negative outside a bracket changes the signs of every term inside. Keep each algebraic step on a separate line when signs are easy to lose."),
        ("23. Exam checking", "Substitute numerical solutions back into the original equation rather than only checking the last line. For inequalities and graphs, also check direction and boundary conditions."),
        ("24. Revision strategy", "Revise expressions, identities, equations, inequalities and graphs separately, then mix them. The key skill is choosing the correct method from the structure of the question."),
    ],
    "photosynthesis": [
        ("1. Definition", "Photosynthesis is the process by which green plants use light energy to make organic food from carbon dioxide and water, with oxygen released as a product under typical textbook descriptions."),
        ("2. Overall equation", "The word equation is carbon dioxide + water → glucose + oxygen. Light energy and chlorophyll are essential parts of the process, and the balanced chemical equation depends on the level of study."),
        ("3. Chloroplast", "Photosynthesis mainly occurs in chloroplast-containing cells. Chloroplasts contain chlorophyll and internal membrane systems that support the light-dependent reactions."),
        ("4. Chlorophyll", "Chlorophyll is a pigment that absorbs light energy. It allows plants to capture energy that can ultimately be stored in chemical bonds during food formation."),
        ("5. Leaf as a photosynthetic organ", "Leaves are adapted for photosynthesis by providing a large surface area and internal tissues for gas exchange and transport. Their vascular system supplies water and distributes sugars."),
        ("6. Carbon dioxide entry", "Carbon dioxide enters leaves mainly through stomata, which are pores controlled by guard cells. Stomatal opening balances gas exchange with water loss."),
        ("7. Water supply", "Roots absorb water from the soil, and xylem transports water upward to the leaves. Water acts as a raw material for photosynthesis and is also important for maintaining plant tissues."),
        ("8. Light energy", "Light provides the energy needed to drive the photosynthetic reactions. Increasing light intensity can increase the rate when light is the limiting factor, but only within suitable conditions."),
        ("9. Light-dependent reactions", "Light-dependent reactions capture light energy and involve electron transfer and the formation of energy-rich molecules. Water is involved and oxygen is released from the splitting of water in the overall process."),
        ("10. Carbon fixation", "In the carbon-fixation stage, carbon dioxide is incorporated into organic molecules through enzyme-controlled reactions. In higher-level biology, this is associated with the Calvin cycle."),
        ("11. Glucose", "Glucose is an important product because it can be used in cellular respiration, converted to starch for storage, or used as a building block for other biological molecules."),
        ("12. Oxygen", "Oxygen is released during photosynthesis and can diffuse out of the leaf. It is not the food product of photosynthesis; glucose represents the main carbohydrate product in the simplified equation."),
        ("13. Stomata and gas exchange", "Stomata provide a pathway for carbon dioxide entry and oxygen movement. Guard cells regulate the pore size in response to environmental conditions."),
        ("14. Limiting factors", "A limiting factor is a condition that restricts the rate when other requirements are available in excess. Light intensity, carbon dioxide concentration and temperature are common factors studied in school biology."),
        ("15. Effect of light intensity", "At low light intensity, increasing light generally increases the rate because more energy is available. Eventually another factor becomes limiting, so the rate no longer rises proportionally."),
        ("16. Effect of carbon dioxide", "Increasing carbon dioxide can increase the rate when carbon dioxide is limiting. Beyond a certain point, another factor limits the process and additional carbon dioxide has little effect."),
        ("17. Effect of temperature", "Photosynthesis involves enzymes, so temperature affects the reaction rate. Very low temperature slows enzyme activity, while excessive heat can disrupt enzyme structure and reduce the rate."),
        ("18. Photosynthesis versus respiration", "Photosynthesis stores energy in organic molecules using light energy, while cellular respiration releases usable energy from organic molecules. They are related but are not the same process."),
        ("19. Experimental evidence", "A classic school investigation can test starch formation in leaves after controlling light and other conditions. Iodine solution is commonly used as an indicator for starch, following the required safety and laboratory procedure."),
        ("20. Measuring rate", "The rate of photosynthesis can be estimated by measuring oxygen production, carbon dioxide uptake or changes in biomass under controlled conditions. A fair comparison changes one independent variable while controlling others."),
        ("21. Factors that can confuse results", "Leaf area, temperature, water availability, carbon dioxide concentration and previous light exposure can affect an experiment. Controls and repeated measurements improve reliability."),
        ("22. Common misconceptions", "Plants respire as well as photosynthesise. Also, sunlight is an energy source rather than a raw material, while carbon dioxide and water are raw materials in the overall equation."),
        ("23. Exam answer structure", "For a theory question, define the process, state the required conditions, explain the role of the relevant structure or factor, and finish with the expected product or effect."),
        ("24. Revision checklist", "Remember the overall equation, chloroplast/chlorophyll roles, stomata, xylem, glucose uses, oxygen release and the three major limiting factors. Then practise interpreting rate-versus-factor graphs."),
    ],
    "grammar": [
        ("1. What makes a sentence", "A complete sentence expresses a complete thought and normally contains a subject and a predicate. Sentence structure helps the reader understand who performs an action and what happens."),
        ("2. Subject", "The subject is the person, thing or idea the sentence is about. In long sentences, locate the true subject before deciding which verb form is required."),
        ("3. Predicate", "The predicate contains the verb and the information about the subject. It may be a single verb or a much longer phrase."),
        ("4. Nouns", "Nouns name people, places, objects, qualities or ideas. They may be common, proper, abstract or collective depending on the classification system being used."),
        ("5. Pronouns", "Pronouns replace or refer to nouns, helping avoid unnecessary repetition. Their form should match the intended person, number and grammatical role."),
        ("6. Verbs", "Verbs express actions, states or occurrences. The verb form changes according to tense, subject and sometimes voice or mood."),
        ("7. Subject-verb agreement", "A singular subject generally takes a singular verb in the present tense, while a plural subject takes the plural form. Ignore distracting words between the subject and verb when checking agreement."),
        ("8. Adjectives", "Adjectives describe or modify nouns and pronouns. Place them where their relationship to the intended noun is clear."),
        ("9. Adverbs", "Adverbs commonly modify verbs, adjectives or other adverbs and can express manner, time, place or degree. The exact grammatical role depends on the sentence."),
        ("10. Prepositions", "Prepositions show relationships such as place, time, direction or connection. Common examples include in, on, at, under, between and through."),
        ("11. Conjunctions", "Conjunctions connect words, phrases or clauses. Coordinating conjunctions join elements of equal status, while subordinating conjunctions introduce dependent clauses."),
        ("12. Phrases and clauses", "A phrase is a group of words functioning together without a complete subject-verb clause structure, while a clause contains a subject and a verb. Independent clauses can stand as sentences."),
        ("13. Tenses", "Tense indicates time and aspect of an action or state. Use time clues such as yesterday, now, already and tomorrow, but also check the meaning of the entire sentence."),
        ("14. Active and passive voice", "In active voice, the subject performs the action. In passive voice, the subject receives the action, and the appropriate form of 'be' plus the past participle is used."),
        ("15. Direct and indirect speech", "Direct speech reports the exact words within quotation marks, while indirect speech reports the meaning without quoting the original wording. Pronouns and tense may change when converting between forms."),
        ("16. Determiners", "Determiners help specify nouns. Articles such as a, an and the are common determiners, and other words such as this, those, some and each can serve similar functions."),
        ("17. Modals", "Modal verbs such as can, could, may, might, must, should and would express ability, possibility, permission, obligation or expectation. The following verb generally remains in its base form."),
        ("18. Punctuation", "Full stops, commas, question marks, colons, semicolons and apostrophes help organise meaning. Punctuation should reflect sentence structure rather than being inserted only where a pause sounds natural."),
        ("19. Common error detection", "Read the whole sentence before correcting an error. Check subject-verb agreement, tense, article use, prepositions, pronouns, word order and punctuation in that order."),
        ("20. Sentence transformation", "When changing a sentence from one form to another, preserve its meaning while changing the required grammatical structure. Check that no important information is lost."),
        ("21. Editing strategy", "First identify the sentence's intended meaning, then locate the grammatical unit containing the error. Make the smallest correction that produces a grammatically sound sentence."),
        ("22. Common mistakes", "Frequent errors include confusing its/it's, their/there/they're, subject-verb agreement, inconsistent tense and missing punctuation. Always judge the word by its role in the sentence."),
        ("23. Exam strategy", "For grammar questions, eliminate options that break agreement or tense before comparing the remaining choices. Read the completed sentence aloud mentally for meaning and structure."),
        ("24. Revision checklist", "Revise sentence structure, parts of speech, agreement, tenses, voice, reported speech, determiners, modals and punctuation. Practise editing complete sentences rather than isolated words."),
    ],
    "electricity": [
        ("1. Electric charge", "Electric charge is a physical property responsible for electrical interactions. Charge is measured in coulombs, and current describes the rate at which charge passes a point."),
        ("2. Electric current", "Electric current is the rate of flow of charge: I = Q/t. Its SI unit is the ampere, equivalent to coulomb per second."),
        ("3. Conventional current", "Conventional current is taken to flow from higher electric potential to lower potential in the external circuit. Electron motion in metals is opposite to the conventional current direction."),
        ("4. Potential difference", "Potential difference measures energy transferred per unit charge: V = W/Q. It is measured in volts and provides the electrical driving difference between two points."),
        ("5. Electromotive force", "The emf of a source represents the energy supplied by the source per unit charge. It is related to the source's ability to drive current in a circuit."),
        ("6. Resistance", "Resistance measures opposition to current and is measured in ohms. For an ohmic conductor under suitable constant conditions, V = IR."),
        ("7. Ohm's law", "Ohm's law states that current through an ohmic conductor is proportional to potential difference when physical conditions such as temperature remain constant. It can be rearranged as I = V/R or R = V/I."),
        ("8. Resistivity", "Resistivity is a material property that relates resistance to conductor length and cross-sectional area. For a uniform conductor, R = ρL/A."),
        ("9. Series circuits", "In a series circuit, the same current passes through each component. The equivalent resistance is the sum of individual resistances."),
        ("10. Parallel circuits", "In a parallel arrangement, each branch has the same potential difference across it, while the total current is divided among branches. Equivalent resistance is lower than the smallest branch resistance for positive resistors."),
        ("11. Electrical power", "Electrical power is the rate of electrical energy transfer. Useful forms include P = VI, P = I²R and P = V²/R when the relevant conditions apply."),
        ("12. Electrical energy", "Electrical energy transferred over time can be calculated using E = Pt. In domestic contexts, energy may be expressed in kilowatt-hours rather than joules."),
        ("13. Heating effect", "When current passes through resistance, electrical energy can be converted into thermal energy. The heating effect is important in heaters, fuses and other devices."),
        ("14. Ammeter", "An ammeter measures current and is connected in series so that the circuit current passes through the instrument. An ideal ammeter has very low resistance."),
        ("15. Voltmeter", "A voltmeter measures potential difference between two points and is connected in parallel with the component. An ideal voltmeter has very high resistance."),
        ("16. Kirchhoff's current law", "At a junction, the total current entering equals the total current leaving when charge does not accumulate at the junction. This expresses conservation of charge."),
        ("17. Kirchhoff's voltage law", "Around a closed circuit loop, the algebraic sum of potential changes is zero under the chosen sign convention. This expresses conservation of energy."),
        ("18. Cells and internal resistance", "A real cell has internal resistance, so its terminal voltage can fall when current is drawn. Distinguish the emf of the source from the terminal potential difference under load."),
        ("19. Household safety", "Fuses and circuit breakers protect circuits from excessive current. Earthing and appropriate insulation reduce the risk of electric shock, and household wiring normally uses parallel connections for independent operation."),
        ("20. Worked example", "If a 5-ohm resistor carries 2 A, Ohm's law gives V = IR = 10 V. The electrical power is then P = VI = 20 W."),
        ("21. Unit checking", "Convert milliamperes to amperes, kilowatts to watts and other prefixes before substitution. Check that the final unit matches the physical quantity requested."),
        ("22. Common mistakes", "Do not connect an ammeter in parallel or a voltmeter in series. Also distinguish current, charge, potential difference, resistance, power and energy instead of treating them as interchangeable."),
        ("23. Circuit-solving method", "Draw or simplify the circuit, identify series and parallel groups, calculate equivalent resistance, use Ohm's law and then verify current or voltage relationships at each branch."),
        ("24. Revision checklist", "Memorise I = Q/t, V = W/Q, V = IR, P = VI, series/parallel rules and instrument connections. Then practise mixed circuit problems with explicit units and sign conventions."),
    ],
    "thermodynamics": [
        ("1. Thermodynamic system", "A thermodynamic system is the part of the universe selected for study. Everything outside it is the surroundings, and the boundary separates the two."),
        ("2. Open, closed and isolated systems", "An open system can exchange matter and energy with its surroundings. A closed system can exchange energy but not matter, while an ideal isolated system exchanges neither."),
        ("3. State variables", "Pressure, volume and temperature are common state variables. A state is described by a suitable set of variables, while a process describes the change from one state to another."),
        ("4. Thermal equilibrium", "Thermal equilibrium means there is no net heat transfer between systems in thermal contact. The zeroth law provides the basis for the concept of temperature."),
        ("5. Temperature", "Temperature characterises the thermal state of a system and determines the direction of heat transfer between bodies initially at different temperatures. It is not the same physical quantity as heat."),
        ("6. Heat", "Heat is energy transferred because of a temperature difference. It is a process of energy transfer, not a substance stored inside an object."),
        ("7. Internal energy", "Internal energy is the microscopic energy associated with the constituents of a system. Its change depends on the initial and final states for a state function, even though heat and work depend on the path."),
        ("8. Work in thermodynamics", "Work is energy transfer associated with macroscopic forces and displacement. For a quasistatic expansion or compression, mechanical work is related to the area under a pressure-volume curve."),
        ("9. First law of thermodynamics", "Using W as work done by the system, the first law can be written Q = ΔU + W. It expresses conservation of energy and requires a consistent sign convention."),
        ("10. Sign convention", "Before solving a numerical problem, state whether W is work done by or on the system and how heat entering or leaving is signed. Many apparent disagreements are caused by switching conventions mid-solution."),
        ("11. Isothermal process", "An isothermal process occurs at constant temperature. For an ideal gas under suitable conditions, internal energy depends only on temperature, so the change in internal energy is zero."),
        ("12. Adiabatic process", "An adiabatic process has no heat transfer, so Q = 0. Any change in internal energy is then connected to the work interaction according to the chosen sign convention."),
        ("13. Isobaric process", "An isobaric process occurs at constant pressure. When a system expands at constant external pressure, mechanical work is related to pressure and the change in volume."),
        ("14. Isochoric process", "An isochoric process occurs at constant volume. For a simple fixed-volume system doing no boundary work, the volume-work term is zero, so heat transfer changes internal energy directly."),
        ("15. P-V diagrams", "A pressure-volume graph represents a thermodynamic path. For a quasistatic process, the area under the curve corresponds to the mechanical work with the sign determined by expansion or compression convention."),
        ("16. Reversible and irreversible processes", "A reversible process is an idealised process that can be reversed through infinitesimal changes without net changes to the surroundings. Real processes involve finite gradients, friction or other irreversibilities."),
        ("17. Second law", "The second law introduces the directionality of natural processes and limits the conversion of heat into work. It also provides the foundation for entropy and heat-engine efficiency."),
        ("18. Entropy", "Entropy is a state function associated with the direction and dispersal of energy in thermodynamic processes. For an isolated system, the total entropy does not decrease in a spontaneous irreversible process."),
        ("19. Heat engines", "A heat engine operates cyclically, taking energy from a high-temperature source, doing useful work and rejecting some energy to a lower-temperature sink. No engine can convert all input heat into work in a cyclic process."),
        ("20. Carnot engine", "The Carnot cycle is an ideal reversible cycle used as a benchmark for maximum efficiency between two temperatures. Its efficiency depends on the absolute temperatures of the hot and cold reservoirs."),
        ("21. Refrigerator", "A refrigerator uses external work to transfer heat from a colder region to a warmer environment. Its performance is described using a coefficient of performance rather than ordinary heat-engine efficiency."),
        ("22. Ideal gas connection", "For an ideal gas, pressure, volume, amount and absolute temperature are related by an equation of state. Always use kelvin for thermodynamic temperature in gas-law calculations."),
        ("23. Heat capacities", "Specific heat capacity measures the energy required per unit mass per unit temperature change. In gases, molar heat capacities at constant pressure and constant volume differ because expansion work can occur at constant pressure."),
        ("24. Worked example", "If a system receives 500 J of heat and does 200 J of work, then with W defined as work done by the system, ΔU = Q - W = 300 J. The numerical result follows directly from the stated convention."),
        ("25. Exam strategy", "Write the system and sign convention first, identify the process, list known quantities with units, choose the appropriate law, substitute carefully and check whether the direction of heat/work makes physical sense."),
    ],
    "vector": [
        ("1. What is a vector?", "A vector is a quantity that has both magnitude and direction. Examples include displacement, velocity, acceleration and force, whereas scalar quantities such as mass, time and temperature have magnitude only."),
        ("2. Scalar versus vector", "A scalar is described completely by a numerical value and unit, while a vector also requires direction. Adding vectors therefore requires attention to direction, not just their numerical magnitudes."),
        ("3. Magnitude", "The magnitude of a vector is its size or length and is a non-negative scalar. For a vector a = ai + bj + ck, its magnitude is √(a²+b²+c²)."),
        ("4. Direction", "Direction describes the orientation of a vector relative to a chosen reference. In two dimensions it may be represented by an angle, while in three dimensions direction can be represented using components or direction cosines."),
        ("5. Unit vectors", "A unit vector has magnitude 1 and indicates direction only. The standard Cartesian unit vectors are i, j and k along the x, y and z axes respectively."),
        ("6. Position vector", "The position vector of a point gives its location relative to the chosen origin. If P has coordinates (x,y,z), its position vector is xi + yj + zk."),
        ("7. Vector components", "A vector can be resolved into perpendicular components along coordinate axes. Components make addition, subtraction and many geometric calculations systematic."),
        ("8. Addition of vectors", "Vectors are added component-wise or geometrically using the triangle/parallelogram rule. The direction of the resultant must be considered along with its magnitude."),
        ("9. Subtraction", "Subtracting vector b from vector a means adding the negative of b: a-b = a+(-b). The negative vector has the same magnitude as b but the opposite direction."),
        ("10. Multiplication by a scalar", "Multiplying a vector by a positive scalar changes its magnitude, while a negative scalar also reverses its direction. A zero scalar produces the zero vector."),
        ("11. Zero vector", "The zero vector has magnitude zero and no unique direction. It acts as the additive identity because a + 0 = a."),
        ("12. Parallel and collinear vectors", "Two non-zero vectors are parallel when one is a scalar multiple of the other. Collinear points have position vectors related along the same line."),
        ("13. Section formula", "A point dividing a line segment in a specified ratio can be represented using weighted position vectors. The internal-division formula is applied only after the ratio and endpoint order are identified correctly."),
        ("14. Dot product", "The dot product of vectors a and b is a·b = |a||b|cosθ and is a scalar. In components, multiply corresponding components and add them."),
        ("15. Perpendicular vectors", "Two non-zero vectors are perpendicular when their dot product is zero. This provides a convenient algebraic test for right angles."),
        ("16. Projection", "The scalar projection of one vector onto another measures how much of one vector acts in the direction of the other. It is closely related to the dot product and cosine of the included angle."),
        ("17. Cross product", "The cross product a×b produces a vector perpendicular to both a and b. Its magnitude is |a||b|sinθ, and its direction follows the right-hand rule."),
        ("18. Area using cross product", "The magnitude of a×b gives the area of the parallelogram formed by a and b. Half of that magnitude gives the area of the triangle formed by the same two vectors."),
        ("19. Direction cosines", "For a vector in three dimensions, its direction cosines are the cosines of the angles it makes with the positive coordinate axes. They satisfy l²+m²+n²=1 for a unit direction vector."),
        ("20. Equation of a line", "A vector equation of a line can be written as r = a + λb, where a is a point on the line, b gives its direction and λ is a scalar parameter."),
        ("21. Coplanarity", "Vectors or points are coplanar when they lie in the same plane. In three dimensions, scalar triple products provide a standard algebraic test for coplanarity."),
        ("22. Worked example", "For a = 2i+3j and b = i-j, a+b = 3i+2j and a·b = 2(1)+3(-1) = -1. The first result is a vector; the second is a scalar."),
        ("23. Common mistakes", "Do not add magnitudes when directions differ, and do not confuse dot and cross products. Check whether the required answer should be a scalar or a vector before choosing the operation."),
        ("24. Exam strategy", "Write vectors in component form when possible, state the relevant formula, substitute carefully and keep i, j and k components separate until the final simplification."),
        ("25. Quick revision", "Remember magnitude, unit vectors, components, addition/subtraction, dot product, perpendicularity, cross product, line equations and the distinction between scalar and vector results."),
    ],
}


def _clean_wikipedia_text(text):
    """Turn Wikipedia's plain extract into readable study paragraphs."""
    text = re.sub(r'\[[0-9]+\]', '', text or '')
    text = text.replace('\r', '\n')
    lines = []
    for raw in text.split('\n'):
        line = re.sub(r'\s+', ' ', raw).strip()
        if not line:
            continue
        # Skip navigation/meta headings that are not useful as learner notes.
        if line.lower() in {'references', 'external links', 'see also', 'notes', 'further reading'}:
            continue
        lines.append(line)
    return lines


# Small offline packs cover common classroom topics so the demo remains useful
# even when the learner's machine has no internet connection. For other topics,
# the engine uses source-backed retrieval and never invents missing facts.
OFFLINE_TOPIC_PACKS = {
    "hydrocarbons": [
        ("Meaning", "Hydrocarbons are organic compounds composed only of carbon and hydrogen."),
        ("Main classification", "Hydrocarbons are broadly classified as aliphatic and aromatic. Aliphatic compounds include saturated and unsaturated members."),
        ("Alkanes", "Alkanes are saturated hydrocarbons containing only carbon-carbon single bonds. Their general formula for open-chain members is CnH2n+2."),
        ("Alkenes", "Alkenes contain at least one carbon-carbon double bond. Acyclic monoalkenes have the general formula CnH2n."),
        ("Alkynes", "Alkynes contain at least one carbon-carbon triple bond. Acyclic monoalkynes have the general formula CnH2n-2."),
        ("Aromatic hydrocarbons", "Aromatic hydrocarbons contain aromatic ring systems. Benzene is the standard example and has a planar six-carbon ring with delocalised pi electrons."),
        ("Homologous series", "Members of a homologous series have the same functional pattern and successive members differ by a CH2 unit. They show gradual changes in physical properties."),
        ("IUPAC naming", "Systematic naming requires selection of the parent chain or ring, identification of multiple bonds and substituents, numbering to give the lowest appropriate locants, and assembly of the name."),
        ("Isomerism", "Hydrocarbons can show structural isomerism, including chain and position isomerism. Alkenes can also show geometrical isomerism when the required substituent conditions are satisfied."),
        ("Combustion", "Hydrocarbons burn in oxygen. Complete combustion produces carbon dioxide and water, while limited oxygen can lead to incomplete-combustion products such as carbon monoxide and carbon."),
        ("Addition reactions", "Alkenes and alkynes undergo addition reactions because their pi bonds can participate in reactions with suitable reagents. Hydrogenation converts an unsaturated bond to a more saturated one."),
        ("Substitution reactions", "Alkanes commonly undergo substitution reactions under suitable conditions. Halogenation is a standard example in which a hydrogen atom can be replaced by a halogen."),
        ("Benzene reactions", "Benzene commonly undergoes electrophilic substitution rather than simple addition because substitution preserves the aromatic system."),
        ("Markovnikov orientation", "For addition of an unsymmetrical reagent to an unsymmetrical alkene, the Markovnikov orientation describes the usual placement pattern under the stated conditions."),
        ("Polymerisation", "Many alkenes can form polymers through addition polymerisation, in which monomer double bonds are converted into carbon-carbon single-bond links in the chain."),
        ("Physical properties", "Physical properties of hydrocarbons vary with molecular size and structure. Increasing chain length generally increases boiling point within comparable homologous series."),
        ("Sources", "Important practical sources of hydrocarbons include petroleum and natural gas. Industrial processing separates and converts hydrocarbon mixtures into useful fractions and products."),
        ("Environmental impact", "Combustion of hydrocarbons releases carbon dioxide, and incomplete combustion can release carbon monoxide and particulate matter. Fuel choice and combustion efficiency therefore matter environmentally."),
        ("Exam checklist", "For a hydrocarbon question, first identify saturation and the relevant class, then write the required structure or formula, apply the correct reaction pattern, and check carbon valency and the final molecular formula."),
        ("Quick revision", "Remember the distinction between alkane, alkene, alkyne and aromatic systems; the common open-chain formulae; the role of sigma and pi bonding; and the difference between addition and substitution.")
    ],
    "lens": [
        ("Meaning", "A lens is a transparent optical element bounded by two refracting surfaces, at least one of which is curved."),
        ("Convex lens", "A convex lens is thicker at the centre than at the edges and, in the usual surrounding medium, tends to converge approximately parallel incident rays."),
        ("Concave lens", "A concave lens is thinner at the centre than at the edges and tends to diverge approximately parallel incident rays."),
        ("Principal axis", "The principal axis is the straight line passing through the optical centre and the centres of curvature of the lens surfaces."),
        ("Optical centre", "The optical centre is a point on a thin lens through which a ray can pass approximately undeviated in the paraxial approximation."),
        ("Principal focus", "The principal focus is the point at which rays parallel to the principal axis converge, or from which they appear to diverge, after refraction."),
        ("Focal length", "The focal length is the distance from the optical centre to the principal focus. Its sign depends on the adopted Cartesian sign convention."),
        ("Lens formula", "For a thin lens using the Cartesian sign convention, the relation is 1/f = 1/v - 1/u, where u is object distance, v is image distance and f is focal length."),
        ("Magnification", "Linear magnification for a thin lens is m = h_i/h_o = v/u under the same sign convention. Its sign indicates the orientation of the image."),
        ("Ray rules", "A ray parallel to the principal axis is refracted through the principal focus for a converging lens; a ray through the optical centre is approximately undeviated for a thin lens."),
        ("Image formation", "The position and nature of an image formed by a convex lens depend on the object's position relative to the focal point and twice the focal length."),
        ("Concave-lens image", "For a real object, a concave lens normally forms a virtual, erect and diminished image on the same side as the object."),
        ("Power", "The power of a lens is P = 1/f when f is measured in metres. The SI unit is the dioptre (D)."),
        ("Combination", "For thin lenses in contact, the equivalent power is the algebraic sum of the individual powers: P = P1 + P2 + ..."),
        ("Sign convention", "In numerical problems, choose one sign convention and apply it consistently to object distance, image distance, focal length and height."),
        ("Practical use", "Lenses are used in cameras, microscopes, telescopes, spectacles and many other optical instruments."),
        ("Common error", "Do not mix centimetres and metres in the power formula, and do not change signs midway through a lens-formula calculation."),
        ("Quick revision", "Know the difference between convex and concave lenses, the focus and focal length, the lens formula, magnification, power, and the standard image cases.")
    ],
    "semiconductor": [
        ("Meaning", "A semiconductor is a material whose electrical conductivity lies between that of a good conductor and an insulator and can be controlled by temperature, impurities and other conditions."),
        ("Valence and conduction bands", "In a solid, electrons occupy allowed energy bands. The valence band is associated with bound valence electrons, while the conduction band contains mobile charge carriers when sufficiently populated."),
        ("Band gap", "The energy gap between the valence and conduction bands influences electrical behaviour. A semiconductor has a relatively small band gap compared with an insulator."),
        ("Intrinsic semiconductor", "An intrinsic semiconductor is a pure semiconductor in which thermally generated electrons and holes are produced in equal numbers."),
        ("Electron-hole pair", "When an electron gains sufficient energy to leave its bound state, it can contribute to conduction and leave behind a vacancy called a hole."),
        ("Extrinsic semiconductor", "An extrinsic semiconductor is obtained by adding a controlled impurity to change the concentration of charge carriers."),
        ("n-type", "Doping a semiconductor with a suitable donor impurity increases the concentration of electrons. Electrons are the majority carriers in n-type material."),
        ("p-type", "Doping with a suitable acceptor impurity increases the concentration of holes. Holes are the majority carriers in p-type material."),
        ("Majority and minority carriers", "In n-type material electrons are majority carriers and holes are minority carriers; in p-type material holes are majority carriers and electrons are minority carriers."),
        ("p-n junction", "A p-n junction is formed when p-type and n-type semiconductor regions meet. Carrier diffusion near the junction creates a depletion region."),
        ("Depletion region", "The depletion region contains very few mobile majority carriers and has an internal electric field associated with the separated charged ions."),
        ("Junction biasing", "Forward bias reduces the junction barrier and permits substantial current after the relevant threshold behaviour. Reverse bias increases the barrier and normally permits only a small reverse current until breakdown conditions."),
        ("Diode", "A semiconductor diode is a p-n junction device that allows current to be controlled predominantly in one direction."),
        ("Rectification", "Diodes can be used for rectification, converting an alternating input into a unidirectional or pulsating output."),
        ("LED", "A light-emitting diode produces light when carriers recombine in the active region under forward-bias operation."),
        ("Photodiode", "A photodiode is designed to respond to incident light and is commonly operated under reverse bias in sensing applications."),
        ("Transistor", "A transistor is a semiconductor device with three regions and can be used for switching and amplification."),
        ("Digital logic", "Semiconductor switching devices form the basis of digital logic circuits, where controlled states represent logical values."),
        ("Temperature effect", "For common semiconductors, conductivity generally increases as temperature rises because more charge carriers become available."),
        ("Quick revision", "Remember intrinsic versus extrinsic material, electrons versus holes, n-type versus p-type, depletion region, forward/reverse bias, diode applications and the basic role of transistors.")
    ],
}

# High-confidence school mathematics packs for common short/ambiguous topics.
# These are intentionally local so common classroom topics do not depend on a
# slow or ambiguous external search.
OFFLINE_TOPIC_PACKS.update({
    "integration": [
        ("Meaning", "Integration is the inverse process of differentiation. In calculus, an antiderivative F of f satisfies F'(x) = f(x)."),
        ("Indefinite integral", "The indefinite integral of f(x) is written ∫f(x) dx and represents the family of antiderivatives F(x) + C, where C is an arbitrary constant."),
        ("Constant of integration", "The constant C is included because differentiating any constant gives zero, so antiderivatives of the same function can differ by a constant."),
        ("Basic power rule", "For n ≠ −1, ∫xⁿ dx = xⁿ⁺¹/(n+1) + C. The exponent increases by one and the result is divided by the new exponent."),
        ("Constant multiple rule", "A constant factor can be taken outside an integral: ∫k f(x) dx = k∫f(x) dx."),
        ("Sum and difference", "Integration is linear: the integral of a sum or difference can be found by integrating the terms separately."),
        ("Standard exponential integral", "For a nonzero constant a, ∫e^(ax) dx = e^(ax)/a + C. The factor 1/a accounts for the derivative of ax."),
        ("Standard trigonometric integrals", "Common results include ∫cos x dx = sin x + C and ∫sin x dx = −cos x + C."),
        ("Substitution", "In substitution, a suitable expression is replaced by a new variable so that the integral becomes simpler. The differential must be transformed consistently."),
        ("Definite integral", "A definite integral has limits and gives a numerical signed area or accumulated quantity: ∫ₐᵇ f(x) dx."),
        ("Fundamental theorem", "The Fundamental Theorem of Calculus connects differentiation and definite integration and allows a definite integral to be evaluated using an antiderivative."),
        ("Area interpretation", "When f(x) is nonnegative on [a,b], ∫ₐᵇ f(x) dx represents the area between the graph and the x-axis over that interval."),
        ("Area between curves", "The area between an upper curve and a lower curve over an interval is found by integrating upper minus lower, provided the curves are ordered consistently."),
        ("Integration by parts", "Integration by parts follows from the product rule and is commonly written ∫u dv = uv − ∫v du."),
        ("Choosing u", "In integration by parts, choose u so that differentiating it simplifies the expression, while dv is chosen so that it can be integrated readily."),
        ("Partial fractions", "Rational functions with factorable denominators can sometimes be decomposed into simpler fractions before integration."),
        ("Definite-integral properties", "Reversing the limits changes the sign, and splitting an interval allows a definite integral to be written as the sum over adjacent subintervals."),
        ("Symmetry", "For an even function, the integral from −a to a is twice the integral from 0 to a. For an odd function, the integral over [−a,a] is zero."),
        ("Checking an antiderivative", "Differentiate the proposed antiderivative to verify an indefinite integration result. For a definite integral, also check the limits and sign."),
        ("Common errors", "Common errors include forgetting C in an indefinite integral, mishandling substitution differentials, changing limits incorrectly, or using the wrong order for area between curves."),
    ],
    "matrix": [
        ("Meaning", "A matrix is a rectangular arrangement of numbers, symbols or expressions organised in rows and columns."),
        ("Order", "The order of a matrix is m × n when it has m rows and n columns."),
        ("Element notation", "The element in row i and column j is commonly denoted aᵢⱼ."),
        ("Row matrix", "A row matrix has exactly one row."),
        ("Column matrix", "A column matrix has exactly one column."),
        ("Square matrix", "A square matrix has the same number of rows and columns."),
        ("Zero matrix", "A zero matrix has every element equal to zero."),
        ("Diagonal matrix", "A diagonal matrix is square and has zero entries outside its main diagonal."),
        ("Scalar matrix", "A scalar matrix is a diagonal matrix whose diagonal entries are all equal."),
        ("Identity matrix", "An identity matrix is a square matrix with ones on the main diagonal and zeros elsewhere. It acts as the multiplicative identity for compatible matrices."),
        ("Equality", "Two matrices are equal when they have the same order and their corresponding elements are equal."),
        ("Addition", "Matrices can be added only when they have the same order; corresponding elements are added."),
        ("Scalar multiplication", "Multiplying a matrix by a scalar multiplies every element by that scalar."),
        ("Matrix multiplication", "For AB to be defined, the number of columns of A must equal the number of rows of B. The product entry is formed from a row of A and a column of B."),
        ("Non-commutativity", "Matrix multiplication is generally not commutative: AB need not equal BA."),
        ("Transpose", "The transpose Aᵀ is obtained by interchanging rows and columns."),
        ("Determinant", "A determinant is a scalar associated with a square matrix. For a 2 × 2 matrix [[a,b],[c,d]], det(A) = ad − bc."),
        ("Inverse", "A square matrix A has an inverse A⁻¹ when it is nonsingular, and then AA⁻¹ = A⁻¹A = I."),
        ("Singular matrix", "A square matrix is singular when its determinant is zero; such a matrix does not have an ordinary inverse."),
        ("Applications", "Matrices are used to represent systems of linear equations, transformations and many structured numerical relationships."),
    ],
    "rectangle": [
        ("Definition", "A rectangle is a quadrilateral with four right angles."),
        ("Opposite sides", "Opposite sides of a rectangle are parallel and equal in length."),
        ("Diagonals", "The diagonals of a rectangle are equal in length and bisect each other."),
        ("Perimeter", "If the length is l and breadth is b, the perimeter is 2(l + b)."),
        ("Area", "If the length is l and breadth is b, the area is l × b."),
        ("Right angles", "Each interior angle of a rectangle measures 90°."),
        ("Square relation", "A square is a special rectangle in which all four sides are equal."),
        ("Diagonal formula", "For a rectangle with sides l and b, the diagonal length is √(l² + b²), from the Pythagorean theorem."),
        ("Symmetry", "A non-square rectangle has two lines of reflection symmetry and rotational symmetry of order 2."),
        ("Coordinate geometry", "A rectangle aligned with the coordinate axes can be described using its two x-coordinates and two y-coordinates."),
        ("Area from diagonal", "If the diagonal and one side are known, the other side can be found using the Pythagorean theorem before calculating area."),
        ("Perimeter from area", "Knowing only the area does not determine a unique rectangle; an additional condition such as perimeter or one side is needed."),
        ("Construction idea", "A rectangle can be constructed using perpendicular lines and a chosen pair of side lengths."),
        ("Opposite angles", "Opposite angles of a rectangle are equal because all four angles are right angles."),
        ("Adjacent angles", "Adjacent interior angles of a rectangle are supplementary because each is 90°."),
        ("Diagonal midpoint", "The two diagonals intersect at their common midpoint, so each diagonal is bisected."),
        ("Special case", "When the length equals the breadth, the rectangle becomes a square."),
        ("Common error", "Do not use l + b as the perimeter or l × b as the perimeter; keep area and perimeter formulas distinct."),
        ("Units", "Area is expressed in square units, while perimeter and side lengths are expressed in linear units."),
        ("Revision", "Remember the four right angles, equal and parallel opposite sides, equal bisecting diagonals, area l×b and perimeter 2(l+b)."),
    ],
})

def _offline_topic_notes(topic):
    key = re.sub(r'\s+', ' ', str(topic or '').strip().casefold())
    aliases = {'matrices': 'matrix', 'rectangles': 'rectangle', 'integrals': 'integration', 'calculus integration': 'integration'}
    rows = OFFLINE_TOPIC_PACKS.get(key) or OFFLINE_TOPIC_PACKS.get(aliases.get(key, ''))
    if not rows:
        return None
    return [(str(heading).strip(), body) for heading, body in rows]


@lru_cache(maxsize=128)
def _dynamic_topic_notes(topic, subject):
    """Fetch one high-confidence, subject-matched source for a topic.

    Safety rule: the engine must prefer *no factual content* over unrelated
    content.  Search results are scored using the topic, subject evidence in the
    page lead, and disambiguation/category cues.  Only the single best page is
    used; unrelated search hits are never concatenated into one lesson.
    """
    t = re.sub(r'\s+', ' ', str(topic or '').strip())
    subj = re.sub(r'\s+', ' ', str(subject or '').strip())
    if not t:
        return None

    cache_path = os.path.join(BASE_DIR, 'instance', 'topic_knowledge_cache.json')
    cache_key = re.sub(r'\s+', ' ', f'v16|{subj}|{t}'.strip().casefold())

    def load_cache():
        try:
            with open(cache_path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save_cache(payload):
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            cache = load_cache()
            cache[cache_key] = payload
            tmp = cache_path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as fh:
                json.dump(cache, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, cache_path)
        except Exception:
            pass

    cached = load_cache().get(cache_key)
    if isinstance(cached, dict) and cached.get('verified') and len(cached.get('sections', [])) >= 4:
        return cached

    offline = _offline_topic_notes(t)
    if offline:
        payload = {
            'sections': offline,
            'source_title': 'Learn4All curated classroom reference',
            'source_url': '',
            'source_note': 'Verified offline classroom reference selected for this topic.',
            'verified': True,
        }
        save_cache(payload)
        return payload

    def get_json(url, timeout=4):
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Learn4All/16.0 (educational prototype)',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))

    def clean(text):
        text = re.sub(r'\[[^\]]*\]', '', text or '')
        text = re.sub(r'\{\{.*?\}\}', ' ', text, flags=re.S)
        return re.sub(r'\s+', ' ', text).strip()

    def strip_html(value):
        value = re.sub(r'<(script|style|table|sup|math)[^>]*>.*?</\1>', ' ', value or '', flags=re.I | re.S)
        value = re.sub(r'<br\s*/?>', '\n', value, flags=re.I)
        value = re.sub(r'</(p|div|li|h[1-6])\s*>', '\n', value, flags=re.I)
        value = re.sub(r'<[^>]+>', ' ', value)
        import html as _html
        return clean(_html.unescape(value))

    profiles = {
        'physics': {
            'positive': ['physics','force','energy','motion','velocity','acceleration','mass','momentum','electric','magnetic','current','voltage','resistance','wave','optics','thermodynamic','quantum','charge'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','novel','fictional character','video game','band','director'],
        },
        'chemistry': {
            'positive': ['chemistry','chemical','atom','molecule','compound','reaction','bond','ion','organic','inorganic','acid','base','element','periodic'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','novel','fictional character','video game','band','director'],
        },
        'mathematics': {
            'positive': ['mathematics','mathematical','equation','theorem','function','number','algebra','geometry','calculus','probability','statistics','vector','matrix','integral','derivative','angle'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','novel','fictional character','video game','band','director'],
        },
        'maths': {
            'positive': ['mathematics','mathematical','equation','theorem','function','number','algebra','geometry','calculus','probability','statistics','vector','matrix','integral','derivative','angle'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','novel','fictional character','video game','band','director'],
        },
        'biology': {
            'positive': ['biology','biological','cell','organism','gene','genetic','protein','enzyme','plant','animal','ecology','evolution','tissue','organ','species','dna','rna'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','novel','fictional character','video game','band','director'],
        },
        'computer science': {
            'positive': ['computer','computing','programming','algorithm','software','hardware','data','database','network','operating system','python','java','code','programming language','binary'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','novel','fictional character','video game','band','director'],
        },
        'english': {
            'positive': ['language','linguistics','grammar','syntax','semantics','literature','literary','poetry','poem','novel','prose','drama','play','tragedy','rhetoric','author','writer','english'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','video game','band'],
        },
        'science': {
            'positive': ['science','scientific','physics','chemistry','biology','energy','matter','force','atom','molecule','cell','organism','reaction','motion','electric','magnetic'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','novel','fictional character','video game','band','director'],
        },
        'history': {
            'positive': ['history','historical','war','empire','kingdom','revolution','treaty','civilization','dynasty','colonial','independence'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','video game'],
        },
        'geography': {
            'positive': ['geography','geographical','climate','landform','river','mountain','continent','population','earth','plate','latitude','longitude','region'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','video game'],
        },
        'economics': {
            'positive': ['economics','economic','market','demand','supply','inflation','gdp','income','production','consumption','price','monetary','fiscal'],
            'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','video game'],
        },
    }
    profile = profiles.get(subj.casefold(), {
        'positive': [subj.casefold()] if subj and subj.casefold() not in {'general','other'} else [],
        'negative': ['film','movie','actor','actress','song','album','soundtrack','television','tv series','novel','fictional character','video game','band','director'],
    })

    def is_media_or_nonacademic(title, lead):
        combined = f'{title} {lead[:1200]}'.casefold()
        bad = profile['negative']
        # Strong title/lead signals are enough to reject a candidate.
        return any(term in title.casefold() for term in bad) or sum(combined.count(term) for term in bad) >= 2

    def subject_score(title, lead):
        combined = f'{title} {lead[:2200]}'.casefold()
        return sum(combined.count(term) for term in profile['positive'])

    try:
        api = 'https://en.wikipedia.org/w/api.php'
        # Fast REST search gives better title/description metadata and reduces
        # the number of full page parses needed for short ambiguous topics.
        rest_candidates = []
        try:
            rest_q = f'{t} {subj}'.strip() if subj.casefold() not in {'general','other',''} else t
            rest = get_json('https://en.wikipedia.org/w/rest.php/v1/search/page?' + urllib.parse.urlencode({'q': rest_q, 'limit': 8}), timeout=4)
            for page in (rest.get('pages') or []):
                title = clean(page.get('title', ''))
                desc = clean(page.get('description', ''))
                if title:
                    rest_candidates.append((title, desc, page.get('key') or title))
        except Exception:
            rest_candidates = []

        queries = [f'{t} {subj}'.strip(), f'\"{t}\" {subj}'.strip(), t]
        hits, seen = [], set()
        for q in queries:
            data = get_json(api + '?' + urllib.parse.urlencode({
                'action': 'query', 'list': 'search', 'srsearch': q,
                'format': 'json', 'formatversion': 2, 'srlimit': 6,
            }))
            for hit in data.get('query', {}).get('search', []):
                pid = hit.get('pageid')
                if pid and pid not in seen:
                    seen.add(pid); hits.append(hit)

        for title, desc, key_title in rest_candidates:
            synthetic_id = 'rest:' + re.sub(r'\W+', '_', title.casefold())
            if synthetic_id not in seen:
                hits.insert(0, {'pageid': synthetic_id, 'title': title, 'snippet': desc, '_rest_key': key_title})
                seen.add(synthetic_id)

        if not hits:
            payload = {'sections': [], 'quiz': [], 'video': [], 'video_bodies': [], 'source_title': 'Verified topic source unavailable', 'source_note': 'No sufficiently relevant source was found for this topic and subject.', 'verified': False}
            save_cache(payload)
            return payload

        candidates = []
        topic_cf = t.casefold()
        for hit in hits[:6]:
            pid = hit.get('pageid')
            title = clean(hit.get('title', ''))
            if not pid or not title:
                continue
            # Reject obvious disambiguation/media pages before parsing.
            if is_media_or_nonacademic(title, hit.get('snippet', '')):
                continue
            try:
                parse_params = {
                    'action': 'parse', 'prop': 'text|sections',
                    'format': 'json', 'formatversion': 2,
                }
                if isinstance(pid, str) and pid.startswith('rest:'):
                    parse_params['page'] = title
                else:
                    parse_params['pageid'] = pid
                data = get_json(api + '?' + urllib.parse.urlencode(parse_params), timeout=5)
            except Exception:
                continue
            parsed = data.get('parse') or {}
            text = strip_html(parsed.get('text') or '')
            if len(text) < 500:
                continue
            lead = text[:2600]
            if is_media_or_nonacademic(title, lead):
                continue
            lead_cf = lead.casefold()
            if 'may refer to' in lead_cf or 'can refer to' in lead_cf:
                continue
            tc = title.casefold()
            score = 0
            if tc == topic_cf:
                score += 1200
            if topic_cf in tc:
                score += 450
            # Exact topic mention in the lead is strong evidence.
            if topic_cf in lead.casefold():
                score += 260
            ss = subject_score(title, lead)
            score += min(ss, 8) * 70
            # Search snippet/lead agreement helps disambiguate short topics.
            snippet = clean(hit.get('snippet', ''))
            score += min(sum(1 for term in profile['positive'] if term in snippet.casefold()), 4) * 35
            # Penalise pages whose title looks like a broad disambiguation entry.
            if '(disambiguation)' in tc or tc.endswith(' disambiguation'):
                score -= 1000
            # A subject-specific source needs positive evidence; otherwise do not guess.
            if subj.casefold() in {'general','other',''}:
                min_subject_hits = 0
            else:
                min_subject_hits = 2 if subj.casefold() in profiles else 1
            if ss < min_subject_hits:
                continue
            candidates.append((score, title, text))

        if not candidates:
            payload = {'sections': [], 'quiz': [], 'video': [], 'video_bodies': [], 'source_title': 'Verified topic source unavailable', 'source_note': 'No sufficiently relevant source was verified for this topic and subject.', 'verified': False}
            save_cache(payload)
            return payload
        candidates.sort(key=lambda x: x[0], reverse=True)
        best = candidates[0]
        # Require a meaningful margin over the runner-up to avoid ambiguous matches.
        if len(candidates) > 1 and best[0] - candidates[1][0] < 80:
            # An exact title is allowed to win only when its subject evidence is strong.
            if not (best[1].casefold() == topic_cf and subject_score(best[1], best[2][:2200]) >= 3):
                return None

        title, text = best[1], best[2]
        chunks = []
        for para in re.split(r'\n+', text):
            para = clean(para)
            if len(para) < 80:
                continue
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                sentence = clean(sentence)
                # Keep factual topic material and discard obvious media/pop-culture
                # contamination that can occur on broad Wikipedia pages.
                if is_media_or_nonacademic(title, sentence):
                    continue
                if 80 <= len(sentence) <= 520:
                    chunks.append(sentence)

        unique, seen_text = [], set()
        for sentence in chunks:
            k = re.sub(r'\W+', '', sentence.casefold())
            if k and k not in seen_text:
                seen_text.add(k); unique.append(sentence)
        if len(unique) < 4:
            payload = {'sections': [], 'quiz': [], 'video': [], 'video_bodies': [], 'source_title': 'Verified topic source unavailable', 'source_note': 'The retrieved material was not sufficiently topic-specific to verify this lesson.', 'verified': False}
            save_cache(payload)
            return payload

        selected = unique[:36]
        sections = [(f'{t} — Key Point {i}', text) for i, text in enumerate(selected, 1)]
        payload = {
            'sections': sections,
            'source_title': title,
            'source_url': 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_')),
            'source_note': 'Verified topic source selected using topic + subject relevance checks. Verify board-specific syllabus wording against the prescribed textbook.',
            'verified': True,
        }
        save_cache(payload)
        return payload
    except Exception:
        payload = {'sections': [], 'quiz': [], 'video': [], 'video_bodies': [], 'source_title': 'Verified topic source unavailable', 'source_note': 'The topic source could not be verified at this time.', 'verified': False}
        try:
            save_cache(payload)
        except Exception:
            pass
        return payload


def _ffmpeg_filter_path(path):
    return str(path).replace('\\', '/').replace(':', '\\:')


def _dynamic_video_path(topic, sections):
    """Render a real browser-compatible MP4 from the same lesson sections."""
    if not sections:
        return None
    try:
        import imageio_ffmpeg
        ffmpeg_bin = shutil.which('ffmpeg') or imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    slug = re.sub(r'[^a-z0-9]+', '-', str(topic).casefold()).strip('-') or 'topic'
    digest = hashlib.sha1(('||'.join(f'{h}:{b}' for h,b in sections)).encode('utf-8')).hexdigest()[:10]
    out_dir = os.path.join(BASE_DIR, 'static', 'videos', 'generated')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'{slug}-{digest}.mp4')
    if os.path.exists(out_path) and os.path.getsize(out_path) > 30000:
        return url_for('static', filename=f'videos/generated/{slug}-{digest}.mp4')

    temp = os.path.join(out_dir, f'.{slug}-{digest}')
    os.makedirs(temp, exist_ok=True)
    try:
        font_candidates = [r'C:\Windows\Fonts\segoeui.ttf', r'C:\Windows\Fonts\arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
        bold_candidates = [r'C:\Windows\Fonts\segoeuib.ttf', r'C:\Windows\Fonts\arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
        regular = next((x for x in font_candidates if os.path.exists(x)), None)
        bold = next((x for x in bold_candidates if os.path.exists(x)), regular)
        def font(path, size):
            try: return ImageFont.truetype(path, size) if path else ImageFont.load_default()
            except Exception: return ImageFont.load_default()
        f_title, f_head, f_body = font(bold, 42), font(bold, 28), font(regular, 24)

        def wrap(text, width=76):
            words = str(text).split(); lines=[]; cur=''
            for word in words:
                nxt=(cur+' '+word).strip()
                if len(nxt) > width and cur:
                    lines.append(cur); cur=word
                else: cur=nxt
            if cur: lines.append(cur)
            return lines

        groups=[sections[i:i+3] for i in range(0,len(sections),3)][:8]
        images=[]
        for idx, group in enumerate(groups,1):
            im=Image.new('RGB',(1280,720),(248,244,236)); d=ImageDraw.Draw(im)
            d.rectangle((0,0,1280,112),fill=(122,16,16)); d.rectangle((0,112,1280,120),fill=(184,134,11))
            d.text((55,28), f'Learn4All • {topic}', font=f_title, fill=(255,253,248))
            d.text((60,150), f'Chapter {idx}', font=f_head, fill=(122,16,16))
            y=205
            for heading, body in group:
                d.text((65,y), re.sub(r'^\d+\.\s*','',heading)[:82], font=f_head, fill=(122,16,16)); y+=42
                for line in wrap(body, 82)[:5]:
                    d.text((72,y), '• '+line, font=f_body, fill=(36,32,28)); y+=32
                y+=18
            d.text((60,670),'Learn • Understand • Apply • Review',font=font(regular,18),fill=(111,105,97))
            img_path=os.path.join(temp,f'{idx:02d}.png'); im.save(img_path); images.append(img_path)

        concat=os.path.join(temp,'concat.txt')
        with open(concat,'w',encoding='utf-8') as fh:
            for img in images:
                fh.write(f"file '{img.replace(chr(39), chr(39)+chr(92)+chr(39))}'\n")
                fh.write('duration 5\n')
            fh.write(f"file '{images[-1].replace(chr(39), chr(39)+chr(92)+chr(39))}'\n")

        cmd=[ffmpeg_bin,'-y','-f','concat','-safe','0','-i',concat,'-vsync','vfr','-pix_fmt','yuv420p','-c:v','libx264','-preset','veryfast','-crf','23','-movflags','+faststart',out_path]
        subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
        probe=subprocess.run([ffmpeg_bin,'-v','error','-i',out_path,'-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
        if probe.returncode != 0 or os.path.getsize(out_path) < 30000:
            raise RuntimeError('Generated video failed validation')
        return url_for('static',filename=f'videos/generated/{slug}-{digest}.mp4')
    except Exception:
        try:
            if os.path.exists(out_path): os.remove(out_path)
        except Exception: pass
        return None
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _expanded_generic_notes(topic, subject):
    """Non-factual fallback: never ask the learner to write the notes themselves."""
    t = topic.strip()
    return [
        ("1. Topic overview", f"{t} is the selected topic in {subject}. A topic-specific source was not available at this moment, so this page avoids inventing facts. Use the prescribed textbook for exact definitions, formulae and syllabus-specific content."),
        ("2. How to revise this topic", f"Start with the chapter definition and central idea of {t}, then connect its important terms, rules, examples and applications. Revise the ideas in an order that makes the relationships between them clear."),
        ("3. Definitions", f"For {t}, learn each formal definition together with its conditions and important terms. Do not replace a textbook definition with a loosely worded shortcut when exact wording matters."),
        ("4. Key terms", f"Separate the important vocabulary of {t} into definitions, quantities, symbols, processes, classifications and examples. Similar words should not automatically be treated as synonyms."),
        ("5. Core relationships", f"Identify which ideas in {t} depend on one another. A good revision map should show what causes a change, what remains constant and which condition controls each result."),
        ("6. Formulae or rules", f"Collect the standard formulae or rules for {t} from the prescribed textbook. Beside each one, record what every symbol means and the conditions under which the relation is valid."),
        ("7. Diagrams and representations", f"If {t} uses diagrams, graphs, structures or flow charts, learn what each labelled part represents and how the representation communicates the underlying concept."),
        ("8. Standard examples", f"Study at least two textbook examples of {t}: one that demonstrates the basic method and another that changes the wording or conditions. The second type checks whether the concept is understood rather than memorised."),
        ("9. Numerical method", f"For numerical questions on {t}, identify the given data, the required quantity, the governing relation, the substitution and the final unit. Keep the working visible so an error can be located."),
        ("10. Theory method", f"For theory questions on {t}, begin with the definition or principle, explain the mechanism or reasoning, state relevant conditions and finish with the required consequence or example."),
        ("11. Classification", f"If {t} contains different types or cases, make a comparison using the same criteria for every type: definition, distinguishing condition, behaviour, formula and application."),
        ("12. Important conditions", f"Many mistakes in {t} occur when a rule is applied outside its conditions. Record assumptions, limiting cases and special cases beside the relevant rule during revision."),
        ("13. Graphs and trends", f"When {t} involves a graph, read the axes and units first. Then identify the trend, slope, intercept, turning point or other quantity actually required by the question."),
        ("14. Applications", f"Connect {t} to the standard applications given in the prescribed course. Applications should reinforce the concept rather than replace its formal definition."),
        ("15. Common misconceptions", f"Separate genuine principles of {t} from shortcuts that work only in a particular question pattern. If a statement has conditions, learn those conditions with the statement."),
        ("16. Common errors", f"During revision of {t}, check signs, units, symbols, powers, brackets, copied values and skipped reasoning. Re-read the original question after reaching an answer."),
        ("17. Comparison questions", f"For comparison questions involving {t}, use parallel headings so both ideas are judged by the same criteria. This prevents mixing properties from unrelated concepts."),
        ("18. Worked-solution checklist", f"A complete {t} solution should show the relevant principle, the information used, the logical or mathematical steps, the final result and a verification when appropriate."),
        ("19. Exam presentation", f"Keep notation clear, label diagrams, write units and avoid unexplained jumps. A correct answer is easier to award when the reasoning can be followed from the first step to the conclusion."),
        ("20. One-minute revision", f"At the end of a {t} revision session, recall the formal definition, three important terms, the main rule or relationship, one application and one common mistake without looking at the notes."),
    ]



def _build_topic_quiz(topic, sections, count=20):
    """Build a real, repeatable MCQ bank from the displayed source sections.

    The bank never invents answer facts: every option is an exact statement from
    another lesson section, and the correct option is the statement belonging to
    the named section. If fewer than four distinct sections exist, the quiz is
    intentionally withheld rather than producing an unreliable answer key.
    """
    clean_sections=[]; seen=set()
    for heading, body in sections or []:
        heading=re.sub(r'^\d+\.\s*','',str(heading or '')).strip()
        body=re.sub(r'\s+',' ',str(body or '')).strip()
        key=re.sub(r'\W+','',body.casefold())
        if heading and body and key and key not in seen:
            seen.add(key); clean_sections.append((heading,body))
    if len(clean_sections)<4:
        return []

    import random
    rng=random.Random(hashlib.sha1(f'{topic}|quiz-v10'.encode('utf-8')).hexdigest())
    stems=[
        "Which statement belongs to the lesson point '{heading}'?",
        "Which statement is directly associated with '{heading}'?",
        "For {topic}, which statement matches '{heading}'?",
        "Which lesson statement describes '{heading}'?",
        "Which statement is the best source-backed match for '{heading}'?",
    ]
    questions=[]
    total=max(1,min(int(count or 20),20))
    for qidx in range(total):
        target_index=qidx % len(clean_sections)
        heading,correct=clean_sections[target_index]
        pool=[body for i,(_,body) in enumerate(clean_sections) if i!=target_index]
        rng.shuffle(pool)
        options=[correct]+pool[:3]
        # If source sections are unusually repetitive, find more unique distractors.
        if len({re.sub(r'\W+','',x.casefold()) for x in options})<4:
            continue
        rng.shuffle(options)
        answer=options.index(correct)
        stem=stems[qidx % len(stems)].format(heading=heading,topic=topic)
        questions.append(_q(stem,options,answer))
    return questions if len(questions)>=min(total,4) else []


def resource_content(resource):
    """Return detailed, topic-aware content for video, notes, quiz and practice resources."""
    topic = str(resource["topic"]).strip()
    key = topic.casefold()
    data = RESOURCE_LIBRARY.get(key, _generic_resource(topic, resource["subject"]))
    if key in RESOURCE_ENHANCEMENTS:
        data = dict(data)
        data.update(RESOURCE_ENHANCEMENTS[key])
    data = dict(data)
    data["verified"] = False
    if key in DETAILED_NOTES:
        data["sections"] = DETAILED_NOTES[key]
        data["verified"] = True
        data["source_title"] = data.get("source_title") or "Learn4All curated classroom reference"
        data["source_note"] = data.get("source_note") or "Verified curated classroom content for this topic."
    else:
        dynamic = _dynamic_topic_notes(topic, resource["subject"])
        if dynamic and dynamic.get("verified"):
            data.update(dynamic)
            data["sections"] = dynamic["sections"]
            data["verified"] = True
        else:
            # Never present generic study advice as factual topic knowledge.
            # The resource remains visible, but factual notes/quiz/video are withheld
            # until a sufficiently relevant source is available.
            data["sections"] = []
            data["quiz"] = []
            data["video"] = []
            data["video_bodies"] = []
            data["source_title"] = "Verified topic source unavailable"
            data["source_note"] = "Learn4All could not verify a sufficiently relevant source for this topic and subject. Factual notes, quiz and video are withheld instead of showing unrelated information."

    # Always rebuild the quiz from the exact lesson sections currently shown.
    # This fixes unknown-topic resources whose old catalog quiz contained only
    # generic/repeated questions and guarantees a working 20-question bank.
    topic_quiz = _build_topic_quiz(topic, data.get("sections", []), 20) if data.get("verified") else []
    if topic_quiz:
        data["quiz"] = topic_quiz
    elif not data.get("verified"):
        data["quiz"] = []
    # Keep the chapter navigation synchronized with the actual visual lesson.
    if data.get("slides"):
        data["video"] = [slide[0] for slide in data["slides"]]
        data["video_bodies"] = [" ".join(slide[1]) for slide in data["slides"]]
    elif data.get("sections") and data.get("verified"):
        # Unknown topics may not have a pre-rendered MP4. Build a topic-specific
        # interactive lesson from the same verified notes.
        groups = [data["sections"][i:i+3] for i in range(0, len(data["sections"]), 3)]
        groups = groups[:8]
        data["video"] = [f"{topic}: Chapter {i+1}" for i, _ in enumerate(groups)]
        data["video_bodies"] = [" ".join(body for _, body in group)[:1000] for group in groups]
    return data


@app.route("/resources")
@login_required
def resources():
    db = get_db()
    subject = request.args.get("subject", "").strip()
    category = request.args.get("category", "").strip()
    topic = request.args.get("topic", "").strip()

    query = "SELECT * FROM resources WHERE 1=1"
    params = []
    if subject:
        query += " AND LOWER(subject) = LOWER(?)"
        params.append(subject)
    if category:
        query += " AND LOWER(category) = LOWER(?)"
        params.append(category)
    if topic:
        # Case-insensitive exact topic matching so links/searches like
        # "geometry" also match a catalog topic stored as "Geometry".
        query += " AND LOWER(topic) LIKE LOWER(?)"
        params.append(f"%{topic}%")

    rows = db.execute(
        query + " ORDER BY subject, topic, category, id",
        params,
    ).fetchall()

    # A topic filter is always actionable: if the catalog has never seen the
    # topic before, create a self-contained four-category bundle on demand.
    # This prevents an empty library when a learner enters a new assessment
    # topic such as Thermodynamics.
    if topic and not rows:
        ensure_resource_bundle(db, subject or "General", topic)
        db.commit()
        rows = db.execute(
            query + " ORDER BY subject, topic, category, id",
            params,
        ).fetchall()

    subjects = [
        r["subject"]
        for r in db.execute(
            "SELECT DISTINCT subject FROM resources ORDER BY subject"
        ).fetchall()
    ]
    categories = ["video", "notes", "quiz", "practice"]
    return render_template(
        "resources.html",
        resources=rows,
        subjects=subjects,
        categories=categories,
        selected_subject=subject,
        selected_category=category,
        selected_topic=topic,
    )



@app.route("/resource/<int:resource_id>")
@login_required
def resource_detail(resource_id):
    db = get_db()
    resource = db.execute("SELECT * FROM resources WHERE id = ?", (resource_id,)).fetchone()
    if not resource:
        flash("That resource could not be found.", "warning")
        return redirect(url_for("resources"))
    content = resource_content(resource)
    video_slug = re.sub(r"[^a-z0-9]+", "-", str(resource["topic"]).strip().casefold()).strip("-")
    video_path = os.path.join(BASE_DIR, "static", "videos", f"{video_slug}.mp4")
    video_url = url_for("static", filename=f"videos/{video_slug}.mp4") if os.path.exists(video_path) else None
    if not video_url and resource["category"] == "video":
        video_url = _dynamic_video_path(resource["topic"], content.get("sections", []))
    return render_template(
        "resource.html",
        resource=resource,
        content=content,
        video_url=video_url,
    )


@app.route("/api/resources/<int:resource_id>")
@login_required
def resource_api(resource_id):
    """Expose resource metadata and lesson content for the frontend/demo."""
    db = get_db()
    resource = db.execute("SELECT * FROM resources WHERE id = ?", (resource_id,)).fetchone()
    if not resource:
        return jsonify({"error": "Resource not found"}), 404
    return jsonify({"resource": dict(resource), "content": resource_content(resource)})


@app.route("/report")
@role_required("student")
def report():
    m = student_metrics(g.user["id"])
    student = Student(
        g.user["id"],
        g.user["name"],
        [x.strip() for x in (g.user["accessibility_needs"] or "").split(",") if x.strip()],
    )
    for row in m["assessments"]:
        student.add_assessment(Assessment(row["subject"], row["topic"], row["score"], row["max_score"]))
    db = get_db()
    catalog = db.execute("SELECT * FROM resources ORDER BY id").fetchall()
    recommender = ResourceRecommender([
        Resource(r["id"], r["title"], r["subject"], r["topic"], r["category"], bool(r["accessible"]))
        for r in catalog
    ])
    generated_report = LearnerReport(student, recommender).generate()
    return render_template("report.html", metrics=m, user=g.user, generated_report=generated_report)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        needs = request.form.get("accessibility_needs", "").strip()
        if len(name) < 2:
            flash("Please enter a valid name.", "danger")
        else:
            db.execute(
                "UPDATE users SET name=?, accessibility_needs=? WHERE id=?",
                (name, needs, g.user["id"]),
            )
            db.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
    return render_template("profile.html", user=g.user)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        flash("Your interface preferences are saved for this prototype.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", user=g.user)


@app.route("/teacher")
@role_required("teacher")
def teacher_dashboard():
    db = get_db()
    students = db.execute(
        "SELECT * FROM users WHERE role='student' ORDER BY name"
    ).fetchall()

    student_cards = []
    topic_counts = {}
    total_assessments = 0
    for s in students:
        m = student_metrics(s["id"])
        total_assessments += len(m["assessments"])
        for w in m["weak"]:
            topic_counts[w["topic"]] = topic_counts.get(w["topic"], 0) + 1
        student_cards.append(
            {
                "id": s["id"],
                "name": s["name"],
                "email": s["email"],
                "overall": m["overall"],
                "weak": len(m["weak"]),
                "strengths": len(m["strengths"]),
                "assessments": len(m["assessments"]),
            }
        )

    domain_students = []
    for s in students:
        domain = Student(s["id"], s["name"])
        for row in db.execute("SELECT * FROM assessments WHERE student_id=?", (s["id"],)).fetchall():
            domain.add_assessment(Assessment(row["subject"], row["topic"], row["score"], row["max_score"]))
        domain_students.append(domain)
    class_summary = ClassSummary(domain_students).generate()
    class_avg = class_summary["class_average"]
    common_weak = class_summary["common_weak_topics"]
    return render_template(
        "teacher.html",
        students=student_cards,
        class_avg=class_avg,
        common_weak=common_weak,
        total_assessments=total_assessments,
    )


@app.route("/teacher/student/<int:student_id>")
@role_required("teacher")
def teacher_student(student_id):
    db = get_db()
    student = db.execute(
        "SELECT * FROM users WHERE id=? AND role='student'",
        (student_id,),
    ).fetchone()
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("teacher_dashboard"))
    m = student_metrics(student_id)
    return render_template(
        "teacher_student.html",
        student=student,
        metrics=m,
    )


@app.route("/api/student-progress/<int:student_id>")
@role_required("teacher")
def api_student_progress(student_id):
    db = get_db()
    student = db.execute(
        "SELECT id,name FROM users WHERE id=? AND role='student'",
        (student_id,),
    ).fetchone()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    m = student_metrics(student_id)
    return jsonify(
        {
            "student": dict(student),
            "overall": m["overall"],
            "subjects": m["subject_avg"],
            "weak_topics": m["weak"],
            "strengths": m["strengths"],
        }
    )


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Database initialized.")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
