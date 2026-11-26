"""Self-check. Run:  python check.py

Tells you exactly what is wrong (Python version, missing packages, database
connection, or the app itself). If anything says FAIL, copy the whole output
and send it to Claude.
"""
import os
import shutil
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version

all_ok = True


def step(name, fn):
    global all_ok
    try:
        detail = fn()
        print(f"[ OK ] {name}" + (f"  ({detail})" if detail else ""))
    except Exception as exc:  # noqa: BLE001
        all_ok = False
        print(f"[FAIL] {name}\n        {type(exc).__name__}: {exc}")


def check_python():
    if sys.version_info < (3, 10):
        raise RuntimeError(f"Python 3.10+ needed, you have {sys.version.split()[0]}")
    return sys.version.split()[0]


def check_packages():
    missing, found = [], []
    for pkg in ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "pydantic-settings",
                "PyJWT", "bcrypt", "python-multipart", "httpx", "pytest", "psycopg2-binary"]:
        try:
            found.append(f"{pkg} {version(pkg)}")
        except PackageNotFoundError:
            missing.append(pkg)
    if missing:
        raise RuntimeError("missing: " + ", ".join(missing) + "  ->  run: pip install -r requirements.txt")
    return f"{len(found)} packages found"


def check_database():
    from sqlalchemy import text

    from app.database import engine

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return str(engine.url.render_as_string(hide_password=True))


def check_app_flow():
    from datetime import date

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base, get_db
    from app.main import app

    tmp = tempfile.mkdtemp()
    test_engine = create_engine(
        "sqlite:///" + os.path.join(tmp, "check.db").replace("\\", "/"),
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(bind=test_engine, autoflush=False)
    Base.metadata.create_all(test_engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        creds = {"username": "check_user", "password": "password123"}
        r = client.post("/api/auth/register", json=creds)
        assert r.status_code == 201, f"register -> {r.status_code} {r.text}"
        r = client.post("/api/auth/login", data=creds)
        assert r.status_code == 200, f"login -> {r.status_code} {r.text}"
        headers = {"Authorization": "Bearer " + r.json()["access_token"]}

        r = client.post("/api/categories", json={"name": "Food"}, headers=headers)
        assert r.status_code == 201, f"category -> {r.status_code} {r.text}"
        cid = r.json()["id"]
        today = date.today().isoformat()
        for body in (
            {"type": "income", "amount": 1000, "occurred_on": today},
            {"type": "expense", "amount": 250.5, "occurred_on": today, "category_id": cid},
        ):
            r = client.post("/api/transactions", json=body, headers=headers)
            assert r.status_code == 201, f"transaction -> {r.status_code} {r.text}"

        r = client.get("/api/reports/monthly", headers=headers)
        assert r.status_code == 200, f"report -> {r.status_code} {r.text}"
        rep = r.json()
        assert rep["income"] == 1000 and rep["expense"] == 250.5 and rep["balance"] == 749.5, rep

        r = client.get("/api/transactions/export", headers=headers)
        assert r.status_code == 200 and "Food" in r.text, f"export -> {r.status_code}"
        r = client.get("/")
        assert r.status_code == 200 and "SpendWise" in r.text, f"web page -> {r.status_code}"
        return "register, login, category, transactions, report, CSV, web page"
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()
        shutil.rmtree(tmp, ignore_errors=True)


print("SpendWise self-check\n")
step("Python version", check_python)
step("Required packages", check_packages)
if all_ok:
    step("Database connection", check_database)
    step("App end-to-end (temporary database)", check_app_flow)

print()
if all_ok:
    print("All checks passed. Start the app with:  python -m uvicorn app.main:app --reload")
else:
    print("Some checks FAILED. Copy everything above and send it to Claude.")
    sys.exit(1)
