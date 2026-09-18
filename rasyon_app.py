import streamlit as st
import pandas as pd
import pulp

st.set_page_config(page_title="Besi Rasyon Programı", layout="wide")
st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>Besi Sığırları İçin En Düşük Maliyetli Rasyon Programı</h2>", unsafe_allow_html=True)
st.markdown("---")

col_yem, col_denge, col_hayvan = st.columns([1.5, 1.3, 1.2])

# --- 1. GİRDİLER ---
with col_hayvan:
    st.subheader("🐂 Hayvan & Çevre Verileri")
    with st.expander("Hayvan Tanımı", expanded=True):
        hayvan_tipi = st.selectbox("Hayvan Tipi", ["Besi Sığırı", "Buzağı", "Damızlık Boğa"])
        irk = st.selectbox("Irk", ["Siyah Alaca (Holstein)", "Simental", "Montofon", "Yerli Kara"])
        yas = st.number_input("Yaş (Ay)", value=16, min_value=1)
        canli_agirlik = st.number_input("Canlı Ağırlık (kg)", value=300, step=10)
        hedef_agirlik = st.number_input("Hedef Besi Sonu Ağırlığı (kg)", value=550, step=10)
        adg = st.number_input("Günlük Canlı Ağırlık Artışı (kg/gün)", value=1.600, step=0.1)
        kondisyon = st.slider("Kondisyon Skoru", 1.0, 5.0, 3.0, 0.5)

# --- 2. DİNAMİK HESAPLAMALAR ---
# NRC Standartlarına göre dinamik ihtiyaç formülleri
ihtiyac_km = round((canli_agirlik * 0.015) + (adg * 2.3) + 0.02, 1)
ihtiyac_hp = round((canli_agirlik * 1.5) + (adg * 240), 0)
ihtiyac_me = round((canli_agirlik * 0.04) + (adg * 6.1), 2)
ihtiyac_ca = round((canli_agirlik * 0.08) + (adg * 10.6), 1)
ihtiyac_p = round((canli_agirlik * 0.04) + (adg * 6.25), 1)

# --- 3. VERİLECEK YEMLER VE SOLVER (ÇÖZÜCÜ) OPTİMİZASYONU ---
with col_yem:
    st.subheader("🌾 Verilecek Yemler")
    
    # Yem dosyasını güvenli okuma ve eksik limit sütunlarını otomatik tamamlama
    try:
        df_yem = pd.read_csv("yem_veritabani.csv")
        if 'min_kg' not in df_yem.columns: df_yem['min_kg'] = 0.0
        if 'maks_kg' not in df_yem.columns: df_yem['maks_kg'] = 15.0
    except FileNotFoundError:
        st.error("yem_veritabani.csv dosyası bulunamadı!")
        st.stop()
        
    duzenlenen_yemler = st.data_editor(df_yem, num_rows="dynamic", use_container_width=True)
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        btn_coz = st.button("⚡ RASYONU ÇÖZ (SOLVER)", type="primary", use_container_width=True)
    with col_btn2:
        btn_kaydet = st.button("💾 Rasyonu Kaydet", use_container_width=True)

# Başlangıç değerleri (Çözülmeden önce 0)
rasyon_km = rasyon_hp = rasyon_me = rasyon_ca = rasyon_p = maliyet = 0.0
optimal_mi = False

if btn_coz:
    # --- PuLP İLE EXCEL SOLVER MANTIĞINI KURUYORUZ ---
    prob = pulp.LpProblem("En_Ucuz_Rasyon", pulp.LpMinimize)
    
    # Her yem için bir değişken oluştur (Kullanıcının girdiği Min ve Maks değerleri arasında)
    yem_vars = []
    for index, row in duzenlenen_yemler.iterrows():
        var = pulp.LpVariable(f"yem_{index}", lowBound=row['min_kg'], upBound=row['maks_kg'])
        yem_vars.append(var)
        
    # Amaç: Toplam Maliyeti Minimize Et
    prob += pulp.lpSum([yem_vars[i] * duzenlenen_yemler.loc[i, 'fiyat_tl'] for i in range(len(yem_vars))]), "Maliyet"
    
    # Kısıtlar: Besin ihtiyaçları karşılansın
    prob += pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'kuru_madde_yuzde']/100) for i in range(len(yem_vars))]) >= ihtiyac_km * 0.98
    prob += pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'kuru_madde_yuzde']/100) for i in range(len(yem_vars))]) <= ihtiyac_km * 1.05
    prob += pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'ham_protein_yuzde']*10) for i in range(len(yem_vars))]) >= ihtiyac_hp
    prob += pulp.lpSum([yem_vars[i] * duzenlenen_yemler.loc[i, 'me_mcal_kg'] for i in range(len(yem_vars))]) >= ihtiyac_me
    prob += pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'kalsiyum_yuzde']*10) for i in range(len(yem_vars))]) >= ihtiyac_ca
    prob += pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'fosfor_yuzde']*10) for i in range(len(yem_vars))]) >= ihtiyac_p
    
    # Çöz!
    prob.solve()
    
    if pulp.LpStatus[prob.status] == "Optimal":
        optimal_mi = True
        st.toast("✅ Optimal Rasyon Bulundu!")
        
        # Sonuçları oku ve sağlanan besin maddelerini hesapla
        for i, var in enumerate(yem_vars):
            kg = var.varValue
            duzenlenen_yemler.at[i, 'Önerilen Miktar (kg)'] = round(kg, 2)
            rasyon_km += kg * (duzenlenen_yemler.loc[i, 'kuru_madde_yuzde'] / 100)
            rasyon_hp += kg * (duzenlenen_yemler.loc[i, 'ham_protein_yuzde'] * 10)
            rasyon_me += kg * duzenlenen_yemler.loc[i, 'me_mcal_kg']
            rasyon_ca += kg * (duzenlenen_yemler.loc[i, 'kalsiyum_yuzde'] * 10)
            rasyon_p += kg * (duzenlenen_yemler.loc[i, 'fosfor_yuzde'] * 10)
            maliyet += kg * duzenlenen_yemler.loc[i, 'fiyat_tl']
    else:
        st.error("⚠️ Seçilen yemler ve sınırlar ile uygun bir rasyon bulunamadı. Lütfen yem sınırlarını (Maks) artırın.")

# --- 4. BESİN MADDELERİ DENGESİ (ORTA) ---
with col_denge:
    st.subheader("📊 Besin Maddeleri Dengesi")
    
    # Excel'deki Tamam/Eksik/Fazla karar formülü
    def durum_hesapla(rasyon, ihtiyac):
        if rasyon == 0: return "-"
        if rasyon < ihtiyac * 0.98: return "EKSİK"
        if rasyon > ihtiyac * 1.05: return "FAZLA"
        return "TAMAM"
        
    denge_verileri = {
        "Besin Maddesi": ["Kuru Madde (kg/gün)", "Ham Protein (g/gün)", "ME (Mcal/gün)", "Kalsiyum (g/gün)", "Fosfor (g/gün)"],
        "İhtiyaç": [ihtiyac_km, ihtiyac_hp, ihtiyac_me, ihtiyac_ca, ihtiyac_p],
        "Rasyon": [round(rasyon_km,1), round(rasyon_hp,0), round(rasyon_me,1), round(rasyon_ca,1), round(rasyon_p,1)],
        "Sonuç": [
            durum_hesapla(rasyon_km, ihtiyac_km),
            durum_hesapla(rasyon_hp, ihtiyac_hp),
            durum_hesapla(rasyon_me, ihtiyac_me),
            durum_hesapla(rasyon_ca, ihtiyac_ca),
            durum_hesapla(rasyon_p, ihtiyac_p)
        ]
    }
    
    def stil_uygula(val):
        if val == "EKSİK": return "background-color: #F87171; color: white; font-weight: bold;"
        elif val == "FAZLA": return "background-color: #60A5FA; color: white; font-weight: bold;"
        elif val == "TAMAM": return "background-color: #34D399; color: black; font-weight: bold;"
        return ""

    st.dataframe(pd.DataFrame(denge_verileri).style.map(stil_uygula, subset=["Sonuç"]), use_container_width=True, height=250)
    
    if optimal_mi:
        st.success(f"**💰 Günlük Toplam Rasyon Maliyeti:** {round(maliyet, 2)} TL")
        st.info("👇 İşte hayvan başına günlük verilmesi gereken optimum yem miktarları:")
        st.dataframe(duzenlenen_yemler[['yem_adi', 'Önerilen Miktar (kg)']], use_container_width=True)