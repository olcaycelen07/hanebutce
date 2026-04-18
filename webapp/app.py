from __future__ import annotations

import os
import re
import secrets
import sqlite3
import smtplib
from calendar import monthrange
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import psycopg
    from psycopg.rows import dict_row
except ModuleNotFoundError:
    psycopg = None
    dict_row = None


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "data.db"
MAIL_LOG_PATH = BASE_DIR / "sent_invites.log"
POSTGRES_SCHEMA_PATH = BASE_DIR.parent / "docs" / "schema_postgres.sql"

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "change-this-secret-in-production"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
)

DEFAULT_CATEGORIES = {
    "income": ["Maas", "Serbest Is", "Kira Geliri", "Ek Gelir", "Diger"],
    "expense": ["Market", "Fatura", "Ulasim", "Egitim", "Saglik", "Diger"],
    "bill": ["Kira", "Elektrik", "Su", "Internet", "Kredi", "Aidat"],
}


SQLITE_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS households (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    owner_user_id INTEGER NOT NULL,
    plan_type TEXT NOT NULL DEFAULT 'free',
    currency_code TEXT NOT NULL DEFAULT 'TRY',
    created_at TEXT NOT NULL,
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS household_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    joined_at TEXT NOT NULL,
    UNIQUE (household_id, user_id),
    FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL,
    created_by_user_id INTEGER NOT NULL,
    member_user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    FOREIGN KEY (member_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL,
    created_by_user_id INTEGER NOT NULL,
    member_user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL DEFAULT 'Genel',
    due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    frequency TEXT NOT NULL DEFAULT 'one_time',
    last_generated_date TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    FOREIGN KEY (member_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS household_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (household_id, type, name),
    FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    invited_by_user_id INTEGER NOT NULL,
    accepted_by_user_id INTEGER,
    created_at TEXT NOT NULL,
    accepted_at TEXT,
    FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by_user_id) REFERENCES users(id),
    FOREIGN KEY (accepted_by_user_id) REFERENCES users(id)
);
"""


class DatabaseConnection:
    def __init__(self, connection, engine: str):
        self._connection = connection
        self.engine = engine

    def execute(self, query: str, params=None):
        normalized_query = query
        if self.engine == "postgres":
            normalized_query = normalized_query.replace("?", "%s")
            cursor = self._connection.cursor()
            try:
                cursor.execute(normalized_query, params or ())
            except Exception:
                cursor.close()
                raise
            return cursor
        return self._connection.execute(normalized_query, params or ())

    def executescript(self, script: str) -> None:
        if self.engine == "postgres":
            with self._connection.cursor() as cursor:
                cursor.execute(script)
        else:
            self._connection.executescript(script)

    def commit(self) -> None:
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url[len("postgres://") :]
    return database_url


def is_postgres_url(database_url: str | None) -> bool:
    if not database_url:
        return False
    scheme = urlparse(normalize_database_url(database_url)).scheme
    return scheme in {"postgres", "postgresql"}


def database_engine() -> str:
    return "postgres" if is_postgres_url(os.getenv("DATABASE_URL")) else "sqlite"


def create_db_connection():
    if database_engine() == "postgres":
        if psycopg is None or dict_row is None:
            raise RuntimeError("PostgreSQL baglantisi icin psycopg kurulumu gerekiyor.")
        return psycopg.connect(normalize_database_url(os.environ["DATABASE_URL"]), row_factory=dict_row)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def get_db() -> DatabaseConnection:
    if "db" not in g:
        g.db = DatabaseConnection(create_db_connection(), database_engine())
    return g.db


@app.teardown_appcontext
def close_db(_error) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = DatabaseConnection(create_db_connection(), database_engine())
    if db.engine == "postgres":
        db.executescript(POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8"))
    else:
        db.executescript(SQLITE_SCHEMA)
    ensure_column(db, "bills", "category", "TEXT NOT NULL DEFAULT 'Genel'")
    ensure_column(db, "bills", "frequency", "TEXT NOT NULL DEFAULT 'one_time'")
    ensure_column(db, "bills", "last_generated_date", "TEXT")
    db.commit()
    db.close()


def ensure_column(db: DatabaseConnection, table_name: str, column_name: str, definition: str) -> None:
    if db.engine == "postgres":
        columns = [
            row["column_name"]
            for row in db.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table_name,),
            ).fetchall()
        ]
        if column_name not in columns:
            postgres_definition = (
                definition.replace("TEXT", "TEXT")
                .replace("AUTOINCREMENT", "")
            )
            db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {postgres_definition}")
        return

    columns = [row[1] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()]
    if column_name not in columns:
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def validate_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Sifre en az 8 karakter olmali."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return False, "Sifre en az bir harf ve bir rakam icermeli."
    return True, ""


def ensure_csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(24)
        session["_csrf_token"] = token
    return token


def verify_csrf() -> bool:
    form_token = request.form.get("csrf_token", "")
    session_token = session.get("_csrf_token", "")
    return bool(form_token and session_token and secrets.compare_digest(form_token, session_token))


def smtp_settings() -> dict[str, str | int | bool | None]:
    return {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from_email": os.getenv("SMTP_FROM_EMAIL"),
        "from_name": os.getenv("SMTP_FROM_NAME", "HaneButce"),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
    }


def send_email_invitation(recipient_email: str, household_name: str, invite_url: str, role: str) -> tuple[bool, str]:
    settings = smtp_settings()
    if not settings["host"] or not settings["from_email"]:
        log_invitation_email(recipient_email, household_name, invite_url, role, "smtp-ayari-yok")
        return False, "SMTP ayarlari tanimli degil. Davet linki log dosyasina yazildi."

    message = EmailMessage()
    message["Subject"] = f"{household_name} ailesine davet edildin"
    message["From"] = f"{settings['from_name']} <{settings['from_email']}>"
    message["To"] = recipient_email
    plain_text = "\n".join(
        [
            "Merhaba,",
            "",
            f"{household_name} ailesine {role.upper()} rolunde davet edildin.",
            "HaneButce ile aile butcesi, gelir-gider takibi ve odeme planlarini birlikte yonetebilirsin.",
            "",
            "Daveti kabul etmek icin asagidaki linki ac:",
            invite_url,
            "",
            "Bu daveti sen beklemiyorsan bu e-postayi dikkate alma.",
            "",
            "HaneButce",
        ]
    )
    html_content = f"""
    <html>
      <body style="margin:0;padding:24px;background:#f5efe5;font-family:Segoe UI,Arial,sans-serif;color:#1f2937;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;margin:0 auto;">
          <tr>
            <td style="padding:0;">
              <div style="background:linear-gradient(135deg,#1f2937,#334155);border-radius:28px 28px 0 0;padding:28px 32px;color:#ffffff;">
                <div style="font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#fbbf24;margin-bottom:12px;">Aile Daveti</div>
                <div style="font-size:32px;line-height:1.1;font-weight:800;">{household_name} ailesine katil</div>
                <p style="margin:14px 0 0;color:rgba(255,255,255,0.8);font-size:16px;line-height:1.7;">
                  HaneButce uzerinden aile butcesi, giderler ve odemeler artik ortak yonetilecek.
                </p>
              </div>
              <div style="background:#fffdf9;border:1px solid rgba(31,41,55,0.08);border-top:none;border-radius:0 0 28px 28px;padding:32px;">
                <p style="margin:0 0 18px;font-size:16px;line-height:1.7;">
                  <strong>{recipient_email}</strong> adresi icin <strong>{role.upper()}</strong> rolunde bir davet olusturuldu.
                </p>
                <div style="background:#fff7e8;border:1px solid #fcd9a6;border-radius:18px;padding:18px 20px;margin-bottom:20px;">
                  <div style="font-size:13px;letter-spacing:0.14em;text-transform:uppercase;color:#b45309;margin-bottom:8px;">Bu davetle neler yapabilirsin?</div>
                  <div style="font-size:15px;line-height:1.8;color:#374151;">
                    Gelir ve gider takibi yapabilir, planlanan odemeleri gorebilir ve aile paneline katilabilirsin.
                  </div>
                </div>
                <a href="{invite_url}" style="display:inline-block;padding:16px 24px;border-radius:16px;background:#1f2937;color:#ffffff;text-decoration:none;font-weight:700;">
                  Daveti kabul et
                </a>
                <p style="margin:22px 0 10px;font-size:14px;line-height:1.8;color:#6b7280;">
                  Buton calismazsa bu linki tarayicina yapistir:
                </p>
                <p style="margin:0;padding:14px 16px;border-radius:14px;background:#1f2937;color:#f9fafb;font-size:13px;word-break:break-all;">
                  {invite_url}
                </p>
                <p style="margin:22px 0 0;font-size:14px;line-height:1.8;color:#6b7280;">
                  Bu daveti sen beklemiyorsan e-postayi yok sayabilirsin.
                </p>
              </div>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    message.set_content(plain_text)
    message.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP(settings["host"], settings["port"], timeout=15) as server:
            if settings["use_tls"]:
                server.starttls()
            if settings["username"] and settings["password"]:
                server.login(settings["username"], settings["password"])
            server.send_message(message)
        return True, "Davet e-postasi gonderildi."
    except Exception as exc:
        log_invitation_email(recipient_email, household_name, invite_url, role, f"gonderim-hatasi: {exc}")
        return False, "E-posta gonderilemedi. Davet linki log dosyasina yazildi."


def log_invitation_email(recipient_email: str, household_name: str, invite_url: str, role: str, reason: str) -> None:
    MAIL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MAIL_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(
            "\n".join(
                [
                    f"[{now_iso()}] {reason}",
                    f"Alici: {recipient_email}",
                    f"Hane: {household_name}",
                    f"Rol: {role}",
                    f"Link: {invite_url}",
                    "",
                ]
            )
        )


def month_bounds(month_value: str | None) -> tuple[str, str, str, str]:
    today = datetime.utcnow().date()
    default_month = today.strftime("%Y-%m")
    raw_month = month_value or default_month

    try:
        parsed = datetime.strptime(raw_month, "%Y-%m")
    except ValueError:
        parsed = datetime(today.year, today.month, 1)
        raw_month = default_month

    last_day = monthrange(parsed.year, parsed.month)[1]
    month_start = f"{parsed.year:04d}-{parsed.month:02d}-01"
    month_end = f"{parsed.year:04d}-{parsed.month:02d}-{last_day:02d}"
    month_label = parsed.strftime("%B %Y")
    return raw_month, month_start, month_end, month_label


def seed_default_categories(household_id: int) -> None:
    db = get_db()
    for category_type, names in DEFAULT_CATEGORIES.items():
        for name in names:
            insert_household_category(db, household_id, category_type, name)
    db.commit()


def fetch_categories(household_id: int, category_type: str):
    return get_db().execute(
        """
        SELECT name
        FROM household_categories
        WHERE household_id = ? AND type = ?
        ORDER BY name
        """,
        (household_id, category_type),
    ).fetchall()


def insert_household_category(db: DatabaseConnection, household_id: int, category_type: str, name: str) -> None:
    if db.engine == "postgres":
        db.execute(
            """
            INSERT INTO household_categories (household_id, type, name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (household_id, type, name) DO NOTHING
            """,
            (household_id, category_type, name, now_iso()),
        )
    else:
        db.execute(
            """
            INSERT OR IGNORE INTO household_categories (household_id, type, name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (household_id, category_type, name, now_iso()),
        )


def ensure_recurring_bills(household_id: int) -> None:
    db = get_db()
    today = datetime.utcnow().date().isoformat()
    recurring_bills = db.execute(
        """
        SELECT *
        FROM bills
        WHERE household_id = ? AND frequency != 'one_time'
        """,
        (household_id,),
    ).fetchall()

    for bill in recurring_bills:
        last_generated = bill["last_generated_date"] or bill["due_date"]
        if last_generated >= today:
            continue

        if bill["frequency"] == "monthly":
            last_date = datetime.strptime(last_generated, "%Y-%m-%d").date()
            months_apart = (datetime.utcnow().date().year - last_date.year) * 12 + (
                datetime.utcnow().date().month - last_date.month
            )
            if months_apart <= 0:
                continue

            next_month = datetime.utcnow().date().replace(day=min(last_date.day, 28)).isoformat()
            db.execute(
                """
                INSERT INTO bills (
                    household_id, created_by_user_id, member_user_id, title, amount, category,
                    due_date, status, frequency, last_generated_date, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (
                    bill["household_id"],
                    bill["created_by_user_id"],
                    bill["member_user_id"],
                    bill["title"],
                    bill["amount"],
                    bill["category"],
                    next_month,
                    bill["frequency"],
                    today,
                    bill["note"],
                    now_iso(),
                ),
            )
            db.execute("UPDATE bills SET last_generated_date = ? WHERE id = ?", (today, bill["id"]))

    db.commit()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def current_household():
    user = current_user()
    if not user:
        return None

    return get_db().execute(
        """
        SELECT h.*, hm.role
        FROM households h
        JOIN household_members hm ON hm.household_id = h.id
        WHERE hm.user_id = ?
        ORDER BY h.id
        LIMIT 1
        """,
        (user["id"],),
    ).fetchone()


def current_membership():
    household = current_household()
    if not household:
        return None
    return {"household_id": household["id"], "role": household["role"]}


def is_household_member(household_id: int, user_id: int) -> bool:
    row = get_db().execute(
        "SELECT id FROM household_members WHERE household_id = ? AND user_id = ?",
        (household_id, user_id),
    ).fetchone()
    return row is not None


def require_login():
    if not current_user():
        return redirect(url_for("login"))
    return None


def require_household_role(*allowed_roles: str):
    membership = current_membership()
    if not membership or membership["role"] not in allowed_roles:
        flash("Bu islem icin yetkin bulunmuyor.", "error")
        return redirect(url_for("dashboard"))
    return None


def ensure_member_in_household(household_id: int, member_user_id: str) -> bool:
    row = get_db().execute(
        "SELECT id FROM household_members WHERE household_id = ? AND user_id = ?",
        (household_id, member_user_id),
    ).fetchone()
    return row is not None


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        if request.endpoint in {"login", "register"}:
            ensure_csrf_token()
        if not verify_csrf():
            flash("Form guvenlik dogrulamasi basarisiz oldu. Lutfen tekrar dene.", "error")
            return redirect(request.referrer or url_for("login"))


@app.after_request
def apply_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    if os.getenv("ENABLE_HSTS", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.context_processor
def inject_globals():
    return {
        "current_user": current_user(),
        "current_household": current_household(),
        "csrf_token": ensure_csrf_token(),
    }


@app.template_filter("currency")
def currency_filter(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} TL"


@app.route("/")
def index():
    if current_user():
        if current_household():
            return redirect(url_for("dashboard"))
        return redirect(url_for("onboarding"))
    return redirect(url_for("login"))


@app.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not full_name or not email or not password:
            flash("Tum alanlari doldurman gerekiyor.", "error")
        elif not validate_email(email):
            flash("Gecerli bir e-posta adresi girmen gerekiyor.", "error")
        else:
            is_valid_password, password_message = validate_password(password)
            if not is_valid_password:
                flash(password_message, "error")
                return render_template("register.html")
            db = get_db()
            existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                flash("Bu e-posta zaten kayitli.", "error")
            else:
                db.execute(
                    """
                    INSERT INTO users (full_name, email, password_hash, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (full_name, email, generate_password_hash(password), now_iso()),
                )
                db.commit()
                flash("Kayit olusturuldu. Simdi giris yapabilirsin.", "success")
                return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("E-posta veya sifre hatali.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash("Hos geldin.", "success")
            if current_household():
                return redirect(url_for("dashboard"))
            return redirect(url_for("onboarding"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Cikis yapildi.", "success")
    return redirect(url_for("login"))


@app.route("/onboarding", methods=("GET", "POST"))
def onboarding():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    if current_household():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form["name"].strip()
        slug = request.form["slug"].strip().lower()
        user = current_user()
        db = get_db()

        if not name or not slug:
            flash("Hane adi ve kisa adres gerekli.", "error")
        elif not re.fullmatch(r"[a-z0-9-]+", slug):
            flash("Kisa adres sadece kucuk harf, rakam ve tire icerebilir.", "error")
        else:
            slug_exists = db.execute("SELECT id FROM households WHERE slug = ?", (slug,)).fetchone()
            if slug_exists:
                flash("Bu kisa adres kullaniliyor.", "error")
            else:
                cursor = db.execute(
                    """
                    INSERT INTO households (name, slug, owner_user_id, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, slug, user["id"], now_iso()),
                )
                household_id = cursor.lastrowid
                db.execute(
                    """
                    INSERT INTO household_members (household_id, user_id, role, joined_at)
                    VALUES (?, ?, 'owner', ?)
                    """,
                    (household_id, user["id"], now_iso()),
                )
                db.commit()
                seed_default_categories(household_id)
                flash("Hane olusturuldu.", "success")
                return redirect(url_for("dashboard"))

    return render_template("onboarding.html")


@app.route("/dashboard")
def dashboard():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    household = current_household()
    if not household:
        return redirect(url_for("onboarding"))

    db = get_db()
    seed_default_categories(household["id"])
    ensure_recurring_bills(household["id"])
    selected_month, month_start, month_end, month_label = month_bounds(request.args.get("month"))
    members = db.execute(
        """
        SELECT u.id, u.full_name, u.email, hm.role
        FROM household_members hm
        JOIN users u ON u.id = hm.user_id
        WHERE hm.household_id = ?
        ORDER BY hm.id
        """,
        (household["id"],),
    ).fetchall()

    transactions = db.execute(
        """
        SELECT t.*, u.full_name AS member_name
        FROM transactions t
        JOIN users u ON u.id = t.member_user_id
        WHERE t.household_id = ? AND t.transaction_date BETWEEN ? AND ?
        ORDER BY t.transaction_date DESC, t.id DESC
        LIMIT 12
        """,
        (household["id"], month_start, month_end),
    ).fetchall()

    bills = db.execute(
        """
        SELECT b.*, u.full_name AS member_name
        FROM bills b
        JOIN users u ON u.id = b.member_user_id
        WHERE b.household_id = ? AND b.due_date BETWEEN ? AND ?
        ORDER BY b.due_date ASC, b.id DESC
        """,
        (household["id"], month_start, month_end),
    ).fetchall()

    income_total = db.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE household_id = ? AND type = 'income' AND transaction_date BETWEEN ? AND ?
        """,
        (household["id"], month_start, month_end),
    ).fetchone()["total"]
    expense_total = db.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE household_id = ? AND type = 'expense' AND transaction_date BETWEEN ? AND ?
        """,
        (household["id"], month_start, month_end),
    ).fetchone()["total"]
    category_totals = db.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE household_id = ? AND type = 'expense' AND transaction_date BETWEEN ? AND ?
        GROUP BY category
        ORDER BY total DESC
        LIMIT 5
        """,
        (household["id"], month_start, month_end),
    ).fetchall()
    recurring_bill_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM bills
        WHERE household_id = ? AND frequency != 'one_time' AND due_date BETWEEN ? AND ?
        """,
        (household["id"], month_start, month_end),
    ).fetchone()["total"]
    pending_bill_total = db.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM bills
        WHERE household_id = ? AND status != 'paid' AND due_date BETWEEN ? AND ?
        """,
        (household["id"], month_start, month_end),
    ).fetchone()["total"]
    monthly_net = income_total - expense_total
    paid_bill_total = db.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM bills
        WHERE household_id = ? AND status = 'paid' AND due_date BETWEEN ? AND ?
        """,
        (household["id"], month_start, month_end),
    ).fetchone()["total"]
    top_income = db.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE household_id = ? AND type = 'income' AND transaction_date BETWEEN ? AND ?
        GROUP BY category
        ORDER BY total DESC
        LIMIT 3
        """,
        (household["id"], month_start, month_end),
    ).fetchall()
    invitations = db.execute(
        """
        SELECT i.*, u.full_name AS invited_by_name
        FROM invitations i
        JOIN users u ON u.id = i.invited_by_user_id
        WHERE i.household_id = ?
        ORDER BY i.id DESC
        LIMIT 8
        """,
        (household["id"],),
    ).fetchall()

    return render_template(
        "dashboard.html",
        members=members,
        transactions=transactions,
        bills=bills,
        income_categories=fetch_categories(household["id"], "income"),
        expense_categories=fetch_categories(household["id"], "expense"),
        bill_categories=fetch_categories(household["id"], "bill"),
        income_total=income_total,
        expense_total=expense_total,
        balance_total=income_total - expense_total,
        category_totals=category_totals,
        recurring_bill_count=recurring_bill_count,
        pending_bill_total=pending_bill_total,
        paid_bill_total=paid_bill_total,
        monthly_net=monthly_net,
        selected_month=selected_month,
        month_label=month_label,
        top_income=top_income,
        invitations=invitations,
    )


@app.route("/transactions/add", methods=("POST",))
def add_transaction():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    role_redirect = require_household_role("owner", "admin", "member")
    if role_redirect:
        return role_redirect

    household = current_household()
    db = get_db()
    title = request.form["title"].strip()
    transaction_type = request.form["type"]
    amount = request.form["amount"]
    category = (request.form.get("category") or "").strip()
    custom_category = (request.form.get("custom_category") or "").strip()
    member_user_id = request.form["member_user_id"]
    note = request.form["note"].strip()
    final_category = custom_category or category or "Genel"

    if not title or not amount or transaction_type not in {"income", "expense"}:
        flash("Islem kaydi icin gerekli alanlar eksik.", "error")
        return redirect(url_for("dashboard"))
    if not ensure_member_in_household(household["id"], member_user_id):
        flash("Secilen aile uyesi gecersiz.", "error")
        return redirect(url_for("dashboard"))

    insert_household_category(db, household["id"], transaction_type, final_category)

    db.execute(
        """
        INSERT INTO transactions (
            household_id, created_by_user_id, member_user_id, type, title, amount, category,
            transaction_date, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            household["id"],
            current_user()["id"],
            member_user_id,
            transaction_type,
            title,
            float(amount),
            final_category,
            datetime.utcnow().date().isoformat(),
            note,
            now_iso(),
        ),
    )
    db.commit()
    flash("Gelir / gider kaydi eklendi.", "success")
    return redirect(url_for("dashboard"))


@app.route("/bills/add", methods=("POST",))
def add_bill():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    role_redirect = require_household_role("owner", "admin", "member")
    if role_redirect:
        return role_redirect

    household = current_household()
    db = get_db()
    title = request.form["title"].strip()
    amount = request.form["amount"]
    category = (request.form.get("category") or "").strip()
    custom_category = (request.form.get("custom_category") or "").strip()
    due_date = request.form["due_date"]
    frequency = request.form.get("frequency", "one_time")
    member_user_id = request.form["member_user_id"]
    note = request.form["note"].strip()
    final_category = custom_category or category or "Genel"

    if not title or not amount or not due_date:
        flash("Odeme kaydi icin gerekli alanlar eksik.", "error")
        return redirect(url_for("dashboard"))

    if frequency not in {"one_time", "monthly"}:
        flash("Gecersiz tekrar araligi.", "error")
        return redirect(url_for("dashboard"))
    if not ensure_member_in_household(household["id"], member_user_id):
        flash("Secilen aile uyesi gecersiz.", "error")
        return redirect(url_for("dashboard"))

    insert_household_category(db, household["id"], "bill", final_category)

    status = "overdue" if due_date < datetime.utcnow().date().isoformat() else "pending"
    db.execute(
        """
        INSERT INTO bills (
            household_id, created_by_user_id, member_user_id, title, amount, category, due_date,
            status, frequency, last_generated_date, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            household["id"],
            current_user()["id"],
            member_user_id,
            title,
            float(amount),
            final_category,
            due_date,
            status,
            frequency,
            due_date if frequency != "one_time" else None,
            note,
            now_iso(),
        ),
    )
    db.commit()
    flash("Odeme kaydi eklendi.", "success")
    return redirect(url_for("dashboard"))


@app.route("/bills/<int:bill_id>/pay", methods=("POST",))
def mark_bill_paid(bill_id: int):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    role_redirect = require_household_role("owner", "admin", "member")
    if role_redirect:
        return role_redirect

    household = current_household()
    db = get_db()
    db.execute(
        "UPDATE bills SET status = 'paid' WHERE id = ? AND household_id = ?",
        (bill_id, household["id"]),
    )
    db.commit()
    flash("Odeme tamamlandi olarak isaretlendi.", "success")
    return redirect(url_for("dashboard"))


@app.route("/members/add", methods=("POST",))
def add_member():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    role_redirect = require_household_role("owner", "admin")
    if role_redirect:
        return role_redirect

    household = current_household()
    email = request.form["email"].strip().lower()
    role = request.form["role"].strip().lower()
    db = get_db()

    if role not in {"admin", "member"}:
        flash("Gecersiz rol.", "error")
        return redirect(url_for("dashboard"))
    if not validate_email(email):
        flash("Gecerli bir e-posta adresi girmen gerekiyor.", "error")
        return redirect(url_for("dashboard"))

    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user:
        flash("Bu e-posta ile kayitli kullanici bulunamadi. Once kayit olmasi gerekiyor.", "error")
        return redirect(url_for("dashboard"))

    exists = db.execute(
        "SELECT id FROM household_members WHERE household_id = ? AND user_id = ?",
        (household["id"], user["id"]),
    ).fetchone()
    if exists:
        flash("Bu kullanici zaten ailede yer aliyor.", "error")
        return redirect(url_for("dashboard"))

    db.execute(
        """
        INSERT INTO household_members (household_id, user_id, role, joined_at)
        VALUES (?, ?, ?, ?)
        """,
        (household["id"], user["id"], role, now_iso()),
    )
    db.commit()
    flash("Aile uyesi eklendi.", "success")
    return redirect(url_for("dashboard"))


@app.route("/invites/create", methods=("POST",))
def create_invitation():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    role_redirect = require_household_role("owner", "admin")
    if role_redirect:
        return role_redirect

    household = current_household()
    db = get_db()
    email = request.form["email"].strip().lower()
    role = request.form["role"].strip().lower()

    if role not in {"admin", "member"}:
        flash("Gecersiz davet rolu.", "error")
        return redirect(url_for("dashboard"))

    if not email:
        flash("Davet icin e-posta gerekli.", "error")
        return redirect(url_for("dashboard"))
    if not validate_email(email):
        flash("Gecerli bir e-posta adresi girmen gerekiyor.", "error")
        return redirect(url_for("dashboard"))

    existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing_user and is_household_member(household["id"], existing_user["id"]):
        flash("Bu kullanici zaten ailede yer aliyor.", "error")
        return redirect(url_for("dashboard"))

    active_invite = db.execute(
        """
        SELECT token
        FROM invitations
        WHERE household_id = ? AND email = ? AND status = 'pending'
        ORDER BY id DESC
        LIMIT 1
        """,
        (household["id"], email),
    ).fetchone()
    if active_invite:
        flash("Bu e-posta icin zaten bekleyen bir davet var.", "error")
        return redirect(url_for("dashboard"))

    token = secrets.token_urlsafe(24)
    db.execute(
        """
        INSERT INTO invitations (
            household_id, email, role, token, invited_by_user_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (household["id"], email, role, token, current_user()["id"], now_iso()),
    )
    db.commit()
    invite_url = url_for("accept_invitation", token=token, _external=True)
    email_sent, email_message = send_email_invitation(email, household["name"], invite_url, role)
    flash("Davet olusturuldu. Linki paylasabilirsin.", "success")
    flash(email_message, "success" if email_sent else "error")
    return redirect(url_for("dashboard"))


@app.route("/invite/<token>", methods=("GET", "POST"))
def accept_invitation(token: str):
    invitation = get_db().execute(
        """
        SELECT i.*, h.name AS household_name
        FROM invitations i
        JOIN households h ON h.id = i.household_id
        WHERE i.token = ?
        """,
        (token,),
    ).fetchone()

    if not invitation:
        flash("Davet bulunamadi.", "error")
        return redirect(url_for("login"))

    user = current_user()
    if request.method == "POST":
        redirect_response = require_login()
        if redirect_response:
            return redirect_response

        user = current_user()
        if user["email"].lower() != invitation["email"].lower():
            flash("Bu davet farkli bir e-posta adresi icin olusturulmus.", "error")
            return redirect(url_for("accept_invitation", token=token))

        if invitation["status"] != "pending":
            flash("Bu davet daha once kullanilmis.", "error")
            return redirect(url_for("dashboard"))

        if not is_household_member(invitation["household_id"], user["id"]):
            db = get_db()
            db.execute(
                """
                INSERT INTO household_members (household_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?)
                """,
                (invitation["household_id"], user["id"], invitation["role"], now_iso()),
            )
            db.execute(
                """
                UPDATE invitations
                SET status = 'accepted', accepted_by_user_id = ?, accepted_at = ?
                WHERE id = ?
                """,
                (user["id"], now_iso(), invitation["id"]),
            )
            db.commit()
        flash("Davet kabul edildi. Artik aile panelindesin.", "success")
        return redirect(url_for("dashboard"))

    return render_template("invite.html", invitation=invitation, user=user)


init_db()


if __name__ == "__main__":
    app.run(debug=True)
