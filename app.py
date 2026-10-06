# -*- coding: utf-8 -*-
"""Water Conservation through Digital Monitoring."""

import html
import math
import os
import hashlib
import hmac
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


st.set_page_config(
    page_title="Water Conservation through Digital Monitoring",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_FILE = os.path.join(DB_DIR, "water_monitoring.db")
PBKDF2_ITERATIONS = 310_000
SPIKE_MULTIPLIER = 1.5
SPIKE_MIN_INCREASE_LITERS = 100
DEFAULT_TARGET_ALERT_PERCENT = 100
AREA_PRESETS = [
    "Main Building",
    "Hostel",
    "Canteen",
    "Garden",
    "Laboratory",
    "Household",
    "Office Block",
    "Workshop",
    "Sports Complex",
    "Clinic",
    "Admin Block",
    "Library",
    "Parking Area",
    "Water Treatment Plant",
    "Storage Tank",
    "Residential Block A",
    "Residential Block B",
    "Residential Block C",
    "Teaching Block",
    "Research Center",
    "Student Housing",
    "Staff Housing",
    "Guest House",
    "Boiler Room",
    "Cooling Tower",
    "Irrigation Zone 1",
    "Irrigation Zone 2",
    "Central Store",
    "Security Office",
    "Maintenance Yard",
    "Power House",
    "Wastewater Unit",
    "Water Pump Station",
    "Reservoir North",
    "Reservoir South",
    "Farm Plot A",
    "Farm Plot B",
    "Market Stall Area",
    "Commercial Plaza",
    "School Campus",
    "Community Hall",
    "Bus Depot",
    "Public Toilet Block",
    "Open Market",
    "Warehouse",
    "Distribution Hub",
    "Water Tank 1",
    "Water Tank 2",
    "Water Tank 3",
    "Engine Room",
    "Control Room",
    "Borewell Zone",
    "Ground Floor Lobby",
    "Upper Floor Wing",
    "North Annex",
    "South Annex",
    "East Wing",
    "West Wing",
]
USAGE_TYPES = [
    "General",
    "Sanitation",
    "Cooking",
    "Cleaning",
    "Irrigation",
    "Laboratory",
    "Other",
]


def page_heading(title, subtitle=None, icon="💧"):
    subtitle_html = (
        f"<p class='page-heading-subtitle'>{html.escape(subtitle)}</p>"
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div class="page-heading">
            <div class="page-heading-icon">{icon}</div>
            <div>
                <h1>{html.escape(title)}</h1>
                {subtitle_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_app_styles():
    st.markdown(
        """
        <style>
        :root {
            --ink: #142b45;
            --muted: #6d8298;
            --blue: #168bd2;
            --cyan: #42c6df;
            --green: #1db98a;
            --line: #e3edf4;
            --surface: #ffffff;
        }

        html { scroll-behavior: smooth; }
        .stApp {
            background:
                radial-gradient(ellipse at 82% 4%, rgba(67, 198, 223, .11), transparent 32rem),
                #f4f8fb;
            color: var(--ink);
            font-family: 'Segoe UI', 'Trebuchet MS', sans-serif;
        }
        [data-testid="stHeader"] {
            background: rgba(244, 248, 251, .88);
            backdrop-filter: blur(12px);
        }
        [data-testid="stMain"] > div {
            padding-top: 1.35rem;
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 1440px;
            padding-bottom: 3rem;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(165deg, #102d49 0%, #124d70 58%, #087f91 100%);
            border-right: 1px solid rgba(255,255,255,.09);
        }
        [data-testid="stSidebar"] * {
            color: #effaff;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            border-radius: 11px;
            padding: .35rem .5rem;
            transition: background .2s ease, transform .2s ease;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: rgba(255,255,255,.12);
            transform: translateX(3px);
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] [aria-checked="true"] {
            background: rgba(255,255,255,.15);
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button {
            color: #164663;
            background: rgba(255,255,255,.96);
            border: 0;
            border-radius: 12px;
            font-weight: 700;
            transition: transform .2s ease, box-shadow .2s ease;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(3, 20, 38, .2);
        }
        .brand-lockup {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px 4px 22px;
            animation: fade-up .65s both;
        }
        .brand-drop {
            display: grid;
            place-items: center;
            width: 44px;
            height: 44px;
            border-radius: 15px;
            background: rgba(255,255,255,.16);
            box-shadow: inset 0 0 0 1px rgba(255,255,255,.19);
            font-size: 1.35rem;
            animation: bob 3.4s ease-in-out infinite;
        }
        .brand-name { font: 800 1.12rem 'Segoe UI', sans-serif; letter-spacing: -.03em; }
        .brand-caption { color: rgba(239,250,255,.7) !important; font-size: .78rem; }

        .page-heading {
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 12px 0 22px;
            padding: 17px 21px;
            border: 1px solid rgba(255,255,255,.8);
            border-radius: 18px;
            background: linear-gradient(110deg, rgba(255,255,255,.95), rgba(231,247,250,.88));
            box-shadow: 0 8px 24px rgba(25, 69, 98, .055);
            animation: fade-up .55s both;
        }
        .page-heading-icon {
            display: grid;
            place-items: center;
            flex: 0 0 46px;
            width: 46px;
            height: 46px;
            border-radius: 15px;
            color: white;
            background: linear-gradient(135deg, #168bd2, #25b9a7);
            box-shadow: 0 6px 15px rgba(22,139,210,.2);
            font-size: 1.25rem;
        }
        .page-heading h1 {
            margin: 0;
            color: var(--ink);
            font: 800 clamp(1.45rem, 2.8vw, 2rem)/1.2 'Segoe UI', sans-serif;
            letter-spacing: -.04em;
        }
        .page-heading-subtitle { margin: 4px 0 0; color: var(--muted); font-size: .88rem; }

        .topbar-search {
            padding: 4px;
            border-radius: 14px;
            background: white;
            box-shadow: 0 5px 22px rgba(24, 71, 102, .06);
        }
        .topbar-search input {
            border: 0 !important;
            background: transparent !important;
        }
        .user-pill {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 10px;
            min-height: 48px;
            animation: fade-up .55s both;
        }
        .user-avatar {
            display: grid;
            place-items: center;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            color: white;
            background: linear-gradient(135deg, #158bd2, #35c4b1);
            font-weight: 800;
            box-shadow: 0 5px 14px rgba(22,139,210,.25);
        }
        .user-name { display: grid; color: var(--ink); font-size: .88rem; }
        .user-name span { color: var(--muted); font-size: .75rem; }

        .hero-banner {
            position: relative;
            overflow: hidden;
            margin: 14px 0 20px;
            padding: clamp(26px, 4vw, 42px);
            border: 1px solid rgba(255,255,255,.32);
            border-radius: 24px;
            color: white;
            background: linear-gradient(112deg, #0e5680 0%, #118bb0 58%, #29b9b2 100%);
            box-shadow: 0 17px 38px rgba(14, 93, 130, .19);
            animation: fade-up .65s .08s both;
        }
        .hero-banner::before, .hero-banner::after {
            position: absolute;
            content: "";
            pointer-events: none;
            border: 1px solid rgba(255,255,255,.14);
            border-radius: 50%;
        }
        .hero-banner::before {
            width: 330px; height: 330px; right: 10%; top: -230px;
            box-shadow: 0 0 0 28px rgba(255,255,255,.035), 0 0 0 58px rgba(255,255,255,.025);
            animation: drift 9s ease-in-out infinite alternate;
        }
        .hero-banner::after {
            width: 220px; height: 220px; right: -45px; bottom: -170px;
            box-shadow: 0 0 0 24px rgba(255,255,255,.05), 0 0 0 52px rgba(255,255,255,.035);
        }
        .hero-wrap {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
        }
        .hero-title {
            margin: 0;
            color: white;
            font: 800 clamp(1.8rem, 3.4vw, 2.65rem)/1.15 'Segoe UI', sans-serif;
            letter-spacing: -.045em;
        }
        .hero-subtitle { margin: 12px 0 0; color: rgba(255,255,255,.82); font-size: 1rem; }
        .hero-badge {
            padding: 14px 18px;
            border: 1px solid rgba(255,255,255,.25);
            border-radius: 16px;
            background: rgba(255,255,255,.13);
            backdrop-filter: blur(8px);
            color: white;
            font-weight: 700;
            line-height: 1.55;
            animation: bob 4s ease-in-out infinite;
        }

        .metric-card {
            position: relative;
            overflow: hidden;
            min-height: 132px;
            margin: 0 0 18px;
            padding: 20px;
            border: 1px solid var(--line);
            border-radius: 18px;
            background: var(--surface);
            box-shadow: 0 8px 24px rgba(25, 69, 98, .055);
            animation: fade-up .6s both;
            transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
        }
        .metric-card::after {
            position: absolute;
            content: "";
            width: 100px; height: 100px;
            right: -36px; bottom: -55px;
            border-radius: 50%;
            background: rgba(46, 183, 190, .08);
        }
        .metric-card:hover {
            transform: translateY(-5px);
            border-color: #b9dce9;
            box-shadow: 0 15px 30px rgba(25, 89, 122, .12);
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) .metric-card { animation-delay: .07s; }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) .metric-card { animation-delay: .14s; }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) .metric-card { animation-delay: .21s; }
        .metric-row { display: flex; align-items: center; justify-content: space-between; }
        .metric-label { color: var(--muted); font-size: .81rem; font-weight: 600; }
        .metric-icon {
            display: grid; place-items: center;
            width: 33px; height: 33px; border-radius: 11px;
            background: #e6f7f7; color: #118f9b;
        }
        .metric-value {
            margin-top: 12px;
            color: var(--ink);
            font: 800 clamp(1.45rem, 2vw, 1.9rem) 'Segoe UI', sans-serif;
            letter-spacing: -.04em;
        }
        .metric-meta { margin-top: 4px; color: #188e79; font-size: .76rem; font-weight: 600; }

        .panel-card, .list-card {
            margin: 0;
            padding: 18px 20px 8px;
            border: 1px solid var(--line);
            border-bottom: 0;
            border-radius: 18px 18px 0 0;
            background: white;
            box-shadow: 0 8px 24px rgba(25, 69, 98, .045);
            animation: fade-up .65s .12s both;
        }
        .panel-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }
        .panel-title {
            margin: 0;
            color: var(--ink);
            font: 750 1.08rem 'Segoe UI', sans-serif;
            letter-spacing: -.025em;
        }
        .select-badge {
            padding: 6px 10px;
            border-radius: 999px;
            color: #167da1;
            background: #eaf7fb;
            font-size: .72rem;
            font-weight: 700;
        }
        .pill-list { padding: 0 20px 15px; border: 1px solid var(--line); border-top: 0; border-radius: 0 0 18px 18px; background: white; }
        .pill-list-item {
            display: flex; align-items: center; justify-content: space-between;
            padding: 9px 2px; border-top: 1px solid #eef3f6;
        }
        .pill-left { display: flex; align-items: center; gap: 9px; }
        .pill-icon { width: 9px; height: 9px; border-radius: 50%; box-shadow: 0 0 0 4px rgba(29,139,210,.08); }
        .pill-value { color: var(--ink); font-size: .82rem; font-weight: 600; }
        .pill-sub { color: var(--muted); font-size: .8rem; font-weight: 700; }
        .list-card { padding-bottom: 16px; border-bottom: 1px solid var(--line); border-radius: 18px; }
        .link-button { color: var(--blue); font-size: .78rem; font-weight: 700; text-decoration: none; }
        .alert-row {
            display: flex; align-items: center; justify-content: space-between; gap: 10px;
            padding: 13px 0; border-bottom: 1px solid #edf2f5;
            animation: fade-up .45s both;
        }
        .alert-row:last-child { border-bottom: 0; }
        .alert-main { display: flex; align-items: center; gap: 11px; min-width: 0; }
        .alert-icon {
            display: grid; place-items: center; flex: 0 0 34px;
            width: 34px; height: 34px; border-radius: 12px;
        }
        .alert-icon.safe { color: #138f70; background: #e6f8f1; }
        .alert-icon.warn { color: #c17b13; background: #fff4dd; }
        .alert-text { display: grid; gap: 2px; color: var(--ink); font-size: .8rem; }
        .alert-text span, .alert-time { color: var(--muted); font-size: .73rem; }
        [data-testid="stPlotlyChart"] {
            padding: 0 12px 4px;
            border: 1px solid var(--line);
            border-top: 0;
            border-radius: 0 0 18px 18px;
            background: white;
            box-shadow: 0 8px 24px rgba(25, 69, 98, .045);
        }
        [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input, [data-testid="stSelectbox"] > div > div {
            border-radius: 11px;
        }
        [data-testid="stForm"] {
            width: 100%;
            padding: 22px;
            border: 1px solid var(--line);
            border-radius: 18px;
            background: rgba(255,255,255,.9);
            box-shadow: 0 10px 28px rgba(25, 69, 98, .06);
            animation: fade-up .5s both;
        }
        [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"],
        [data-testid="stButton"] button[kind="primary"] {
            color: white;
            border: 0;
            background: linear-gradient(105deg, #137fb8, #16a5a7);
        }
        [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button,
        [data-testid="stDownloadButton"] button {
            border-radius: 11px;
            transition: transform .18s ease, box-shadow .18s ease;
        }
        [data-testid="stButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 7px 17px rgba(22, 139, 210, .17);
        }
        [data-testid="stDataFrame"], [data-testid="stAlert"] {
            border-radius: 14px;
        }
        [data-testid="stMetric"] {
            height: 100%;
            padding: 17px 18px;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,.94);
            box-shadow: 0 7px 22px rgba(25, 69, 98, .05);
            animation: fade-up .5s both;
            transition: transform .2s ease, box-shadow .2s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 25px rgba(25, 89, 122, .1);
        }
        [data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
        [data-testid="stMetricValue"] { color: var(--ink); font-weight: 800; }
        [data-testid="stTabs"] [role="tablist"] {
            gap: 8px;
            padding: 6px;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: rgba(255,255,255,.78);
        }
        [data-testid="stTabs"] button[role="tab"] {
            min-height: 38px;
            border-radius: 10px;
            color: var(--muted);
            transition: background .2s ease, color .2s ease;
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: white;
            background: linear-gradient(105deg, #137fb8, #16a5a7);
        }
        [data-testid="stExpander"] {
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 15px;
            background: rgba(255,255,255,.9);
            box-shadow: 0 6px 18px rgba(25, 69, 98, .04);
        }
        [data-testid="stExpander"] summary { color: var(--ink); font-weight: 700; }
        [data-testid="stDataFrame"] {
            overflow: hidden;
            border: 1px solid var(--line);
            box-shadow: 0 7px 22px rgba(25, 69, 98, .045);
            animation: fade-up .45s both;
        }
        [data-testid="stPlotlyChart"] {
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,.94);
            box-shadow: 0 7px 22px rgba(25, 69, 98, .045);
            animation: fade-up .5s both;
        }
        [data-testid="stCaptionContainer"] { color: var(--muted); }
        [data-testid="stMarkdownContainer"] a { color: #087fa7; font-weight: 600; }
        [data-testid="stRadio"] [role="radiogroup"] { gap: 8px; }
        [data-testid="stSlider"] [role="slider"] { border-color: #168bd2; }
        h1, h2, h3 { color: var(--ink); font-family: 'Segoe UI', sans-serif; letter-spacing: -.035em; }

        @keyframes fade-up {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
        @keyframes drift { from { transform: translateX(-12px); } to { transform: translateX(20px); } }
        @media (max-width: 760px) {
            [data-testid="stMain"] > div { padding: .8rem .75rem 2rem; }
            .page-heading { align-items: flex-start; padding: 14px; }
            [data-testid="stForm"] { padding: 16px; }
            .hero-wrap { align-items: flex-start; flex-direction: column; }
            .hero-badge { padding: 9px 13px; font-size: .82rem; }
            .metric-card { min-height: 118px; padding: 15px; }
            .user-pill { justify-content: flex-start; margin: 4px 0 12px; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: .01ms !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



@contextmanager
def database_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with database_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS monitoring_sites (
                site_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                daily_target_liters REAL NOT NULL CHECK(daily_target_liters > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS water_readings (
                reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL REFERENCES monitoring_sites(site_id)
                    ON DELETE CASCADE,
                reading_date TEXT NOT NULL,
                liters REAL NOT NULL CHECK(liters >= 0),
                meter_previous REAL,
                meter_current REAL,
                usage_type TEXT NOT NULL DEFAULT 'General',
                recorded_by TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(site_id, reading_date)
            );

            CREATE TABLE IF NOT EXISTS alert_settings (
                settings_id INTEGER PRIMARY KEY CHECK(settings_id = 1),
                target_alert_percent REAL NOT NULL DEFAULT 100,
                spike_multiplier REAL NOT NULL DEFAULT 1.5,
                spike_min_increase_liters REAL NOT NULL DEFAULT 100,
                lookback_days INTEGER NOT NULL DEFAULT 7
            );

            INSERT OR IGNORE INTO alert_settings
                (settings_id, target_alert_percent, spike_multiplier,
                 spike_min_increase_liters, lookback_days)
            VALUES (1, 100, 1.5, 100, 7);
        """)
        user_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(users)")
        }
        if "role" not in user_columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'"
            )

        reading_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(water_readings)")
        }
        if "source" not in reading_columns:
            conn.execute(
                "ALTER TABLE water_readings "
                "ADD COLUMN source TEXT NOT NULL DEFAULT 'Manual estimate'"
            )
        for column, declaration in (
            ("meter_previous", "REAL"),
            ("meter_current", "REAL"),
            ("usage_type", "TEXT NOT NULL DEFAULT 'General'"),
            ("recorded_by", "TEXT NOT NULL DEFAULT ''"),
        ):
            if column not in reading_columns:
                conn.execute(
                    f"ALTER TABLE water_readings ADD COLUMN {column} {declaration}"
                )

def hash_password(password, salt=None):
    salt_bytes = secrets.token_bytes(16) if salt is None else bytes.fromhex(salt)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PBKDF2_ITERATIONS,
    )
    return salt_bytes.hex(), password_hash.hex()


def get_admin_setup_key():
    environment_key = os.environ.get("WATERGUARD_ADMIN_SETUP_KEY")
    if environment_key:
        return environment_key
    try:
        return str(st.secrets.get("admin_setup_key", ""))
    except StreamlitSecretNotFoundError:
        return ""


def register_user(username, email, password, admin_setup_key=""):
    username = username.strip()
    email = email.strip().lower()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        return False, "Username must be 3-32 characters using letters, numbers, dots, dashes, or underscores."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Enter a valid email address."
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    salt, password_hash = hash_password(password)
    try:
        with database_connection() as conn:
            admin_exists = conn.execute(
                "SELECT 1 FROM users WHERE role = 'admin' LIMIT 1"
            ).fetchone()
            configured_key = get_admin_setup_key()
            is_admin_setup = (
                admin_exists is None
                and bool(configured_key)
                and bool(admin_setup_key)
                and hmac.compare_digest(admin_setup_key, configured_key)
            )
            role = "admin" if is_admin_setup else "user"
            conn.execute(
                """INSERT INTO users (username, email, password_hash, salt, role)
                   VALUES (?, ?, ?, ?, ?)""",
                (username, email, password_hash, salt, role),
            )
    except sqlite3.IntegrityError:
        return False, "That username or email is already registered."
    st.cache_data.clear()
    if role == "admin":
        return True, "Account created with administrator access. Sign in to continue."
    return True, "Account created. Sign in to continue."


def login_user(identifier, password):
    identifier = identifier.strip()
    with database_connection() as conn:
        row = conn.execute(
                """SELECT user_id, username, email, password_hash, salt, role, created_at
               FROM users
               WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE""",
            (identifier, identifier),
        ).fetchone()

    if row is None:
        return None
    _, candidate_hash = hash_password(password, row["salt"])
    if not hmac.compare_digest(candidate_hash, row["password_hash"]):
        return None
    return {
        "id": row["user_id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def get_user_profile(user_id):
    with database_connection() as conn:
        row = conn.execute(
            """SELECT user_id, username, email, role, created_at
               FROM users WHERE user_id = ?""",
            (int(user_id),),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["user_id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def change_password(user_id, current_password, new_password):
    if len(new_password) < 8:
        return False, "New password must contain at least 8 characters."

    with database_connection() as conn:
        row = conn.execute(
            "SELECT password_hash, salt FROM users WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
        if row is None:
            return False, "Account not found."
        _, current_hash = hash_password(current_password, row["salt"])
        if not hmac.compare_digest(current_hash, row["password_hash"]):
            return False, "Current password is incorrect."

        new_salt, new_hash = hash_password(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE user_id = ?",
            (new_hash, new_salt, int(user_id)),
        )
    st.cache_data.clear()
    return True, "Password updated."


@st.cache_data(ttl=30)
def get_registered_users():
    with database_connection() as conn:
        rows = conn.execute(
            """SELECT user_id AS ID, username AS Username, email AS Email,
                      role AS Role, created_at AS "Created At"
               FROM users ORDER BY user_id"""
        ).fetchall()
    return pd.DataFrame(
        [dict(row) for row in rows],
        columns=["ID", "Username", "Email", "Role", "Created At"],
    )


def update_user_role(user_id, role):
    if role not in {"admin", "user"}:
        return False, "Choose a valid role."
    with database_connection() as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE user_id = ?", (int(user_id),)
        ).fetchone()
        if row is None:
            return False, "Account not found."
        if row["role"] == "admin" and role == "user":
            admin_count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin'"
            ).fetchone()[0]
            if admin_count <= 1:
                return False, "The last administrator cannot be demoted."
        conn.execute(
            "UPDATE users SET role = ? WHERE user_id = ?",
            (role, int(user_id)),
        )
    st.cache_data.clear()
    return True, "Account role updated."


def login_page():
    page_heading("Sign in", "Welcome back to your water conservation workspace.", "🔐")
    message = st.session_state.pop("auth_message", None)
    if message:
        st.success(message)

    with st.form("login_form"):
        identifier = st.text_input("Username or email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", width="stretch")

    if submitted:
        user = login_user(identifier, password)
        if user:
            st.session_state["user"] = user
            st.rerun()
        st.error("Username/email or password is incorrect.")


def register_page():
    page_heading(
        "Create an account",
        "Start monitoring water use and building better conservation habits.",
        "💧",
    )
    with st.form("register_form"):
        username = st.text_input("Username", max_chars=32)
        email = st.text_input("Email address")
        password = st.text_input("Password", type="password")
        confirmation = st.text_input("Confirm password", type="password")
        admin_setup_key = st.text_input(
            "Administrator setup key (optional)",
            type="password",
            help="Only the project owner should use the key configured in the app's deployment secrets.",
        )
        submitted = st.form_submit_button(
            "Create account", type="primary", width="stretch"
        )

    if submitted:
        if password != confirmation:
            st.error("Passwords do not match.")
            return
        success, message = register_user(
            username, email, password, admin_setup_key
        )
        if success:
            st.session_state["auth_message"] = message
            st.session_state["auth_redirect_to_login"] = True
            st.rerun()
        st.error(message)


@st.cache_data(ttl=30)
def get_sites():
    with database_connection() as conn:
        rows = conn.execute(
            """SELECT site_id, name, daily_target_liters
               FROM monitoring_sites ORDER BY name"""
        ).fetchall()
    return [dict(row) for row in rows]


def add_site(name, daily_target_liters):
    clean_name = name.strip()
    if not clean_name:
        return False, "Enter a location name."
    if len(clean_name) > 100:
        return False, "Location name is too long. Use 100 characters or fewer."
    if daily_target_liters <= 0:
        return False, "The daily target must be greater than zero."

    try:
        with database_connection() as conn:
            conn.execute(
                """INSERT INTO monitoring_sites (name, daily_target_liters)
                   VALUES (?, ?)""",
                (clean_name, float(daily_target_liters)),
            )
        st.cache_data.clear()
        return True, "Monitoring location added."
    except sqlite3.IntegrityError:
        return False, "A location with that name already exists."


def get_meter_defaults(site_id, reading_date):
    with database_connection() as conn:
        same_day = conn.execute(
            """SELECT meter_previous, meter_current FROM water_readings
               WHERE site_id = ? AND reading_date = ?""",
            (int(site_id), reading_date.isoformat()),
        ).fetchone()
        if same_day is not None and same_day["meter_previous"] is not None:
            return float(same_day["meter_previous"]), float(same_day["meter_current"])

        previous = conn.execute(
            """SELECT meter_current FROM water_readings
               WHERE site_id = ? AND reading_date < ? AND meter_current IS NOT NULL
               ORDER BY reading_date DESC LIMIT 1""",
            (int(site_id), reading_date.isoformat()),
        ).fetchone()
    baseline = float(previous["meter_current"]) if previous is not None else 0.0
    return baseline, baseline


def save_reading(site_id, reading_date, meter_previous, meter_current,
                 usage_type, notes, source, recorded_by):
    meter_previous = float(meter_previous)
    meter_current = float(meter_current)
    if not math.isfinite(meter_previous) or not math.isfinite(meter_current):
        return False, "Meter readings must be finite numbers."
    if meter_previous < 0 or meter_current < 0:
        return False, "Meter readings cannot be negative."
    if meter_current < meter_previous:
        return False, "Current meter reading cannot be less than the previous reading."

    liters = meter_current - meter_previous
    with database_connection() as conn:
        conn.execute(
            """INSERT INTO water_readings
                   (site_id, reading_date, liters, meter_previous, meter_current,
                    usage_type, notes, source, recorded_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(site_id, reading_date) DO UPDATE SET
                   liters = excluded.liters,
                   meter_previous = excluded.meter_previous,
                   meter_current = excluded.meter_current,
                   usage_type = excluded.usage_type,
                   notes = excluded.notes,
                   source = excluded.source,
                   recorded_by = excluded.recorded_by,
                   updated_at = CURRENT_TIMESTAMP""",
            (
                int(site_id),
                reading_date.isoformat(),
                liters,
                meter_previous,
                meter_current,
                usage_type,
                notes.strip(),
                source,
                recorded_by,
            ),
        )
    st.cache_data.clear()
    return True, liters


@st.cache_data(ttl=30)
def get_readings():
    with database_connection() as conn:
        rows = conn.execute(
            """SELECT r.reading_id AS ID,
                      r.reading_date AS Date,
                      s.name AS Location,
                      r.liters AS Liters,
                      s.daily_target_liters AS "Daily Target",
                      r.meter_previous AS "Previous Meter",
                      r.meter_current AS "Current Meter",
                      r.usage_type AS "Usage Type",
                      r.source AS Source,
                      r.recorded_by AS "Recorded By",
                      r.notes AS Notes
               FROM water_readings AS r
               JOIN monitoring_sites AS s ON s.site_id = r.site_id
               ORDER BY r.reading_date, s.name"""
        ).fetchall()
    columns = [
        "ID", "Date", "Location", "Liters", "Daily Target",
        "Previous Meter", "Current Meter", "Usage Type", "Source",
        "Recorded By", "Notes",
    ]
    return pd.DataFrame([dict(row) for row in rows], columns=columns)


def delete_reading(reading_id):
    with database_connection() as conn:
        conn.execute(
            "DELETE FROM water_readings WHERE reading_id = ?",
            (int(reading_id),),
        )
    st.cache_data.clear()


@st.cache_data(ttl=30)
def get_alert_settings():
    with database_connection() as conn:
        row = conn.execute(
            """SELECT target_alert_percent, spike_multiplier,
                      spike_min_increase_liters, lookback_days
               FROM alert_settings WHERE settings_id = 1"""
        ).fetchone()
    return dict(row)


def save_alert_settings(target_alert_percent, spike_multiplier,
                        spike_min_increase_liters, lookback_days):
    target_alert_percent = float(target_alert_percent)
    spike_multiplier = float(spike_multiplier)
    spike_min_increase_liters = float(spike_min_increase_liters)
    lookback_days = int(lookback_days)

    if target_alert_percent < 100 or target_alert_percent > 300:
        return False, "Daily target alert threshold must stay between 100% and 300%."
    if spike_multiplier < 1.1 or spike_multiplier > 5.0:
        return False, "Usage spike multiplier must remain between 1.1x and 5.0x."
    if spike_min_increase_liters < 0 or spike_min_increase_liters > 1_000_000:
        return False, "Minimum increase above baseline must stay within a realistic range."
    if lookback_days < 1 or lookback_days > 30:
        return False, "Alert lookback period must be between 1 and 30 days."

    with database_connection() as conn:
        conn.execute(
            """UPDATE alert_settings
               SET target_alert_percent = ?, spike_multiplier = ?,
                   spike_min_increase_liters = ?, lookback_days = ?
               WHERE settings_id = 1""",
            (
                target_alert_percent,
                spike_multiplier,
                spike_min_increase_liters,
                lookback_days,
            ),
        )
    st.cache_data.clear()
    return True, "Alert settings saved."


def find_recent_alerts(readings):
    columns = ["Date", "Location", "Alert", "Usage (L)", "Reference (L)"]
    if readings.empty:
        return pd.DataFrame(columns=columns)

    settings = get_alert_settings()
    cutoff = date.today() - timedelta(days=int(settings["lookback_days"]) - 1)
    alerts = []
    ordered = readings.sort_values(["Location", "Date"])

    for location, group in ordered.groupby("Location", sort=False):
        previous_usage = []
        for _, row in group.iterrows():
            usage = float(row["Liters"])
            target = float(row["Daily Target"])
            reading_date = pd.Timestamp(row["Date"]).date()

            target_threshold = target * float(settings["target_alert_percent"]) / 100
            if reading_date >= cutoff and usage > target_threshold:
                alerts.append({
                    "Date": reading_date.isoformat(),
                    "Location": location,
                    "Alert": (
                        "Daily target exceeded"
                        if settings["target_alert_percent"] == 100
                        else f"Usage above {settings['target_alert_percent']:g}% of daily target"
                    ),
                    "Usage (L)": usage,
                    "Reference (L)": target_threshold,
                })

            if len(previous_usage) >= 3:
                baseline = float(pd.Series(previous_usage[-7:]).median())
                threshold = max(
                    baseline * float(settings["spike_multiplier"]),
                    baseline + float(settings["spike_min_increase_liters"]),
                )
                if reading_date >= cutoff and usage >= threshold:
                    alerts.append({
                        "Date": reading_date.isoformat(),
                        "Location": location,
                        "Alert": "Possible usage spike; check for leaks or unusual activity",
                        "Usage (L)": usage,
                        "Reference (L)": baseline,
                    })

            previous_usage.append(usage)

    return pd.DataFrame(alerts, columns=columns).sort_values(
        ["Date", "Location"], ascending=[False, True]
    )


def alert_settings_page():
    page_heading(
        "Alert Settings",
        "Configure shared usage thresholds and monitoring windows.",
        "🔔",
    )
    settings = get_alert_settings()

    with st.form("alert_settings_form"):
        left, right = st.columns(2)
        with left:
            target_alert_percent = st.number_input(
                "Daily target alert threshold (%)",
                min_value=100.0,
                max_value=300.0,
                value=float(settings["target_alert_percent"]),
                step=5.0,
                help="Alert when a reading exceeds this percentage of its site's daily target.",
            )
            spike_multiplier = st.number_input(
                "Usage spike multiplier",
                min_value=1.1,
                max_value=5.0,
                value=float(settings["spike_multiplier"]),
                step=0.1,
                help="A spike must reach at least this multiple of the recent baseline.",
            )
        with right:
            spike_min_increase_liters = st.number_input(
                "Minimum increase above baseline (liters)",
                min_value=0.0,
                max_value=1_000_000.0,
                value=float(settings["spike_min_increase_liters"]),
                step=25.0,
            )
            lookback_days = st.slider(
                "Alert lookback period (days)",
                min_value=1,
                max_value=30,
                value=int(settings["lookback_days"]),
            )
        submitted = st.form_submit_button(
            "Save alert settings", type="primary", width="stretch"
        )

    if submitted:
        success, message = save_alert_settings(
            target_alert_percent,
            spike_multiplier,
            spike_min_increase_liters,
            lookback_days,
        )
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)


def set_app_page(page):
    st.session_state["app_page"] = page


def dashboard_page(user):
    readings = get_readings()
    sites = get_sites()
    today = date.today()

    if readings.empty:
        total_use = 0.0
        water_saved = 0.0
        active_locations = 0
        trend_pct = 0.0
        daily_total = 0.0
    else:
        total_use = float(readings["Liters"].sum())
        water_saved = float((readings["Daily Target"] - readings["Liters"]).clip(lower=0).sum())
        active_locations = len(readings["Location"].unique())

        current_week = readings[pd.to_datetime(readings["Date"]).dt.date >= today - timedelta(days=6)]
        previous_week = readings[
            (pd.to_datetime(readings["Date"]).dt.date >= today - timedelta(days=13))
            & (pd.to_datetime(readings["Date"]).dt.date < today - timedelta(days=6))
        ]
        current_week_total = float(current_week["Liters"].sum()) if not current_week.empty else 0.0
        previous_week_total = float(previous_week["Liters"].sum()) if not previous_week.empty else 0.0
        trend_pct = ((current_week_total - previous_week_total) / previous_week_total * 100) if previous_week_total else 0.0
        daily_total = float(readings.groupby("Date")["Liters"].sum().mean()) if not readings.empty else 0.0

    alerts = find_recent_alerts(readings)
    area_usage = readings.groupby("Location", as_index=False)["Liters"].sum() if not readings.empty else pd.DataFrame(columns=["Location", "Liters"])
    if not area_usage.empty:
        area_usage = area_usage.sort_values("Liters", ascending=False)
        highest_area = area_usage.iloc[0]
    else:
        highest_area = {"Location": "No data", "Liters": 0.0}

    topbar_search, topbar_user = st.columns([4, 1.15])
    with topbar_search:
        st.markdown('<div class="topbar-search">', unsafe_allow_html=True)
        search_value = st.text_input(
            "Search",
            placeholder="Search location, sensor, or report...",
            label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)
    with topbar_user:
        st.markdown(
            f"""
            <div class="user-pill">
                <div class="user-avatar">{html.escape(user["username"][:2].upper())}</div>
                <div class="user-name">
                    <strong>{html.escape(user["username"])}</strong>
                    <span>{html.escape(user["role"].title())}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="hero-banner">
            <div class="hero-wrap">
                <div>
                    <h1 class="hero-title">Welcome Back, {html.escape(user["username"])}!</h1>
                    <p class="hero-subtitle">Monitor • Conserve • Make a Difference</p>
                </div>
                <div class="hero-badge">Clean Water<br>Brighter Tomorrow</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_data = [
        ("Total Water Usage", f"{total_use:,.0f} L", f"{'↓' if trend_pct > 0 else '↑'} {abs(trend_pct):.0f}% vs last week", ""),
        ("Water Saved", f"{water_saved:,.0f} L", f"{'↑' if water_saved > 0 else '→'} {max(water_saved,0):,.0f} L", ""),
        ("Locations with Readings", f"{active_locations}", f"{len(sites)} locations configured", ""),
        ("Conservation Score", f"{min(100, max(0, int((1 - (total_use / max(total_use + 500, 1)))*100))):d}%", f"{'↑' if trend_pct <= 0 else '↓'} {abs(trend_pct):.0f}% vs last week", ""),
    ]
    cols = st.columns(4)
    for col, (label, value, note, icon) in zip(cols, metric_data):
        icon_html = f"<div class='metric-icon'>{icon}</div>" if icon else ""
        col.markdown(
            f"<div class='metric-card'><div class='metric-row'><div class='metric-label'>{label}</div>{icon_html}</div><div class='metric-value'>{value}</div><div class='metric-meta'>{note}</div></div>",
            unsafe_allow_html=True,
        )

    content_cols = st.columns([1.7, 1.1])
    with content_cols[0]:
        st.markdown("""
        <div class="panel-card">
            <div class="panel-head">
                <h3 class="panel-title">Water Usage Trend</h3>
                <span class="select-badge">Last 7 Days</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if readings.empty:
            st.info("No readings available yet.")
        else:
            chart_data = readings.copy()
            chart_data["Date"] = pd.to_datetime(chart_data["Date"])
            chart_data = chart_data.groupby("Date", as_index=False)["Liters"].sum()
            chart = px.line(
                chart_data,
                x="Date",
                y="Liters",
                markers=True,
                labels={"Date": "", "Liters": "Usage (L)"},
                color_discrete_sequence=["#3b82f6"],
            )
            chart.update_layout(
                height=250,
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                font={"family": "Manrope, sans-serif", "color": "#6076a5", "size": 10},
                xaxis={"showgrid": False, "title": None},
                yaxis={"showgrid": True, "gridcolor": "#edf2ff", "title": None},
            )
            st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

    with content_cols[1]:
        st.markdown("""
        <div class="panel-card">
            <div class="panel-head">
                <h3 class="panel-title">Reading Sources</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if readings.empty:
            st.info("Add readings to see the distribution by reading source.")
        else:
            source_data = readings.groupby("Source", as_index=False)["Liters"].sum()
            donut = px.pie(
                source_data,
                values="Liters",
                names="Source",
                hole=0.55,
                color_discrete_sequence=["#1d9bf0", "#32c48d", "#f6b93b", "#6ec5ff"],
            )
            donut.update_layout(
                height=260,
                margin={"l": 0, "r": 0, "t": 0, "b": 0},
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            donut.update_traces(textinfo='none')
            st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})

    lower_cols = st.columns([1.2, 1])
    with lower_cols[0]:
        st.markdown("""
        <div class='list-card'>
            <div class='panel-head'><h3 class='panel-title'>Recent Alerts</h3><a class='link-button' href='#'>View All</a></div>
        </div>
        """, unsafe_allow_html=True)
        if alerts.empty:
            st.success("No recent alerts.")
        else:
            for _, row in alerts.head(4).iterrows():
                alert_kind = "warn" if "Possible usage spike" in row["Alert"] or "Daily target exceeded" in row["Alert"] else "safe"
                alert_text = html.escape(str(row["Alert"]))
                alert_location = html.escape(str(row["Location"]))
                st.markdown(
                    f"<div class='alert-row'><div class='alert-main'><div class='alert-icon {alert_kind}'>{'⚠' if alert_kind == 'warn' else '✓'}</div><div class='alert-text'><strong>{alert_text}</strong><span>{alert_location}</span></div></div><div class='alert-time'>{pd.Timestamp(row['Date']).strftime('%H:%M')}</div></div>",
                    unsafe_allow_html=True,
                )

    with lower_cols[1]:
        st.markdown("""
        <div class='list-card'>
            <div class='panel-head'><h3 class='panel-title'>Conservation Insights</h3></div>
        </div>
        """, unsafe_allow_html=True)
        insights = [
            ("Regular meter readings make water-use trends easier to spot.", "💧"),
            ("Fixing leaks can save up to 500 L per month.", "🛠️"),
            ("Use low-flow fixtures to reduce water usage.", "🚿"),
        ]
        for text, icon in insights:
            st.markdown(
                f"<div class='alert-row'><div class='alert-main'><div class='alert-icon safe'>{icon}</div><div class='alert-text'><strong>{text}</strong></div></div><div class='alert-time'>›</div></div>",
                unsafe_allow_html=True,
            )


def record_usage_page(user):
    page_heading(
        "Record Water Usage",
        "Enter cumulative meter values; consumption is calculated automatically.",
        "📈",
    )
    sites = get_sites()
    if not sites:
        st.info("Add a monitoring location before recording usage.")
        return

    site_by_name = {site["name"]: site for site in sites}
    location = st.selectbox("Area / location", list(site_by_name))
    reading_date = st.date_input(
        "Reading date", value=date.today(), max_value=date.today()
    )
    selected_site = site_by_name[location]
    default_previous, default_current = get_meter_defaults(
        selected_site["site_id"], reading_date
    )
    st.caption("Consumption = current meter reading - previous meter reading")
    with st.form("usage_form"):
        previous_meter = st.number_input(
            "Previous meter reading (liters)",
            min_value=0.0,
            value=default_previous,
            step=1.0,
        )
        current_meter = st.number_input(
            "Current meter reading (liters)",
            min_value=0.0,
            value=default_current,
            step=1.0,
        )
        usage_type = st.selectbox(
            "Usage type", USAGE_TYPES
        )
        source = st.selectbox(
            "Reading source", ["Water meter", "Flow sensor", "Manual estimate"]
        )
        notes = st.text_area(
            "Notes", placeholder="Optional: maintenance, or other context"
        )
        submitted = st.form_submit_button(
            "Save reading", type="primary", width="stretch"
        )

    if submitted:
        success, result = save_reading(
            selected_site["site_id"],
            reading_date,
            previous_meter,
            current_meter,
            usage_type,
            notes,
            source,
            user["username"],
        )
        if success:
            st.success(
                f"Reading saved: {result:,.1f} liters consumed. "
                "Saving this location and date again updates that reading."
            )
        else:
            st.error(result)


def monitoring_sites_page():
    page_heading(
        "Monitoring Sites",
        "Set up monitoring locations and daily water-use targets.",
        "📍",
    )

    with st.form("site_form"):
        preset_choice = st.selectbox(
            "Area / location preset",
            AREA_PRESETS + ["Custom location"],
            index=0,
        )
        if preset_choice == "Custom location":
            name = st.text_input(
                "Location name",
                placeholder="For example, East Residential Zone",
            )
        else:
            name = preset_choice
        target = st.number_input(
            "Daily target (liters)",
            min_value=1.0,
            max_value=1_000_000_000.0,
            value=5000.0,
            step=100.0,
        )
        submitted = st.form_submit_button(
            "Add location", type="primary", width="stretch"
        )

    if submitted:
        success, message = add_site(name, target)
        if success:
            st.success(message)
        else:
            st.error(message)

    sites = get_sites()
    if sites:
        site_frame = pd.DataFrame(sites).rename(columns={
            "name": "Location",
            "daily_target_liters": "Daily target (L)",
        })
        st.subheader("Configured locations")
        st.dataframe(
            site_frame[["Location", "Daily target (L)"]],
            width="stretch",
            hide_index=True,
        )
        site_by_name = {site["name"]: site for site in sites}
        with st.expander("Update a daily target"):
            with st.form("target_form"):
                selected_site = st.selectbox("Location", list(site_by_name))
                selected_id = site_by_name[selected_site]["site_id"]
                new_target = st.number_input(
                    "Daily target (liters)",
                    min_value=1.0,
                    max_value=1_000_000_000.0,
                    value=float(site_by_name[selected_site]["daily_target_liters"]),
                    step=100.0,
                    key=f"target_{selected_id}",
                )
                update_submitted = st.form_submit_button("Update target")
            if update_submitted:
                with database_connection() as conn:
                    conn.execute(
                        "UPDATE monitoring_sites SET daily_target_liters = ? WHERE site_id = ?",
                        (float(new_target), int(selected_id)),
                    )
                st.success("Daily target updated.")
                st.rerun()
    else:
        st.info("No locations have been added yet.")


def analytics_page():
    page_heading(
        "Analytics",
        "Explore water consumption patterns across days, locations, and usage types.",
        "📊",
    )
    readings = get_readings()
    if readings.empty:
        st.info("Record water usage to see consumption analytics.")
        return

    chart_data = readings.copy()
    chart_data["Date"] = pd.to_datetime(chart_data["Date"])
    daily = chart_data.groupby("Date", as_index=False)["Liters"].sum()
    weekly = chart_data.assign(
        Week=chart_data["Date"].dt.to_period("W").dt.start_time
    ).groupby("Week", as_index=False)["Liters"].sum()
    monthly = chart_data.assign(
        Month=chart_data["Date"].dt.to_period("M").dt.to_timestamp()
    ).groupby("Month", as_index=False)["Liters"].sum()
    area_usage = chart_data.groupby("Location", as_index=False)["Liters"].sum()
    area_usage = area_usage.sort_values("Liters", ascending=False)
    type_usage = chart_data.groupby("Usage Type", as_index=False)["Liters"].sum()
    type_usage = type_usage.sort_values("Liters", ascending=False)

    highest_area = area_usage.iloc[0]
    summary = st.columns(3)
    summary[0].metric("Highest-use area", highest_area["Location"])
    summary[1].metric("Area consumption", f"{highest_area['Liters']:,.0f} L")
    summary[2].metric("Recorded days", chart_data["Date"].dt.date.nunique())

    daily_tab, weekly_tab, monthly_tab = st.tabs(
        ["Daily", "Weekly", "Monthly"]
    )
    with daily_tab:
        daily_chart = px.line(
            daily, x="Date", y="Liters", markers=True,
            labels={"Date": "", "Liters": "Liters"},
        )
        st.plotly_chart(daily_chart, width="stretch")
    with weekly_tab:
        weekly_chart = px.bar(
            weekly, x="Week", y="Liters",
            labels={"Week": "Week starting", "Liters": "Liters"},
            color_discrete_sequence=["#318879"],
        )
        st.plotly_chart(weekly_chart, width="stretch")
    with monthly_tab:
        monthly_chart = px.bar(
            monthly, x="Month", y="Liters",
            labels={"Month": "", "Liters": "Liters"},
            color_discrete_sequence=["#318879"],
        )
        st.plotly_chart(monthly_chart, width="stretch")

    area_column, type_column = st.columns(2)
    with area_column:
        st.subheader("Area-wise consumption")
        area_chart = px.bar(
            area_usage, x="Location", y="Liters",
            labels={"Location": "", "Liters": "Liters"},
            color_discrete_sequence=["#318879"],
        )
        st.plotly_chart(area_chart, width="stretch")
    with type_column:
        st.subheader("Usage-type comparison")
        type_chart = px.bar(
            type_usage, x="Usage Type", y="Liters",
            labels={"Usage Type": "", "Liters": "Liters"},
            color_discrete_sequence=["#cc941f"],
        )
        st.plotly_chart(type_chart, width="stretch")


def insights_reports_page():
    page_heading(
        "Insights and Reports",
        "Review conservation checks, practical recommendations, and reading history.",
        "🌱",
    )
    readings = get_readings()
    if readings.empty:
        st.info("Record water usage to see conservation insights and reports.")
        return

    alerts = find_recent_alerts(readings)
    st.subheader("Conservation checks")
    if alerts.empty:
        st.success("No recent target exceedances or usage spikes were found.")
    else:
        st.dataframe(alerts, width="stretch", hide_index=True)

    recent_cutoff = date.today() - timedelta(days=29)
    parsed_dates = pd.to_datetime(readings["Date"]).dt.date
    recent = readings.loc[parsed_dates >= recent_cutoff]
    if recent.empty:
        recent = readings
        st.caption("No readings in the last 30 days; recommendations use the available readings.")

    st.subheader("Suggested actions")
    over_target = recent[recent["Liters"] > recent["Daily Target"]]
    if over_target.empty:
        st.write("Recent readings are within their configured daily targets. Continue regular monitoring.")
    else:
        for location, group in over_target.groupby("Location"):
            st.write(
                f"{location}: {len(group)} recorded day(s) exceeded the daily target. "
                "Review high-use activities, taps, toilets, irrigation, and meter readings."
            )
    st.write("Investigate sudden increases promptly; inspect plumbing and confirm the meter reading before concluding there is a leak.")
    st.write("Compare readings over consistent periods and share the results with people using the monitored location.")
    st.markdown(
        "- Repair leaking taps and pipes.\n"
        "- Avoid unnecessary water use and reuse suitable water where possible.\n"
        "- Consider rainwater harvesting and water-efficient equipment.\n"
        "- Reduce excessive garden watering by adjusting irrigation to conditions."
    )

    st.subheader("Reading log")
    filters = st.columns(3)
    record_search = filters[0].text_input(
        "Search records", placeholder="Search records..."
    ).strip().casefold()
    locations = ["All locations"] + sorted(readings["Location"].unique())
    selected_location = filters[1].selectbox("Location filter", locations)
    sources = ["All sources"] + sorted(readings["Source"].dropna().unique())
    selected_source = filters[2].selectbox("Source filter", sources)
    start_date, end_date = st.date_input(
        "Report period",
        value=(date.today() - timedelta(days=29), date.today()),
        max_value=date.today(),
    )
    parsed_dates = pd.to_datetime(readings["Date"]).dt.date
    mask = (parsed_dates >= start_date) & (parsed_dates <= end_date)
    if selected_location != "All locations":
        mask &= readings["Location"] == selected_location
    if selected_source != "All sources":
        mask &= readings["Source"] == selected_source
    if record_search:
        searchable = readings[
            ["Date", "Location", "Usage Type", "Source", "Recorded By", "Notes"]
        ].fillna("").astype(str)
        matches = searchable.apply(
            lambda column: column.str.casefold().str.contains(
                record_search, regex=False
            )
        ).any(axis=1)
        mask &= matches
    filtered = readings.loc[mask]
    report_metrics = st.columns(2)
    report_metrics[0].metric("Total recorded use", f"{filtered['Liters'].sum():,.0f} L")
    estimated_savings = (filtered["Daily Target"] - filtered["Liters"]).clip(
        lower=0
    ).sum()
    report_metrics[1].metric(
        "Water saved (est.)",
        f"{estimated_savings:,.0f} L",
        help="Unused daily target allowance on the filtered recorded site-days; not measured savings.",
    )
    st.dataframe(filtered, width="stretch", hide_index=True)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download readings as CSV",
        data=csv,
        file_name="water_readings.csv",
        mime="text/csv",
    )

    if not filtered.empty:
        with st.expander("Correct or remove a reading"):
            reading_ids = filtered["ID"].astype(int).tolist()
            selected_id = st.selectbox("Reading ID", reading_ids)
            if st.button("Delete selected reading"):
                delete_reading(selected_id)
                st.success("Reading deleted.")
                st.rerun()


def account_page(user):
    page_heading("My Account", "Manage your profile and account security.", "👤")
    profile, security = st.columns(2)
    with profile:
        st.subheader("Profile")
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Role:** {user['role'].title()}")
        st.write(f"**Joined:** {user['created_at']}")

    with security:
        st.subheader("Change password")
        with st.form("change_password_form"):
            current_password = st.text_input("Current password", type="password")
            new_password = st.text_input("New password", type="password")
            confirmation = st.text_input("Confirm new password", type="password")
            submitted = st.form_submit_button(
                "Update password", type="primary", width="stretch"
            )
        if submitted:
            if new_password != confirmation:
                st.error("New passwords do not match.")
            else:
                success, message = change_password(
                    user["id"], current_password, new_password
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)


def admin_page(user):
    if user["role"] != "admin":
        st.error("Administrator access is required.")
        return

    page_heading(
        "Admin Panel",
        "Manage accounts and review system-wide water monitoring.",
        "⚙️",
    )
    users = get_registered_users()
    readings = get_readings()
    alerts = find_recent_alerts(readings)
    sites = get_sites()

    metrics = st.columns(4)
    metrics[0].metric("Registered users", len(users))
    metrics[1].metric("Monitoring areas", len(sites))
    metrics[2].metric("Total recorded use", f"{readings['Liters'].sum():,.0f} L")
    metrics[3].metric("Current alerts", len(alerts))

    st.subheader("Registered users")
    st.dataframe(users, width="stretch", hide_index=True)
    if not users.empty:
        user_options = {
            f"{row.Username} ({row.Role})": int(row.ID)
            for row in users.itertuples(index=False)
        }
        with st.form("user_role_form"):
            selected_user = st.selectbox("Account", list(user_options))
            new_role = st.selectbox("Role", ["user", "admin"])
            role_submitted = st.form_submit_button("Update role")
        if role_submitted:
            success, message = update_user_role(
                user_options[selected_user], new_role
            )
            if success:
                st.success(message)
                st.rerun()
            st.error(message)

    st.subheader("High-usage alerts")
    if alerts.empty:
        st.info("No current high-usage alerts.")
    else:
        st.dataframe(alerts, width="stretch", hide_index=True)

    st.subheader("All water usage records")
    st.dataframe(readings, width="stretch", hide_index=True)


def main():
    init_db()
    inject_app_styles()
    session_user = st.session_state.get("user")
    user = get_user_profile(session_user["id"]) if session_user else None
    if session_user and user is None:
        st.session_state.pop("user", None)
        st.rerun()
    if user is not None:
        st.session_state["user"] = user

    if user is None:
        if st.session_state.pop("auth_redirect_to_login", False):
            st.session_state["auth_page"] = "Login"
        with st.sidebar:
            st.markdown(
                '<div class="brand-lockup"><span class="brand-drop">💧</span>'
                '<div><div class="brand-name">AquaSense</div>'
                '<div class="brand-caption">Water Conservation</div></div></div>',
                unsafe_allow_html=True,
            )
            auth_page = st.radio("Account", ["Login", "Register"], key="auth_page")
        if auth_page == "Login":
            login_page()
        else:
            register_page()
        return

    with st.sidebar:
        st.markdown(
            '<div class="brand-lockup"><span class="brand-drop">💧</span>'
            '<div><div class="brand-name">AquaSave</div>'
            '<div class="brand-caption">Water Conservation</div></div></div>',
            unsafe_allow_html=True,
        )
        pages = [
            "Dashboard",
            "Water Usage",
            "Reports",
            "Alerts",
            "Conservation Tips",
            "Users",
            "Settings",
        ]
        if st.session_state.get("app_page") not in pages:
            st.session_state["app_page"] = "Dashboard"
        page = st.radio("", pages, key="app_page")
        st.markdown("<div style='margin-top: 12px; padding: 10px 0 0; color: rgba(255,255,255,.75); font-size: .78rem;'>Every Drop Counts</div>", unsafe_allow_html=True)
        st.divider()
        if st.button("Log out", width="stretch"):
            st.session_state.pop("user", None)
            st.rerun()
        st.caption("Readings and site settings are stored locally in SQLite.")

    page_key = page

    if page_key == "Dashboard":
        dashboard_page(user)
    elif page_key == "Water Usage":
        record_usage_page(user)
    elif page_key == "Reports":
        insights_reports_page()
    elif page_key == "Alerts":
        alert_settings_page()
    elif page_key == "Conservation Tips":
        insights_reports_page()
    elif page_key == "Users":
        admin_page(user)
    elif page_key == "Settings":
        account_page(user)
    else:
        dashboard_page(user)


main()