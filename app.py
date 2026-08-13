from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


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


@app.route("/")
def home():
    conn = sqlite3.connect("notice.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM notices ORDER BY id DESC")
    notices = cur.fetchall()

    conn.close()
    return render_template("home.html", notices=notices)


@app.route("/admin")
def admin():
    conn = sqlite3.connect("notice.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM notices ORDER BY id DESC")
    notices = cur.fetchall()

    conn.close()
    return render_template("admin.html", notices=notices)


@app.route("/add", methods=["GET", "POST"])
def add():
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

if __name__ == "__main__":
    app.run(debug=True)