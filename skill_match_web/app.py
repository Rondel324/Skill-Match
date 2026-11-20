import hashlib
import json
import os
import shutil
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "skill_match_data.json")
AVATAR_DIR = os.path.join(BASE_DIR, "avatars")

# ---------- Theme ----------
INDIGO = "#4f46e5"
INDIGO_DARK = "#3730a3"
INDIGO_LIGHT = "#eef2ff"
PINK = "#ec4899"
PINK_LIGHT = "#fce7f3"
BG = "#f5f3ff"
WHITE = "#ffffff"
GRAY = "#6b7280"
GRAY_LIGHT = "#f3f4f6"
GREEN = "#059669"
RED = "#e11d48"
AMBER_BG, AMBER_FG = "#fef3c7", "#92400e"
GREEN_BG, GREEN_FG = "#d1fae5", "#065f46"
RED_BG, RED_FG = "#ffe4e6", "#9f1239"

FONT = ("Segoe UI", 10)
FONT_B = ("Segoe UI", 10, "bold")
FONT_SM = ("Segoe UI", 9)
FONT_SM_B = ("Segoe UI", 9, "bold")
FONT_H1 = ("Segoe UI", 18, "bold")
FONT_H2 = ("Segoe UI", 14, "bold")

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


# ---------- Storage ----------
class Database:
    """Tiny JSON-file database (replaces localStorage)."""

    def __init__(self, path=DATA_FILE):
        self.path = path
        self.data = {"users": [], "posts": [], "requests": [], "current_user_id": None}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    @property
    def users(self):
        return self.data["users"]

    @property
    def posts(self):
        return self.data["posts"]

    @property
    def requests(self):
        return self.data["requests"]

    def get_user(self, user_id):
        return next((u for u in self.users if u["id"] == user_id), None)


def new_id():
    return str(int(datetime.now().timestamp() * 1000000))


def hash_password(password, salt):
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# ---------- UI helpers ----------
def make_button(parent, text, command, bg=INDIGO, fg=WHITE, **kw):
    hover = {INDIGO: INDIGO_DARK, PINK: "#db2777", GREEN: "#047857", RED: "#be123c"}.get(bg, bg)
    b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=hover,
                  activeforeground=fg, relief="flat", bd=0, padx=kw.pop("padx", 12),
                  pady=kw.pop("pady", 5), font=kw.pop("font", FONT_B), cursor="hand2", **kw)
    return b


def make_label(parent, text, font=FONT, fg="#1f2937", bg=WHITE, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)


def card(parent, **kw):
    return tk.Frame(parent, bg=WHITE, highlightbackground="#e0e7ff", highlightthickness=1, **kw)


def badge(parent, text, bg, fg):
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=("Segoe UI", 8, "bold"), padx=6, pady=1)


def initials(name):
    parts = name.split()
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def color_for(name):
    palette = ["#6366f1", "#8b5cf6", "#ec4899", "#14b8a6", "#f59e0b", "#3b82f6", "#10b981", "#ef4444"]
    return palette[sum(ord(c) for c in name) % len(palette)]


class Avatar(tk.Canvas):
    """Round avatar: uploaded photo (needs Pillow) or colored initials."""

    def __init__(self, parent, user_name, avatar_path="", size=40, bg=WHITE):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0)
        self._img = None
        if avatar_path and HAS_PIL and os.path.exists(avatar_path):
            try:
                img = Image.open(avatar_path).convert("RGB").resize((size, size))
                from PIL import ImageDraw
                mask = Image.new("L", (size, size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
                img.putalpha(mask)
                self._img = ImageTk.PhotoImage(img)
                self.create_image(size // 2, size // 2, image=self._img)
                return
            except Exception:
                pass
        self.create_oval(1, 1, size - 1, size - 1, fill=color_for(user_name), outline=INDIGO)
        self.create_text(size // 2, size // 2, text=initials(user_name), fill=WHITE,
                         font=("Segoe UI", max(8, size // 3), "bold"))


class ScrollFrame(tk.Frame):
    """Vertically scrollable frame; put widgets into `.inner`."""

    def __init__(self, parent, bg=BG):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="n")
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_wheel())

    def _on_resize(self, event):
        self.canvas.coords(self._win, event.width // 2, 0)
        self.canvas.itemconfigure(self._win, width=min(event.width, 1000))

    def _bind_wheel(self):
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def _unbind_wheel(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120) or (-1 if event.delta > 0 else 1), "units")


def field(parent, label, widget_factory, bg=WHITE):
    wrap = tk.Frame(parent, bg=bg)
    tk.Label(wrap, text=label.upper(), font=("Segoe UI", 8, "bold"), fg=GRAY, bg=bg).pack(anchor="w")
    w = widget_factory(wrap)
    w.pack(fill="x", pady=(2, 0), ipady=4)
    return wrap, w


# ---------- Main application ----------
class SkillMatchApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Skill Match - Creative Peer Tutoring Platform")
        self.geometry("1000x720")
        self.minsize(760, 560)
        self.configure(bg=BG)
        self.db = Database()
        self.current_user = self.db.get_user(self.db.data.get("current_user_id"))
        self.content = None
        self.nav_buttons = {}
        self.request_badge = None

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self._build_navbar()
        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True)

        if self.current_user:
            self.show_section("feed")
        else:
            self.show_section("auth")

    # ----- Navigation -----
    def _build_navbar(self):
        self.nav = tk.Frame(self, bg=WHITE, highlightbackground="#e0e7ff", highlightthickness=1)
        self.nav.pack(fill="x")
        tk.Label(self.nav, text="🎓  Skill Match", font=("Segoe UI", 15, "bold"), fg=INDIGO, bg=WHITE).pack(side="left", padx=14, pady=10)
        self.nav_links = tk.Frame(self.nav, bg=WHITE)

        def nav_btn(key, text):
            b = tk.Button(self.nav_links, text=text, command=lambda: self.show_section(key), relief="flat",
                          bd=0, bg=WHITE, fg=GRAY, activebackground=INDIGO_LIGHT, font=FONT_B, padx=10, pady=4, cursor="hand2")
            b.pack(side="left", padx=2)
            self.nav_buttons[key] = b
            return b

        nav_btn("feed", "🏠 Feed")
        nav_btn("find", "👥 Find Tutors")
        req_btn = nav_btn("requests", "🤝 Requests")
        self.request_badge = tk.Label(self.nav_links, text="0", bg=PINK, fg=WHITE, font=("Segoe UI", 8, "bold"), padx=5)
        nav_btn("profile", "Profile")
        make_button(self.nav_links, "Logout", self.logout, bg=PINK, pady=3).pack(side="left", padx=(8, 0))

    def _update_nav(self, active):
        if self.current_user:
            self.nav_links.pack(side="right", padx=10)
        else:
            self.nav_links.pack_forget()
        for key, btn in self.nav_buttons.items():
            btn.configure(fg=INDIGO if key == active else GRAY, bg=INDIGO_LIGHT if key == active else WHITE)
        self._update_badge()

    def _update_badge(self):
        if not self.current_user:
            return
        pending = sum(1 for r in self.db.requests if r["toId"] == self.current_user["id"] and r["status"] == "Pending")
        btn = self.nav_buttons["requests"]
        btn.configure(text=f"🤝 Requests ({pending})" if pending else "🤝 Requests")

    def show_section(self, name):
        for child in self.body.winfo_children():
            child.destroy()
        self._update_nav(name)
        {"auth": self.build_auth, "feed": self.build_feed, "find": self.build_find,
         "requests": self.build_requests, "profile": self.build_profile}[name]()

    # ----- Authentication -----
    def build_auth(self):
        outer = tk.Frame(self.body, bg=BG)
        outer.pack(expand=True)
        box = card(outer)
        box.pack(pady=30, ipadx=24, ipady=18)

        make_label(box, "Welcome to Skill Match!", font=FONT_H2, fg="#312e81").pack(pady=(14, 0))
        make_label(box, "Connect, share skills, and ace your courses together.", font=FONT_SM, fg=GRAY).pack(pady=(2, 12))

        tabs = tk.Frame(box, bg=GRAY_LIGHT)
        tabs.pack(fill="x", padx=24)
        forms = tk.Frame(box, bg=WHITE)
        forms.pack(fill="x", padx=24, pady=14)

        login_f, reg_f = tk.Frame(forms, bg=WHITE), tk.Frame(forms, bg=WHITE)
        tab_btns = {}

        def switch(which):
            login_f.pack_forget()
            reg_f.pack_forget()
            (login_f if which == "login" else reg_f).pack(fill="x")
            for k, b in tab_btns.items():
                b.configure(bg=WHITE if k == which else GRAY_LIGHT, fg=INDIGO if k == which else GRAY)

        for key, text in (("login", "Login"), ("register", "Register")):
            b = tk.Button(tabs, text=text, command=lambda k=key: switch(k), relief="flat", bd=0, font=FONT_B, pady=6, cursor="hand2")
            b.pack(side="left", expand=True, fill="x", padx=2, pady=2)
            tab_btns[key] = b

        # Login form
        le = tk.StringVar()
        lp = tk.StringVar()
        field(login_f, "Email", lambda p: tk.Entry(p, textvariable=le, relief="solid", bd=1, width=38))[0].pack(fill="x", pady=4)
        field(login_f, "Password", lambda p: tk.Entry(p, textvariable=lp, show="•", relief="solid", bd=1))[0].pack(fill="x", pady=4)
        make_button(login_f, "Login", lambda: self.handle_login(le.get(), lp.get()), pady=8).pack(fill="x", pady=(10, 0))

        # Register form
        rn, re_, rp = tk.StringVar(), tk.StringVar(), tk.StringVar()
        rc, ry = tk.StringVar(value=ALL_PROGRAMS[0]), tk.StringVar(value=YEARS[0])
        field(reg_f, "Full Name", lambda p: tk.Entry(p, textvariable=rn, relief="solid", bd=1))[0].pack(fill="x", pady=4)
        field(reg_f, "Email", lambda p: tk.Entry(p, textvariable=re_, relief="solid", bd=1))[0].pack(fill="x", pady=4)
        field(reg_f, "Password", lambda p: tk.Entry(p, textvariable=rp, show="•", relief="solid", bd=1))[0].pack(fill="x", pady=4)
        field(reg_f, "College Program", lambda p: ttk.Combobox(p, textvariable=rc, values=ALL_PROGRAMS, state="readonly"))[0].pack(fill="x", pady=4)
        field(reg_f, "Year Level", lambda p: ttk.Combobox(p, textvariable=ry, values=YEARS, state="readonly"))[0].pack(fill="x", pady=4)
        make_button(reg_f, "Create Account",
                    lambda: self.handle_register(rn.get(), re_.get(), rp.get(), rc.get(), ry.get()), pady=8).pack(fill="x", pady=(10, 0))

        switch("login")

    def handle_register(self, name, email, password, course, year):
        name, email = name.strip(), email.strip().lower()
        if not name or not email or not password:
            messagebox.showwarning("Missing info", "Please fill in all fields.")
            return
        if "@" not in email:
            messagebox.showwarning("Invalid email", "Please enter a valid email address.")
            return
        if any(u["email"] == email for u in self.db.users):
            messagebox.showwarning("Account exists", "Account already exists with this email.")
            return
        salt = os.urandom(8).hex()
        user = {
            "id": new_id(), "name": name, "email": email, "salt": salt,
            "password": hash_password(password, salt), "course": course, "year": year,
            "skills": [], "needs": [], "availability": "Flexible", "avatar": "",
        }
        self.db.users.append(user)
        self.current_user = user
        self.db.data["current_user_id"] = user["id"]
        self.db.save()
        messagebox.showinfo("Welcome", "Account created successfully!")
        self.show_section("feed")

    def handle_login(self, email, password):
        email = email.strip().lower()
        for u in self.db.users:
            if u["email"] == email and u["password"] == hash_password(password, u["salt"]):
                self.current_user = u
                self.db.data["current_user_id"] = u["id"]
                self.db.save()
                self.show_section("feed")
                return
        messagebox.showerror("Login failed", "Invalid email or password.")

    def logout(self):
        self.current_user = None
        self.db.data["current_user_id"] = None
        self.db.save()
        self.show_section("auth")

    # ----- Campus Feed -----
    def build_feed(self):
        sf = ScrollFrame(self.body)
        sf.pack(fill="both", expand=True)
        wrap = tk.Frame(sf.inner, bg=BG)
        wrap.pack(fill="x", padx=60, pady=14)

        # Create-post box
        box = card(wrap)
        box.pack(fill="x", pady=(0, 14))
        head = tk.Frame(box, bg=WHITE)
        head.pack(fill="x", padx=14, pady=(12, 6))
        Avatar(head, self.current_user["name"], self.current_user.get("avatar", ""), 40).pack(side="left")
        make_label(head, self.current_user["name"], font=FONT_B).pack(side="left", padx=10)
        text = tk.Text(box, height=3, wrap="word", relief="solid", bd=1, font=FONT)
        text.pack(fill="x", padx=14)
        foot = tk.Frame(box, bg=WHITE)
        foot.pack(fill="x", padx=14, pady=10)
        make_label(foot, "Be helpful & respectful ✨", font=FONT_SM, fg="#9ca3af").pack(side="left")
        make_button(foot, "Post to Feed", lambda: self.create_post(text.get("1.0", "end"))).pack(side="right")

        # Posts
        if not self.db.posts:
            tk.Label(wrap, text="No posts in the feed yet. Be the first to share something!", bg=BG, fg="#9ca3af", font=FONT).pack(pady=30)
        for post in self.db.posts:
            self._post_card(wrap, post)

    def _post_card(self, parent, post):
        c = card(parent)
        c.pack(fill="x", pady=6)
        author = self.db.get_user(post["userId"])
        name = author["name"] if author else post["userName"]
        avatar = author.get("avatar", "") if author else ""

        head = tk.Frame(c, bg=WHITE)
        head.pack(fill="x", padx=14, pady=(12, 4))
        Avatar(head, name, avatar, 40).pack(side="left")
        info = tk.Frame(head, bg=WHITE)
        info.pack(side="left", padx=10)
        make_label(info, name, font=FONT_B, fg="#312e81").pack(anchor="w")
        make_label(info, f"{post['userCourse']} • {post['timestamp']}", font=("Segoe UI", 8), fg="#9ca3af").pack(anchor="w")

        tk.Label(c, text=post["content"], bg=WHITE, fg="#374151", font=FONT, justify="left",
                 wraplength=560, anchor="w").pack(fill="x", padx=14, pady=6)

        liked = self.current_user["id"] in post["likes"]
        bar = tk.Frame(c, bg=WHITE)
        bar.pack(fill="x", padx=14, pady=(4, 6))
        tk.Button(bar, text=f"❤ {len(post['likes'])} Likes", relief="flat", bd=0, bg=WHITE,
                  fg=PINK if liked else GRAY, font=FONT_SM_B if liked else FONT_SM, cursor="hand2",
                  command=lambda: self.toggle_like(post["id"])).pack(side="left")
        make_label(bar, f"💬 {len(post['comments'])} Comments", font=FONT_SM, fg=GRAY).pack(side="left", padx=14)

        reply = tk.Frame(c, bg=WHITE)
        reply.pack(fill="x", padx=14, pady=(0, 6))
        entry = tk.Entry(reply, relief="solid", bd=1, font=FONT_SM)
        entry.pack(side="left", fill="x", expand=True, ipady=3)
        entry.bind("<Return>", lambda e: self.add_comment(post["id"], entry.get()))
        make_button(reply, "Reply", lambda: self.add_comment(post["id"], entry.get()), font=FONT_SM_B, pady=2).pack(side="left", padx=(6, 0))

        for cm in post["comments"]:
            cb = tk.Frame(c, bg=GRAY_LIGHT)
            cb.pack(fill="x", padx=14, pady=2)
            tk.Label(cb, text=cm["userName"], bg=GRAY_LIGHT, fg="#312e81", font=FONT_SM_B).pack(anchor="w", padx=8, pady=(4, 0))
            tk.Label(cb, text=cm["text"], bg=GRAY_LIGHT, fg="#4b5563", font=FONT_SM, wraplength=540,
                     justify="left", anchor="w").pack(fill="x", padx=8, pady=(0, 4))
        tk.Frame(c, bg=WHITE, height=8).pack()

    def create_post(self, content):
        content = content.strip()
        if not content:
            return
        u = self.current_user
        self.db.posts.insert(0, {
            "id": new_id(), "userId": u["id"], "userName": u["name"], "userCourse": u["course"],
            "content": content, "timestamp": datetime.now().strftime("%I:%M %p"),
            "likes": [], "comments": [],
        })
        self.db.save()
        self.show_section("feed")

    def toggle_like(self, post_id):
        post = next((p for p in self.db.posts if p["id"] == post_id), None)
        if post:
            uid = self.current_user["id"]
            if uid in post["likes"]:
                post["likes"].remove(uid)
            else:
                post["likes"].append(uid)
            self.db.save()
            self.show_section("feed")

    def add_comment(self, post_id, text):
        text = text.strip()
        post = next((p for p in self.db.posts if p["id"] == post_id), None)
        if post and text:
            post["comments"].append({"userName": self.current_user["name"], "text": text})
            self.db.save()
            self.show_section("feed")

    # ----- Find Tutors -----
    def build_find(self):
        top = card(self.body)
        top.pack(fill="x", padx=20, pady=(14, 8))
        make_label(top, "🔍  Discover Study Partners & Tutors", font=("Segoe UI", 12, "bold"), fg="#312e81").pack(side="left", padx=14, pady=12)
        self.filter_var = tk.StringVar(value="All Programs")
        self.search_var = tk.StringVar()
        ttk.Combobox(top, textvariable=self.filter_var, values=["All Programs"] + ALL_PROGRAMS,
                     state="readonly", width=28).pack(side="right", padx=14)
        tk.Entry(top, textvariable=self.search_var, relief="solid", bd=1, width=26).pack(side="right", padx=4, ipady=3)
        make_label(top, "Search:", font=FONT_SM, fg=GRAY).pack(side="right")

        self.student_area = tk.Frame(self.body, bg=BG)
        self.student_area.pack(fill="both", expand=True)
        self.search_var.trace_add("write", lambda *a: self.render_students())
        self.filter_var.trace_add("write", lambda *a: self.render_students())
        self.render_students()

    def render_students(self):
        for w in self.student_area.winfo_children():
            w.destroy()
        sf = ScrollFrame(self.student_area)
        sf.pack(fill="both", expand=True)

        query = self.search_var.get().lower().strip()
        course = self.filter_var.get()
        students = []
        for u in self.db.users:
            if u["id"] == self.current_user["id"]:
                continue
            if course != "All Programs" and u["course"] != course:
                continue
            hay = [u["name"].lower()] + [s.lower() for s in u["skills"]] + [n.lower() for n in u["needs"]]
            if query and not any(query in h for h in hay):
                continue
            students.append(u)

        if not students:
            tk.Label(sf.inner, text="No students found matching your search.", bg=BG, fg="#9ca3af", font=FONT).pack(pady=40)
            return

        grid = tk.Frame(sf.inner, bg=BG)
        grid.pack(fill="x", padx=14, pady=6)
        cols = 3
        for i in range(cols):
            grid.columnconfigure(i, weight=1, uniform="col")
        for idx, s in enumerate(students):
            c = self._student_card(grid, s)
            c.grid(row=idx // cols, column=idx % cols, padx=6, pady=6, sticky="nsew")

    def _student_card(self, parent, s):
        c = card(parent)
        head = tk.Frame(c, bg=WHITE)
        head.pack(fill="x", padx=12, pady=(12, 4))
        Avatar(head, s["name"], s.get("avatar", ""), 48).pack(side="left")
        info = tk.Frame(head, bg=WHITE)
        info.pack(side="left", padx=8)
        make_label(info, s["name"], font=FONT_B, fg="#312e81").pack(anchor="w")
        tk.Label(info, text=s["course"], bg=WHITE, fg=INDIGO, font=("Segoe UI", 8, "bold"), wraplength=150, justify="left").pack(anchor="w")
        badge(info, s["year"], GRAY_LIGHT, GRAY).pack(anchor="w", pady=2)

        make_label(c, f"Availability: {s.get('availability') or 'Flexible'}", font=FONT_SM, fg=GRAY, wraplength=220, justify="left").pack(anchor="w", padx=12, pady=2)

        for title, items, bg, fg in (("CAN TEACH:", s["skills"], INDIGO_LIGHT, INDIGO_DARK),
                                     ("NEEDS HELP WITH:", s["needs"], PINK_LIGHT, "#9d174d")):
            make_label(c, title, font=("Segoe UI", 8, "bold"), fg="#9ca3af").pack(anchor="w", padx=12, pady=(6, 0))
            row = tk.Frame(c, bg=WHITE)
            row.pack(anchor="w", padx=12)
            if items:
                for it in items:
                    badge(row, it, bg, fg).pack(side="left", padx=(0, 3), pady=1)
            else:
                make_label(row, "None listed", font=("Segoe UI", 8), fg="#9ca3af").pack(side="left")

        make_button(c, "Request Help", lambda: self.open_request_modal(s), font=FONT_SM_B, pady=5).pack(fill="x", padx=12, pady=12)
        return c

    # ----- Help request modal -----
    def open_request_modal(self, tutor):
        win = tk.Toplevel(self)
        win.title("Request Help")
        win.configure(bg=WHITE)
        win.transient(self)
        win.grab_set()
        win.geometry("420x330")

        tk.Label(win, text=f"Request Help from {tutor['name']}", font=FONT_H2, fg="#312e81", bg=WHITE, wraplength=380).pack(pady=(16, 8), padx=20, anchor="w")
        sched = tk.StringVar()
        f1, _ = field(win, "Preferred Schedule / Time", lambda p: tk.Entry(p, textvariable=sched, relief="solid", bd=1))
        f1.pack(fill="x", padx=20, pady=4)
        tk.Label(win, text="MESSAGE / TOPICS TO COVER", font=("Segoe UI", 8, "bold"), fg=GRAY, bg=WHITE).pack(anchor="w", padx=20)
        msg = tk.Text(win, height=5, wrap="word", relief="solid", bd=1, font=FONT)
        msg.pack(fill="x", padx=20, pady=(2, 8))

        def submit():
            if not sched.get().strip() or not msg.get("1.0", "end").strip():
                messagebox.showwarning("Missing info", "Please fill in the schedule and message.", parent=win)
                return
            self.db.requests.append({
                "id": new_id(), "fromId": self.current_user["id"], "fromName": self.current_user["name"],
                "toId": tutor["id"], "toName": tutor["name"], "schedule": sched.get().strip(),
                "message": msg.get("1.0", "end").strip(), "status": "Pending",
            })
            self.db.save()
            messagebox.showinfo("Sent", "Help request sent!", parent=win)
            win.destroy()
            self._update_badge()

        btns = tk.Frame(win, bg=WHITE)
        btns.pack(fill="x", padx=20, pady=6)
        make_button(btns, "Send Request", submit).pack(side="right")
        make_button(btns, "Cancel", win.destroy, bg=GRAY_LIGHT, fg="#111827").pack(side="right", padx=6)

    # ----- Requests -----
    def build_requests(self):
        sf = ScrollFrame(self.body)
        sf.pack(fill="both", expand=True)
        wrap = tk.Frame(sf.inner, bg=BG)
        wrap.pack(fill="x", padx=80, pady=14)
        make_label(wrap, "🤝  Tutoring & Help Requests", font=FONT_H2, fg="#312e81", bg=BG).pack(anchor="w", pady=(0, 10))

        uid = self.current_user["id"]
        received = [r for r in self.db.requests if r["toId"] == uid]
        sent = [r for r in self.db.requests if r["fromId"] == uid]

        for title, items, is_received in (("RECEIVED REQUESTS", received, True), ("SENT REQUESTS", sent, False)):
            box = card(wrap)
            box.pack(fill="x", pady=8)
            make_label(box, title, font=("Segoe UI", 9, "bold"), fg="#9ca3af").pack(anchor="w", padx=14, pady=(12, 6))
            if not items:
                make_label(box, "No incoming requests." if is_received else "No sent requests.", font=FONT_SM, fg="#9ca3af").pack(anchor="w", padx=14, pady=(0, 12))
            for req in items:
                self._request_row(box, req, is_received)

    def _request_row(self, parent, req, is_received):
        row = tk.Frame(parent, bg=GRAY_LIGHT, highlightbackground="#e5e7eb", highlightthickness=1)
        row.pack(fill="x", padx=14, pady=5)
        top = tk.Frame(row, bg=GRAY_LIGHT)
        top.pack(fill="x", padx=10, pady=(8, 2))
        title = f"{req['fromName']} requested help" if is_received else f"Request to {req['toName']}"
        tk.Label(top, text=title, bg=GRAY_LIGHT, fg="#312e81", font=FONT_B).pack(side="left")
        colors = {"Pending": (AMBER_BG, AMBER_FG), "Accepted": (GREEN_BG, GREEN_FG), "Declined": (RED_BG, RED_FG)}[req["status"]]
        badge(top, req["status"], *colors).pack(side="right")
        tk.Label(row, text=f"Schedule: {req['schedule']}", bg=GRAY_LIGHT, fg="#4b5563", font=FONT_SM, anchor="w").pack(fill="x", padx=10)
        tk.Label(row, text=f"\"{req['message']}\"", bg=GRAY_LIGHT, fg="#4b5563", font=FONT_SM, anchor="w",
                 justify="left", wraplength=560).pack(fill="x", padx=10, pady=(0, 6))
        if is_received and req["status"] == "Pending":
            btns = tk.Frame(row, bg=GRAY_LIGHT)
            btns.pack(anchor="w", padx=10, pady=(0, 8))
            make_button(btns, "Accept", lambda: self.respond_request(req["id"], "Accepted"), bg=GREEN, font=FONT_SM_B, pady=2).pack(side="left")
            make_button(btns, "Decline", lambda: self.respond_request(req["id"], "Declined"), bg=RED, font=FONT_SM_B, pady=2).pack(side="left", padx=6)
        else:
            tk.Frame(row, bg=GRAY_LIGHT, height=4).pack()

    def respond_request(self, req_id, status):
        req = next((r for r in self.db.requests if r["id"] == req_id), None)
        if req:
            req["status"] = status
            self.db.save()
            self.show_section("requests")

    # ----- Profile -----
    def build_profile(self):
        sf = ScrollFrame(self.body)
        sf.pack(fill="both", expand=True)
        u = self.current_user
        box = card(sf.inner)
        box.pack(padx=100, pady=20, fill="x")

        head = tk.Frame(box, bg=WHITE)
        head.pack(fill="x", padx=20, pady=16)
        self.profile_avatar_holder = tk.Frame(head, bg=WHITE)
        self.profile_avatar_holder.pack(side="left")
        Avatar(self.profile_avatar_holder, u["name"], u.get("avatar", ""), 80).pack()
        info = tk.Frame(head, bg=WHITE)
        info.pack(side="left", padx=14)
        make_label(info, u["name"], font=FONT_H2, fg="#312e81").pack(anchor="w")
        make_label(info, f"{u['course']} • {u['year']}", font=FONT_SM_B, fg=INDIGO).pack(anchor="w")
        make_button(info, "📷 Change Photo", self.upload_avatar, bg=INDIGO_LIGHT, fg=INDIGO, font=FONT_SM_B, pady=2).pack(anchor="w", pady=(6, 0))
        if not HAS_PIL:
            make_label(info, "(install Pillow to display photos)", font=("Segoe UI", 8), fg="#9ca3af").pack(anchor="w")

        tk.Frame(box, bg="#e5e7eb", height=1).pack(fill="x", padx=20)

        form = tk.Frame(box, bg=WHITE)
        form.pack(fill="x", padx=20, pady=14)
        v_name = tk.StringVar(value=u["name"])
        v_course = tk.StringVar(value=u["course"])
        v_year = tk.StringVar(value=u["year"])
        v_skills = tk.StringVar(value=", ".join(u["skills"]))
        v_needs = tk.StringVar(value=", ".join(u["needs"]))
        v_avail = tk.StringVar(value=u.get("availability", ""))

        field(form, "Name", lambda p: tk.Entry(p, textvariable=v_name, relief="solid", bd=1))[0].pack(fill="x", pady=5)
        field(form, "Email (Read Only)", lambda p: tk.Entry(p, relief="solid", bd=1, state="normal"))[0].pack_forget()
        email_wrap, email_entry = field(form, "Email (Read Only)", lambda p: tk.Entry(p, relief="solid", bd=1))
        email_entry.insert(0, u["email"])
        email_entry.configure(state="readonly")
        email_wrap.pack(fill="x", pady=5)
        field(form, "College Program", lambda p: ttk.Combobox(p, textvariable=v_course, values=ALL_PROGRAMS, state="readonly"))[0].pack(fill="x", pady=5)
        field(form, "Year Level", lambda p: ttk.Combobox(p, textvariable=v_year, values=YEARS, state="readonly"))[0].pack(fill="x", pady=5)
        field(form, "Skills You Can Teach (comma-separated)", lambda p: tk.Entry(p, textvariable=v_skills, relief="solid", bd=1))[0].pack(fill="x", pady=5)
        field(form, "Subjects You Need Help With (comma-separated)", lambda p: tk.Entry(p, textvariable=v_needs, relief="solid", bd=1))[0].pack(fill="x", pady=5)
        field(form, "Availability (e.g. Mon/Wed 2-5 PM)", lambda p: tk.Entry(p, textvariable=v_avail, relief="solid", bd=1))[0].pack(fill="x", pady=5)

        def save():
            name = v_name.get().strip()
            if not name:
                messagebox.showwarning("Missing name", "Name cannot be empty.")
                return
            u["name"] = name
            u["course"] = v_course.get()
            u["year"] = v_year.get()
            u["skills"] = [s.strip() for s in v_skills.get().split(",") if s.strip()]
            u["needs"] = [s.strip() for s in v_needs.get().split(",") if s.strip()]
            u["availability"] = v_avail.get().strip()
            self.db.save()
            messagebox.showinfo("Saved", "Profile updated successfully!")
            self.show_section("profile")

        make_button(form, "Save Profile", save, pady=8).pack(fill="x", pady=(12, 4))

    def upload_avatar(self):
        path = filedialog.askopenfilename(title="Choose a profile photo",
                                          filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")])
        if not path:
            return
        os.makedirs(AVATAR_DIR, exist_ok=True)
        ext = os.path.splitext(path)[1].lower()
        dest = os.path.join(AVATAR_DIR, f"{self.current_user['id']}{ext}")
        try:
            shutil.copyfile(path, dest)
        except OSError as e:
            messagebox.showerror("Error", f"Could not save image: {e}")
            return
        self.current_user["avatar"] = dest
        self.db.save()
        self.show_section("profile")


if __name__ == "__main__":
    SkillMatchApp().mainloop()
