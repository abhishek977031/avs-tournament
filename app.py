from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import create_tables, get_connection

app = Flask(__name__)

app.secret_key = "change-this-secret-key"

create_tables()


# =========================
# HOME
# =========================
@app.route("/")
def home():

    connection = get_connection()

    tournaments = connection.execute(
        "SELECT * FROM tournaments ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template(
        "index.html",
        tournaments=tournaments
    )


# =========================
# ADMIN LOGIN
# =========================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["admin_logged_in"] = True

            return redirect("/admin")

        return render_template(
            "admin_login.html",
            error="Invalid username or password"
        )

    return render_template("admin_login.html")


# =========================
# ADMIN LOGOUT
# =========================
@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect("/admin/login")


# =========================
# ADMIN DASHBOARD
# =========================
@app.route("/admin")
def admin_dashboard():

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    connection = get_connection()

    tournaments = connection.execute("""
        SELECT
            t.id,
            t.name,
            t.game_name,
            t.tournament_date,
            t.tournament_time,
            t.entry_fee,
            t.prize_pool,
            t.status,
            COUNT(r.id) AS total_players
        FROM tournaments t
        LEFT JOIN registrations r
            ON t.id = r.tournament_id
        GROUP BY t.id
        ORDER BY t.id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        tournaments=tournaments
    )


# =========================
# CREATE TOURNAMENT
# =========================
@app.route("/admin/create-tournament", methods=["GET", "POST"])
def create_tournament():

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    if request.method == "POST":

        name = request.form["name"]
        game_name = request.form["game_name"]
        tournament_date = request.form["tournament_date"]
        tournament_time = request.form["tournament_time"]
        entry_fee = request.form["entry_fee"]
        prize_pool = request.form["prize_pool"]
        max_players = request.form["max_players"]
        rules = request.form["rules"]

        connection = get_connection()

        connection.execute("""
            INSERT INTO tournaments
            (
                name,
                game_name,
                tournament_date,
                tournament_time,
                entry_fee,
                prize_pool,
                max_players,
                rules,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            game_name,
            tournament_date,
            tournament_time,
            entry_fee,
            prize_pool,
            max_players,
            rules,
            "upcoming"
        ))

        connection.commit()
        connection.close()

        return redirect("/admin")

    return render_template("create_tournament.html")


# =========================
# EDIT TOURNAMENT
# =========================
@app.route(
    "/admin/tournament/<int:tournament_id>/edit",
    methods=["GET", "POST"]
)
def edit_tournament(tournament_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    connection = get_connection()

    tournament = connection.execute(
        "SELECT * FROM tournaments WHERE id = ?",
        (tournament_id,)
    ).fetchone()

    if tournament is None:

        connection.close()

        return "Tournament not found", 404

    if request.method == "POST":

        name = request.form["name"]
        game_name = request.form["game_name"]
        tournament_date = request.form["tournament_date"]
        tournament_time = request.form["tournament_time"]
        entry_fee = request.form["entry_fee"]
        prize_pool = request.form["prize_pool"]
        max_players = request.form["max_players"]
        rules = request.form["rules"]
        status = request.form["status"]

        connection.execute("""
            UPDATE tournaments
            SET
                name = ?,
                game_name = ?,
                tournament_date = ?,
                tournament_time = ?,
                entry_fee = ?,
                prize_pool = ?,
                max_players = ?,
                rules = ?,
                status = ?
            WHERE id = ?
        """, (
            name,
            game_name,
            tournament_date,
            tournament_time,
            entry_fee,
            prize_pool,
            max_players,
            rules,
            status,
            tournament_id
        ))

        connection.commit()
        connection.close()

        return redirect("/admin")

    connection.close()

    return render_template(
        "edit_tournament.html",
        tournament=tournament
    )


# =========================
# DELETE TOURNAMENT
# =========================
@app.route(
    "/admin/tournament/<int:tournament_id>/delete",
    methods=["GET"]
)
def delete_tournament(tournament_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    connection = get_connection()

    tournament = connection.execute(
        "SELECT id FROM tournaments WHERE id = ?",
        (tournament_id,)
    ).fetchone()

    if tournament is None:

        connection.close()

        return "Tournament not found", 404

    connection.execute(
        "DELETE FROM registrations WHERE tournament_id = ?",
        (tournament_id,)
    )

    connection.execute(
        "DELETE FROM tournaments WHERE id = ?",
        (tournament_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/admin")


# =========================
# TOURNAMENT DETAILS
# =========================
@app.route("/tournament/<int:tournament_id>")
def tournament_details(tournament_id):

    connection = get_connection()

    tournament = connection.execute(
        "SELECT * FROM tournaments WHERE id = ?",
        (tournament_id,)
    ).fetchone()

    connection.close()

    if tournament is None:
        return "Tournament not found", 404

    return render_template(
        "tournament_details.html",
        tournament=tournament
    )


# =========================
# PLAYER REGISTRATION
# =========================
@app.route(
    "/tournament/<int:tournament_id>/register",
    methods=["GET", "POST"]
)
def register_tournament(tournament_id):

    connection = get_connection()

    tournament = connection.execute(
        "SELECT * FROM tournaments WHERE id = ?",
        (tournament_id,)
    ).fetchone()

    if tournament is None:

        connection.close()

        return "Tournament not found", 404

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]

        # Check email
        existing_player = connection.execute(
            "SELECT id FROM players WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_player:

            connection.close()

            return """
            <h2 style="text-align:center;margin-top:50px;">
                Email already registered
            </h2>

            <p style="text-align:center;">
                Please login with your existing account.
            </p>

            <p style="text-align:center;">
                <a href="/player/login">
                    Login
                </a>
            </p>
            """

        # Password hash
        password_hash = generate_password_hash(password)

        # Create player
        cursor = connection.execute("""
            INSERT INTO players
            (
                name,
                email,
                phone,
                password
            )
            VALUES (?, ?, ?, ?)
        """, (
            name,
            email,
            phone,
            password_hash
        ))

        player_id = cursor.lastrowid

        # Register tournament
        connection.execute("""
            INSERT INTO registrations
            (
                player_id,
                tournament_id,
                registration_status
            )
            VALUES (?, ?, ?)
        """, (
            player_id,
            tournament_id,
            "confirmed"
        ))

        connection.commit()
        connection.close()

        # Player login
        session["player_id"] = player_id

        # Registration success page
        return render_template(
            "registration_success.html",
            tournament=tournament
        )

    connection.close()

    return render_template(
        "register.html",
        tournament=tournament
    )


# =========================
# PLAYER LOGIN
# =========================
@app.route(
    "/player/login",
    methods=["GET", "POST"]
)
def player_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_connection()

        player = connection.execute(
            "SELECT * FROM players WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if player and check_password_hash(
            player["password"],
            password
        ):

            session["player_id"] = player["id"]

            return redirect("/my-tournaments")

        return render_template(
            "player_login.html",
            error="Invalid email or password"
        )

    return render_template("player_login.html")


# =========================
# PLAYER LOGOUT
# =========================
@app.route("/player/logout")
def player_logout():

    session.pop("player_id", None)

    return redirect("/")


# =========================
# MY TOURNAMENTS
# =========================
@app.route("/my-tournaments")
def my_tournaments():

    player_id = session.get("player_id")

    if not player_id:
        return redirect("/player/login")

    connection = get_connection()

    player = connection.execute(
        "SELECT * FROM players WHERE id = ?",
        (player_id,)
    ).fetchone()

    tournaments = connection.execute("""
        SELECT
            t.*
        FROM tournaments t
        JOIN registrations r
            ON t.id = r.tournament_id
        WHERE r.player_id = ?
        ORDER BY t.id DESC
    """, (
        player_id,
    )).fetchall()

    connection.close()

    return render_template(
        "my_tournaments.html",
        player=player,
        tournaments=tournaments
    )


# =========================
# REGISTERED PLAYERS
# =========================
@app.route(
    "/admin/tournament/<int:tournament_id>/players"
)
def tournament_players(tournament_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    connection = get_connection()

    tournament = connection.execute(
        "SELECT * FROM tournaments WHERE id = ?",
        (tournament_id,)
    ).fetchone()

    players = connection.execute("""
        SELECT
            p.id,
            p.name,
            p.email,
            p.phone,
            r.registration_status,
            r.registered_at
        FROM registrations r
        JOIN players p
            ON r.player_id = p.id
        WHERE r.tournament_id = ?
        ORDER BY r.id DESC
    """, (
        tournament_id,
    )).fetchall()

    connection.close()

    if tournament is None:
        return "Tournament not found", 404

    return render_template(
        "tournament_players.html",
        tournament=tournament,
        players=players
    )


# =========================
# ROOM MANAGEMENT
# =========================
@app.route(
    "/admin/tournament/<int:tournament_id>/room",
    methods=["GET", "POST"]
)
def manage_room(tournament_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    connection = get_connection()

    tournament = connection.execute(
        "SELECT * FROM tournaments WHERE id = ?",
        (tournament_id,)
    ).fetchone()

    if tournament is None:

        connection.close()

        return "Tournament not found", 404

    if request.method == "POST":

        room_id = request.form["room_id"]
        room_password = request.form["room_password"]
        room_visible_at = request.form["room_visible_at"]

        connection.execute("""
            UPDATE tournaments
            SET
                room_id = ?,
                room_password = ?,
                room_visible_at = ?
            WHERE id = ?
        """, (
            room_id,
            room_password,
            room_visible_at,
            tournament_id
        ))

        connection.commit()
        connection.close()

        return redirect("/admin")

    connection.close()

    return render_template(
        "manage_room.html",
        tournament=tournament
    )


# =========================
# START SERVER
# =========================
if __name__ == "__main__":

    app.run(
        debug=True
    )