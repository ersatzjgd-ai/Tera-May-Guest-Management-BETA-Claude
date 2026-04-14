import streamlit as st
import pandas as pd
from sqlalchemy import text
import datetime
from database import conn, init_db
from ui_components import ddp_dialog, batch_actions_dialog

# ─────────────────────────────────────────────
# THEME INJECTION  (runs before any widget)
# ─────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #21262d;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 14px; }

/* ── Option-menu active pill ── */
.nav-link-selected { background-color: #1f6feb !important; border-radius: 8px !important; }
.nav-link { border-radius: 8px !important; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] { font-size: 11px !important; letter-spacing: 1.5px; text-transform: uppercase; color: #8b949e !important; }
[data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; color: #e6edf3 !important; }

/* ── Guest row cards ── */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px !important;
    border-color: #21262d !important;
    background: #161b22;
    transition: border-color 0.2s ease;
}
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #1f6feb !important;
}

/* ── Primary buttons (unassigned alerts) ── */
[data-testid="stButton"] button[kind="primary"] {
    background: #da3633 !important;
    border: none !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px;
}
[data-testid="stButton"] button[kind="secondary"] {
    background: #21262d !important;
    border: 1px solid #30363d !important;
    color: #c9d1d9 !important;
    font-weight: 500 !important;
}
[data-testid="stButton"] button:hover { opacity: 0.88; }

/* ── Search inputs ── */
[data-testid="stTextInput"] input, [data-testid="stSelectbox"] select {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    color: #e6edf3 !important;
    font-family: 'DM Sans', sans-serif;
}

/* ── Divider ── */
hr { border-color: #21262d !important; }

/* ── Page title ── */
h1 { font-weight: 700 !important; letter-spacing: -0.5px; }
h2, h3 { font-weight: 600 !important; }

/* ── Warning/unassigned tag ── */
.unassigned-tag {
    color: #f85149;
    font-size: 10px;
    font-family: 'DM Mono', monospace;
    letter-spacing: 1px;
    margin-top: -12px;
    display: block;
}

/* ── Status badge helpers ── */
.badge-ok   { color: #3fb950; font-size: 12px; font-weight: 600; }
.badge-warn { color: #d29922; font-size: 12px; font-weight: 600; }
.badge-err  { color: #f85149; font-size: 12px; font-weight: 600; }

/* ── Column headers ── */
.col-header {
    font-size: 11px;
    font-family: 'DM Mono', monospace;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #8b949e;
    padding-bottom: 6px;
}
</style>
"""

# ─────────────────────────────────────────────
# DATA LAYER
# ─────────────────────────────────────────────
@st.cache_data(ttl=20)
def fetch_all_guests():
    return conn.query("SELECT * FROM guests", ttl=0)


# ─────────────────────────────────────────────
# HELPER: status badge
# ─────────────────────────────────────────────
def _status_badge(ok: bool, ok_label: str, fail_label: str) -> str:
    if ok:
        return f'<span class="badge-ok">✔ {ok_label}</span>'
    return f'<span class="badge-err">✖ {fail_label}</span>'


# ─────────────────────────────────────────────
# SEARCH & RESULTS FRAGMENT
# ─────────────────────────────────────────────
@st.fragment
def search_results_fragment():
    raw_df = fetch_all_guests()

    expected = ['category', 'speaker_category', 'accompanying_persons', 'poc',
                'assigned_gre', 'departure_time', 'housing', 'gift_type', 'ashram_tour']
    for col in expected:
        if col not in raw_df.columns:
            raw_df[col] = None

    if not raw_df.empty:
        raw_df['arrival_dt'] = pd.to_datetime(
            raw_df['arrival_time'], format='%d/%m/%Y %H:%M', errors='coerce'
        )

    today = datetime.date.today()

    # ── Page header ──────────────────────────────
    st.markdown("## 🔍 Guest Search")
    st.caption("Search by name, POC, category, or arrival date. Click any guest to open their details.")

    # ── Filters in a styled container ────────────
    with st.container(border=True):
        f1, f1a, f2, f3 = st.columns([2, 2, 2, 2])

        all_guests = sorted([str(x) for x in raw_df['name'].dropna().unique() if str(x).strip()])
        all_pocs   = sorted([str(x) for x in raw_df['poc'].dropna().unique()  if str(x).strip()])

        with f1:
            s_name = st.selectbox("👤 Guest Name", options=all_guests, index=None,
                                  placeholder="Type or select…", key="s_name_input")
        with f1a:
            s_poc = st.selectbox("📞 POC Name", options=all_pocs, index=None,
                                 placeholder="Type or select…", key="s_poc_input")
        with f2:
            available = sorted(list(set([
                str(c).strip() for c in raw_df['category'].dropna()
                if str(c).strip() not in ["", "nan", "None", "--"]
            ]))) if not raw_df.empty else []
            s_cats = st.multiselect("🏷️ Categories", available, key="s_cat_select")
        with f3:
            d_range = st.date_input("📅 Arrival Date Range",
                                    value=(today, today),
                                    format="DD/MM/YYYY", key="s_date_range")

    # ── Apply filters ─────────────────────────────
    filtered_df = raw_df.copy()
    if not filtered_df.empty:
        if s_name:
            filtered_df = filtered_df[filtered_df['name'] == s_name]
        if s_poc:
            filtered_df = filtered_df[filtered_df['poc'] == s_poc]
        if s_cats:
            filtered_df = filtered_df[filtered_df['category'].isin(s_cats)]
        if isinstance(d_range, tuple) and len(d_range) == 2:
            def to_dummy(dt):
                if pd.isna(dt): return pd.NaT
                return pd.Timestamp(year=2024, month=dt.month, day=dt.day)
            d_start, d_end = to_dummy(d_range[0]), to_dummy(d_range[1])
            filtered_df['dummy_date'] = filtered_df['arrival_dt'].apply(to_dummy)
            filtered_df = filtered_df[
                (filtered_df['dummy_date'] >= d_start) &
                (filtered_df['dummy_date'] <= d_end) |
                filtered_df['arrival_dt'].isna()
            ]

    st.divider()

    is_default = (not s_name) and (not s_poc) and (not s_cats) and (d_range == (today, today))

    # ── Dashboard / Metrics ───────────────────────
    if is_default:
        st.markdown("### 📅 Today's Arrivals")
        disp = raw_df[raw_df['arrival_dt'].dt.date == today] if not raw_df.empty else pd.DataFrame()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Arrivals Today", len(disp))
        m2.metric("Pending Pickups",
                  len(disp[disp['airport_pickup_sent'] == 0]) if not disp.empty else 0)
        m3.metric("Rooms Unclean",
                  len(disp[disp['room_cleaned'] == 0]) if not disp.empty else 0)
        m4.metric("Unassigned GRE",
                  len(disp[disp['assigned_gre'].isna() |
                           (disp['assigned_gre'].astype(str).str.strip() == "")]) if not disp.empty else 0)
    else:
        st.markdown("### 📊 Search Results")
        disp = filtered_df

        metrics_data = [
            ("Total Results", len(disp)),
            ("Speakers", len(disp[disp['speaker_category'] == 'Speaker']) if not disp.empty else 0),
        ]
        if not disp.empty and 'category' in disp.columns:
            cat_counts = (
                disp['category']
                .replace(r'^\s*$', 'Uncategorized', regex=True)
                .fillna('Uncategorized')
                .value_counts()
            )
            for cat_name, count in cat_counts.items():
                metrics_data.append((str(cat_name), count))

        cols_per_row = 4
        for i in range(0, len(metrics_data), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, (label, val) in enumerate(metrics_data[i: i + cols_per_row]):
                cols[j].metric(label, val)

    st.divider()

    # ── Guest List ────────────────────────────────
    if not disp.empty:
        # Priority sort: unassigned GRE → today's dirty rooms → arrival time
        def eval_warnings(row):
            dt = row['arrival_dt']
            is_today = pd.notna(dt) and dt.date() == today
            room_w = is_today and not bool(row['room_cleaned'])
            gre_w  = pd.isna(row['assigned_gre']) or \
                     str(row['assigned_gre']).strip() in ["", "-- Unassigned --", "None", "--"]
            return pd.Series(
                [2 if gre_w else (1 if room_w else 0),
                 pd.Timestamp(dt.date()) if pd.notna(dt) else pd.NaT],
                index=['w_score', 's_date']
            )

        disp[['w_score', 's_date']] = disp.apply(eval_warnings, axis=1)
        disp = disp.sort_values(
            by=['s_date', 'w_score', 'arrival_dt'],
            ascending=[True, False, True],
            na_position='last'
        )

        # Batch action bar
        selected_ids = [
            row['id'] for _, row in disp.iterrows()
            if st.session_state.get(f"chk_{row['id']}", False)
        ]
        top_left, top_right = st.columns([8, 2])
        with top_right:
            if st.button(
                f"🛠️ Batch Actions ({len(selected_ids)})",
                use_container_width=True, key="batch_btn",
                type="primary" if selected_ids else "secondary"
            ):
                if selected_ids:
                    batch_actions_dialog(selected_ids)
                else:
                    st.warning("Select at least one guest first.")

        # Column headers
        with st.container():
            h0, h1, h2, h3, h4, h5, h6 = st.columns([0.4, 2.8, 1.8, 1.8, 1.8, 1.2, 1.2])
            h0.markdown('<div class="col-header">☑</div>', unsafe_allow_html=True)
            h1.markdown('<div class="col-header">Guest Name</div>', unsafe_allow_html=True)
            h2.markdown('<div class="col-header">Arrival</div>', unsafe_allow_html=True)
            h3.markdown('<div class="col-header">POC</div>', unsafe_allow_html=True)
            h4.markdown('<div class="col-header">GRE</div>', unsafe_allow_html=True)
            h5.markdown('<div class="col-header">Pax</div>', unsafe_allow_html=True)
            h6.markdown('<div class="col-header">Room</div>', unsafe_allow_html=True)

        # Guest rows
        for _, row in disp.iterrows():
            gre_w = pd.isna(row['assigned_gre']) or \
                    str(row['assigned_gre']).strip() in ["", "-- Unassigned --", "None", "--"]
            room_clean = bool(row.get('room_cleaned', 0))

            with st.container(border=True):
                r0, r1, r2, r3, r4, r5, r6 = st.columns([0.4, 2.8, 1.8, 1.8, 1.8, 1.2, 1.2])

                r0.checkbox(" ", key=f"chk_{row['id']}", label_visibility="collapsed")

                guest_icon = "🚨" if gre_w else "👤"
                btn_type   = "primary" if gre_w else "secondary"
                if r1.button(f"{guest_icon} {row['name']}",
                             key=f"btn_{row['id']}",
                             type=btn_type,
                             use_container_width=True):
                    ddp_dialog(row.to_dict())

                if gre_w:
                    st.markdown('<span class="unassigned-tag">⚠ GRE NOT ASSIGNED</span>',
                                unsafe_allow_html=True)

                r2.write(row.get('arrival_time') or "—")
                r3.write(row.get('poc') or "—")
                r4.markdown(
                    _status_badge(not gre_w,
                                  str(row['assigned_gre']),
                                  "Pending"),
                    unsafe_allow_html=True
                )
                r5.write(str(row.get('accompanying_persons', '0')))
                r6.markdown(
                    _status_badge(room_clean, "Clean", "Dirty"),
                    unsafe_allow_html=True
                )
    else:
        st.info("No guests match the current filters.", icon="🔍")


# ─────────────────────────────────────────────
# ADMIN TOOLS FRAGMENT
# ─────────────────────────────────────────────
@st.fragment
def admin_tools_fragment():
    with st.expander("🛠️ Admin Tools — Add GRE · Bulk Import"):
        t1, t2 = st.tabs(["➕ Add GRE", "📥 CSV Import"])

        with t1:
            st.caption("Create a new Guest Relations Executive entry.")
            with st.form("gre_f", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                gn = col_a.text_input("Full Name")
                gp = col_b.text_input("Phone (e.g. 9876543210)")
                if st.form_submit_button("➕ Create GRE", type="primary"):
                    clean_phone = "".join(c for c in str(gp) if c.isdigit() or c == "+")
                    if clean_phone and not clean_phone.startswith("+"):
                        clean_phone = "+91" + clean_phone
                    with conn.session as s:
                        s.execute(
                            text("INSERT INTO gres (gre_name, gre_phone) VALUES (:n, :p)"),
                            {"n": gn, "p": clean_phone}
                        )
                        s.commit()
                    st.cache_data.clear()
                    st.success(f"✔ GRE '{gn}' added successfully!")

        with t2:
            st.info(
                "**Required CSV columns:** `name`, `admin_username`  \n"
                "**Optional:** `poc`, `category`, `housing`, `speaker_category`",
                icon="📄"
            )
            f = st.file_uploader("Upload CSV", type="csv", key="bulk_csv_uploader")
            if f and st.button("▶ Run Import", type="primary", key="csv_import_btn"):
                data = pd.read_csv(f)
                data.columns = data.columns.str.lower().str.strip()
                with conn.session as s:
                    for _, r in data.iterrows():
                        g_name  = str(r['name']).strip()
                        a_user  = str(r['admin_username']).strip()
                        cat     = str(r.get('category', '')).strip()
                        hou     = str(r.get('housing', 'TBD')).strip()
                        spk     = str(r.get('speaker_category', 'Non-Speaker')).strip()

                        s.execute(
                            text("INSERT INTO admins (username, password) VALUES (:u, :p) ON CONFLICT DO NOTHING"),
                            {"u": a_user, "p": "password123"}
                        )
                        existing = s.execute(
                            text("SELECT id FROM guests WHERE name = :n AND admin_owner = :u"),
                            {"n": g_name, "u": a_user}
                        ).fetchone()
                        if existing:
                            s.execute(
                                text("UPDATE guests SET category=:c, housing=:h, speaker_category=:s WHERE id=:id"),
                                {"c": cat, "h": hou, "s": spk, "id": existing[0]}
                            )
                        else:
                            s.execute(
                                text("INSERT INTO guests (name, admin_owner, category, housing, speaker_category) VALUES (:n, :u, :c, :h, :s)"),
                                {"n": g_name, "u": a_user, "c": cat, "h": hou, "s": spk}
                            )
                    s.commit()
                st.cache_data.clear()
                st.success("✔ Import complete!")


# ─────────────────────────────────────────────
# PUBLIC SEARCH PAGE
# ─────────────────────────────────────────────
def public_search_page():
    st.markdown("## 🛂 Guest Inquiry")
    st.caption("Look up arrival and room details for any registered guest.")
    search = st.text_input("Search by guest name", placeholder="e.g. Swami Chinmayananda…")
    if search:
        df = conn.query(
            "SELECT name, arrival_time, departure_time, housing FROM guests WHERE name ILIKE :n",
            params={"n": f"%{search}%"}, ttl=0
        )
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("No matching guest found.")


# ─────────────────────────────────────────────
# STAFF PORTAL PAGE
# ─────────────────────────────────────────────
def staff_portal_page():
    st.markdown("## 🛎️ Staff Portal (GRE)")
    st.caption("Enter your name to view your assigned guests.")
    gre_name = st.text_input("Your GRE Name")
    if gre_name:
        df = conn.query(
            "SELECT name, arrival_time, departure_time, housing, airport_pickup_sent, room_cleaned "
            "FROM guests WHERE assigned_gre = :g",
            params={"g": gre_name}, ttl=0
        )
        if not df.empty:
            st.success(f"Welcome {gre_name}! You have **{len(df)}** assigned guest(s).")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No guests currently assigned to **{gre_name}**.")


# ─────────────────────────────────────────────
# LOGIN SCREEN
# ─────────────────────────────────────────────
def login_screen():
    st.markdown("## 🔐 Admin Login")
    st.caption("Restricted to authorised event staff only.")
    with st.container(border=True):
        col_l, col_r = st.columns([1, 1])
        u = col_l.text_input("Username", placeholder="admin")
        p = col_r.text_input("Password", type="password", placeholder="••••••••")
        if st.button("Login →", type="primary"):
            res = conn.query(
                "SELECT * FROM admins WHERE username = :u AND password = :p",
                params={"u": u, "p": p}, ttl=0
            )
            if not res.empty:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Dignitary Management System",
        page_icon="🛂",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # ── Sidebar ──────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<div style='padding:12px 0 24px'>"
            "<span style='font-size:22px;font-weight:700;color:#e6edf3;letter-spacing:-0.5px'>"
            "🛂 Event Control</span><br>"
            "<span style='font-size:11px;color:#8b949e;letter-spacing:1px'>DIGNITARY MANAGEMENT</span>"
            "</div>",
            unsafe_allow_html=True
        )

        try:
            from streamlit_option_menu import option_menu
            mode = option_menu(
                menu_title=None,
                options=["Public Search", "Staff Portal", "Admin Portal"],
                icons=["search", "person-badge", "shield-lock"],
                default_index=0,
                styles={
                    "container":        {"background-color": "#0d1117", "padding": "0"},
                    "nav-link":         {"font-size": "13px", "color": "#8b949e",
                                         "border-radius": "8px", "margin": "2px 0"},
                    "nav-link-selected":{"background-color": "#1f6feb", "color": "#ffffff",
                                         "font-weight": "600"},
                }
            )
        except ImportError:
            # Graceful fallback if streamlit-option-menu isn't installed
            mode_map = {"🔍 Public Search": "Public Search",
                        "🛎️ Staff Portal":  "Staff Portal",
                        "🔐 Admin Portal":  "Admin Portal"}
            mode = mode_map[st.radio("Navigate", list(mode_map.keys()))]

        st.divider()

        if st.session_state.logged_in:
            st.success(f"✔ Logged in as **{st.session_state.user}**")
            if st.button("Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.rerun()

    # ── Page routing ─────────────────────────────
    if mode == "Public Search":
        public_search_page()

    elif mode == "Staff Portal":
        staff_portal_page()

    elif mode == "Admin Portal":
        if not st.session_state.logged_in:
            login_screen()
        else:
            search_results_fragment()
            st.divider()
            admin_tools_fragment()


if __name__ == "__main__":
    main()
