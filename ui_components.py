import streamlit as st
import pandas as pd
from sqlalchemy import text
import datetime
import urllib.parse
import re
from database import conn


# ─────────────────────────────────────────────
# 1. SILENT SAVE CALLBACKS
# ─────────────────────────────────────────────
# BUG FIX: No st.toast() inside dialog callbacks — causes blank screen crash.

def db_update(field, widget_key, gid):
    val = st.session_state[widget_key]
    with conn.session as s:
        s.execute(
            text(f"UPDATE guests SET {field} = :v WHERE id = :id"),
            {"v": val, "id": gid}
        )
        s.commit()


def db_update_datetime(field, date_key, time_key, gid):
    d_val = st.session_state.get(date_key)
    t_val = st.session_state.get(time_key)
    # Safety: only commit when BOTH date and time are filled
    if not d_val or not t_val:
        return
    final_dt = f"{d_val.strftime('%d/%m/%Y')} {t_val.strftime('%H:%M')}"
    with conn.session as s:
        s.execute(
            text(f"UPDATE guests SET {field} = :v WHERE id = :id"),
            {"v": final_dt, "id": gid}
        )
        s.commit()


def update_gre_cb(widget_key, gid):
    val = st.session_state[widget_key]
    v = None if val == "-- Unassigned --" else val
    with conn.session as s:
        s.execute(
            text("UPDATE guests SET assigned_gre = :v WHERE id = :id"),
            {"v": v, "id": gid}
        )
        s.commit()


def toggle_room_cb(k, gid):
    with conn.session as s:
        s.execute(
            text("UPDATE guests SET room_cleaned = :r WHERE id = :id"),
            {"r": int(st.session_state[k]), "id": gid}
        )
        s.commit()


def toggle_pk_cb(k, gid):
    with conn.session as s:
        s.execute(
            text("UPDATE guests SET airport_pickup_sent = :p WHERE id = :id"),
            {"p": int(st.session_state[k]), "id": gid}
        )
        s.commit()


def toggle_ashram_cb(k, gid):
    with conn.session as s:
        s.execute(
            text("UPDATE guests SET ashram_tour = :a WHERE id = :id"),
            {"a": int(st.session_state[k]), "id": gid}
        )
        s.commit()


def parse_dt(dt_str):
    if not dt_str or pd.isna(dt_str) or str(dt_str).strip() in ["", "TBD"]:
        return datetime.date.today(), datetime.time(12, 0)
    try:
        dt_obj = datetime.datetime.strptime(str(dt_str).strip(), "%d/%m/%Y %H:%M")
        return dt_obj.date(), dt_obj.time()
    except Exception:
        return datetime.date.today(), datetime.time(12, 0)


# ─────────────────────────────────────────────
# 2. SECTION HEADER HELPER
# ─────────────────────────────────────────────
def _section(icon: str, title: str):
    """Renders a tidy section divider inside the DDP dialog."""
    st.markdown(
        f"<div style='margin:18px 0 10px;padding:8px 12px;"
        f"background:#161b22;border-left:3px solid #1f6feb;"
        f"border-radius:0 6px 6px 0'>"
        f"<span style='font-size:13px;font-weight:600;color:#e6edf3'>"
        f"{icon} {title}</span></div>",
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────
# 3. DIGNITARY DETAILS PAGE (DDP) DIALOG
# ─────────────────────────────────────────────
@st.dialog("Dignitary Details", width="large")
def ddp_dialog(guest_data_input):
    gid = guest_data_input['id']

    # Always fetch freshest data to prevent stale-state loops
    try:
        fresh_df = conn.query(
            "SELECT * FROM guests WHERE id = :id",
            params={"id": gid}, ttl=0
        )
        guest_data = fresh_df.iloc[0].to_dict() if not fresh_df.empty else guest_data_input
    except Exception:
        guest_data = guest_data_input

    # ── Dialog header ────────────────────────────
    name = guest_data.get('name', 'Unknown Guest')
    category = guest_data.get('category', '')
    speaker  = guest_data.get('speaker_category', '')

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:4px'>"
        f"<span style='font-size:26px;font-weight:700;color:#e6edf3'>{name}</span>"
        f"{'<span style=\"background:#1f6feb22;color:#58a6ff;font-size:11px;padding:3px 9px;border-radius:20px;border:1px solid #1f6feb55\">' + speaker + '</span>' if speaker else ''}"
        f"{'<span style=\"background:#21262d;color:#8b949e;font-size:11px;padding:3px 9px;border-radius:20px;margin-left:4px\">' + category + '</span>' if category else ''}"
        f"</div>",
        unsafe_allow_html=True
    )
    st.caption("✏️ All fields auto-save on change — no submit button needed.")
    st.divider()

    # ── Three-column layout ──────────────────────
    col1, col2, col3 = st.columns([1, 1.2, 0.9])

    # ── COL 1 : Profile ──────────────────────────
    with col1:
        _section("🪪", "Profile")

        st.text_input(
            "Category", value=guest_data.get('category', ''),
            key=f"cat_{gid}", on_change=db_update, args=("category", f"cat_{gid}", gid)
        )
        st.selectbox(
            "Speaker Status", ["Speaker", "Non-Speaker"],
            index=0 if guest_data.get('speaker_category') == "Speaker" else 1,
            key=f"spk_{gid}", on_change=db_update, args=("speaker_category", f"spk_{gid}", gid)
        )
        st.number_input(
            "Accompanying Pax", min_value=0,
            value=int(guest_data.get('accompanying_persons', 0))
            if pd.notna(guest_data.get('accompanying_persons')) else 0,
            key=f"pax_{gid}", on_change=db_update, args=("accompanying_persons", f"pax_{gid}", gid)
        )
        st.text_input(
            "POC Name", value=guest_data.get('poc', ''),
            key=f"poc_{gid}", on_change=db_update, args=("poc", f"poc_{gid}", gid)
        )
        st.text_input(
            "Gift Type", value=guest_data.get('gift_type', 'Pending'),
            key=f"gift_{gid}", on_change=db_update, args=("gift_type", f"gift_{gid}", gid)
        )

    # ── COL 2 : Logistics ────────────────────────
    with col2:
        _section("✈️", "Logistics")

        st.text_input(
            "Housing / Room", value=guest_data.get('housing', 'TBD'),
            key=f"hou_{gid}", on_change=db_update, args=("housing", f"hou_{gid}", gid)
        )

        # GRE assignment
        gre_df    = conn.query("SELECT gre_name FROM gres", ttl=0)
        avail_gres = (["-- Unassigned --"] + gre_df['gre_name'].tolist()) if not gre_df.empty else ["-- Unassigned --"]
        raw_gre    = guest_data.get('assigned_gre')
        current_gre = (
            raw_gre if pd.notna(raw_gre) and str(raw_gre).strip() not in ["", "None"]
            else "-- Unassigned --"
        )
        if current_gre not in avail_gres:
            avail_gres.append(current_gre)

        st.selectbox(
            "Assigned GRE", avail_gres, index=avail_gres.index(current_gre),
            key=f"gre_{gid}", on_change=update_gre_cb, args=(f"gre_{gid}", gid)
        )

        # GRE contact + WhatsApp
        if current_gre != "-- Unassigned --":
            gre_query = conn.query(
                "SELECT gre_phone FROM gres WHERE gre_name = :n",
                params={"n": current_gre}, ttl=0
            )
            if not gre_query.empty:
                raw_phone = str(gre_query.iloc[0]['gre_phone']).strip()
                if raw_phone and raw_phone.lower() not in ["none", "nan", ""]:
                    c_call, c_wa = st.columns(2)
                    c_call.markdown(
                        f"<a href='tel:{raw_phone}' style='font-size:13px;color:#58a6ff;text-decoration:none'>"
                        f"📞 {raw_phone}</a>",
                        unsafe_allow_html=True
                    )

                    # Build WhatsApp message
                    wa_msg = (
                        f"🛎️ *New VIP Assignment*\n\n"
                        f"Hello {current_gre},\nYou have been assigned as GRE for:\n\n"
                        f"👤 *Guest:* {guest_data['name']} (+{guest_data.get('accompanying_persons', 0)} Pax)\n"
                        f"✈️ *Arrival:* {guest_data.get('arrival_time', 'TBD')}\n"
                        f"🛫 *Departure:* {guest_data.get('departure_time', 'TBD')}\n"
                        f"🏨 *Room:* {guest_data.get('housing', 'TBD')}\n"
                        f"📞 *Guest POC:* {guest_data.get('poc', 'TBD')}\n"
                        f"🎁 *Gift:* {guest_data.get('gift_type', 'Pending')}\n"
                        f"🛕 *Ashram Tour:* {'Yes' if guest_data.get('ashram_tour') else 'No'}\n\n"
                        f"Please ensure everything is prepared."
                    )
                    clean_phone = re.sub(r'\D', '', raw_phone)
                    wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(wa_msg)}"
                    st.link_button("💬 Send WhatsApp Itinerary", wa_url, use_container_width=True)
                else:
                    st.warning(f"No phone number saved for **{current_gre}**.")
            else:
                st.warning(f"GRE '{current_gre}' not found in database.")

        st.divider()

        # Arrival
        arr_str = guest_data.get('arrival_time')
        if not arr_str or str(arr_str).strip() in ["", "None", "TBD", "nan"]:
            st.warning("Arrival: **Not set**")
            with st.expander("➕ Set Arrival"):
                ca1, ca2 = st.columns(2)
                ca1.date_input("Date", value=None, key=f"arr_d_{gid}",
                               on_change=db_update_datetime,
                               args=("arrival_time", f"arr_d_{gid}", f"arr_t_{gid}", gid))
                ca2.time_input("Time", value=None, key=f"arr_t_{gid}",
                               on_change=db_update_datetime,
                               args=("arrival_time", f"arr_d_{gid}", f"arr_t_{gid}", gid))
        else:
            arr_d, arr_t = parse_dt(arr_str)
            ca1, ca2 = st.columns(2)
            ca1.date_input("Arrival Date", value=arr_d, format="DD/MM/YYYY",
                           key=f"arr_d_{gid}", on_change=db_update_datetime,
                           args=("arrival_time", f"arr_d_{gid}", f"arr_t_{gid}", gid))
            ca2.time_input("Arrival Time", value=arr_t, key=f"arr_t_{gid}",
                           on_change=db_update_datetime,
                           args=("arrival_time", f"arr_d_{gid}", f"arr_t_{gid}", gid))

        # Departure
        dep_str = guest_data.get('departure_time')
        if not dep_str or str(dep_str).strip() in ["", "None", "TBD", "nan"]:
            st.warning("Departure: **Not set**")
            with st.expander("➕ Set Departure"):
                cd1, cd2 = st.columns(2)
                cd1.date_input("Date", value=None, key=f"dep_d_{gid}",
                               on_change=db_update_datetime,
                               args=("departure_time", f"dep_d_{gid}", f"dep_t_{gid}", gid))
                cd2.time_input("Time", value=None, key=f"dep_t_{gid}",
                               on_change=db_update_datetime,
                               args=("departure_time", f"dep_d_{gid}", f"dep_t_{gid}", gid))
        else:
            dep_d, dep_t = parse_dt(dep_str)
            cd1, cd2 = st.columns(2)
            cd1.date_input("Departure Date", value=dep_d, format="DD/MM/YYYY",
                           key=f"dep_d_{gid}", on_change=db_update_datetime,
                           args=("departure_time", f"dep_d_{gid}", f"dep_t_{gid}", gid))
            cd2.time_input("Departure Time", value=dep_t, key=f"dep_t_{gid}",
                           on_change=db_update_datetime,
                           args=("departure_time", f"dep_d_{gid}", f"dep_t_{gid}", gid))

    # ── COL 3 : Ground Status ────────────────────
    with col3:
        _section("🛎️", "Ground Status")

        st.toggle(
            "✅ Room Cleaned",
            value=bool(guest_data.get('room_cleaned', 0)),
            key=f"ddp_rm_{gid}", on_change=toggle_room_cb, args=(f"ddp_rm_{gid}", gid)
        )
        st.toggle(
            "🚗 Pickup Sent",
            value=bool(guest_data.get('airport_pickup_sent', 0)),
            key=f"ddp_pk_{gid}", on_change=toggle_pk_cb, args=(f"ddp_pk_{gid}", gid)
        )
        st.toggle(
            "🛕 Ashram Tour",
            value=bool(guest_data.get('ashram_tour', 0)),
            key=f"ddp_ash_{gid}", on_change=toggle_ashram_cb, args=(f"ddp_ash_{gid}", gid)
        )

        st.divider()

        _section("👤", "Admin Info")
        st.markdown(
            f"<div style='background:#161b22;border:1px solid #21262d;border-radius:8px;"
            f"padding:10px 14px;font-size:13px;color:#c9d1d9'>"
            f"<b>Owner:</b> {guest_data.get('admin_owner', 'System')}</div>",
            unsafe_allow_html=True
        )

        _section("🏨", "Housing Support")
        st.markdown(
            "<a href='tel:9699372475' style='font-size:13px;color:#58a6ff;text-decoration:none'>"
            "📞 Call Housing: 9699372475</a>",
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────
# 4. BATCH ACTIONS DIALOG
# ─────────────────────────────────────────────
@st.dialog("🛠️ Batch Actions", width="medium")
def batch_actions_dialog(selected_ids):
    st.markdown(
        f"<div style='background:#161b22;border:1px solid #21262d;border-radius:8px;"
        f"padding:12px 16px;margin-bottom:16px;font-size:14px;color:#c9d1d9'>"
        f"Applying changes to <b style='color:#e6edf3'>{len(selected_ids)}</b> selected guest(s).</div>",
        unsafe_allow_html=True
    )

    gre_df    = conn.query("SELECT gre_name FROM gres", ttl=0)
    avail_gres = (["-- No Change --"] + gre_df['gre_name'].tolist()) if not gre_df.empty else ["-- No Change --"]

    batch_gre    = st.selectbox("👤 Assign GRE", avail_gres)
    batch_room   = st.selectbox("🛏️ Room Status", ["-- No Change --", "Mark Cleaned", "Mark Dirty/Pending"])
    batch_pickup = st.selectbox("🚗 Pickup Status", ["-- No Change --", "Mark Sent", "Mark Pending"])

    st.divider()

    if st.button("✔ Apply Changes", type="primary", use_container_width=True):
        with conn.session as s:
            for gid in selected_ids:
                if batch_gre != "-- No Change --":
                    s.execute(
                        text("UPDATE guests SET assigned_gre = :g WHERE id = :id"),
                        {"g": batch_gre, "id": gid}
                    )
                if batch_room != "-- No Change --":
                    s.execute(
                        text("UPDATE guests SET room_cleaned = :r WHERE id = :id"),
                        {"r": 1 if batch_room == "Mark Cleaned" else 0, "id": gid}
                    )
                if batch_pickup != "-- No Change --":
                    s.execute(
                        text("UPDATE guests SET airport_pickup_sent = :p WHERE id = :id"),
                        {"p": 1 if batch_pickup == "Mark Sent" else 0, "id": gid}
                    )
            s.commit()

        for gid in selected_ids:
            st.session_state[f"chk_{gid}"] = False

        st.success(f"✔ Updated {len(selected_ids)} guest(s) successfully!")
        st.rerun()
