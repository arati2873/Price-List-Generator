import streamlit as st
import pandas as pd
import zipfile
import io

st.set_page_config(page_title="Pricelist Generator", layout="wide")
st.title("📦 Pricelist File Generator (SKU x Pricelist Factors)")

st.write("""
### Upload 3 Files:
1) Base Price file → columns: **SKU, BasePrice**  
2) Pricelist Factors file → columns: **PricelistName, Factor**  
3) RM Mapping file → columns: **PricelistName, RMName**
""")

base_file = st.file_uploader("Upload Base Price File (CSV)", type=["csv"])
factor_file = st.file_uploader("Upload Pricelist Factors File (CSV)", type=["csv"])
rm_file = st.file_uploader("Upload RM Mapping File (CSV)", type=["csv"])

def read_csv(uploaded_file, label):
    try:
        return pd.read_csv(uploaded_file)
    except Exception:
        st.error(f"❌ Could not read {label}. Please upload a valid CSV file.")
        return None

if base_file and factor_file and rm_file:

    df_base = read_csv(base_file, "Base Price file")
    df_factor = read_csv(factor_file, "Pricelist Factors file")
    df_rm = read_csv(rm_file, "RM Mapping file")

    if df_base is None or df_factor is None or df_rm is None:
        st.stop()

    # Validate columns
    if not {"SKU", "BasePrice"}.issubset(df_base.columns):
        st.error("❌ Base Price file must contain: SKU, BasePrice")
        st.stop()

    if not {"PricelistName", "Factor"}.issubset(df_factor.columns):
        st.error("❌ Pricelist Factors file must contain: PricelistName, Factor")
        st.stop()

    if not {"PricelistName", "RMName"}.issubset(df_rm.columns):
        st.error("❌ RM Mapping file must contain: PricelistName, RMName")
        st.stop()

    # Clean
    df_base["SKU"] = df_base["SKU"].astype(str).str.strip()
    df_factor["PricelistName"] = df_factor["PricelistName"].astype(str).str.strip()
    df_rm["PricelistName"] = df_rm["PricelistName"].astype(str).str.strip()
    df_rm["RMName"] = df_rm["RMName"].astype(str).str.strip()

    df_base["BasePrice"] = pd.to_numeric(df_base["BasePrice"], errors="coerce")
    df_factor["Factor"] = pd.to_numeric(df_factor["Factor"], errors="coerce")

    if df_base["BasePrice"].isna().any():
        st.error("❌ BasePrice has non-numeric values. Please fix your base file.")
        st.stop()

    if df_factor["Factor"].isna().any():
        st.error("❌ Factor has non-numeric values. Please fix your factor file.")
        st.stop()

    # Check pricelist consistency
    factor_pricelists = set(df_factor["PricelistName"].unique())
    rm_pricelists = set(df_rm["PricelistName"].unique())

    missing_in_factor = rm_pricelists - factor_pricelists
    if missing_in_factor:
        st.error(
            "❌ RM Mapping file contains pricelist(s) not found in Factor file:\n\n"
            + ", ".join(sorted(missing_in_factor))
        )
        st.stop()

    st.success("✅ Files validated successfully. Generating ZIP with RM folders...")

    # Create zip in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:

        # Loop through RM groups
        for rm_name, rm_group in df_rm.groupby("RMName"):

            for _, rm_row in rm_group.iterrows():
                pricelist_name = rm_row["PricelistName"]

                # Get factor
                factor = df_factor.loc[df_factor["PricelistName"] == pricelist_name, "Factor"].iloc[0]

                # Generate output
                df_out = df_base.copy()
                df_out["NewPrice"] = (df_out["BasePrice"] * factor).round(2)
                df_out = df_out[["SKU", "NewPrice"]]

                # Save as CSV
                csv_buffer = io.StringIO()
                df_out.to_csv(csv_buffer, index=False)

                # Put inside RM folder
                safe_rm = rm_name.replace("/", "_").replace("\\", "_")
                file_path = f"{safe_rm}/{pricelist_name}.csv"

                zf.writestr(file_path, csv_buffer.getvalue())

    zip_buffer.seek(0)

    st.download_button(
        label="⬇️ Download ZIP (RM Folders + Pricelist Files)",
        data=zip_buffer,
        file_name="generated_pricelists_by_rm.zip",
        mime="application/zip"
    )

    st.info("📌 ZIP generated successfully with RM-wise folders.")
