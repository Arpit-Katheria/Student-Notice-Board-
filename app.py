from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import datetime, date
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "smartnotice123"

DATABASE = "notice.db"

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "webp",
    "doc", "docx", "xls", "xlsx", "txt"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notices(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            description TEXT NOT NULL,

            category TEXT NOT NULL,

            created_at TEXT NOT NULL,

            priority TEXT NOT NULL DEFAULT 'Normal',

            expiry_date TEXT,

            pinned INTEGER NOT NULL DEFAULT 0,

            status TEXT NOT NULL DEFAULT 'Active',

            updated_at TEXT,

            department TEXT DEFAULT 'All Departments',

            audience TEXT DEFAULT 'All Students',

            attachment TEXT,

            views INTEGER NOT NULL DEFAULT 0,

            featured INTEGER NOT NULL DEFAULT 0,

            publish_at TEXT,

            deleted_at TEXT,

            smart_score INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("PRAGMA table_info(notices)")

    columns = {
        row["name"]
        for row in cur.fetchall()
    }

    migrations = {

        "priority":
            "ALTER TABLE notices ADD COLUMN priority TEXT NOT NULL DEFAULT 'Normal'",

        "expiry_date":
            "ALTER TABLE notices ADD COLUMN expiry_date TEXT",

        "pinned":
            "ALTER TABLE notices ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0",

        "status":
            "ALTER TABLE notices ADD COLUMN status TEXT NOT NULL DEFAULT 'Active'",

        "updated_at":
            "ALTER TABLE notices ADD COLUMN updated_at TEXT",

        "department":
            "ALTER TABLE notices ADD COLUMN department TEXT DEFAULT 'All Departments'",

        "audience":
            "ALTER TABLE notices ADD COLUMN audience TEXT DEFAULT 'All Students'",

        "attachment":
            "ALTER TABLE notices ADD COLUMN attachment TEXT",

        "views":
            "ALTER TABLE notices ADD COLUMN views INTEGER NOT NULL DEFAULT 0",

        "featured":
            "ALTER TABLE notices ADD COLUMN featured INTEGER NOT NULL DEFAULT 0",

        "publish_at":
            "ALTER TABLE notices ADD COLUMN publish_at TEXT",

        "deleted_at":
            "ALTER TABLE notices ADD COLUMN deleted_at TEXT",

        "smart_score":
            "ALTER TABLE notices ADD COLUMN smart_score INTEGER NOT NULL DEFAULT 0"
    }

    for column, sql in migrations.items():

        if column not in columns:
            cur.execute(sql)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# HELPERS
# =========================================================

def current_time():

    return datetime.now().strftime(
        "%d %b %Y • %I:%M %p"
    )


def now_iso():

    return datetime.now().isoformat(timespec="minutes")


def parse_created_time(value):

    if not value:
        return None

    formats = [
        "%d %b %Y • %I:%M %p",
        "%Y-%m-%d %H:%M:%S"
    ]

    for fmt in formats:

        try:
            return datetime.strptime(value, fmt)

        except ValueError:
            pass

    return None


def allowed_file(filename):

    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def calculate_score(notice):

    score = 0

    priority_scores = {
        "Normal": 10,
        "Important": 30,
        "Urgent": 50
    }

    score += priority_scores.get(
        notice["priority"],
        10
    )

    if notice["pinned"]:
        score += 20

    if notice["featured"]:
        score += 25

    created = parse_created_time(
        notice["created_at"]
    )

    if created:

        age = datetime.now() - created

        if age.total_seconds() <= 86400:
            score += 10

    expiry = notice["expiry_date"]

    if expiry:

        try:

            expiry_date = datetime.strptime(
                expiry,
                "%Y-%m-%d"
            ).date()

            days_left = (
                expiry_date - date.today()
            ).days

            if 0 <= days_left <= 3:
                score += 15

        except ValueError:
            pass

    return score


def update_notice_statuses():

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM notices"
    )

    notices = cur.fetchall()

    now = datetime.now()
    today = date.today()

    for notice in notices:

        if notice["deleted_at"]:

            status = "Trashed"

        elif notice["status"] == "Archived":

            status = "Archived"

        else:

            publish_at = notice["publish_at"]

            if publish_at:

                try:

                    publish_time = datetime.fromisoformat(
                        publish_at
                    )

                    if publish_time > now:

                        status = "Scheduled"

                    else:

                        status = "Active"

                except ValueError:

                    status = "Active"

            else:

                status = "Active"


            expiry = notice["expiry_date"]

            if expiry and status == "Active":

                try:

                    expiry_date = datetime.strptime(
                        expiry,
                        "%Y-%m-%d"
                    ).date()

                    if expiry_date < today:
                        status = "Expired"

                except ValueError:
                    pass

        score = calculate_score(notice)

        cur.execute("""
            UPDATE notices
            SET
                status = ?,
                smart_score = ?
            WHERE id = ?
        """, (
            status,
            score,
            notice["id"]
        ))

    conn.commit()
    conn.close()


def prepare_notice(row):

    notice = dict(row)

    created = parse_created_time(
        notice.get("created_at")
    )

    notice["created_timestamp"] = (
        created.timestamp()
        if created
        else 0
    )

    notice["is_new"] = False

    if created:

        age = datetime.now() - created

        notice["is_new"] = (
            age.total_seconds() <= 86400
        )

    return notice


def get_all_notices():

    update_notice_statuses()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM notices
        ORDER BY
            CASE status
                WHEN 'Trashed' THEN 5
                WHEN 'Archived' THEN 4
                WHEN 'Expired' THEN 3
                WHEN 'Scheduled' THEN 2
                ELSE 1
            END,
            featured DESC,
            pinned DESC,
            smart_score DESC,
            id DESC
    """)

    rows = cur.fetchall()

    conn.close()

    return [
        prepare_notice(row)
        for row in rows
    ]


def get_public_notices():

    update_notice_statuses()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM notices
        WHERE status = 'Active'
        AND deleted_at IS NULL
        ORDER BY
            featured DESC,
            pinned DESC,
            smart_score DESC,
            id DESC
    """)

    rows = cur.fetchall()

    conn.close()

    return [
        prepare_notice(row)
        for row in rows
    ]


# =========================================================
# PUBLIC HOME
# =========================================================

@app.route("/")
def home():

    notices = get_public_notices()

    ticker = [
        notice
        for notice in notices
        if notice["priority"]
        in ["Urgent", "Important"]
    ][:5]

    featured = [
        notice
        for notice in notices
        if notice["featured"]
    ]

    return render_template(
        "home.html",
        notices=notices,
        ticker=ticker,
        featured=featured
    )


# =========================================================
# VIEW NOTICE
# =========================================================

@app.route("/notice/<int:id>")
def view_notice(id):

    update_notice_statuses()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM notices
        WHERE id = ?
        AND status = 'Active'
        AND deleted_at IS NULL
    """, (id,))

    notice = cur.fetchone()

    if not notice:

        conn.close()

        return redirect(url_for("home"))

    cur.execute("""
        UPDATE notices
        SET views = views + 1
        WHERE id = ?
    """, (id,))

    conn.commit()

    cur.execute(
        "SELECT * FROM notices WHERE id = ?",
        (id,)
    )

    notice = cur.fetchone()

    conn.close()

    return render_template(
        "notice.html",
        notice=prepare_notice(notice)
    )


# =========================================================
# API FOR BROWSER NOTIFICATIONS
# =========================================================

@app.route("/api/latest")
def latest_notices():

    notices = get_public_notices()

    latest = [
        {
            "id": notice["id"],
            "title": notice["title"],
            "priority": notice["priority"]
        }
        for notice in notices[:5]
    ]

    return jsonify(latest)


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if (
            username == "admin"
            and password == "admin123"
        ):

            session["admin"] = True

            return redirect(url_for("admin"))

        return render_template(
            "login.html",
            error="Invalid Username or Password"
        )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    if "admin" not in session:
        return redirect(url_for("login"))

    notices = get_all_notices()

    total = len(notices)

    normal = sum(
        1 for n in notices
        if n["priority"] == "Normal"
        and n["status"] != "Trashed"
    )

    important = sum(
        1 for n in notices
        if n["priority"] == "Important"
        and n["status"] != "Trashed"
    )

    urgent = sum(
        1 for n in notices
        if n["priority"] == "Urgent"
        and n["status"] != "Trashed"
    )

    active = sum(
        1 for n in notices
        if n["status"] == "Active"
    )

    scheduled = sum(
        1 for n in notices
        if n["status"] == "Scheduled"
    )

    expired = sum(
        1 for n in notices
        if n["status"] == "Expired"
    )

    archived = sum(
        1 for n in notices
        if n["status"] == "Archived"
    )

    trashed = sum(
        1 for n in notices
        if n["status"] == "Trashed"
    )

    total_views = sum(
        n["views"]
        for n in notices
    )

    most_viewed = sorted(
        [
            n for n in notices
            if n["status"] != "Trashed"
        ],
        key=lambda n: n["views"],
        reverse=True
    )[:5]

    return render_template(
        "admin.html",

        notices=notices,

        total=total,

        normal=normal,

        important=important,

        urgent=urgent,

        active=active,

        scheduled=scheduled,

        expired=expired,

        archived=archived,

        trashed=trashed,

        total_views=total_views,

        most_viewed=most_viewed
    )


# =========================================================
# ADD NOTICE
# =========================================================

@app.route("/add", methods=["GET", "POST"])
def add():

    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"].strip()

        description = request.form[
            "description"
        ].strip()

        category = request.form["category"]

        priority = request.form["priority"]

        department = request.form[
            "department"
        ]

        audience = request.form[
            "audience"
        ]

        expiry_date = (
            request.form.get("expiry_date")
            or None
        )

        publish_at = (
            request.form.get("publish_at")
            or None
        )

        featured = (
            1
            if request.form.get("featured")
            else 0
        )

        pinned = (
            1
            if request.form.get("pinned")
            else 0
        )

        created = current_time()

        attachment = None

        file = request.files.get(
            "attachment"
        )

        if file and file.filename:

            if allowed_file(file.filename):

                filename = secure_filename(
                    file.filename
                )

                timestamp = datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                )

                filename = (
                    timestamp
                    + "_"
                    + filename
                )

                file.save(
                    os.path.join(
                        app.config[
                            "UPLOAD_FOLDER"
                        ],
                        filename
                    )
                )

                attachment = filename

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO notices(
                title,
                description,
                category,
                created_at,
                priority,
                expiry_date,
                pinned,
                status,
                updated_at,
                department,
                audience,
                attachment,
                views,
                featured,
                publish_at,
                deleted_at,
                smart_score
            )
            VALUES(
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, 0, ?, ?, NULL, 0
            )
        """, (
            title,
            description,
            category,
            created,
            priority,
            expiry_date,
            pinned,
            "Scheduled"
            if publish_at
            and datetime.fromisoformat(
                publish_at
            ) > datetime.now()
            else "Active",
            created,
            department,
            audience,
            attachment,
            featured,
            publish_at
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin"))

    return render_template(
        "add.html",
        now_date=date.today().isoformat()
    )


# =========================================================
# EDIT NOTICE
# =========================================================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM notices WHERE id = ?",
        (id,)
    )

    notice = cur.fetchone()

    if not notice:

        conn.close()

        return redirect(url_for("admin"))

    if request.method == "POST":

        title = request.form["title"].strip()

        description = request.form[
            "description"
        ].strip()

        category = request.form["category"]

        priority = request.form["priority"]

        department = request.form[
            "department"
        ]

        audience = request.form[
            "audience"
        ]

        expiry_date = (
            request.form.get("expiry_date")
            or None
        )

        publish_at = (
            request.form.get("publish_at")
            or None
        )

        featured = (
            1
            if request.form.get("featured")
            else 0
        )

        updated = current_time()

        attachment = notice["attachment"]

        file = request.files.get(
            "attachment"
        )

        if file and file.filename:

            if allowed_file(file.filename):

                filename = secure_filename(
                    file.filename
                )

                timestamp = datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                )

                filename = (
                    timestamp
                    + "_"
                    + filename
                )

                file.save(
                    os.path.join(
                        app.config[
                            "UPLOAD_FOLDER"
                        ],
                        filename
                    )
                )

                attachment = filename

        if publish_at:

            try:

                status = (
                    "Scheduled"
                    if datetime.fromisoformat(
                        publish_at
                    ) > datetime.now()
                    else "Active"
                )

            except ValueError:

                status = "Active"

        else:

            status = (
                "Archived"
                if notice["status"] == "Archived"
                else "Active"
            )

        cur.execute("""
            UPDATE notices
            SET
                title = ?,
                description = ?,
                category = ?,
                priority = ?,
                expiry_date = ?,
                updated_at = ?,
                department = ?,
                audience = ?,
                attachment = ?,
                featured = ?,
                publish_at = ?,
                status = ?
            WHERE id = ?
        """, (
            title,
            description,
            category,
            priority,
            expiry_date,
            updated,
            department,
            audience,
            attachment,
            featured,
            publish_at,
            status,
            id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin"))

    conn.close()

    return render_template(
        "edit.html",
        notice=notice,
        now_date=date.today().isoformat()
    )


# =========================================================
# PIN
# =========================================================

@app.route("/pin/<int:id>")
def pin(id):

    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE notices
        SET pinned =
            CASE
                WHEN pinned = 1 THEN 0
                ELSE 1
            END
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# =========================================================
# FEATURE
# =========================================================

@app.route("/feature/<int:id>")
def feature(id):

    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE notices
        SET featured =
            CASE
                WHEN featured = 1 THEN 0
                ELSE 1
            END
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# =========================================================
# ARCHIVE
# =========================================================

@app.route("/archive/<int:id>")
def archive(id):

    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT status FROM notices WHERE id = ?",
        (id,)
    )

    notice = cur.fetchone()

    if notice:

        if notice["status"] == "Archived":

            new_status = "Active"

        else:

            new_status = "Archived"

        cur.execute("""
            UPDATE notices
            SET
                status = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            current_time(),
            id
        ))

        conn.commit()

    conn.close()

    return redirect(url_for("admin"))


# =========================================================
# TRASH
# =========================================================

@app.route("/trash/<int:id>")
def trash(id):

    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE notices
        SET
            deleted_at = ?,
            status = 'Trashed',
            updated_at = ?
        WHERE id = ?
    """, (
        current_time(),
        current_time(),
        id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# =========================================================
# RESTORE
# =========================================================

@app.route("/restore/<int:id>")
def restore(id):

    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT expiry_date, publish_at FROM notices WHERE id = ?",
        (id,)
    )

    notice = cur.fetchone()

    if notice:

        status = "Active"

        if notice["publish_at"]:

            try:

                if datetime.fromisoformat(
                    notice["publish_at"]
                ) > datetime.now():

                    status = "Scheduled"

            except ValueError:
                pass

        if (
            notice["expiry_date"]
            and notice["expiry_date"]
            < date.today().isoformat()
        ):

            status = "Expired"

        cur.execute("""
            UPDATE notices
            SET
                deleted_at = NULL,
                status = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            status,
            current_time(),
            id
        ))

        conn.commit()

    conn.close()

    return redirect(url_for("admin"))


# =========================================================
# PERMANENT DELETE
# =========================================================

@app.route("/delete/<int:id>")
def delete(id):

    if "admin" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT attachment FROM notices WHERE id = ?",
        (id,)
    )

    notice = cur.fetchone()

    if notice and notice["attachment"]:

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            notice["attachment"]
        )

        if os.path.exists(filepath):
            os.remove(filepath)

    cur.execute(
        "DELETE FROM notices WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)