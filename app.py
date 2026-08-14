from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "smartnotice123"

# ---------- DATABASE ----------

def init_db():
    conn = sqlite3.connect("notice.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- HOME ----------

@app.route("/")
def home():
    conn = sqlite3.connect("notice.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM notices ORDER BY id DESC")
    notices = cur.fetchall()
    conn.close()

    return render_template("home.html", notices=notices)

# ---------- LOGIN ----------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect("/admin")

        return render_template(
            "login.html",
            error="Invalid Username or Password"
        )

    return render_template("login.html")

# ---------- LOGOUT ----------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- ADMIN ----------

@app.route("/admin")
def admin():

    if "admin" not in session:
        return redirect("/login")

    conn = sqlite3.connect("notice.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM notices ORDER BY id DESC")
    notices = cur.fetchall()
    conn.close()

    return render_template("admin.html", notices=notices)

# ---------- ADD ----------

@app.route("/add", methods=["GET", "POST"])
def add():

    if "admin" not in session:
        return redirect("/login")

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]

        conn = sqlite3.connect("notice.db")
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO notices(title,description,category) VALUES(?,?,?)",
            (title, description, category)
        )

        conn.commit()
        conn.close()

        return redirect("/admin")

    return render_template("add.html")

# ---------- EDIT ----------

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    if "admin" not in session:
        return redirect("/login")

    conn = sqlite3.connect("notice.db")
    cur = conn.cursor()

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]

        cur.execute("""
            UPDATE notices
            SET title=?, description=?, category=?
            WHERE id=?
        """, (title, description, category, id))

        conn.commit()
        conn.close()

        return redirect("/admin")

    cur.execute("SELECT * FROM notices WHERE id=?", (id,))
    notice = cur.fetchone()
    conn.close()

    return render_template("edit.html", notice=notice)

# ---------- DELETE ----------

@app.route("/delete/<int:id>")
def delete(id):

    if "admin" not in session:
        return redirect("/login")

    conn = sqlite3.connect("notice.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM notices WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/admin")

# ---------- RUN ----------

if __name__ == "__main__":
    app.run(debug=True)