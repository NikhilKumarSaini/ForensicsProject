# ------------------------------------------------------------------
# ANALYZE BUTTON
# ------------------------------------------------------------------
if st.button("Analyze Document"):
    if not uploaded_file:
        st.error("Please upload a valid document first")
    else:
        with st.spinner("Running forensic analysis... Please wait"):

            # ----------------------------------------------------------
            # SAVE FILE WITH UNIX TIMESTAMP
            # ----------------------------------------------------------
            unix_ts = int(time.time())
            safe_name = f"{unix_ts}_{uploaded_file.name}"
            file_path = UPLOAD_DIR / safe_name

            with open(file_path, "wb") as f:
                f.write(uploaded_file.read())

            # ----------------------------------------------------------
            # DB: SAVE UPLOAD METADATA
            # ----------------------------------------------------------
            record_id = save_upload_metadata(
                filename=safe_name,
                filepath=str(file_path),
                content_type=uploaded_file.type,
                size_bytes=uploaded_file.size
            )

            # ----------------------------------------------------------
            # PDF METADATA
            # ----------------------------------------------------------
            if uploaded_file.type == "application/pdf":
                metadata = extract_pdf_metadata(str(file_path))
                save_pdf_metadata(record_id, metadata)

            # ----------------------------------------------------------
            # SOURCECODE PIPELINE (UNCHANGED)
            # ----------------------------------------------------------
            subprocess.run(["python", str(DETAILS_SCRIPT)], check=True)
            subprocess.run(["python", str(FORENSICS_SCRIPT)], check=True)

            # ----------------------------------------------------------
            # SCORING + ML
            # ----------------------------------------------------------
            final_report = run_scoring(
                record_id=record_id,
                pdf_path=str(file_path)
            )

            # -------- STORE RESULT IN SESSION (KEY FIX) --------
            st.session_state.final_report = final_report
            st.session_state.analysis_done = True

        st.success("Analysis completed successfully!")

# ==========================================================
# RESULTS DASHBOARD (SESSION SAFE)
# ==========================================================
if st.session_state.analysis_done:

    final_report = st.session_state.final_report

    st.markdown("## 📊 Risk Assessment Result")

    final = final_report["final_result"]
    final_score = final["final_score"]
    risk_category = final["risk_category"]

    # ------------------------------
    # FLASH CARD
    # ------------------------------
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #0033A0, #0075B7);
                padding: 28px;
                border-radius: 14px;
                color: white;
                box-shadow: 0 10px 24px rgba(0,0,0,0.15);
            ">
                <h3 style="margin-bottom: 6px;">Final Risk Score</h3>
                <h1 style="font-size: 46px; margin: 0;">
                    {final_score} / 100
                </h1>
                <p style="margin-top: 10px; font-size: 16px;">
                    Risk Classification: <b>{risk_category}</b>
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown("#### Risk Severity Indicator")

        # ------------------------------
        # ✅ SEVERITY COLOR INDICATOR (LOW=GREEN, MED=YELLOW, HIGH=RED)
        # ------------------------------
        risk_value = min(final_score / 100, 1.0)

        if final_score < 34:
            sev_label = "Low"
            sev_color = "#16A34A"  # green
        elif final_score < 67:
            sev_label = "Medium"
            sev_color = "#F59E0B"  # yellow
        else:
            sev_label = "High"
            sev_color = "#DC2626"  # red

        st.markdown(
            f"""
            <div style="
                padding: 12px 14px;
                border-radius: 12px;
                border: 1px solid rgba(0,0,0,0.08);
                background: rgba(255,255,255,0.75);
                margin-bottom: 10px;
            ">
                <div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
                    <div style="font-weight: 700;">{sev_label} Risk</div>
                    <div style="
                        background: {sev_color};
                        color: white;
                        padding: 6px 10px;
                        border-radius: 999px;
                        font-size: 12px;
                        font-weight: 700;
                    ">
                        {final_score}/100
                    </div>
                </div>
                <div style="
                    height: 10px;
                    background: rgba(0,0,0,0.08);
                    border-radius: 999px;
                    margin-top: 10px;
                    overflow: hidden;
                ">
                    <div style="
                        height: 10px;
                        width: {risk_value * 100:.0f}%;
                        background: {sev_color};
                        border-radius: 999px;
                    "></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.caption("0 = No Risk • 100 = Critical Risk")

    # ------------------------------
    # ✅ PIE / DONUT CHART (RISK=RED, CLEAN=BLUE like SCB)
    # ------------------------------
    st.markdown("### 📈 Uploaded Document Risk")

    import plotly.graph_objects as go

    risk = min(max(final_score / 100, 0.0), 1.0)
    clean = 1.0 - risk

    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Clean", "Risk"],
                values=[clean, risk],
                hole=0.62,
                sort=False,
                direction="clockwise",
                marker=dict(
                    colors=["#0072CE", "#EE3124"],  # SCB-like blue, red
                    line=dict(color="white", width=2),
                ),
                textinfo="percent",
                textposition="inside",
                hovertemplate="%{label}: %{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=240,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    fig.add_annotation(
        text=f"<b>{final_score}</b><br><span style='font-size:12px;color:#6B7280'>/ 100</span>",
        x=0.5, y=0.5,
        font=dict(size=22),
        showarrow=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # ------------------------------
    # TECHNICAL DETAILS
    # ------------------------------
    with st.expander("🔍 View Detailed Technical Report"):
        st.json(final_report)

    # ------------------------------
    # DOWNLOAD BUTTONS (NO RESET) + ✅ BETTER LOOK
    # ------------------------------
    st.markdown(
        """
        <style>
        div[data-testid="column"] .stDownloadButton > button {
            width: 100%;
            border-radius: 12px;
            padding: 0.75rem 1rem;
            font-weight: 700;
        }
        div[data-testid="column"]:nth-child(1) .stDownloadButton > button {
            background: #0072CE;
            color: white;
            border: 1px solid rgba(0,0,0,0.08);
        }
        div[data-testid="column"]:nth-child(1) .stDownloadButton > button:hover {
            filter: brightness(0.95);
        }
        div[data-testid="column"]:nth-child(2) .stDownloadButton > button {
            background: #111827;
            color: white;
            border: 1px solid rgba(0,0,0,0.08);
        }
        div[data-testid="column"]:nth-child(2) .stDownloadButton > button:hover {
            filter: brightness(0.95);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    # ---- Download JSON Report
    report_path = final_report.get("report_path")
    if report_path and os.path.exists(report_path):
        with c1:
            with open(report_path, "rb") as f:
                st.download_button(
                    label="⬇ Download Risk Report (JSON)",
                    data=f,
                    file_name=os.path.basename(report_path),
                    mime="application/json"
                )

    # ---- Download Forensics ZIP (MEMORY SAFE)
    forensics_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(report_path),
            "..",
            "Forensics_Output",
            final_report["forensics_folder"]
        )
    )

    if st.session_state.forensics_zip is None and os.path.exists(forensics_dir):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(forensics_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, forensics_dir)
                    zipf.write(file_path, arcname)
        zip_buffer.seek(0)
        st.session_state.forensics_zip = zip_buffer

    if st.session_state.forensics_zip:
        with c2:
            st.download_button(
                label="⬇ Download Forensics Evidence (ZIP)",
                data=st.session_state.forensics_zip,
                file_name=f"{final_report['forensics_folder']}.zip",
                mime="application/zip"
            )

# ------------------------------------------------------------------
# FOOTER (✅ FIXED: visible + pinned)
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    .app-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        padding: 10px 16px;
        background: rgba(255,255,255,0.92);
        border-top: 1px solid rgba(0,0,0,0.08);
        font-size: 13px;
        color: #111827;
        text-align: center;
        z-index: 9999;
        backdrop-filter: blur(10px);
    }
    /* Add bottom padding so footer doesn't overlap content */
    section.main > div { padding-bottom: 64px; }
    </style>
    <div class="app-footer">
        AI-Powered Document Forensics System · Built for Secure Financial Integrity Analysis
    </div>
    """,
    unsafe_allow_html=True
)
