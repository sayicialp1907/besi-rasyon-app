import streamlit as st
import pandas as pd

st.set_page_config(page_title="Besi Rasyon Programı", layout="wide")

st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>Besi Sığırları İçin En Düşük Maliyetli Rasyon Programı</h2>", unsafe_allow_html=True)
st.markdown("---")

col_yem, col_denge, col_hayvan = st.columns([1.5, 1.3, 1.2])

# --- 1. GİRDİLERİ ÖNCE ALIYORUZ (Hesaplamada kullanmak için) ---
with col_hayvan:
    st.subheader("🐂 Hayvan & Çevre Verileri")
    
    with st.expander("Hayvan Tanımı", expanded=True):
        hayvan_tipi = st.selectbox("Hayvan Tipi", ["Besi Sığırı", "Buzağı", "Damızlık Boğa"])
        irk = st.selectbox("Irk", ["Siyah Alaca (Holstein)", "Simental", "Montofon", "Yerli Kara"])
        yas = st.number_input("Yaş (Ay)", value=16, min_value=1)
        # Değerler değiştiğinde hesaplamayı tetikleyecek ana değişkenler
        canli_agirlik = st.number_input("Canlı Ağırlık (kg)", value=300, step=10)
        hedef_agirlik = st.number_input("Hedef Besi Sonu Ağırlığı (kg)", value=550, step=10)
        adg = st.number_input("Günlük Canlı Ağırlık Artışı (kg/gün)", value=1.600, step=0.1)
        kondisyon = st.slider("Kondisyon Skoru", 1.0, 5.0, 3.0, 0.5)

    with st.expander("Çevre ve Barınak Koşulları", expanded=False):
        sicaklik = st.number_input("Mevcut Sıcaklık (°C)", value=18.0)
        gecmis_sicaklik = st.number_input("Geçen Ayın Ort. Sıcaklığı (°C)", value=15.0)
        camur = st.selectbox("Zemindeki Çamur Miktarı", ["Yok", "Bileğe Kadar", "Dize Kadar"])
        deri_durumu = st.selectbox("Deri ve Kıl Durumu", ["Kuru", "Islak / Çamurlu"])
        mera = st.checkbox("Merada Otluyor mu?", value=False)

# --- 2. MATEMATİKSEL HESAPLAMALAR (AŞAMA 2) ---
# NRC Standartlarına benzer yaklaşık besi sığırı ihtiyaç formülleri (Dinamik)
ihtiyac_km = round((canli_agirlik * 0.015) + (adg * 2.3) + 0.02, 1)
ihtiyac_hp = round((canli_agirlik * 1.5) + (adg * 240), 0)
ihtiyac_me = round((canli_agirlik * 0.04) + (adg * 6.1), 2)
ihtiyac_ca = round((canli_agirlik * 0.08) + (adg * 10.6), 1)
ihtiyac_p = round((canli_agirlik * 0.04) + (adg * 6.25), 1)

# --- 3. VERİLECEK YEMLER (SOL) ---
with col_yem:
    st.subheader("🌾 Verilecek Yemler")
    df_yem = pd.read_csv("yem_veritabani.csv")
    duzenlenen_yemler = st.data_editor(df_yem, num_rows="dynamic", use_container_width=True)
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        btn_coz = st.button("⚡ RASYONU ÇÖZ (SOLVER)", type="primary", use_container_width=True)
    with col_btn2:
        btn_kaydet = st.button("💾 Rasyonu Kaydet", use_container_width=True)

# --- 4. BESİN MADDELERİ DENGESİ (ORTA) ---
with col_denge:
    st.subheader("📊 Besin Maddeleri Dengesi")
    
    denge_verileri = {
        "Besin Maddesi": [
            "Kuru Madde (kg/gün)",
            "Ham Protein (g/gün)",
            "ME (Mcal/gün)",
            "Kalsiyum - Ca (g/gün)",
            "Fosfor - P (g/gün)"
        ],
        # İhtiyaç değerleri artık yukarıdaki formüllerden dinamik olarak geliyor
        "İhtiyaç": [ihtiyac_km, ihtiyac_hp, ihtiyac_me, ihtiyac_ca, ihtiyac_p],
        "Rasyon": [8.4, 936, 21.6, 41.8, 22.3], # (Bu sütun Aşama 3'te dinamikleşecek)
        "Sonuç": ["FAZLA", "FAZLA", "TAMAM", "TAMAM", "TAMAM"] 
    }
    df_denge = pd.DataFrame(denge_verileri)
    
    def stil_uygula(val):
        if val == "EKSİK": return "background-color: #F87171; color: white; font-weight: bold;"
        elif val == "FAZLA": return "background-color: #60A5FA; color: white; font-weight: bold;"
        elif val in ["TAMAM", "UYGUN"]: return "background-color: #34D399; color: black; font-weight: bold;"
        return ""

    st.dataframe(df_denge.style.map(stil_uygula, subset=["Sonuç"]), use_container_width=True, height=460)