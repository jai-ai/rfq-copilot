import streamlit as st
import pandas as pd

st.set_page_config(page_title="RFQ Copilot", page_icon="📋", layout="wide")

st.title("📋 RFQ & Supplier Response Copilot")
st.markdown("*Procurement tool for RFQ generation, quote comparison, and award recommendation.*")

# ==============================
# SIDEBAR – NAVIGATION
# ==============================

section = st.sidebar.radio(
    "Navigate",
    ["📋 RFQ Generator", "📊 Quote Comparison", "🏆 Award & Risk"]
)

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
    st.markdown("Enter supplier quotes below. The copilot will calculate total landed cost automatically.")

    annual_volume = st.number_input("Annual Volume (pcs)", value=50000, step=1000)

    st.subheader("Supplier Quotes")
    default_quotes = pd.DataFrame([
        {"Supplier": "Supplier A", "Item_ID": "ITEM-001", "Unit_price": 4.20, "Tooling_cost": 5000, "Freight_cost": 1200, "Other_charges": 0, "MOQ": 5000, "Lead_time_weeks": 7, "Payment_terms": "Net 45"},
        {"Supplier": "Supplier B", "Item_ID": "ITEM-001", "Unit_price": 4.05, "Tooling_cost": 6500, "Freight_cost": 1500, "Other_charges": 0, "MOQ": 6000, "Lead_time_weeks": 9, "Payment_terms": "Net 30"},
    ])

    quotes_input = st.data_editor(default_quotes, num_rows="dynamic", use_container_width=True)

    if st.button("Compare Quotes"):
        df = quotes_input.copy()
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
        st.dataframe(df[["Supplier", "Item_ID", "Unit_price", "Tooling_cost", "Freight_cost",
                          "MOQ", "Lead_time_weeks", "Payment_terms",
                          "Total_material_cost", "Total_landed_cost"]], use_container_width=True)

        best_cost = df.loc[df["Total_landed_cost"].idxmin()]
        best_lead = df.loc[df["Lead_time_weeks"].idxmin()]

        st.subheader("Copilot Insights")
        st.info(f"💰 Lowest total landed cost: **{best_cost['Supplier']}** (${best_cost['Total_landed_cost']:,.2f})")
        st.info(f"⚡ Shortest lead time: **{best_lead['Supplier']}** ({best_lead['Lead_time_weeks']} weeks)")
        st.warning("Consider trade-offs between cost, lead time, payment terms, and MOQs before final award.")

# ==============================
# SECTION 3 – AWARD & RISK
# ==============================

elif section == "🏆 Award & Risk":
    st.header("🏆 Award Recommendation & Risk Flags")
    st.markdown("Set your priority and thresholds. The copilot will recommend which supplier gets each item.")

    priority = st.slider("Priority: Cost vs Speed", 0.0, 1.0, 0.5,
                         help="1.0 = pure cost focus | 0.0 = pure speed focus | 0.5 = balanced")

    st.subheader("Risk Thresholds")
    col1, col2, col3 = st.columns(3)
    with col1:
        max_moq = st.number_input("Max MOQ (pcs)", value=10000, step=500)
    with col2:
        max_lead = st.number_input("Max Lead Time (weeks)", value=8, step=1)
    with col3:
        std_payment = st.number_input("Standard Payment Days", value=45, step=5)

    annual_volume = st.number_input("Annual Volume (pcs)", value=50000, step=1000)

    st.subheader("Supplier Quotes")
    default_quotes = pd.DataFrame([
        {"Supplier": "Supplier A", "Item_ID": "ITEM-001", "Unit_price": 4.20, "Tooling_cost": 5000, "Freight_cost": 1200, "Other_charges": 0, "MOQ": 5000, "Lead_time_weeks": 7, "Payment_terms": "Net 45"},
        {"Supplier": "Supplier A", "Item_ID": "ITEM-002", "Unit_price": 3.10, "Tooling_cost": 3000, "Freight_cost": 800,  "Other_charges": 0, "MOQ": 3000, "Lead_time_weeks": 6, "Payment_terms": "Net 45"},
        {"Supplier": "Supplier A", "Item_ID": "ITEM-003", "Unit_price": 0.85, "Tooling_cost": 1500, "Freight_cost": 500,  "Other_charges": 0, "MOQ": 10000,"Lead_time_weeks": 5, "Payment_terms": "Net 45"},
        {"Supplier": "Supplier B", "Item_ID": "ITEM-001", "Unit_price": 4.05, "Tooling_cost": 6500, "Freight_cost": 1500, "Other_charges": 0, "MOQ": 6000, "Lead_time_weeks": 9, "Payment_terms": "Net 30"},
        {"Supplier": "Supplier B", "Item_ID": "ITEM-002", "Unit_price": 2.95, "Tooling_cost": 3500, "Freight_cost": 900,  "Other_charges": 0, "MOQ": 4000, "Lead_time_weeks": 8, "Payment_terms": "Net 30"},
        {"Supplier": "Supplier B", "Item_ID": "ITEM-003", "Unit_price": 0.80, "Tooling_cost": 2000, "Freight_cost": 600,  "Other_charges": 0, "MOQ": 12000,"Lead_time_weeks": 7, "Payment_terms": "Net 30"},
    ])

    quotes_input = st.data_editor(default_quotes, num_rows="dynamic", use_container_width=True)

    if st.button("Get Award Recommendation"):
        df = quotes_input.copy()
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
            item_df["cost_score"] = 1 - ((item_df["Total_landed_cost"] - min_cost) / (max_cost - min_cost)) if max_cost != min_cost else 1.0

            max_lead = item_df["Lead_time_weeks"].max()
            min_lead = item_df["Lead_time_weeks"].min()
            item_df["lead_score"] = 1 - ((item_df["Lead_time_weeks"] - min_lead) / (max_lead - min_lead)) if max_lead != min_lead else 1.0

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
                payment_days = int(''.join(filter(str.isdigit, str(row["Payment_terms"]))))
            except:
                payment_days = std_payment
            if payment_days < std_payment:
                flags.append(f"⚠ TIGHT PAYMENT TERMS: {row['Payment_terms']} (standard: Net {std_payment}) – cash flow risk.")

            if flags:
                st.error(f"**{row['Item_ID']} → {row['Recommended_Supplier']}**")
                for f in flags:
                    st.warning(f)
            else:
                st.success(f"**{row['Item_ID']} → {row['Recommended_Supplier']}**: ✅ No risks flagged.")
