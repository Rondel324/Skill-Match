import hashlib
import json
import os
import shutil
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageTk, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "skill_match_data.json")
AVATAR_DIR = os.path.join(BASE_DIR, "avatars")

# colors
INDIGO = "#4f46e5"
INDIGO_LIGHT = "#eef2ff"
PINK = "#ec4899"
PINK_LIGHT = "#fce7f3"
BG = "#f5f3ff"
WHITE = "#ffffff"
GRAY = "#6b7280"
GRAY_LIGHT = "#f3f4f6"
GREEN = "#059669"
RED = "#e11d48"
DARK_TEXT = "#312e81"

# status colors: (background, text)
STATUS_COLORS = {
    "Pending": ("#fef3c7", "#92400e"),
    "Accepted": ("#d1fae5", "#065f46"),
    "Declined": ("#ffe4e6", "#9f1239"),
}

# fonts
FONT = ("Segoe UI", 10)
BOLD = ("Segoe UI", 10, "bold")
SMALL = ("Segoe UI", 9)
SMALL_BOLD = ("Segoe UI", 9, "bold")
TITLE = ("Segoe UI", 14, "bold")

COLLEGE_PROGRAMS = {
    "Computer Studies & IT": ["BS Computer Science", "BS Information Technology", "BS Information Systems", "BS Cybersecurity", "BS Data Science"],
    "Engineering": ["BS Civil Engineering", "BS Computer Engineering", "BS Electrical Engineering", "BS Mechanical Engineering", "BS Industrial Engineering"],
    "Business & Management": ["BS Business Administration", "BS Accountancy", "BS Marketing Management", "BS Financial Management", "BS Entrepreneurship"],
    "Health Sciences": ["BS Nursing", "BS Medical Technology", "BS Pharmacy", "BS Physical Therapy", "BS Psychology"],
    "Sciences & Math": ["BS Biology", "BS Chemistry", "BS Physics", "BS Mathematics", "BS Environmental Science"],
    "Arts & Social Sciences": ["BA Communication", "BA Political Science", "BA English Literature", "BA Journalism", "BA Sociology"],
    "Education": ["Bachelor of Elementary Education", "Bachelor of Secondary Education", "Bachelor of Special Needs Education"],
}

# put every program in one list for the dropdowns
ALL_PROGRAMS = []
for group in COLLEGE_PROGRAMS:
    for program in COLLEGE_PROGRAMS[group]:
        ALL_PROGRAMS.append(program)

YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year+"]

AVATAR_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#14b8a6", "#f59e0b", "#3b82f6", "#10b981", "#ef4444"]


# ---------- saving and loading ----------
def load_data():
    data = {"users": [], "posts": [], "requests": [], "current_user_id": None}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass  # file is broken, so just start with empty data
    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def make_id():
    # microsecond timestamp so two ids almost never match
    return str(int(datetime.now().timestamp() * 1000000))


def hash_password(password, salt):
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# ---------- small helper functions for the screens ----------
def make_button(parent, text, command, bg=INDIGO, fg=WHITE, font=BOLD, pady=5):
    return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, font=font,
                     relief="flat", bd=0, padx=12, pady=pady, cursor="hand2")


def make_card(parent):
    return tk.Frame(parent, bg=WHITE, highlightbackground="#e0e7ff", highlightthickness=1)


def make_badge(parent, text, bg, fg):
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=("Segoe UI", 8, "bold"), padx=6, pady=1)


def labeled_entry(parent, text, var, show=""):
    tk.Label(parent, text=text.upper(), font=("Segoe UI", 8, "bold"), fg=GRAY, bg=WHITE).pack(anchor="w", pady=(6, 0))
    entry = tk.Entry(parent, textvariable=var, show=show, relief="solid", bd=1)
    entry.pack(fill="x", ipady=4)
    return entry


def labeled_combo(parent, text, var, values):
    tk.Label(parent, text=text.upper(), font=("Segoe UI", 8, "bold"), fg=GRAY, bg=WHITE).pack(anchor="w", pady=(6, 0))
    combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly")
    combo.pack(fill="x", ipady=4)
    return combo


def get_initials(name):
    words = name.split()
    letters = ""
    for word in words[:2]:
        letters += word[0]
    if letters == "":
        return "?"
    return letters.upper()


def draw_avatar(parent, name, photo_path, size):
    canvas = tk.Canvas(parent, width=size, height=size, bg=WHITE, highlightthickness=0)
    canvas.photo = None  # keep a reference so the picture doesn't disappear

    if photo_path and HAS_PIL and os.path.exists(photo_path):
        try:
            img = Image.open(photo_path).convert("RGB").resize((size, size))
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
            img.putalpha(mask)
            canvas.photo = ImageTk.PhotoImage(img)
            canvas.create_image(size // 2, size // 2, image=canvas.photo)
            return canvas
        except Exception:
            pass  # if the photo can't load, show the initials instead

    # the same name always gets the same color
    color = AVATAR_COLORS[sum(ord(ch) for ch in name) % len(AVATAR_COLORS)]
    canvas.create_oval(1, 1, size - 1, size - 1, fill=color, outline=INDIGO)
    canvas.create_text(size // 2, size // 2, text=get_initials(name), fill=WHITE,
                       font=("Segoe UI", max(8, size // 3), "bold"))
    return canvas


def make_scroll_area(parent):
    # returns the inner frame, put the page content inside it
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill="both", expand=True)
    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=BG)

    window = canvas.create_window((0, 0), window=inner, anchor="n")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def update_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def keep_centered(event):
        canvas.coords(window, event.width // 2, 0)
        canvas.itemconfigure(window, width=min(event.width, 1000))

    def mouse_wheel(event):
        if event.delta > 0:
            canvas.yview_scroll(-1, "units")
        else:
            canvas.yview_scroll(1, "units")

    inner.bind("<Configure>", update_scroll_region)
    canvas.bind("<Configure>", keep_centered)
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", mouse_wheel))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
    return inner


# ---------- main app ----------
class SkillMatchApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Skill Match - Creative Peer Tutoring Platform")
        self.geometry("1000x720")
        self.minsize(760, 560)
        self.configure(bg=BG)

        self.data = load_data()
        self.current_user = self.find_user(self.data["current_user_id"])
        self.nav_buttons = {}

        try:
            ttk.Style(self).theme_use("clam")
        except tk.TclError:
            pass

        self.build_navbar()
        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True)

        if self.current_user:
            self.show_page("feed")
        else:
            self.show_page("auth")

    def find_user(self, user_id):
        for user in self.data["users"]:
            if user["id"] == user_id:
                return user
        return None

    def find_post(self, post_id):
        for post in self.data["posts"]:
            if post["id"] == post_id:
                return post
        return None

    # ----- navbar and page switching -----
    def build_navbar(self):
        self.navbar = tk.Frame(self, bg=WHITE, highlightbackground="#e0e7ff", highlightthickness=1)
        self.navbar.pack(fill="x")
        tk.Label(self.navbar, text="Skill Match", font=("Segoe UI", 15, "bold"), fg=INDIGO, bg=WHITE).pack(side="left", padx=14, pady=10)

        self.nav_links = tk.Frame(self.navbar, bg=WHITE)
        pages = [("feed", "Feed"), ("find", "Find Tutors"), ("requests", "Requests"), ("profile", "Profile")]
        for key, text in pages:
            btn = tk.Button(self.nav_links, text=text, command=lambda k=key: self.show_page(k),
                            relief="flat", bd=0, bg=WHITE, fg=GRAY, font=BOLD, padx=10, pady=4, cursor="hand2")
            btn.pack(side="left", padx=2)
            self.nav_buttons[key] = btn
        make_button(self.nav_links, "Logout", self.logout, bg=PINK, pady=3).pack(side="left", padx=(8, 0))

    def show_page(self, name):
        # clear the old page first
        for widget in self.body.winfo_children():
            widget.destroy()

        # nav links only show when logged in
        if self.current_user:
            self.nav_links.pack(side="right", padx=10)
        else:
            self.nav_links.pack_forget()

        # highlight the button of the page we are on
        for key in self.nav_buttons:
            if key == name:
                self.nav_buttons[key].configure(fg=INDIGO, bg=INDIGO_LIGHT)
            else:
                self.nav_buttons[key].configure(fg=GRAY, bg=WHITE)
        self.update_pending_count()

        if name == "auth":
            self.build_auth()
        elif name == "feed":
            self.build_feed()
        elif name == "find":
            self.build_find()
        elif name == "requests":
            self.build_requests()
        elif name == "profile":
            self.build_profile()

    def update_pending_count(self):
        if not self.current_user:
            return
        pending = 0
        for req in self.data["requests"]:
            if req["toId"] == self.current_user["id"] and req["status"] == "Pending":
                pending += 1
        if pending > 0:
            self.nav_buttons["requests"].configure(text="Requests (" + str(pending) + ")")
        else:
            self.nav_buttons["requests"].configure(text="Requests")

    # ----- login and register -----
    def build_auth(self):
        outer = tk.Frame(self.body, bg=BG)
        outer.pack(expand=True)
        box = make_card(outer)
        box.pack(pady=30, ipadx=24, ipady=18)

        tk.Label(box, text="Welcome to Skill Match!", font=TITLE, fg=DARK_TEXT, bg=WHITE).pack(pady=(14, 0))
        tk.Label(box, text="Connect, share skills, and ace your courses together.", font=SMALL, fg=GRAY, bg=WHITE).pack(pady=(2, 12))

        tabs = tk.Frame(box, bg=GRAY_LIGHT)
        tabs.pack(fill="x", padx=24)
        forms = tk.Frame(box, bg=WHITE)
        forms.pack(fill="x", padx=24, pady=14)
        login_frame = tk.Frame(forms, bg=WHITE)
        register_frame = tk.Frame(forms, bg=WHITE)

        login_tab = tk.Button(tabs, text="Login", relief="flat", bd=0, font=BOLD, pady=6, cursor="hand2")
        register_tab = tk.Button(tabs, text="Register", relief="flat", bd=0, font=BOLD, pady=6, cursor="hand2")
        login_tab.pack(side="left", expand=True, fill="x", padx=2, pady=2)
        register_tab.pack(side="left", expand=True, fill="x", padx=2, pady=2)

        def show_login():
            register_frame.pack_forget()
            login_frame.pack(fill="x")
            login_tab.configure(bg=WHITE, fg=INDIGO)
            register_tab.configure(bg=GRAY_LIGHT, fg=GRAY)

        def show_register():
            login_frame.pack_forget()
            register_frame.pack(fill="x")
            register_tab.configure(bg=WHITE, fg=INDIGO)
            login_tab.configure(bg=GRAY_LIGHT, fg=GRAY)

        login_tab.configure(command=show_login)
        register_tab.configure(command=show_register)

        # login form
        login_email = tk.StringVar()
        login_password = tk.StringVar()
        labeled_entry(login_frame, "Email", login_email)
        labeled_entry(login_frame, "Password", login_password, show="*")
        make_button(login_frame, "Login", lambda: self.login(login_email.get(), login_password.get()),
                    pady=8).pack(fill="x", pady=(12, 0))

        # register form
        reg_name = tk.StringVar()
        reg_email = tk.StringVar()
        reg_password = tk.StringVar()
        reg_course = tk.StringVar(value=ALL_PROGRAMS[0])
        reg_year = tk.StringVar(value=YEARS[0])
        labeled_entry(register_frame, "Full Name", reg_name)
        labeled_entry(register_frame, "Email", reg_email)
        labeled_entry(register_frame, "Password", reg_password, show="*")
        labeled_combo(register_frame, "College Program", reg_course, ALL_PROGRAMS)
        labeled_combo(register_frame, "Year Level", reg_year, YEARS)
        make_button(register_frame, "Create Account",
                    lambda: self.register(reg_name.get(), reg_email.get(), reg_password.get(), reg_course.get(), reg_year.get()),
                    pady=8).pack(fill="x", pady=(12, 0))

        show_login()

    def register(self, name, email, password, course, year):
        name = name.strip()
        email = email.strip().lower()

        if name == "" or email == "" or password == "":
            messagebox.showwarning("Missing info", "Please fill in all fields.")
            return
        if "@" not in email:
            messagebox.showwarning("Invalid email", "Please enter a valid email address.")
            return
        for user in self.data["users"]:
            if user["email"] == email:
                messagebox.showwarning("Account exists", "Account already exists with this email.")
                return

        # random salt so two people with the same password get different hashes
        salt = os.urandom(8).hex()
        new_user = {
            "id": make_id(),
            "name": name,
            "email": email,
            "salt": salt,
            "password": hash_password(password, salt),
            "course": course,
            "year": year,
            "skills": [],
            "needs": [],
            "availability": "Flexible",
            "avatar": "",
        }
        self.data["users"].append(new_user)
        self.current_user = new_user
        self.data["current_user_id"] = new_user["id"]
        save_data(self.data)
        messagebox.showinfo("Welcome", "Account created successfully!")
        self.show_page("feed")

    def login(self, email, password):
        email = email.strip().lower()
        for user in self.data["users"]:
            if user["email"] == email and user["password"] == hash_password(password, user["salt"]):
                self.current_user = user
                self.data["current_user_id"] = user["id"]
                save_data(self.data)
                self.show_page("feed")
                return
        messagebox.showerror("Login failed", "Invalid email or password.")

    def logout(self):
        self.current_user = None
        self.data["current_user_id"] = None
        save_data(self.data)
        self.show_page("auth")

    # ----- feed -----
    def build_feed(self):
        inner = make_scroll_area(self.body)
        page = tk.Frame(inner, bg=BG)
        page.pack(fill="x", padx=60, pady=14)

        # box for writing a new post
        box = make_card(page)
        box.pack(fill="x", pady=(0, 14))
        top = tk.Frame(box, bg=WHITE)
        top.pack(fill="x", padx=14, pady=(12, 6))
        draw_avatar(top, self.current_user["name"], self.current_user["avatar"], 40).pack(side="left")
        tk.Label(top, text=self.current_user["name"], font=BOLD, bg=WHITE).pack(side="left", padx=10)

        post_text = tk.Text(box, height=3, wrap="word", relief="solid", bd=1, font=FONT)
        post_text.pack(fill="x", padx=14)
        bottom = tk.Frame(box, bg=WHITE)
        bottom.pack(fill="x", padx=14, pady=10)
        tk.Label(bottom, text="Be helpful and respectful", font=SMALL, fg="#9ca3af", bg=WHITE).pack(side="left")
        make_button(bottom, "Post to Feed", lambda: self.create_post(post_text.get("1.0", "end"))).pack(side="right")

        if len(self.data["posts"]) == 0:
            tk.Label(page, text="No posts in the feed yet. Be the first to share something!",
                     bg=BG, fg="#9ca3af", font=FONT).pack(pady=30)

        for post in self.data["posts"]:
            self.build_post_card(page, post)

    def build_post_card(self, parent, post):
        card = make_card(parent)
        card.pack(fill="x", pady=6)

        # use the author's newest name/photo, if the account still exists
        author = self.find_user(post["userId"])
        if author:
            name = author["name"]
            photo = author["avatar"]
        else:
            name = post["userName"]
            photo = ""

        top = tk.Frame(card, bg=WHITE)
        top.pack(fill="x", padx=14, pady=(12, 4))
        draw_avatar(top, name, photo, 40).pack(side="left")
        info = tk.Frame(top, bg=WHITE)
        info.pack(side="left", padx=10)
        tk.Label(info, text=name, font=BOLD, fg=DARK_TEXT, bg=WHITE).pack(anchor="w")
        tk.Label(info, text=post["userCourse"] + " - " + post["timestamp"], font=("Segoe UI", 8), fg="#9ca3af", bg=WHITE).pack(anchor="w")

        tk.Label(card, text=post["content"], bg=WHITE, fg="#374151", font=FONT, justify="left",
                 wraplength=560, anchor="w").pack(fill="x", padx=14, pady=6)

        # like button turns pink if I already liked it
        already_liked = self.current_user["id"] in post["likes"]
        bar = tk.Frame(card, bg=WHITE)
        bar.pack(fill="x", padx=14, pady=(4, 6))
        if already_liked:
            like_color = PINK
            like_font = SMALL_BOLD
        else:
            like_color = GRAY
            like_font = SMALL
        tk.Button(bar, text="Like (" + str(len(post["likes"])) + ")", relief="flat", bd=0, bg=WHITE,
                  fg=like_color, font=like_font, cursor="hand2",
                  command=lambda: self.toggle_like(post["id"])).pack(side="left")
        tk.Label(bar, text=str(len(post["comments"])) + " Comments", font=SMALL, fg=GRAY, bg=WHITE).pack(side="left", padx=14)

        # reply box
        reply_row = tk.Frame(card, bg=WHITE)
        reply_row.pack(fill="x", padx=14, pady=(0, 6))
        reply_entry = tk.Entry(reply_row, relief="solid", bd=1, font=SMALL)
        reply_entry.pack(side="left", fill="x", expand=True, ipady=3)
        reply_entry.bind("<Return>", lambda e: self.add_comment(post["id"], reply_entry.get()))
        make_button(reply_row, "Reply", lambda: self.add_comment(post["id"], reply_entry.get()),
                    font=SMALL_BOLD, pady=2).pack(side="left", padx=(6, 0))

        for comment in post["comments"]:
            comment_box = tk.Frame(card, bg=GRAY_LIGHT)
            comment_box.pack(fill="x", padx=14, pady=2)
            tk.Label(comment_box, text=comment["userName"], bg=GRAY_LIGHT, fg=DARK_TEXT, font=SMALL_BOLD).pack(anchor="w", padx=8, pady=(4, 0))
            tk.Label(comment_box, text=comment["text"], bg=GRAY_LIGHT, fg="#4b5563", font=SMALL,
                     wraplength=540, justify="left", anchor="w").pack(fill="x", padx=8, pady=(0, 4))

        tk.Frame(card, bg=WHITE, height=8).pack()

    def create_post(self, content):
        content = content.strip()
        if content == "":
            return
        user = self.current_user
        new_post = {
            "id": make_id(),
            "userId": user["id"],
            "userName": user["name"],
            "userCourse": user["course"],
            "content": content,
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "likes": [],
            "comments": [],
        }
        self.data["posts"].insert(0, new_post)  # newest post goes on top
        save_data(self.data)
        self.show_page("feed")

    def toggle_like(self, post_id):
        post = self.find_post(post_id)
        if post is None:
            return
        my_id = self.current_user["id"]
        if my_id in post["likes"]:
            post["likes"].remove(my_id)
        else:
            post["likes"].append(my_id)
        save_data(self.data)
        self.show_page("feed")

    def add_comment(self, post_id, text):
        text = text.strip()
        post = self.find_post(post_id)
        if post is None or text == "":
            return
        post["comments"].append({"userName": self.current_user["name"], "text": text})
        save_data(self.data)
        self.show_page("feed")

    # ----- find tutors -----
    def build_find(self):
        top = make_card(self.body)
        top.pack(fill="x", padx=20, pady=(14, 8))
        tk.Label(top, text="Discover Study Partners & Tutors", font=("Segoe UI", 12, "bold"),
                 fg=DARK_TEXT, bg=WHITE).pack(side="left", padx=14, pady=12)

        self.filter_var = tk.StringVar(value="All Programs")
        self.search_var = tk.StringVar()
        ttk.Combobox(top, textvariable=self.filter_var, values=["All Programs"] + ALL_PROGRAMS,
                     state="readonly", width=28).pack(side="right", padx=14)
        tk.Entry(top, textvariable=self.search_var, relief="solid", bd=1, width=26).pack(side="right", padx=4, ipady=3)
        tk.Label(top, text="Search:", font=SMALL, fg=GRAY, bg=WHITE).pack(side="right")

        self.student_area = tk.Frame(self.body, bg=BG)
        self.student_area.pack(fill="both", expand=True)

        # redraw the list every time the search or filter changes
        self.search_var.trace_add("write", lambda *args: self.show_students())
        self.filter_var.trace_add("write", lambda *args: self.show_students())
        self.show_students()

    def show_students(self):
        for widget in self.student_area.winfo_children():
            widget.destroy()
        inner = make_scroll_area(self.student_area)

        search = self.search_var.get().lower().strip()
        program = self.filter_var.get()

        matches = []
        for user in self.data["users"]:
            if user["id"] == self.current_user["id"]:
                continue  # don't show myself
            if program != "All Programs" and user["course"] != program:
                continue

            # search matches the name, a skill, or a need
            words = [user["name"].lower()]
            for skill in user["skills"]:
                words.append(skill.lower())
            for need in user["needs"]:
                words.append(need.lower())
            found = False
            for word in words:
                if search in word:
                    found = True
            if search != "" and not found:
                continue

            matches.append(user)

        if len(matches) == 0:
            tk.Label(inner, text="No students found matching your search.", bg=BG, fg="#9ca3af", font=FONT).pack(pady=40)
            return

        grid = tk.Frame(inner, bg=BG)
        grid.pack(fill="x", padx=14, pady=6)
        columns = 3
        for i in range(columns):
            grid.columnconfigure(i, weight=1, uniform="col")

        for index in range(len(matches)):
            card = self.build_student_card(grid, matches[index])
            card.grid(row=index // columns, column=index % columns, padx=6, pady=6, sticky="nsew")

    def build_student_card(self, parent, student):
        card = make_card(parent)
        top = tk.Frame(card, bg=WHITE)
        top.pack(fill="x", padx=12, pady=(12, 4))
        draw_avatar(top, student["name"], student["avatar"], 48).pack(side="left")
        info = tk.Frame(top, bg=WHITE)
        info.pack(side="left", padx=8)
        tk.Label(info, text=student["name"], font=BOLD, fg=DARK_TEXT, bg=WHITE).pack(anchor="w")
        tk.Label(info, text=student["course"], bg=WHITE, fg=INDIGO, font=("Segoe UI", 8, "bold"),
                 wraplength=150, justify="left").pack(anchor="w")
        make_badge(info, student["year"], GRAY_LIGHT, GRAY).pack(anchor="w", pady=2)

        availability = student["availability"]
        if availability == "":
            availability = "Flexible"
        tk.Label(card, text="Availability: " + availability, font=SMALL, fg=GRAY, bg=WHITE,
                 wraplength=220, justify="left").pack(anchor="w", padx=12, pady=2)

        # same layout for both lists, only the title, items and colors change
        sections = [
            ("CAN TEACH:", student["skills"], INDIGO_LIGHT, "#3730a3"),
            ("NEEDS HELP WITH:", student["needs"], PINK_LIGHT, "#9d174d"),
        ]
        for title, items, badge_bg, badge_fg in sections:
            tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg="#9ca3af", bg=WHITE).pack(anchor="w", padx=12, pady=(6, 0))
            row = tk.Frame(card, bg=WHITE)
            row.pack(anchor="w", padx=12)
            if len(items) == 0:
                tk.Label(row, text="None listed", font=("Segoe UI", 8), fg="#9ca3af", bg=WHITE).pack(side="left")
            for item in items:
                make_badge(row, item, badge_bg, badge_fg).pack(side="left", padx=(0, 3), pady=1)

        make_button(card, "Request Help", lambda: self.open_request_popup(student),
                    font=SMALL_BOLD, pady=5).pack(fill="x", padx=12, pady=12)
        return card

    # ----- help request popup -----
    def open_request_popup(self, tutor):
        popup = tk.Toplevel(self)
        popup.title("Request Help")
        popup.configure(bg=WHITE)
        popup.transient(self)
        popup.grab_set()
        popup.geometry("420x330")

        tk.Label(popup, text="Request Help from " + tutor["name"], font=TITLE, fg=DARK_TEXT, bg=WHITE,
                 wraplength=380).pack(pady=(16, 8), padx=20, anchor="w")

        form = tk.Frame(popup, bg=WHITE)
        form.pack(fill="x", padx=20)
        schedule_var = tk.StringVar()
        labeled_entry(form, "Preferred Schedule / Time", schedule_var)
        tk.Label(form, text="MESSAGE / TOPICS TO COVER", font=("Segoe UI", 8, "bold"), fg=GRAY, bg=WHITE).pack(anchor="w", pady=(6, 0))
        message_box = tk.Text(form, height=5, wrap="word", relief="solid", bd=1, font=FONT)
        message_box.pack(fill="x", pady=(2, 8))

        def send():
            schedule = schedule_var.get().strip()
            message = message_box.get("1.0", "end").strip()
            if schedule == "" or message == "":
                messagebox.showwarning("Missing info", "Please fill in the schedule and message.", parent=popup)
                return
            new_request = {
                "id": make_id(),
                "fromId": self.current_user["id"],
                "fromName": self.current_user["name"],
                "toId": tutor["id"],
                "toName": tutor["name"],
                "schedule": schedule,
                "message": message,
                "status": "Pending",
            }
            self.data["requests"].append(new_request)
            save_data(self.data)
            messagebox.showinfo("Sent", "Help request sent!", parent=popup)
            popup.destroy()
            self.update_pending_count()

        buttons = tk.Frame(popup, bg=WHITE)
        buttons.pack(fill="x", padx=20, pady=6)
        make_button(buttons, "Send Request", send).pack(side="right")
        make_button(buttons, "Cancel", popup.destroy, bg=GRAY_LIGHT, fg="#111827").pack(side="right", padx=6)

    # ----- requests page -----
    def build_requests(self):
        inner = make_scroll_area(self.body)
        page = tk.Frame(inner, bg=BG)
        page.pack(fill="x", padx=80, pady=14)
        tk.Label(page, text="Tutoring & Help Requests", font=TITLE, fg=DARK_TEXT, bg=BG).pack(anchor="w", pady=(0, 10))

        my_id = self.current_user["id"]
        received = []
        sent = []
        for req in self.data["requests"]:
            if req["toId"] == my_id:
                received.append(req)
            if req["fromId"] == my_id:
                sent.append(req)

        # received and sent use the same box, only the text is different
        sections = [
            ("RECEIVED REQUESTS", received, True, "No incoming requests."),
            ("SENT REQUESTS", sent, False, "No sent requests."),
        ]
        for title, items, is_received, empty_text in sections:
            box = make_card(page)
            box.pack(fill="x", pady=8)
            tk.Label(box, text=title, font=SMALL_BOLD, fg="#9ca3af", bg=WHITE).pack(anchor="w", padx=14, pady=(12, 6))
            if len(items) == 0:
                tk.Label(box, text=empty_text, font=SMALL, fg="#9ca3af", bg=WHITE).pack(anchor="w", padx=14, pady=(0, 12))
            for req in items:
                self.build_request_row(box, req, is_received)

    def build_request_row(self, parent, req, is_received):
        row = tk.Frame(parent, bg=GRAY_LIGHT, highlightbackground="#e5e7eb", highlightthickness=1)
        row.pack(fill="x", padx=14, pady=5)

        top = tk.Frame(row, bg=GRAY_LIGHT)
        top.pack(fill="x", padx=10, pady=(8, 2))
        if is_received:
            title = req["fromName"] + " requested help"
        else:
            title = "Request to " + req["toName"]
        tk.Label(top, text=title, bg=GRAY_LIGHT, fg=DARK_TEXT, font=BOLD).pack(side="left")

        badge_bg, badge_fg = STATUS_COLORS[req["status"]]
        make_badge(top, req["status"], badge_bg, badge_fg).pack(side="right")

        tk.Label(row, text="Schedule: " + req["schedule"], bg=GRAY_LIGHT, fg="#4b5563", font=SMALL, anchor="w").pack(fill="x", padx=10)
        tk.Label(row, text='"' + req["message"] + '"', bg=GRAY_LIGHT, fg="#4b5563", font=SMALL, anchor="w",
                 justify="left", wraplength=560).pack(fill="x", padx=10, pady=(0, 6))

        # only the receiver can answer, and only while it's still pending
        if is_received and req["status"] == "Pending":
            buttons = tk.Frame(row, bg=GRAY_LIGHT)
            buttons.pack(anchor="w", padx=10, pady=(0, 8))
            make_button(buttons, "Accept", lambda: self.answer_request(req["id"], "Accepted"),
                        bg=GREEN, font=SMALL_BOLD, pady=2).pack(side="left")
            make_button(buttons, "Decline", lambda: self.answer_request(req["id"], "Declined"),
                        bg=RED, font=SMALL_BOLD, pady=2).pack(side="left", padx=6)
        else:
            tk.Frame(row, bg=GRAY_LIGHT, height=4).pack()

    def answer_request(self, request_id, new_status):
        for req in self.data["requests"]:
            if req["id"] == request_id:
                req["status"] = new_status
                save_data(self.data)
                self.show_page("requests")
                return

    # ----- profile -----
    def build_profile(self):
        user = self.current_user
        inner = make_scroll_area(self.body)
        box = make_card(inner)
        box.pack(padx=100, pady=20, fill="x")

        top = tk.Frame(box, bg=WHITE)
        top.pack(fill="x", padx=20, pady=16)
        draw_avatar(top, user["name"], user["avatar"], 80).pack(side="left")
        info = tk.Frame(top, bg=WHITE)
        info.pack(side="left", padx=14)
        tk.Label(info, text=user["name"], font=TITLE, fg=DARK_TEXT, bg=WHITE).pack(anchor="w")
        tk.Label(info, text=user["course"] + " - " + user["year"], font=SMALL_BOLD, fg=INDIGO, bg=WHITE).pack(anchor="w")
        make_button(info, "Change Photo", self.upload_photo, bg=INDIGO_LIGHT, fg=INDIGO,
                    font=SMALL_BOLD, pady=2).pack(anchor="w", pady=(6, 0))
        if not HAS_PIL:
            tk.Label(info, text="(install Pillow to display photos)", font=("Segoe UI", 8), fg="#9ca3af", bg=WHITE).pack(anchor="w")

        tk.Frame(box, bg="#e5e7eb", height=1).pack(fill="x", padx=20)

        form = tk.Frame(box, bg=WHITE)
        form.pack(fill="x", padx=20, pady=14)

        name_var = tk.StringVar(value=user["name"])
        email_var = tk.StringVar(value=user["email"])
        course_var = tk.StringVar(value=user["course"])
        year_var = tk.StringVar(value=user["year"])
        skills_var = tk.StringVar(value=", ".join(user["skills"]))
        needs_var = tk.StringVar(value=", ".join(user["needs"]))
        availability_var = tk.StringVar(value=user["availability"])

        labeled_entry(form, "Name", name_var)
        email_entry = labeled_entry(form, "Email (Read Only)", email_var)
        email_entry.configure(state="readonly")  # email can't be changed
        labeled_combo(form, "College Program", course_var, ALL_PROGRAMS)
        labeled_combo(form, "Year Level", year_var, YEARS)
        labeled_entry(form, "Skills You Can Teach (comma-separated)", skills_var)
        labeled_entry(form, "Subjects You Need Help With (comma-separated)", needs_var)
        labeled_entry(form, "Availability (e.g. Mon/Wed 2-5 PM)", availability_var)

        def save_profile():
            name = name_var.get().strip()
            if name == "":
                messagebox.showwarning("Missing name", "Name cannot be empty.")
                return

            # turn "python, java" into ["python", "java"] and skip empty items
            skills = []
            for item in skills_var.get().split(","):
                if item.strip() != "":
                    skills.append(item.strip())
            needs = []
            for item in needs_var.get().split(","):
                if item.strip() != "":
                    needs.append(item.strip())

            user["name"] = name
            user["course"] = course_var.get()
            user["year"] = year_var.get()
            user["skills"] = skills
            user["needs"] = needs
            user["availability"] = availability_var.get().strip()
            save_data(self.data)
            messagebox.showinfo("Saved", "Profile updated successfully!")
            self.show_page("profile")

        make_button(form, "Save Profile", save_profile, pady=8).pack(fill="x", pady=(12, 4))

    def upload_photo(self):
        path = filedialog.askopenfilename(title="Choose a profile photo",
                                          filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")])
        if path == "":
            return  # user closed the window

        os.makedirs(AVATAR_DIR, exist_ok=True)
        extension = os.path.splitext(path)[1].lower()
        new_path = os.path.join(AVATAR_DIR, self.current_user["id"] + extension)
        try:
            shutil.copyfile(path, new_path)
        except OSError as error:
            messagebox.showerror("Error", "Could not save image: " + str(error))
            return

        self.current_user["avatar"] = new_path
        save_data(self.data)
        self.show_page("profile")


if __name__ == "__main__":
    app = SkillMatchApp()
    app.mainloop()
