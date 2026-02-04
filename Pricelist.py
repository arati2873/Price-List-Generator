import streamlit as st
import pandas as pd
import zipfile
import io

st.set_page_config(page_title="Pricelist Generator", layout="wide")

st.title("📦 Pricelist File Generator (BasePrice x Pricelist Factors)")

st.write("""
Upload:
1) Base Price file → columns: **SKU, BasePrice**  
2) Pricelist file → columns: **PricelistName, Factor**  
The app will generate one output file per pricelist and allow you to download them all as a ZIP.
""")

base_file = st.file_uploader("Upload Base Price File (CSV or Excel)", type=["csv", "xlsx"])
pricelist_file = st.file_uploader("Upload Pricelist Factors File (CSV or Excel)", type=["csv", "xlsx"])


def read_file(uploaded_file):
    try:
        if uploaded_file.name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        else:
            return pd.read_excel(uploaded_file)
    except Exception:
        return None


def validate_required_columns(df, required_cols, file_label):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(
            f"❌ {file_label} is missing required column(s): {', '.join(missing)}.\n\n"
            f"✅ Please upload a file containing: {', '.join(required_cols)}."
        )
        return False
    return True


if base_file and pricelist_file:

    df_base = read_file(base_file)
    df_pl = read_file(pricelist_file)

    if df_base is None:
        st.error("❌ Could not read the Base Price file. Please upload a valid CSV or Excel file.")
        st.stop()

    if df_pl is None:
        st.error("❌ Could not read the Pricelist Factors file. Please upload a valid CSV or Excel file.")
        st.stop()

    if df_base.empty:
        st.error("❌ Base Price file is empty. Please upload a file with SKU and BasePrice data.")
        st.stop()

    if df_pl.empty:
        st.error("❌ Pricelist Factors file is empty. Please upload a file with PricelistName and Factor data.")
        st.stop()

    # Column checks
    if not validate_required_columns(df_base, ["SKU", "BasePrice"], "Base Price file"):
        st.stop()

    if not validate_required_columns(df_pl, ["PricelistName", "Factor"], "Pricelist Factors file"):
        st.stop()

    # Remove blanks
    df_base["SKU"] = df_base["SKU"].astype(str).str.strip()
    df_pl["PricelistName"] = df_pl["PricelistName"].astype(str).str.strip()

    # Check for blank SKUs
    if (df_base["SKU"] == "").any():
        st.error("❌ Some SKUs are blank in the Base Price file. Please fix and upload again.")
        st.stop()

    # Check for blank pricelist names
    if (df_pl["PricelistName"] == "").any():
        st.error("❌ Some PricelistName values are blank in the Pricelist Factors file. Please fix and upload again.")
        st.stop()

    # Numeric conversion
    df_base["BasePrice"] = pd.to_numeric(df_base["BasePrice"], errors="coerce")
    df_pl["Factor"] = pd.to_numeric(df_pl["Factor"], errors="coerce")

    if df_base["BasePrice"].isna().any():
        bad_rows = df_base[df_base["BasePrice"].isna()].head(5)
        st.error("❌ Some BasePrice values are not numeric (example rows shown below). Please correct them.")
        st.dataframe(bad_rows)
        st.stop()

    if df_pl["Factor"].isna().any():
        bad_rows = df_pl[df_pl["Factor"].isna()].head(5)
        st.error("❌ Some Factor values are not numeric (example rows shown below). Please correct them.")
        st.dataframe(bad_rows)
        st.stop()

    # Optional: check factor values (example: avoid negative)
    if (df_pl["Factor"] <= 0).any():
        st.error("❌ Factor must be greater than 0. Please fix the pricelist file.")
        st.stop()

    st.subheader("🔍 Preview: Base Price File")
    st.dataframe(df_base.head())

    st.subheader("🔍 Preview: Pricelist Factors File")
    st.dataframe(df_pl.head())

    st.success("✅ Files validated successfully. Generating pricelist outputs...")

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for _, row in df_pl.iterrows():
            pricelist_name = row["PricelistName"]
            factor = row["Factor"]

            df_out = df_base.copy()
            df_out["NewPrice"] = (df_out["BasePrice"] * factor).round(2)

            df_out = df_out[["SKU", "NewPrice"]]

            csv_buffer = io.StringIO()
            df_out.to_csv(csv_buffer, index=False)

            filename = f"{pricelist_name}.csv"
            zf.writestr(filename, csv_buffer.getvalue())

    zip_buffer.seek(0)

    st.download_button(
        label="⬇️ Download ALL Pricelist Files (ZIP)",
        data=zip_buffer,
        file_name="generated_pricelists.zip",
        mime="application/zip"
    )

    st.info(f"📌 Generated {len(df_pl)} pricelist files successfully.")
