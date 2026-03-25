import streamlit as st
import pandas as pd

st.set_page_config(page_title="RFQ Copilot", page_icon="📋", layout="wide")

st.title("📋 RFQ & Supplier Response Copilot")
st.markdown("*Procurement tool for RFQ generation, quote comparison, and award recommendation.*")

section = st.sidebar.radio(
    "Navigate",
    [
        "💬 Instant Quote Assistant",
        "📋 RFQ Generator",
        "📊 Quote Comparison",
        "🏆 Award & Risk",
        "📈 Sourcing Summary",
        "📊 Supplier Scorecard",
    ],
)

# Helper function used by Sourcing Summary
def compute_award_df(quotes_df, annual_volume, priority):
    df = quotes_df.copy()
    for col in ["Unit_price", "Tooling_cost", "Freight_cost", "Other_charges"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Total_material_cost"] = df["Unit_price"] * annual_volume
    df["Total_landed_cost"] = (
        df["Total_material_cost"]
        + df["Tooling_cost"]
        + df["Freight_cost"]
        + df["Other_charges"]
    )

    results = []
    for item_id in df["Item_ID"].unique():
        item_df = df[df["Item_ID"] == item_id].copy()

        max_cost = item_df["Total_landed_cost"].max()
        min_cost = item_df["Total_landed_cost"].min()
        if max_cost != min_cost:
            item_df["cost_score"] = 1 - (
                (item_df["Total_landed_cost"] - min_cost) / (max_cost - min_cost)
            )
        else:
            item_df["cost_score"] = 1.0

        max_lead_item = item_df["Lead_time_weeks"].max()
        min_lead_item = item_df["Lead_time_weeks"].min()
        if max_lead_item != min_lead_item:
            item_df["lead_score"] = 1 - (
                (item_df["Lead_time_weeks"] - min_lead_item) / (max_lead_item - min_lead_item)
            )
        else:
            item_df["lead_score"] = 1.0

        item_df["final_score"] = priority * item_df["cost_score"] + (1 - priority) * item_df["lead_score"]
        winner = item_df.loc[item_df["final_score"].idxmax()]
        results.append({
            "Item_ID": item_id,
            "Supplier": winner["Supplier"],
            "Total_landed_cost": winner["Total_landed_cost"],
            "Lead_time_weeks": winner["Lead_time_weeks"],
            "MOQ": winner["MOQ"],
            "Payment_terms": winner["Payment_terms"],
            "Final_score": round(winner["final_score"], 3),
        })

    award_df = pd.DataFrame(results)
    return df, award_df

# ==============================
# SECTION 0 – INSTANT QUOTE ASSISTANT (SAMPLE LOGIC)
# ==============================

if section == "💬 Instant Quote Assistant":
    st.header("💬 Instant Quote Assistant")
    st.markdown(
        "Describe what you need in natural language and the copilot will return a sample quote and availability statement."
    )

    # 1) Simple static “catalog” just for demo
    catalog = {
        "7075": {"name": "7075-T651 plate", "unit_price": 95.0, "lead_weeks": 2, "stock": True},
        "6061": {"name": "6061-T651 plate", "unit_price": 65.0, "lead_weeks": 1, "stock": True},
    }

    # 2) Chat history state
    if "iq_messages" not in st.session_state:
        st.session_state.iq_messages = []

    # Show previous messages
    for msg in st.session_state.iq_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 3) User input at the bottom
    prompt = st.chat_input("Example: I need 7075 plate, 2\" x 12\" x 24\", qty 10 in 3–4 days")

    if prompt:
        # Add user message
        st.session_state.iq_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- Very simple parsing logic for demo only ---
        material_key = "7075" if "7075" in prompt else "6061" if "6061" in prompt else None

        if material_key and material_key in catalog:
            info = catalog[material_key]

            # crude qty parse: look for first integer
            import re

            m = re.search(r"\b(\d+)\b", prompt)
            qty = int(m.group(1)) if m else 10

            reply = (
                f"Here’s your quote for **{info['name']}** (sample logic):\n\n"
                f"- Estimated unit price: **${info['unit_price']:.2f}**\n"
                f"- Quantity: **{qty} pcs**\n"
                f"- Estimated line value: **${info['unit_price'] * qty:,.2f}**\n"
                f"- Lead time: **{info['lead_weeks']}–{info['lead_weeks'] + 1} weeks**\n"
                f"- Availability: {'In stock window' if info['stock'] else 'Made to order'}\n\n"
                "You can now capture this as a line in RFQ Generator or Quote Comparison."
            )
        else:
            reply = (
                "This is a demo assistant. I couldn’t match the material from your text.\n\n"
                "Try including `7075` or `6061` in your request (e.g., *7075 plate, qty 10*)."
            )

        # Show assistant reply
        with st.chat_message("assistant"):
            st.markdown(reply)

        st.session_state.iq_messages.append({"role": "assistant", "content": reply})


# ==============================
# SECTION 1 – RFQ GENERATOR
# ==============================

if section == "📋 RFQ Generator":
    st.header("📋 RFQ Generator")
    st.markdown("Fill in the details below to generate a professional RFQ email.")

    col1, col2 = st.columns(2)

    with col1:
        part_name = st.text_input("Part / Category", "Stamped steel bracket")
        description = st.text_area("Technical Description", "Bracket for automotive chassis mounting, CR steel, e-coated.")
        annual_volume = st.number_input("Annual Volume (pcs)", value=50000, step=1000)
        release_pattern = st.text_input("Release Pattern", "Monthly releases with weekly shipments")

    with col2:
        region_incoterm = st.text_input("Target Region & Incoterm", "North America, FOB supplier dock")
        lead_time = st.text_input("Target Lead Time", "6-8 weeks")
        contract_duration = st.text_input("Contract Duration", "2 years")
        special_requirements = st.text_area("Special Requirements", "PPAP required, RoHS compliant, line-side packaging.")

    if st.button("Generate RFQ Email"):
        email = f"""Subject: Request for Quotation – {part_name}

Dear Supplier,

We are initiating a sourcing event and request your quotation for the following part/category:

Part / Category: {part_name}
Technical description: {description}
Annual volume: {annual_volume} pcs
Release pattern: {release_pattern}
Target region & Incoterm: {region_incoterm}
Target lead time: {lead_time}
Expected contract duration: {contract_duration}
Special requirements: {special_requirements}

Please provide a quotation including:
- Unit price by volume tier (if applicable)
- Tooling cost (if any)
- Freight and logistics assumptions
- Minimum order quantity (MOQ)
- Standard lead time and any expedite options
- Payment terms
- Incoterm and shipping point
- Any technical or commercial deviations from this request

Kindly submit your quotation by [insert deadline date].

Best regards,
[Your Name]
[Your Role]
[Your Company]"""

        st.success("RFQ Email Generated!")
        st.text_area("RFQ Email Draft", email, height=400)

        st.subheader("RFQ Line Items")
        items_df = pd.DataFrame([{
            "Item_ID": "ITEM-001",
            "Item_description": part_name,
            "Qty": annual_volume,
            "Unit": "pcs",
            "Target_date": "2026-06-01",
            "Notes": f"Annual volume, released as per pattern: {release_pattern}"
        }])
        st.dataframe(items_df, use_container_width=True)

# ==============================
# SECTION 2 – QUOTE COMPARISON
# ==============================

elif section == "📊 Quote Comparison":
    st.header("📊 Quote Comparison")

    mode = st.radio(
        "How do you want to provide quotes?",
        ["Enter manually", "Upload CSV"]
    )

    annual_volume = st.number_input("Annual Volume (pcs)", value=50000, step=1000)

    def run_quote_comparison(df, annual_volume):
        for col in ["Unit_price", "Tooling_cost", "Freight_cost", "Other_charges"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["Total_material_cost"] = df["Unit_price"] * annual_volume
        df["Total_landed_cost"] = (
            df["Total_material_cost"]
            + df["Tooling_cost"]
            + df["Freight_cost"]
            + df["Other_charges"]
        )

        st.success("Quote Comparison Complete!")
        st.dataframe(
            df[
                [
                    "Supplier",
                    "Item_ID",
                    "Unit_price",
                    "Tooling_cost",
                    "Freight_cost",
                    "MOQ",
                    "Lead_time_weeks",
                    "Payment_terms",
                    "Total_material_cost",
                    "Total_landed_cost",
                ]
            ],
            use_container_width=True,
        )

        best_cost = df.loc[df["Total_landed_cost"].idxmin()]
        best_lead = df.loc[df["Lead_time_weeks"].idxmin()]

        st.subheader("Copilot Insights")
        st.info(
            f"💰 Lowest total landed cost: **{best_cost['Supplier']}** (${best_cost['Total_landed_cost']:,.2f})"
        )
        st.info(
            f"⚡ Shortest lead time: **{best_lead['Supplier']}** ({best_lead['Lead_time_weeks']} weeks)"
        )
        st.warning(
            "Consider trade-offs between cost, lead time, payment terms, and MOQs before final award."
        )

    if mode == "Enter manually":
        st.subheader("Supplier Quotes (manual entry)")

        default_quotes = pd.DataFrame([
            {"Supplier": "Supplier A", "Item_ID": "ITEM-001", "Unit_price": 4.20, "Tooling_cost": 5000, "Freight_cost": 1200, "Other_charges": 0, "MOQ": 5000, "Lead_time_weeks": 7, "Payment_terms": "Net 45"},
            {"Supplier": "Supplier B", "Item_ID": "ITEM-001", "Unit_price": 4.05, "Tooling_cost": 6500, "Freight_cost": 1500, "Other_charges": 0, "MOQ": 6000, "Lead_time_weeks": 9, "Payment_terms": "Net 30"},
        ])

        quotes_input = st.data_editor(default_quotes, num_rows="dynamic", use_container_width=True)

        if st.button("Compare Quotes (manual)"):
            run_quote_comparison(quotes_input.copy(), annual_volume)

    elif mode == "Upload CSV":
        st.subheader("Upload Supplier Quotes (CSV)")
        st.caption(
            "Template columns: Supplier, Item_ID, Unit_price, Tooling_cost, "
            "Freight_cost, Other_charges, MOQ, Lead_time_weeks, Payment_terms"
        )

        uploaded_file = st.file_uploader("Upload quote file", type=["csv"])

        if uploaded_file is not None:
            quotes_input = pd.read_csv(uploaded_file)
            st.dataframe(quotes_input, use_container_width=True)

            if st.button("Compare Quotes (from file)"):
                run_quote_comparison(quotes_input.copy(), annual_volume)
        else:
            st.info("Upload a CSV file to enable file-based comparison.")

# ==============================
# SECTION 3 – AWARD & RISK
# ==============================

elif section == "🏆 Award & Risk":
    st.header("🏆 Award Recommendation & Risk Flags")
    st.markdown("Set your priority and thresholds. The copilot will recommend which supplier gets each item.")

    mode = st.radio(
        "How do you want to provide quotes for award?",
        ["Enter manually", "Upload CSV"]
    )

    priority = st.slider(
        "Priority: Cost vs Speed",
        0.0, 1.0, 0.5,
        help="1.0 = pure cost focus | 0.0 = pure speed focus | 0.5 = balanced"
    )

    st.subheader("Risk Thresholds")
    col1, col2, col3 = st.columns(3)
    with col1:
        max_moq = st.number_input("Max MOQ (pcs)", value=10000, step=500)
    with col2:
        max_lead = st.number_input("Max Lead Time (weeks)", value=8, step=1)
    with col3:
        std_payment = st.number_input("Standard Payment Days", value=45, step=5)

    annual_volume = st.number_input("Annual Volume (pcs)", value=50000, step=1000)

    def run_award_and_risk(quotes_df):
        df = quotes_df.copy()
        for col in ["Unit_price", "Tooling_cost", "Freight_cost", "Other_charges"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["Total_material_cost"] = df["Unit_price"] * annual_volume
        df["Total_landed_cost"] = (
            df["Total_material_cost"] + df["Tooling_cost"]
            + df["Freight_cost"] + df["Other_charges"]
        )

        results = []
        for item_id in df["Item_ID"].unique():
            item_df = df[df["Item_ID"] == item_id].copy()

            max_cost = item_df["Total_landed_cost"].max()
            min_cost = item_df["Total_landed_cost"].min()
            if max_cost != min_cost:
                item_df["cost_score"] = 1 - (
                    (item_df["Total_landed_cost"] - min_cost) / (max_cost - min_cost)
                )
            else:
                item_df["cost_score"] = 1.0

            max_lead_item = item_df["Lead_time_weeks"].max()
            min_lead_item = item_df["Lead_time_weeks"].min()
            if max_lead_item != min_lead_item:
                item_df["lead_score"] = 1 - (
                    (item_df["Lead_time_weeks"] - min_lead_item) / (max_lead_item - min_lead_item)
                )
            else:
                item_df["lead_score"] = 1.0

            item_df["final_score"] = priority * item_df["cost_score"] + (1 - priority) * item_df["lead_score"]
            winner = item_df.loc[item_df["final_score"].idxmax()]
            results.append({
                "Item_ID": item_id,
                "Recommended_Supplier": winner["Supplier"],
                "Total_landed_cost": winner["Total_landed_cost"],
                "Lead_time_weeks": winner["Lead_time_weeks"],
                "MOQ": winner["MOQ"],
                "Payment_terms": winner["Payment_terms"],
                "Final_score": round(winner["final_score"], 3),
            })

        award_df = pd.DataFrame(results)

        st.success("Award Recommendation Ready!")
        st.dataframe(award_df, use_container_width=True)
        st.metric("Total Projected Spend", f"${award_df['Total_landed_cost'].sum():,.2f}")

        st.subheader("Risk Flags")
        for _, row in award_df.iterrows():
            flags = []
            if row["MOQ"] > max_moq:
                flags.append(f"⚠ HIGH MOQ: {int(row['MOQ'])} pcs (threshold: {max_moq} pcs) – risk of excess inventory.")
            if row["Lead_time_weeks"] > max_lead:
                flags.append(f"⚠ LONG LEAD TIME: {row['Lead_time_weeks']} weeks (threshold: {max_lead} weeks) – risk of program delay.")
            try:
                payment_days = int("".join(filter(str.isdigit, str(row["Payment_terms"]))))
            except Exception:
                payment_days = std_payment
            if payment_days < std_payment:
                flags.append(f"⚠ TIGHT PAYMENT TERMS: {row['Payment_terms']} (standard: Net {std_payment}) – cash flow risk.")

            if flags:
                st.error(f"**{row['Item_ID']} → {row['Recommended_Supplier']}**")
                for f in flags:
                    st.warning(f)
            else:
                st.success(f"**{row['Item_ID']} → {row['Recommended_Supplier']}**: ✅ No risks flagged.")

    if mode == "Enter manually":
        st.subheader("Supplier Quotes for Award (manual entry)")
        default_quotes = pd.DataFrame([
            {"Supplier": "Supplier A", "Item_ID": "ITEM-001", "Unit_price": 4.20, "Tooling_cost": 5000, "Freight_cost": 1200, "Other_charges": 0, "MOQ": 5000, "Lead_time_weeks": 7, "Payment_terms": "Net 45"},
            {"Supplier": "Supplier A", "Item_ID": "ITEM-002", "Unit_price": 3.10, "Tooling_cost": 3000, "Freight_cost": 800,  "Other_charges": 0, "MOQ": 3000, "Lead_time_weeks": 6, "Payment_terms": "Net 45"},
            {"Supplier": "Supplier A", "Item_ID": "ITEM-003", "Unit_price": 0.85, "Tooling_cost": 1500, "Freight_cost": 500,  "Other_charges": 0, "MOQ": 10000,"Lead_time_weeks": 5, "Payment_terms": "Net 45"},
            {"Supplier": "Supplier B", "Item_ID": "ITEM-001", "Unit_price": 4.05, "Tooling_cost": 6500, "Freight_cost": 1500, "Other_charges": 0, "MOQ": 6000, "Lead_time_weeks": 9, "Payment_terms": "Net 30"},
            {"Supplier": "Supplier B", "Item_ID": "ITEM-002", "Unit_price": 2.95, "Tooling_cost": 3500, "Freight_cost": 900,  "Other_charges": 0, "MOQ": 4000, "Lead_time_weeks": 8, "Payment_terms": "Net 30"},
            {"Supplier": "Supplier B", "Item_ID": "ITEM-003", "Unit_price": 0.80, "Tooling_cost": 2000, "Freight_cost": 600,  "Other_charges": 0, "MOQ": 12000,"Lead_time_weeks": 7, "Payment_terms": "Net 30"},
        ])

        quotes_input = st.data_editor(default_quotes, num_rows="dynamic", use_container_width=True)

        if st.button("Get Award Recommendation (manual)"):
            run_award_and_risk(quotes_input)

    elif mode == "Upload CSV":
        st.subheader("Upload Supplier Quotes for Award (CSV)")
        st.caption(
            "Template columns: Supplier, Item_ID, Unit_price, Tooling_cost, "
            "Freight_cost, Other_charges, MOQ, Lead_time_weeks, Payment_terms"
        )

        uploaded_file = st.file_uploader("Upload quote file for award", type=["csv"], key="award_upload")

        if uploaded_file is not None:
            quotes_input = pd.read_csv(uploaded_file)
            st.dataframe(quotes_input, use_container_width=True)

            if st.button("Get Award Recommendation (from file)"):
                run_award_and_risk(quotes_input)
        else:
            st.info("Upload a CSV file to enable file-based award recommendation.")

# ==============================
# SECTION 4 – SOURCING SUMMARY
# ==============================

elif section == "📈 Sourcing Summary":
    st.header("📈 Sourcing Summary Dashboard")

    st.markdown(
        "High-level view of RFQ outcome: savings, supplier split, and cost vs lead time."
    )

    annual_volume = st.number_input("Annual Volume (pcs)", value=50000, step=1000)
    priority = st.slider(
        "Priority used for award (for scoring reference only)",
        0.0, 1.0, 0.5,
        help="1.0 = pure cost focus | 0.0 = pure speed focus | 0.5 = balanced"
    )

    # Default data (can be overridden by CSV upload)
    default_quotes = pd.DataFrame([
        {"Supplier": "Supplier A", "Item_ID": "ITEM-001", "Unit_price": 4.20, "Tooling_cost": 5000, "Freight_cost": 1200, "Other_charges": 0, "MOQ": 5000, "Lead_time_weeks": 7, "Payment_terms": "Net 45"},
        {"Supplier": "Supplier A", "Item_ID": "ITEM-002", "Unit_price": 3.10, "Tooling_cost": 3000, "Freight_cost": 800,  "Other_charges": 0, "MOQ": 3000, "Lead_time_weeks": 6, "Payment_terms": "Net 45"},
        {"Supplier": "Supplier B", "Item_ID": "ITEM-001", "Unit_price": 4.05, "Tooling_cost": 6500, "Freight_cost": 1500, "Other_charges": 0, "MOQ": 6000, "Lead_time_weeks": 9, "Payment_terms": "Net 30"},
        {"Supplier": "Supplier B", "Item_ID": "ITEM-002", "Unit_price": 2.95, "Tooling_cost": 3500, "Freight_cost": 900,  "Other_charges": 0, "MOQ": 4000, "Lead_time_weeks": 8, "Payment_terms": "Net 30"},
    ])

    st.subheader("Quotes used for dashboard")

    uploaded_summary = st.file_uploader(
        "Upload quotes CSV for dashboard (optional)",
        type=["csv"],
        key="summary_upload",
    )

    if uploaded_summary is not None:
        quotes_input = pd.read_csv(uploaded_summary)
        st.caption("Using uploaded CSV for dashboard. You can still edit below.")
    else:
        quotes_input = default_quotes.copy()
        st.caption("Using default sample data. Upload a CSV to override.")

    with st.expander("View / adjust quote data used for dashboard"):
        quotes_input = st.data_editor(quotes_input, num_rows="dynamic", use_container_width=True)

    base_price = st.number_input(
        "Baseline unit price (for savings calc, e.g., incumbent price)",
        value=4.50,
        step=0.10
    )

    if st.button("Refresh Dashboard"):
        full_df, award_df = compute_award_df(quotes_input, annual_volume, priority)

        total_qty = annual_volume * award_df["Item_ID"].nunique()
        baseline_cost = base_price * total_qty
        awarded_cost = award_df["Total_landed_cost"].sum()
        savings = baseline_cost - awarded_cost
        savings_pct = (savings / baseline_cost * 100) if baseline_cost else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Baseline Spend", f"${baseline_cost:,.0f}")
        with col2:
            st.metric("Awarded Spend", f"${awarded_cost:,.0f}")
        with col3:
            st.metric("Savings", f"${savings:,.0f}", f"{savings_pct:,.1f}%")

        spend_by_supplier = award_df.groupby("Supplier")["Total_landed_cost"].sum().reset_index()
        st.subheader("Spend by Supplier")
        st.bar_chart(
            data=spend_by_supplier.set_index("Supplier")["Total_landed_cost"]
        )

        st.subheader("Share of Business (Approx.)")
        st.bar_chart(
            data=(spend_by_supplier.set_index("Supplier")["Total_landed_cost"] / awarded_cost)
        )

        st.subheader("Cost vs Lead Time (Items)")
        scatter_df = award_df[["Item_ID", "Total_landed_cost", "Lead_time_weeks", "Supplier"]]
        st.dataframe(scatter_df, use_container_width=True)
        st.caption("Use this table to discuss trade-offs between lead time and cost at item level.")
    else:
        st.info("Click 'Refresh Dashboard' to compute KPIs and charts.")


# ==============================
# SECTION 5 – SUPPLIER SCORECARD
# ==============================

elif section == "📊 Supplier Scorecard":
    st.header("📊 Supplier Scorecard")

    st.markdown(
        "Combine commercial outcome with quality and delivery performance to rate suppliers."
    )

    st.subheader("Define weights for scorecard")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        w_cost = st.number_input("Weight: Cost", value=0.40, min_value=0.0, max_value=1.0, step=0.05)
    with col2:
        w_quality = st.number_input("Weight: Quality", value=0.25, min_value=0.0, max_value=1.0, step=0.05)
    with col3:
        w_delivery = st.number_input("Weight: Delivery", value=0.25, min_value=0.0, max_value=1.0, step=0.05)
    with col4:
        w_collab = st.number_input("Weight: Collaboration", value=0.10, min_value=0.0, max_value=1.0, step=0.05)

    total_w = w_cost + w_quality + w_delivery + w_collab
    if abs(total_w - 1.0) > 0.001:
        st.warning(f"Current weights sum to {total_w:.2f}. Consider adjusting to 1.0 for clean interpretation.")

    st.subheader("Supplier performance inputs")

    # Default scorecard (can be overridden by CSV)
    scorecard_default = pd.DataFrame([
        {"Supplier": "Supplier A", "Cost_rating": 4, "Quality_rating": 4, "Delivery_rating": 5, "Collaboration_rating": 4, "Strategic_role": "Core"},
        {"Supplier": "Supplier B", "Cost_rating": 5, "Quality_rating": 3, "Delivery_rating": 3, "Collaboration_rating": 3, "Strategic_role": "Backup"},
    ])

    uploaded_scorecard = st.file_uploader(
        "Upload supplier scorecard CSV (optional)",
        type=["csv"],
        key="scorecard_upload",
    )

    if uploaded_scorecard is not None:
        scorecard_input = pd.read_csv(uploaded_scorecard)
        st.caption("Using uploaded CSV for scorecard. You can still edit below.")
    else:
        scorecard_input = scorecard_default.copy()
        st.caption("Using default sample scorecard. Upload a CSV to override.")

    scorecard_input = st.data_editor(
        scorecard_input,
        num_rows="dynamic",
        use_container_width=True
    )

    if st.button("Calculate Supplier Scores"):
        df = scorecard_input.copy()

        for col in ["Cost_rating", "Quality_rating", "Delivery_rating", "Collaboration_rating"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        max_rating = 5.0
        df["Cost_norm"] = df["Cost_rating"] / max_rating
        df["Quality_norm"] = df["Quality_rating"] / max_rating
        df["Delivery_norm"] = df["Delivery_rating"] / max_rating
        df["Collab_norm"] = df["Collaboration_rating"] / max_rating

        df["Total_score"] = (
            w_cost * df["Cost_norm"]
            + w_quality * df["Quality_norm"]
            + w_delivery * df["Delivery_norm"]
            + w_collab * df["Collab_norm"]
        )

        def band(score):
            if score >= 0.80:
                return "Preferred"
            elif score >= 0.60:
                return "Approved"
            else:
                return "Monitor / Develop"

        df["Rating_band"] = df["Total_score"].apply(band)

        st.subheader("Scorecard Results")
        st.dataframe(
            df[[
                "Supplier",
                "Strategic_role",
                "Cost_rating",
                "Quality_rating",
                "Delivery_rating",
                "Collaboration_rating",
                "Total_score",
                "Rating_band",
            ]],
            use_container_width=True,
        )

        st.caption("Use this table during QBRs and sourcing decisions to justify supplier positioning.")
    else:
        st.info("Adjust ratings and weights, then click 'Calculate Supplier Scores'.")
