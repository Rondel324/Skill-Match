"""
Skill Match - Creative Peer Tutoring Platform (Flask web version)

Run locally:   pip install -r requirements.txt && python app.py
Production:    gunicorn app:app   (set SECRET_KEY and DATABASE_URL, see README.md)
"""
import os
import secrets
from datetime import datetime, timezone
from functools import wraps
from io import BytesIO
from zoneinfo import ZoneInfo

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   send_file, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageOps
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COLLEGE_PROGRAMS = {
    "Computer Studies & IT": ["BS Computer Science", "BS Information Technology", "BS Information Systems", "BS Cybersecurity", "BS Data Science"],
    "Engineering": ["BS Civil Engineering", "BS Computer Engineering", "BS Electrical Engineering", "BS Mechanical Engineering", "BS Industrial Engineering"],
    "Business & Management": ["BS Business Administration", "BS Accountancy", "BS Marketing Management", "BS Financial Management", "BS Entrepreneurship"],
    "Health Sciences": ["BS Nursing", "BS Medical Technology", "BS Pharmacy", "BS Physical Therapy", "BS Psychology"],
    "Sciences & Math": ["BS Biology", "BS Chemistry", "BS Physics", "BS Mathematics", "BS Environmental Science"],
    "Arts & Social Sciences": ["BA Communication", "BA Political Science", "BA English Literature", "BA Journalism", "BA Sociology"],
    "Education": ["Bachelor of Elementary Education", "Bachelor of Secondary Education", "Bachelor of Special Needs Education"],
}
ALL_PROGRAMS = [p for progs in COLLEGE_PROGRAMS.values() for p in progs]
YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year+"]
AVATAR_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#14b8a6", "#f59e0b", "#3b82f6", "#10b981", "#ef4444"]
APP_TZ = ZoneInfo(os.environ.get("APP_TZ", "Asia/Manila"))


def database_url():
    url = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(BASE_DIR, "skill_match.db")
    if url.startswith("postgres://"):  # some hosts still hand out the old scheme
        url = url.replace("postgres://", "postgresql://", 1)
    return url


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # correct URLs behind a proxy/load balancer
app.config.update(
    # Every server instance MUST share the same SECRET_KEY so logins work on all of them.
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    SQLALCHEMY_DATABASE_URI=database_url(),
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
)
if app.config["SECRET_KEY"] == "dev-only-change-me":
    print("WARNING: using the default SECRET_KEY. Set SECRET_KEY in production.")

db = SQLAlchemy(app)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    course = db.Column(db.String(120), nullable=False)
    year = db.Column(db.String(30), nullable=False)
    skills = db.Column(db.Text, default="", nullable=False)
    needs = db.Column(db.Text, default="", nullable=False)
    availability = db.Column(db.String(200), default="Flexible", nullable=False)
    avatar_data = db.deferred(db.Column(db.LargeBinary))  # photo lives in the DB, not on one server's disk
    avatar_v = db.Column(db.Integer, default=0, nullable=False)

    @property
    def skill_list(self):
        return [s.strip() for s in self.skills.split(",") if s.strip()]

    @property
    def need_list(self):
        return [s.strip() for s in self.needs.split(",") if s.strip()]

    @property
    def has_avatar(self):
        return self.avatar_v > 0

    @property
    def initials(self):
        return "".join(p[0] for p in self.name.split()[:2]).upper() or "?"

    @property
    def color(self):
        return AVATAR_COLORS[sum(ord(c) for c in self.name) % len(AVATAR_COLORS)]


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    user = db.relationship("User")
    likes = db.relationship("Like", cascade="all, delete-orphan")
    comments = db.relationship("Comment", order_by="Comment.id", cascade="all, delete-orphan")

    @property
    def liked_ids(self):
        return {l.user_id for l in self.likes}


class Like(db.Model):
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    user = db.relationship("User")


class HelpRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    schedule = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    sender = db.relationship("User", foreign_keys=[from_id])
    receiver = db.relationship("User", foreign_keys=[to_id])


with app.app_context():
    db.create_all()


# ---------- Security / session helpers ----------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals.update(csrf_token=csrf_token, program_groups=COLLEGE_PROGRAMS, programs=ALL_PROGRAMS, years=YEARS)


@app.before_request
def load_user_and_check_csrf():
    g.user = db.session.get(User, session["uid"]) if "uid" in session else None
    if request.method == "POST":
        sent, expected = request.form.get("_csrf", ""), session.get("_csrf", "")
        if not expected or not secrets.compare_digest(sent, expected):
            abort(400, "Invalid or missing form token. Please go back and try again.")


@app.context_processor
def inject_globals():
    pending = 0
    if g.get("user"):
        pending = HelpRequest.query.filter_by(to_id=g.user.id, status="Pending").count()
    return {"me": g.get("user"), "pending_count": pending}


@app.template_filter("localtime")
def localtime(dt):
    return dt.replace(tzinfo=timezone.utc).astimezone(APP_TZ).strftime("%b %d, %I:%M %p")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth"))
        return view(*args, **kwargs)
    return wrapped


# ---------- Auth ----------
@app.route("/")
def index():
    return redirect(url_for("feed" if g.user else "auth"))


@app.route("/auth")
def auth():
    if g.user:
        return redirect(url_for("feed"))
    return render_template("auth.html", tab=request.args.get("tab", "login"))


@app.post("/login")
def login():
    email = request.form.get("email", "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, request.form.get("password", "")):
        session.clear()
        session["uid"] = user.id
        return redirect(url_for("feed"))
    flash("Invalid email or password.", "error")
    return redirect(url_for("auth"))


@app.post("/register")
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    course = request.form.get("course", "")
    year = request.form.get("year", "")
    back = redirect(url_for("auth", tab="register"))
    if not name or not email or not password:
        flash("Please fill in all fields.", "error")
        return back
    if "@" not in email:
        flash("Please enter a valid email address.", "error")
        return back
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return back
    if course not in ALL_PROGRAMS or year not in YEARS:
        flash("Please choose a valid program and year level.", "error")
        return back
    if User.query.filter_by(email=email).first():
        flash("An account already exists with this email.", "error")
        return back
    user = User(name=name[:120], email=email, password_hash=generate_password_hash(password),
                course=course, year=year)
    db.session.add(user)
    db.session.commit()
    session.clear()
    session["uid"] = user.id
    flash("Account created successfully!", "success")
    return redirect(url_for("feed"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth"))


# ---------- Campus feed ----------
@app.route("/feed")
@login_required
def feed():
    posts = Post.query.order_by(Post.id.desc()).limit(100).all()
    return render_template("feed.html", posts=posts, active="feed")


@app.post("/post")
@login_required
def create_post():
    content = request.form.get("content", "").strip()
    if content:
        db.session.add(Post(user_id=g.user.id, content=content[:2000]))
        db.session.commit()
    return redirect(url_for("feed"))


@app.post("/post/<int:post_id>/like")
@login_required
def toggle_like(post_id):
    db.get_or_404(Post, post_id)
    like = db.session.get(Like, (post_id, g.user.id))
    if like:
        db.session.delete(like)
    else:
        db.session.add(Like(post_id=post_id, user_id=g.user.id))
    db.session.commit()
    return redirect(url_for("feed", _anchor=f"post-{post_id}"))


@app.post("/post/<int:post_id>/comment")
@login_required
def add_comment(post_id):
    db.get_or_404(Post, post_id)
    text = request.form.get("text", "").strip()
    if text:
        db.session.add(Comment(post_id=post_id, user_id=g.user.id, text=text[:1000]))
        db.session.commit()
    return redirect(url_for("feed", _anchor=f"post-{post_id}"))


# ---------- Find tutors ----------
@app.route("/find")
@login_required
def find():
    q = request.args.get("q", "").strip().lower()
    program = request.args.get("program", "All Programs")
    users = User.query.filter(User.id != g.user.id)
    if program in ALL_PROGRAMS:
        users = users.filter_by(course=program)
    students = []
    for u in users.order_by(User.name):
        haystack = [u.name.lower()] + [s.lower() for s in u.skill_list + u.need_list]
        if not q or any(q in h for h in haystack):
            students.append(u)
    return render_template("find.html", students=students, q=request.args.get("q", ""),
                           program=program, active="find")


@app.route("/request/<int:tutor_id>", methods=["GET", "POST"])
@login_required
def request_help(tutor_id):
    tutor = db.get_or_404(User, tutor_id)
    if tutor.id == g.user.id:
        abort(400, "You can't send a request to yourself.")
    if request.method == "POST":
        schedule = request.form.get("schedule", "").strip()
        message = request.form.get("message", "").strip()
        if not schedule or not message:
            flash("Please fill in the schedule and message.", "error")
            return redirect(url_for("request_help", tutor_id=tutor.id))
        db.session.add(HelpRequest(from_id=g.user.id, to_id=tutor.id,
                                   schedule=schedule[:200], message=message[:2000]))
        db.session.commit()
        flash("Help request sent!", "success")
        return redirect(url_for("requests_page"))
    return render_template("request_form.html", tutor=tutor, active="find")


# ---------- Requests ----------
@app.route("/requests")
@login_required
def requests_page():
    received = HelpRequest.query.filter_by(to_id=g.user.id).order_by(HelpRequest.id.desc()).all()
    sent = HelpRequest.query.filter_by(from_id=g.user.id).order_by(HelpRequest.id.desc()).all()
    return render_template("requests.html", received=received, sent=sent, active="requests")


@app.post("/requests/<int:req_id>/<action>")
@login_required
def respond_request(req_id, action):
    if action not in ("accept", "decline"):
        abort(404)
    req = db.get_or_404(HelpRequest, req_id)
    if req.to_id != g.user.id:
        abort(403)
    if req.status == "Pending":
        req.status = "Accepted" if action == "accept" else "Declined"
        db.session.commit()
    return redirect(url_for("requests_page"))


# ---------- Profile ----------
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name cannot be empty.", "error")
            return redirect(url_for("profile"))
        course, year = request.form.get("course", ""), request.form.get("year", "")
        if course not in ALL_PROGRAMS or year not in YEARS:
            flash("Please choose a valid program and year level.", "error")
            return redirect(url_for("profile"))
        u = g.user
        u.name, u.course, u.year = name[:120], course, year
        u.skills = request.form.get("skills", "").strip()[:500]
        u.needs = request.form.get("needs", "").strip()[:500]
        u.availability = request.form.get("availability", "").strip()[:200] or "Flexible"
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", active="profile")


@app.post("/profile/avatar")
@login_required
def upload_avatar():
    file = request.files.get("photo")
    if not file or not file.filename:
        flash("Please choose an image first.", "error")
        return redirect(url_for("profile"))
    try:
        img = Image.open(file.stream)
        img = ImageOps.exif_transpose(img).convert("RGB")
        img = ImageOps.fit(img, (256, 256))
        buf = BytesIO()
        img.save(buf, "JPEG", quality=85)
    except Exception:
        flash("That file doesn't look like a valid image.", "error")
        return redirect(url_for("profile"))
    g.user.avatar_data = buf.getvalue()
    g.user.avatar_v += 1
    db.session.commit()
    flash("Profile photo updated.", "success")
    return redirect(url_for("profile"))


@app.route("/avatar/<int:user_id>")
def avatar(user_id):
    user = db.get_or_404(User, user_id)
    if not user.has_avatar or not user.avatar_data:
        abort(404)
    return send_file(BytesIO(user.avatar_data), mimetype="image/jpeg", max_age=86400)


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
