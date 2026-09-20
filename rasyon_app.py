import streamlit as st
import pandas as pd
import pulp
from fpdf import FPDF

# PDF Dosyasındaki Türkçe karakter sorununu çözen araç
def tr2eng(text):
    chars = {'ı':'i', 'ş':'s', 'ğ':'g', 'ç':'c', 'ö':'o', 'ü':'u', 'İ':'I', 'Ş':'S', 'Ğ':'G', 'Ç':'C', 'Ö':'O', 'Ü':'U'}
    for k, v in chars.items():
        text = str(text).replace(k, v)
    return text

# PDF Raporunu çizen fonksiyon
def create_pdf(h_tipi, h_irk, h_kg, h_adg, maliyet, yem_df, r_ca, r_p, r_ndf, r_km):
    pdf = FPDF()
    pdf.add_page()
    
    # Başlık
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt=tr2eng("CUMHURİYET ÜNİVERSİTESİ - VETERİNER HEKİMLİK RASYON RAPORU"), ln=True, align='C')
    pdf.line(10, 20, 200, 20)
    pdf.ln(5)
    
    # Hayvan Bilgileri
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=tr2eng("Hayvan Bilgileri"), ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 8, txt=tr2eng(f"Tip: {h_tipi} | Irk: {h_irk} | Canli Agirlik: {h_kg} kg | Gunluk Artis: {h_adg} kg"), ln=True)
    pdf.ln(5)
    
    # Yem Tablosu
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=tr2eng("Onerilen Yemler ve Miktarlar (kg/gun)"), ln=True)
    pdf.set_font("Arial", '', 12)
    for index, row in yem_df.iterrows():
        kg = row['Önerilen Miktar (kg)']
        if kg > 0:
            pdf.cell(200, 8, txt=tr2eng(f"- {row['yem_adi']}: {round(kg, 2)} kg"), ln=True)
    pdf.ln(5)
    
    # Klinik Dengeler ve Maliyet
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=tr2eng("Klinik Degerler & Maliyet"), ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 8, txt=tr2eng(f"Ca/P Orani: {round(r_ca/r_p, 2)} (Klinik Sinir: 1.5 - 2.0)"), ln=True)
    pdf.cell(200, 8, txt=tr2eng(f"Rasyon NDF Orani: % {round((r_ndf/r_km)*100, 1)}"), ln=True)
    pdf.cell(200, 8, txt=tr2eng(f"Tahmini Gunluk Maliyet: {round(maliyet, 2)} TL"), ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

st.set_page_config(page_title="Besi Rasyon Programı", layout="wide")
st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>Besi Sığırları İçin En Düşük Maliyetli Rasyon Programı</h2>", unsafe_allow_html=True)
st.markdown("---")

col_yem, col_denge, col_hayvan = st.columns([1.5, 1.3, 1.2])

with col_hayvan:
    st.subheader("🐂 Hayvan & Çevre Verileri")
with st.expander("Hayvan Tanımı", expanded=True):
        hayvan_tipi = st.selectbox("Hayvanın Tipi", ["Besi Sığırı", "Buzağı", "Damızlık Boğa"])
        irk = st.selectbox("Irkı", [
            "Siyah Alaca (Holstein)", "Simental (Flekvi)", "Montofon (Esmer)", 
            "Yerli Kara", "Angus", "Şarole (Charolais)", "Limuzin", "Hereford", 
            "Belçika Mavisi", "Doğu Anadolu Kırmızısı (DAK)", "Boz Irk", 
            "Güney Anadolu Kırmızısı (GAK)", "Melez (Kırma)"
        ])
        yas = st.number_input("Yaşı (ay)", value=16, min_value=1)
        kondisyon = st.slider("Kondisyon Skoru", 1.0, 5.0, 5.0, 0.5)
        canli_agirlik = st.number_input("Canlı ağırlığı (kg)", value=300, step=10)
        hedef_agirlik = st.number_input("Hedef besi sonu ağırlığı (kg)", value=350, step=10)
        adg = st.number_input("İstenilen canlı ağırlık artışı (kg/gün)", value=1.600, step=0.1)
        hedef_yaglilik = st.selectbox("Hedef yağlılık düzeyi", ["Çok az yağlı, % 25 yağ", "Orta yağlı, % 28 yağ", "Yağlı, % 32 yağ"])
 with st.expander("Çevre ve Barınak Koşulları", expanded=False):
        sicaklik = st.number_input("Mevcut Sıcaklık (°C)", value=18.0)
        gecmis_sicaklik = st.number_input("Geçen Ayın Ort. Sıcaklığı (°C)", value=15.0)
        camur = st.selectbox("Zemindeki Çamur Miktarı", ["Yok", "Bileğe Kadar", "Dize Kadar"])
        deri_durumu = st.selectbox("Deri ve Kıl Durumu", ["Kuru", "Islak / Çamurlu"])
        mera = st.checkbox("Merada Otluyor mu?", value=False)

ihtiyac_km = round((canli_agirlik * 0.015) + (adg * 2.3) + 0.02, 1)
ihtiyac_hp = round((canli_agirlik * 1.5) + (adg * 240), 0)
ihtiyac_me = round((canli_agirlik * 0.04) + (adg * 6.1), 2)

# Çevre koşullarının enerjiye (ME) etkisi 
if camur == "Dize Kadar":
    ihtiyac_me = round(ihtiyac_me * 1.10, 2) # %10 enerji artışı
elif camur == "Bileğe Kadar":
    ihtiyac_me = round(ihtiyac_me * 1.05, 2) # %5 enerji artışı

if deri_durumu == "Islak / Çamurlu":
    ihtiyac_me = round(ihtiyac_me * 1.05, 2) # %5 ekstra enerji ihtiyacı
    
ihtiyac_ca = round((canli_agirlik * 0.08) + (adg * 10.6), 1)
ihtiyac_p = round((canli_agirlik * 0.04) + (adg * 6.25), 1)
ihtiyac_ndf_min = round(ihtiyac_km * 0.28, 1)

with col_yem:
    st.subheader("🌾 Verilecek Yemler")
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

rasyon_km = rasyon_hp = rasyon_me = rasyon_ca = rasyon_p = rasyon_ndf = maliyet = 0.0
optimal_mi = False

if btn_coz:
    prob = pulp.LpProblem("En_Ucuz_ve_Guvenli_Rasyon", pulp.LpMinimize)
    yem_vars = []
    for index, row in duzenlenen_yemler.iterrows():
        var = pulp.LpVariable(f"yem_{index}", lowBound=row['min_kg'], upBound=row['maks_kg'])
        yem_vars.append(var)
        
    prob += pulp.lpSum([yem_vars[i] * duzenlenen_yemler.loc[i, 'fiyat_tl'] for i in range(len(yem_vars))])
    
    prob += pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'kuru_madde_yuzde']/100) for i in range(len(yem_vars))]) >= ihtiyac_km * 0.98
    prob += pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'kuru_madde_yuzde']/100) for i in range(len(yem_vars))]) <= ihtiyac_km * 1.05
    prob += pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'ham_protein_yuzde']*10) for i in range(len(yem_vars))]) >= ihtiyac_hp
    prob += pulp.lpSum([yem_vars[i] * duzenlenen_yemler.loc[i, 'me_mcal_kg'] for i in range(len(yem_vars))]) >= ihtiyac_me
    
    total_ca = pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'kalsiyum_yuzde']*10) for i in range(len(yem_vars))])
    total_p = pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'fosfor_yuzde']*10) for i in range(len(yem_vars))])
    prob += total_ca >= 1.5 * total_p
    prob += total_ca <= 2.0 * total_p
    prob += total_ca >= ihtiyac_ca
    prob += total_p >= ihtiyac_p
    prob += pulp.lpSum([yem_vars[i] * (duzenlenen_yemler.loc[i, 'kuru_madde_yuzde']/100) * (duzenlenen_yemler.loc[i, 'ndf_yuzde']/100) for i in range(len(yem_vars))]) >= ihtiyac_ndf_min
    
    prob.solve()
    
    if pulp.LpStatus[prob.status] == "Optimal":
        optimal_mi = True
        st.toast("✅ Klinik Olarak Güvenli Rasyon Bulundu!")
        
        for i, var in enumerate(yem_vars):
            kg = var.varValue
            duzenlenen_yemler.at[i, 'Önerilen Miktar (kg)'] = round(kg, 2)
            km_katkisi = kg * (duzenlenen_yemler.loc[i, 'kuru_madde_yuzde'] / 100)
            rasyon_km += km_katkisi
            rasyon_hp += kg * (duzenlenen_yemler.loc[i, 'ham_protein_yuzde'] * 10)
            rasyon_me += kg * duzenlenen_yemler.loc[i, 'me_mcal_kg']
            rasyon_ca += kg * (duzenlenen_yemler.loc[i, 'kalsiyum_yuzde'] * 10)
            rasyon_p += kg * (duzenlenen_yemler.loc[i, 'fosfor_yuzde'] * 10)
            rasyon_ndf += km_katkisi * (duzenlenen_yemler.loc[i, 'ndf_yuzde'] / 100)
            maliyet += kg * duzenlenen_yemler.loc[i, 'fiyat_tl']
    else:
        st.error("⚠️ HATA: Seçtiğiniz yemlerle metabolik dengeyi bozmayacak bir rasyon oluşturulamıyor.")

with col_denge:
    st.subheader("📊 Klinik Denge Panosu")
    
    def durum_hesapla(rasyon, ihtiyac):
        if rasyon == 0: return "-"
        if rasyon < ihtiyac * 0.98: return "EKSİK"
        if rasyon > ihtiyac * 1.05: return "FAZLA"
        return "TAMAM"
        
    denge_verileri = {
        "Klinik Parametre": ["Kuru Madde (kg)", "Ham Protein (g)", "ME (Mcal)", "Kalsiyum (g)", "Fosfor (g)", "NDF (kg)"],
        "İhtiyaç": [ihtiyac_km, ihtiyac_hp, ihtiyac_me, ihtiyac_ca, ihtiyac_p, ihtiyac_ndf_min],
        "Rasyon": [round(rasyon_km,1), round(rasyon_hp,0), round(rasyon_me,1), round(rasyon_ca,1), round(rasyon_p,1), round(rasyon_ndf,1)],
        "Sonuç": [
            durum_hesapla(rasyon_km, ihtiyac_km), durum_hesapla(rasyon_hp, ihtiyac_hp),
            durum_hesapla(rasyon_me, ihtiyac_me), durum_hesapla(rasyon_ca, ihtiyac_ca),
            durum_hesapla(rasyon_p, ihtiyac_p), durum_hesapla(rasyon_ndf, ihtiyac_ndf_min)
        ]
    }
    
    def stil_uygula(val):
        if val == "EKSİK": return "background-color: #F87171; color: white; font-weight: bold;"
        elif val == "FAZLA": return "background-color: #60A5FA; color: white; font-weight: bold;"
        elif val == "TAMAM": return "background-color: #34D399; color: black; font-weight: bold;"
        return ""

    st.dataframe(pd.DataFrame(denge_verileri).style.map(stil_uygula, subset=["Sonuç"]), use_container_width=True, height=250)
    
    if optimal_mi:
        st.markdown(f"**🔬 Klinik Oranlar:** Ca/P Oranı: `{round(rasyon_ca/rasyon_p, 2)}` | Toplam KM'de NDF: `% {round((rasyon_ndf/rasyon_km)*100, 1)}`")
        st.success(f"**💰 Günlük Rasyon Maliyeti:** {round(maliyet, 2)} TL")
        st.dataframe(duzenlenen_yemler[['yem_adi', 'Önerilen Miktar (kg)']], use_container_width=True)
        
        # PDF OLUŞTURMA VE İNDİRME BUTONU
        pdf_bytes = create_pdf(hayvan_tipi, irk, canli_agirlik, adg, maliyet, duzenlenen_yemler, rasyon_ca, rasyon_p, rasyon_ndf, rasyon_km)
        st.download_button(
            label="📥 RAPORU PDF OLARAK İNDİR",
            data=pdf_bytes,
            file_name="Veteriner_Hekimlik_Rasyon_Raporu.pdf",
            mime="application/pdf",
            type="primary"
        )