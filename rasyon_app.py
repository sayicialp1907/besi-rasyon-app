import streamlit as st
import pandas as pd
import pulp
from fpdf import FPDF

# --- 1. AYARLAR VE AKADEMİK / PETROL MAVİSİ TASARIM (CSS) ---
st.set_page_config(page_title="Profesyonel Rasyon Optimizasyonu", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 1. Tüm sayfanın arka planını Petrol Mavisi yap ve yazıları beyaz yap */
    .stApp { background-color: #0B3C49 !important; }
    
    /* 2. Tüm yazıları görünür kıl (Beyaz/Krem) ve Akademik Font kullan */
    html, body, p, h1, h2, h3, h4, h5, h6, span, label, div {
        color: #F8F9FA !important;
        font-family: 'Times New Roman', Times, serif !important;
    }
    
    /* 3. Kurumsal Üst Menü Çubuğu (Kalın ve Yatay) */
    .kurumsal-menu {
        background-color: #06222A;
        padding: 30px;
        text-align: center;
        border-bottom: 5px solid #D4AF37; /* Kurumsal Altın Sarısı Çizgi */
        margin-top: -80px;
        padding-top: 80px;
        margin-bottom: 40px;
    }
    .kurumsal-menu h1 {
        font-size: 32px !important;
        letter-spacing: 2px;
        margin: 0;
        text-transform: uppercase;
        color: #FFFFFF !important;
    }
    .kurumsal-menu p {
        font-size: 16px !important;
        color: #A9BCC1 !important;
        margin-top: 10px;
    }
    
    /* 4. Akademik Düz Çizgiler (Divider) */
    hr { border-top: 2px solid #D4AF37 !important; margin: 30px 0 !important; }
    
    /* 5. Girdi Kutuları (Input/Select) Keskin Hatlı ve Koyu Temaya Uygun */
    input, select, .stSelectbox > div > div {
        background-color: #124B5A !important;
        color: white !important;
        border: 1px solid #4A7A89 !important;
        border-radius: 0px !important; /* Akademik Keskinlik */
    }
    
    /* 6. Buton Tasarımı (Altın Sarısı / Kurumsal) */
    div.stButton > button:first-child { 
        background-color: #D4AF37 !important;
        color: #000000 !important;
        border: none !important;
        border-radius: 0px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        height: 60px;
        width: 100%;
        text-transform: uppercase;
    }
    div.stButton > button:first-child:hover { background-color: #B3912A !important; }
    
    /* 7. Tablo (DataFrame) Arka Planları */
    [data-testid="stDataFrame"] { background-color: #124B5A !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. KURUMSAL MENÜ ÇUBUĞU (HTML) ---
st.markdown("""
    <div class="kurumsal-menu">
        <img src="https://upload.wikimedia.org/wikipedia/commons/e/e6/Vet_symbol.svg" style="width: 80px; margin-bottom: 10px; filter: brightness(0) invert(1);">
        <h1>VETERİNER KLİNİK RASYON SİSTEMİ</h1>
        <p>Büyükbaş Hayvan Besleme ve Optimizasyon Modülü v2.0</p>
    </div>
""", unsafe_allow_html=True)

# --- 3. OTOMATİK DEV YEM VERİTABANI ---
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

# --- 4. KLİNİK VE PDF FONKSİYONLARI ---
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
    pdf.set_fill_color(11, 60, 73); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 15, txt=tr2eng("KLINIK RASYON VE OPTIMIZASYON RAPORU"), ln=True, align='C', fill=True); pdf.ln(5)
    
    pdf.set_text_color(0, 0, 0); pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=tr2eng("  BÖLÜM 1: Hayvan Spesifikasyonlari ve Performans"), ln=True, fill=True); pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, txt=tr2eng(f"  Tip/Irk: {h_tipi} - {h_irk}  |  Mevcut: {h_kg} kg -> Hedef: {h_hedef} kg"), ln=True)
    pdf.cell(0, 8, txt=tr2eng(f"  Besi Suresi: {h_sure} Gun  |  Hesaplanan Gunluk Artis (ADG): {h_adg} kg/gun"), ln=True); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.set_fill_color(212, 175, 55); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, txt=tr2eng("  BÖLÜM 2: Tavsiye Edilen Yem Bilesimi (kg/gun)"), ln=True, fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 11); pdf.set_fill_color(250, 250, 250)
    for index, row in yem_df.iterrows():
        kg = row.get('Önerilen Miktar (kg)', 0)
        if kg > 0:
            pdf.cell(150, 8, txt=tr2eng(f"   {row['yem_adi']}"), border='B', fill=True)
            pdf.cell(40, 8, txt=f"{round(kg, 2)} kg", border='B', ln=True, align='R', fill=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.set_fill_color(240, 240, 240); pdf.cell(0, 10, txt=tr2eng("  BÖLÜM 3: Optimizasyon Bulgulari ve Risk Analizi"), ln=True, fill=True)
    pdf.set_font("Arial", '', 11); pdf.cell(100, 8, txt=tr2eng(f"   Ekonomik Maliyet: {round(maliyet, 2)} TL/gun | Ca/P: {round(r_ca/r_p,2) if r_p>0 else 0} | NDF: %{round((r_ndf/r_km)*100,1) if r_km>0 else 0}"), ln=True)
    pdf.set_text_color(220, 38, 38)
    for risk in riskler: pdf.multi_cell(0, 8, txt=tr2eng(f"- {risk}"), border='B')
    return pdf.output(dest='S').encode('latin-1')

# --- 5. AKADEMİK ARAYÜZ TASARIMI ---

st.markdown("### BÖLÜM I: HAYVAN MATERYALİ VE ÇEVRESEL FAKTÖRLER")
col_hayvan, col_cevre = st.columns(2)

with col_hayvan:
    hayvan_tipi = st.selectbox("Hayvanın Tipi", ["Besi Sığırı", "Buzağı", "Damızlık Boğa"])
    irk = st.selectbox("Irk Spesifikasyonu", ["Siyah Alaca (Holstein)", "Simental", "Montofon", "Yerli Kara", "Angus", "Şarole", "Limuzin", "Melez"])
    col_y, col_k = st.columns(2)
    yas = col_y.number_input("Yaşı (Ay)", value=16, min_value=1)
    kondisyon = col_k.number_input("Kondisyon Skoru", value=5.0, min_value=1.0, max_value=5.0, step=0.5)

with col_cevre:
    canli_agirlik = st.number_input("Mevcut Vücut Ağırlığı (kg)", value=300, step=10)
    col_h1, col_h2 = st.columns(2)
    hedef_agirlik = col_h1.number_input("Hedef Ağırlık (kg)", value=350, step=10)
    besi_suresi = col_h2.number_input("Besi Süresi (Gün)", value=30, step=1)
    
    adg = round((hedef_agirlik - canli_agirlik) / besi_suresi, 3) if (besi_suresi > 0 and hedef_agirlik > canli_agirlik) else 0.0
    st.info(f"Hesaplanan Ortalama Günlük Ağırlık Artışı (ADG): **{adg} kg/gün**")
    
    col_c1, col_c2 = st.columns(2)
    sicaklik = col_c1.number_input("Mevcut Sıcaklık (°C)", value=18.0)
    camur = col_c2.selectbox("Zemin Çamur Faktörü", ["Yok", "Bileğe Kadar", "Dize Kadar"])
    deri_durumu = st.selectbox("Deri ve Kıl Örtüsü Durumu", ["Kuru", "Islak / Çamurlu"])

st.markdown("---")

st.markdown("### BÖLÜM II: RASYON BİLEŞENLERİ VE MATEMATİKSEL KISITLAR")
tum_yemler = df_yem_ham['yem_adi'].tolist()
secilen_isimler = st.multiselect("Optimizasyona Dahil Edilecek Yem Materyalleri:", options=tum_yemler, default=["Misir Silaji", "Yonca Kuru Otu", "Arpa Ezmesi", "Soya Kuspesi (%44)", "Mermer Tozu (Ca Kaynagi)"])

if not secilen_isimler:
    st.warning("Analiz için en az bir yem materyali seçilmelidir.")
    st.stop()

df_secilen = df_yem_ham[df_yem_ham['yem_adi'].isin(secilen_isimler)].copy().reset_index(drop=True)

duzenlenen_gorunum = st.data_editor(
    df_secilen,
    column_config={
        "yem_grubu": None, "kuru_madde_yuzde": None, "ham_protein_yuzde": None, 
        "me_mcal_kg": None, "kalsiyum_yuzde": None, "fosfor_yuzde": None, "ndf_yuzde": None, "endf_yuzde": None,
        "yem_adi": st.column_config.TextColumn("Yem Adı (Materyal)", disabled=True),
        "fiyat_tl": st.column_config.NumberColumn("Birim Fiyat (TL)"),
        "min_kg": st.column_config.NumberColumn("Minimum Kısıt (kg)"),
        "maks_kg": st.column_config.NumberColumn("Maksimum Kısıt (kg)")
    }, hide_index=True, use_container_width=True
)
df_secilen['fiyat_tl'] = duzenlenen_gorunum['fiyat_tl']
df_secilen['min_kg'] = duzenlenen_gorunum['min_kg']
df_secilen['maks_kg'] = duzenlenen_gorunum['maks_kg']

st.markdown("---")

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

# --- ÇÖZÜCÜ ---
btn_coz = st.button("LİNEER PROGRAMLAMA İLE OPTİMİZASYONU BAŞLAT")

if btn_coz:
    st.markdown("### BÖLÜM III: BULGULAR VE OPTİMİZASYON SONUÇLARI")
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
            
        col_tablo, col_risk = st.columns([1.2, 1])
        with col_tablo:
            st.markdown(f"<h4 style='color:#D4AF37;'>Hesaplanan Günlük Maliyet: {round(maliyet,2)} TL</h4>", unsafe_allow_html=True)
            st.markdown("**Besin Madde Karşılama Tablosu**")
            denge_df = pd.DataFrame({
                "Parametre": ["Kuru Madde (kg)", "Ham Protein (g)", "ME (Mcal)", "Kalsiyum (g)", "Fosfor (g)", "NDF (kg)"],
                "İhtiyaç Edilen": [ihtiyac_km, ihtiyac_hp, ihtiyac_me, ihtiyac_ca, ihtiyac_p, ihtiyac_ndf_min],
                "Rasyonda Bulunan": [round(rasyon_km,1), round(rasyon_hp,0), round(rasyon_me,1), round(rasyon_ca,1), round(rasyon_p,1), round(rasyon_ndf,1)]
            })
            st.table(denge_df)
            
            st.markdown("**Optimize Edilmiş Yem Miktarları**")
            st.dataframe(df_secilen[df_secilen['Önerilen Miktar (kg)'] > 0][['yem_adi', 'Önerilen Miktar (kg)']], use_container_width=True, hide_index=True)

        with col_risk:
            st.markdown(f"<h4 style='color:#D4AF37;'>Klinik Bulgular</h4>", unsafe_allow_html=True)
            saptanan_riskler = risk_analizi(rasyon_km, rasyon_ndf, rasyon_ca, rasyon_p, rasyon_me, ihtiyac_me, rasyon_hp, ihtiyac_hp)
            for r in saptanan_riskler:
                if "GÜVENLİ" in r: st.success(r)
                else: st.error(r)
            
            st.info(f"Ca/P Oranı: {round(rasyon_ca/rasyon_p,2) if rasyon_p>0 else 0} | Kuru Maddede NDF: %{round((rasyon_ndf/rasyon_km)*100,1) if rasyon_km>0 else 0}")
            
            pdf_bytes = create_pdf(hayvan_tipi, irk, canli_agirlik, hedef_agirlik, besi_suresi, adg, maliyet, df_secilen, rasyon_ca, rasyon_p, rasyon_ndf, rasyon_km, saptanan_riskler)
            st.download_button("PDF OLARAK İNDİR", data=pdf_bytes, file_name="Rasyon_Raporu.pdf", mime="application/pdf", type="primary", use_container_width=True)
    else:
        st.error("Matematiksel kısıtlar sağlanamadı. Yem sınırlarını (Maks) artırınız veya rasyona farklı yem materyalleri ekleyiniz.")