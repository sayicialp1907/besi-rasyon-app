import streamlit as st
import pandas as pd
import pulp
from fpdf import FPDF
import datetime

# --- 1. AYARLAR VE KOMPAKT DASHBOARD CSS ---
st.set_page_config(page_title="Veteriner Rasyon Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Ana arka planı medikal gri yaparak boş beyazlık hissini yok ediyoruz */
    .stApp { background-color: #F1F5F9; }
    
    /* Ekranın yanlarındaki ve üstündeki ölü boşlukları daralt */
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 98% !important; }
    
    /* Başlık ve Panel Renkleri */
    h1, h2, h3 { color: #1E293B !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Kutuları belirginleştir, beyaz boşlukları "Panel" hissine çevir */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #FFFFFF;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        padding: 15px;
        border-top: 4px solid #0F172A;
    }
    
    /* Dev Çöz Butonu (Medikal Lacivert) */
    div.stButton > button:first-child { 
        height: 60px; font-size: 22px !important; font-weight: bold; 
        background-color: #0F172A !important; color: white !important; border-radius: 8px; width: 100%;
    }
    div.stButton > button:first-child:hover { background-color: #334155 !important; }
    
    /* Metrik (KPI) Kartları */
    div[data-testid="stMetric"] {
        background-color: #E2E8F0; padding: 10px; border-radius: 8px; text-align: center; border-left: 5px solid #2563EB;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. OTOMATİK YEM VERİTABANI ---
EKSIKSIZ_YEM_LISTESI = """yem_adi,yem_grubu,kuru_madde_yuzde,ham_protein_yuzde,me_mcal_kg,kalsiyum_yuzde,fosfor_yuzde,ndf_yuzde,endf_yuzde,fiyat_tl
Misir Silaji,Sulu Kaba Yem,30.0,8.0,2.4,0.25,0.20,45.0,35.0,2.0
Yonca Kuru Otu,Kuru Kaba Yem,88.0,16.0,2.1,1.50,0.25,40.0,38.0,5.5
Fig Kuru Otu,Kuru Kaba Yem,88.0,14.0,2.0,1.20,0.30,45.0,40.0,4.5
Cayir Kuru Otu,Kuru Kaba Yem,88.0,9.0,1.8,0.60,0.25,55.0,50.0,3.5
Bugday Samani,Kuru Kaba Yem,90.0,3.5,1.3,0.15,0.05,78.0,72.0,1.5
Arpa Samani,Kuru Kaba Yem,90.0,4.0,1.4,0.30,0.10,75.0,70.0,1.5
Yulaf Samani,Kuru Kaba Yem,90.0,4.5,1.4,0.35,0.15,70.0,65.0,1.6
Pancar Posasi (Yas),Sulu Kaba Yem,22.0,9.0,2.6,0.90,0.10,45.0,30.0,1.0
Pancar Posasi (Kuru),Enerji Kaynagi,90.0,9.0,2.7,0.90,0.10,45.0,30.0,6.0
Arpa Ezmesi,Enerji Kaynagi,89.0,11.5,3.1,0.05,0.35,18.0,8.0,7.5
Misir Ezmesi,Enerji Kaynagi,88.0,9.0,3.2,0.03,0.30,10.0,5.0,8.0
Bugday Ezmesi,Enerji Kaynagi,88.0,12.0,3.2,0.05,0.35,12.0,5.0,8.0
Bugday Kepegi,Enerji Kaynagi,88.0,15.5,2.5,0.10,1.10,40.0,10.0,6.0
Soya Kuspesi (%44),Protein Kaynagi,89.0,44.0,3.0,0.30,0.65,15.0,3.0,16.0
Aycicek Kuspesi (%28),Protein Kaynagi,90.0,28.0,2.0,0.40,0.90,40.0,10.0,7.0
Pamuk Tohumu Kuspesi,Protein Kaynagi,90.0,28.0,2.5,0.20,1.00,35.0,15.0,8.0
Kanola Kuspesi,Protein Kaynagi,90.0,34.0,2.4,0.65,1.00,30.0,10.0,10.0
Melas,Enerji Kaynagi,75.0,4.0,2.4,0.80,0.05,0.0,0.0,5.0
Besi Yemi (%14 HP),Ticari Yem,88.0,14.0,2.6,1.00,0.50,25.0,10.0,8.5
Besi Yemi (%16 HP),Ticari Yem,88.0,16.0,2.7,1.00,0.50,25.0,10.0,9.0
Sut Yemi (%19 HP),Ticari Yem,88.0,19.0,2.7,1.00,0.50,25.0,10.0,9.5
Mermer Tozu (Ca Kaynagi),Mineral,99.0,0.0,0.0,38.0,0.0,0.0,0.0,1.5
DCP (Kalsiyum+Fosfor),Mineral,99.0,0.0,0.0,24.0,18.0,0.0,0.0,15.0
Tuz,Mineral,99.0,0.0,0.0,0.0,0.0,0.0,0.0,2.0"""
with open("yem_veritabani.csv", "w", encoding="utf-8") as f: f.write(EKSIKSIZ_YEM_LISTESI)
df_yem_ham = pd.read_csv("yem_veritabani.csv")
df_yem_ham['min_kg'] = 0.0; df_yem_ham['maks_kg'] = 15.0

# --- 3. FONKSİYONLAR ---
def tr2eng(text):
    for k, v in {'ı':'i', 'ş':'s', 'ğ':'g', 'ç':'c', 'ö':'o', 'ü':'u', 'İ':'I', 'Ş':'S', 'Ğ':'G', 'Ç':'C', 'Ö':'O', 'Ü':'U'}.items(): 
        text = str(text).replace(k, v)
    return text

def risk_analizi(r_km, r_ndf, r_ca, r_p, r_me, i_me, r_hp, i_hp):
    riskler = []
    ndf_orani = (r_ndf / r_km) * 100 if r_km > 0 else 0
    ca_p_orani = r_ca / r_p if r_p > 0 else 0
    if ndf_orani < 28: riskler.append("ASİDOZ RİSKİ: Rasyondaki kaba yem (NDF) yetersiz. Rumen pH'ı düşebilir.")
    if 0 < ca_p_orani < 1.2: riskler.append("ÜROLİTİYAZİS RİSKİ: Ca/P oranı çok düşük. İdrar taşı oluşabilir.")
    elif ca_p_orani > 3.0: riskler.append("MİNERAL BLOKAJI RİSKİ: Aşırı Kalsiyum emilimi bozuyor.")
    if r_hp > (i_hp * 1.15): riskler.append("HEPATİK STRES: Fazla protein verildi. Karaciğer yorulabilir.")
    if r_me > (i_me * 1.15): riskler.append("KARACİĞER YAĞLANMASI: Aşırı enerji yüklemesi mevcut.")
    if not riskler: riskler.append("RASYON GÜVENLİ: Klinik parametreler fizyolojik sınırlar içerisindedir.")
    return riskler

def create_pdf(h_tipi, h_irk, h_kg, h_hedef, h_sure, h_adg, maliyet, yem_df, r_ca, r_p, r_ndf, r_km, riskler):
    pdf = FPDF(); pdf.add_page()
    pdf.set_fill_color(15, 23, 42); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 15, txt=tr2eng("KLINIK RASYON RAPORU - VETERINER GÖSTERGE PANELI"), ln=True, align='C', fill=True); pdf.ln(5)
    
    pdf.set_text_color(0, 0, 0); pdf.set_fill_color(226, 232, 240); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=tr2eng("  Hayvan Bilgileri & Performans Hedefi"), ln=True, fill=True); pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, txt=tr2eng(f"  Tip/Irk: {h_tipi} - {h_irk}  |  Mevcut: {h_kg} kg -> Hedef: {h_hedef} kg"), ln=True)
    pdf.cell(0, 8, txt=tr2eng(f"  Besi Suresi: {h_sure} Gun  |  Hesaplanan Gunluk Artis: {h_adg} kg/gun"), ln=True); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.set_fill_color(15, 23, 42); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, txt=tr2eng("  Tavsiye Edilen Yemler (kg/gun)"), ln=True, fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 11); pdf.set_fill_color(248, 250, 252)
    for index, row in yem_df.iterrows():
        kg = row.get('Önerilen Miktar (kg)', 0)
        if kg > 0:
            pdf.cell(150, 8, txt=tr2eng(f"   {row['yem_adi']}"), border='B', fill=True)
            pdf.cell(40, 8, txt=f"{round(kg, 2)} kg", border='B', ln=True, align='R', fill=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.set_fill_color(226, 232, 240); pdf.cell(0, 10, txt=tr2eng("  Veteriner Risk Analizi & KPI Verileri"), ln=True, fill=True)
    pdf.set_font("Arial", '', 11); pdf.cell(100, 8, txt=tr2eng(f"   Maliyet: {round(maliyet, 2)} TL/gun | Ca/P: {round(r_ca/r_p,2) if r_p>0 else 0} | NDF: %{round((r_ndf/r_km)*100,1) if r_km>0 else 0}"), ln=True)
    pdf.set_text_color(220, 38, 38)
    for risk in riskler: pdf.multi_cell(0, 8, txt=tr2eng(f"- {risk}"), border='B')
    return pdf.output(dest='S').encode('latin-1')

# --- 4. ANA BAŞLIK BANNER ---
st.markdown("<div style='background-color:#0F172A; padding:15px; border-radius:8px; margin-bottom:15px;'><h2 style='color:white !important; margin:0; text-align:center;'>🐄 Veteriner Klinik Gösterge Paneli (Dashboard)</h2></div>", unsafe_allow_html=True)

# --- 5. YATAY VE KOMPAKT VERİ GİRİŞ PANELİ (BOL BOŞLUK YOK) ---
col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    with st.container(border=True):
        st.markdown("#### 📌 Hayvan Kimliği")
        hayvan_tipi = st.selectbox("Hayvanın Tipi", ["Besi Sığırı", "Buzağı", "Damızlık Boğa"])
        irk = st.selectbox("Irkı", ["Siyah Alaca (Holstein)", "Simental", "Montofon", "Yerli Kara", "Angus", "Şarole", "Limuzin", "Melez"])
        col_y, col_k = st.columns(2)
        yas = col_y.number_input("Yaşı (ay)", value=16, min_value=1)
        kondisyon = col_k.number_input("Kondisyon", value=5.0, min_value=1.0, max_value=5.0, step=0.5)

with col_info2:
    with st.container(border=True):
        st.markdown("#### 🎯 Besi Hedefleri (ADG)")
        canli_agirlik = st.number_input("Mevcut Canlı Ağırlık (kg)", value=300, step=10)
        hedef_agirlik = st.number_input("Hedef Besi Sonu Ağırlığı (kg)", value=350, step=10)
        besi_suresi = st.number_input("Planlanan Besi Süresi (Gün)", value=30, step=1)
        
        adg = round((hedef_agirlik - canli_agirlik) / besi_suresi, 3) if (besi_suresi > 0 and hedef_agirlik > canli_agirlik) else 0.0
        st.info(f"**Hesaplanan Günlük Artış:** {adg} kg/gün")

with col_info3:
    with st.container(border=True):
        st.markdown("#### 🌤️ Çevre ve Barınak (Açık)")
        col_s1, col_s2 = st.columns(2)
        sicaklik = col_s1.number_input("Mevcut Sıcaklık (°C)", value=18.0)
        gecmis_sicaklik = col_s2.number_input("Geçen Ay Ort. (°C)", value=15.0)
        camur = st.selectbox("Zemindeki Çamur", ["Yok", "Bileğe Kadar", "Dize Kadar"])
        deri_durumu = st.selectbox("Deri Durumu", ["Kuru", "Islak / Çamurlu"])

# --- HESAPLAMALAR ---
ihtiyac_km = round((canli_agirlik * 0.015) + (adg * 2.3) + 0.02, 1)
ihtiyac_hp = round((canli_agirlik * 1.5) + (adg * 240), 0)
ihtiyac_me = round((canli_agirlik * 0.04) + (adg * 6.1), 2)
if camur == "Dize Kadar": ihtiyac_me *= 1.10 
elif camur == "Bileğe Kadar": ihtiyac_me *= 1.05
if deri_durumu == "Islak / Çamurlu": ihtiyac_me *= 1.05
if sicaklik < 5.0: ihtiyac_me *= 1.05
ihtiyac_ca = round((canli_agirlik * 0.08) + (adg * 10.6), 1)
ihtiyac_p = round((canli_agirlik * 0.04) + (adg * 6.25), 1)
ihtiyac_ndf_min = round(ihtiyac_km * 0.28, 1)

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# --- 6. YEM SEÇİMİ VE DASHBOARD EKRANI ---
col_yem, col_dashboard = st.columns([1.2, 1.8])

with col_yem:
    with st.container(border=True):
        st.markdown("#### 🌾 Yem Deposu & Optimizasyon")
        tum_yemler = df_yem_ham['yem_adi'].tolist()
        secilen_isimler = st.multiselect("Rasyona eklenecek yemleri seçin:", options=tum_yemler, default=["Misir Silaji", "Yonca Kuru Otu", "Arpa Ezmesi", "Soya Kuspesi (%44)", "Mermer Tozu (Ca Kaynagi)"])
        
        if not secilen_isimler:
            st.warning("En az bir yem seçiniz!")
            st.stop()
            
        df_secilen = df_yem_ham[df_yem_ham['yem_adi'].isin(secilen_isimler)].copy().reset_index(drop=True)
        
        duzenlenen_gorunum = st.data_editor(
            df_secilen,
            column_config={
                "yem_grubu": None, "kuru_madde_yuzde": None, "ham_protein_yuzde": None, 
                "me_mcal_kg": None, "kalsiyum_yuzde": None, "fosfor_yuzde": None, "ndf_yuzde": None, "endf_yuzde": None,
                "yem_adi": st.column_config.TextColumn("Yem Adı", disabled=True),
                "fiyat_tl": st.column_config.NumberColumn("Fiyat(TL)"),
                "min_kg": st.column_config.NumberColumn("Min"),
                "maks_kg": st.column_config.NumberColumn("Maks")
            }, hide_index=True, use_container_width=True, height=250
        )
        df_secilen['fiyat_tl'] = duzenlenen_gorunum['fiyat_tl']
        df_secilen['min_kg'] = duzenlenen_gorunum['min_kg']
        df_secilen['maks_kg'] = duzenlenen_gorunum['maks_kg']
        
        st.markdown("<br>", unsafe_allow_html=True)
        btn_coz = st.button("🚀 RASYONU ÇÖZ VE ANALİZ ET")

with col_dashboard:
    if btn_coz:
        prob = pulp.LpProblem("Rasyon", pulp.LpMinimize)
        yem_vars = [pulp.LpVariable(f"yem_{i}", lowBound=row['min_kg'], upBound=row['maks_kg']) for i, row in df_secilen.iterrows()]
        
        prob += pulp.lpSum([yem_vars[i] * df_secilen.loc[i, 'fiyat_tl'] for i in range(len(yem_vars))])
        prob += pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'kuru_madde_yuzde']/100) for i in range(len(yem_vars))]) >= ihtiyac_km * 0.98
        prob += pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'kuru_madde_yuzde']/100) for i in range(len(yem_vars))]) <= ihtiyac_km * 1.05
        prob += pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'ham_protein_yuzde']*10) for i in range(len(yem_vars))]) >= ihtiyac_hp
        prob += pulp.lpSum([yem_vars[i] * df_secilen.loc[i, 'me_mcal_kg'] for i in range(len(yem_vars))]) >= ihtiyac_me
        prob += pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'kalsiyum_yuzde']*10) for i in range(len(yem_vars))]) >= ihtiyac_ca
        prob += pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'fosfor_yuzde']*10) for i in range(len(yem_vars))]) >= ihtiyac_p
        prob.solve()
        
        if pulp.LpStatus[prob.status] == "Optimal":
            rasyon_km=rasyon_hp=rasyon_me=rasyon_ca=rasyon_p=rasyon_ndf=maliyet=0.0
            for i, var in enumerate(yem_vars):
                kg = var.varValue
                df_secilen.at[i, 'Önerilen Miktar (kg)'] = round(kg, 2)
                km_k = kg * (df_secilen.loc[i, 'kuru_madde_yuzde'] / 100)
                rasyon_km += km_k
                rasyon_hp += kg * (df_secilen.loc[i, 'ham_protein_yuzde'] * 10)
                rasyon_me += kg * df_secilen.loc[i, 'me_mcal_kg']
                rasyon_ca += kg * (df_secilen.loc[i, 'kalsiyum_yuzde'] * 10)
                rasyon_p += kg * (df_secilen.loc[i, 'fosfor_yuzde'] * 10)
                rasyon_ndf += km_k * (df_secilen.loc[i, 'ndf_yuzde'] / 100)
                maliyet += kg * df_secilen.loc[i, 'fiyat_tl']
            
            # --- HASTANE TİPİ KPI METRİKLERİ ---
            st.markdown("#### 🩺 Sistem Monitörü")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric(label="Günlük Maliyet", value=f"{round(maliyet,2)} TL")
            kpi2.metric(label="Hesaplanan ADG", value=f"{adg} kg")
            kpi3.metric(label="Ca / P Oranı", value=f"{round(rasyon_ca/rasyon_p,2) if rasyon_p>0 else 0}")
            kpi4.metric(label="K.Madde NDF", value=f"%{round((rasyon_ndf/rasyon_km)*100,1) if rasyon_km>0 else 0}")
            
            col_tablo, col_risk = st.columns([1.2, 1])
            with col_tablo:
                st.markdown("**Besin Denge Tablosu**")
                denge_df = pd.DataFrame({
                    "Madde": ["KM(kg)", "HP(g)", "ME(Mcal)", "Ca(g)", "P(g)", "NDF(kg)"],
                    "İhtiyaç": [ihtiyac_km, ihtiyac_hp, ihtiyac_me, ihtiyac_ca, ihtiyac_p, ihtiyac_ndf_min],
                    "Rasyon": [round(rasyon_km,1), round(rasyon_hp,0), round(rasyon_me,1), round(rasyon_ca,1), round(rasyon_p,1), round(rasyon_ndf,1)]
                })
                st.dataframe(denge_df, use_container_width=True, hide_index=True)
                st.markdown("**Seçilen Yem Miktarları (kg)**")
                st.dataframe(df_secilen[df_secilen['Önerilen Miktar (kg)'] > 0][['yem_adi', 'Önerilen Miktar (kg)']], use_container_width=True, hide_index=True)

            with col_risk:
                st.markdown("**Klinik Analiz**")
                saptanan_riskler = risk_analizi(rasyon_km, rasyon_ndf, rasyon_ca, rasyon_p, rasyon_me, ihtiyac_me, rasyon_hp, ihtiyac_hp)
                for r in saptanan_riskler:
                    if "GÜVENLİ" in r: st.success(r)
                    else: st.error(r)
                
                pdf_bytes = create_pdf(hayvan_tipi, irk, canli_agirlik, hedef_agirlik, besi_suresi, adg, maliyet, df_secilen, rasyon_ca, rasyon_p, rasyon_ndf, rasyon_km, saptanan_riskler)
                st.download_button("📥 KLİNİK RAPORU İNDİR", data=pdf_bytes, file_name="Rapor.pdf", mime="application/pdf", type="primary", use_container_width=True)
        else:
            st.error("⚠️ Sistem bu limitlerle (Maks değerleri düşük olabilir) matematiksel bir model kuramadı. Yem sınırlarını esnetin.")
    else:
        st.info("Sol taraftaki 'RASYONU ÇÖZ' butonuna bastığınızda, Klinik Monitör verileri burada belirecektir.")