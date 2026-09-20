import streamlit as st
import pandas as pd
import pulp
from fpdf import FPDF

# --- AYARLAR VE TASARIM ---
st.set_page_config(page_title="Veteriner Rasyon Modülü", layout="wide", initial_sidebar_state="collapsed")

# Butonları ve tabloları güzelleştiren özel CSS
st.markdown("""
    <style>
    div.stButton > button:first-child { height: 60px; font-size: 20px; font-weight: bold; border-radius: 10px; }
    .baslik { color: #1E3A8A; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    </style>
""", unsafe_allow_html=True)

# Türkçe karakter düzeltici
def tr2eng(text):
    chars = {'ı':'i', 'ş':'s', 'ğ':'g', 'ç':'c', 'ö':'o', 'ü':'u', 'İ':'I', 'Ş':'S', 'Ğ':'G', 'Ç':'C', 'Ö':'O', 'Ü':'U'}
    for k, v in chars.items(): text = str(text).replace(k, v)
    return text

# --- KLİNİK RİSK ANALİZİ ---
def risk_analizi(r_km, r_ndf, r_ca, r_p, r_me, i_me, r_hp, i_hp):
    riskler = []
    ndf_orani = (r_ndf / r_km) * 100 if r_km > 0 else 0
    ca_p_orani = r_ca / r_p if r_p > 0 else 0

    if ndf_orani < 28:
        riskler.append("ASİDOZ & LAMİNİTİS RİSKİ: Rasyondaki kaba yem (NDF) yetersiz. Rumen pH'ı düşerek asidoz ve tırnak hastalıklarına yol açabilir.")
        riskler.append("ABOMASUM DEPLASMANI RİSKİ: Fiziksel yapı eksikliği mide dönmesi ihtimalini artırır.")
    
    if 0 < ca_p_orani < 1.2:
        riskler.append("ÜROLİTİYAZİS RİSKİ: Kalsiyum/Fosfor oranı çok düşük. Erkek besilerde idrar taşı oluşabilir.")
    elif ca_p_orani > 3.0:
        riskler.append("MİNERAL BLOKAJI RİSKİ: Aşırı Kalsiyum, Fosfor emilimini bozmaktadır.")
        
    if r_hp > (i_hp * 1.15):
        riskler.append("HEPATİK STRES: Fazla protein verildi. Karaciğer yorulabilir.")
        
    if r_me > (i_me * 1.15):
        riskler.append("KARACİĞER YAĞLANMASI: Aşırı enerji yüklemesi metabolik çökmeye yol açabilir.")
        
    if not riskler:
        riskler.append("RASYON GÜVENLİ: Klinik parametreler fizyolojik sınırlar içerisindedir.")
        
    return riskler

# --- PDF MOTORU ---
def create_pdf(h_tipi, h_irk, h_kg, h_adg, maliyet, yem_df, r_ca, r_p, r_ndf, r_km, riskler):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(30, 58, 138); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 15, txt=tr2eng("CUMHURIYET UNIVERSITESI - KLINIK RASYON RAPORU"), ln=True, align='C', fill=True)
    pdf.ln(5)
    
    pdf.set_text_color(0, 0, 0); pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=tr2eng("  Hayvan Bilgileri & Performans"), ln=True, fill=True); pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, txt=tr2eng(f"  Tip/Irk: {h_tipi} - {h_irk}  |  Canli Agirlik: {h_kg} kg  |  Buyume: {h_adg} kg/gun"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.set_fill_color(34, 197, 94); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, txt=tr2eng("  Tavsiye Edilen Yemler (kg/gun)"), ln=True, fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 11); pdf.set_fill_color(250, 250, 250)
    for index, row in yem_df.iterrows():
        kg = row.get('Önerilen Miktar (kg)', 0)
        if kg > 0:
            pdf.cell(150, 8, txt=tr2eng(f"   {row['yem_adi']}"), border='B', fill=True)
            pdf.cell(40, 8, txt=f"{round(kg, 2)} kg", border='B', ln=True, align='R', fill=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.set_fill_color(240, 240, 240); pdf.cell(0, 10, txt=tr2eng("  Veriler"), ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(100, 8, txt=tr2eng(f"   Maliyet: {round(maliyet, 2)} TL/gun | Ca/P: {round(r_ca/r_p,2) if r_p>0 else 0} | NDF: %{round((r_ndf/r_km)*100,1) if r_km>0 else 0}"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.set_fill_color(220, 38, 38); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, txt=tr2eng("  VETERINER HEKIM RISK ANALIZI"), ln=True, fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'I', 10); pdf.set_fill_color(254, 242, 242)
    for risk in riskler:
        pdf.multi_cell(0, 8, txt=tr2eng(f"- {risk}"), fill=True, border='B')
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# GÖRSEL BAŞLIK ALANI
# ==========================================
col_logo, col_baslik = st.columns([1, 4])
with col_logo:
    # Modern bir inek/çiftlik görseli
    st.image("https://images.unsplash.com/photo-1574686588825-348a478be9fc?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80", use_column_width=True)
with col_baslik:
    st.markdown("<h1 class='baslik'>🐄 Veteriner Klinik Rasyon Optimizasyon Modülü</h1>", unsafe_allow_html=True)
    st.info("Bu profesyonel araç; rumen sağlığı, asidoz riski ve maliyet hesaplamalarını gözeterek en optimum rasyonu hazırlamanızı sağlar. **Aşağıdaki 3 adımı sırasıyla uygulayın.**")

st.markdown("---")

# ==========================================
# 1. VE 2. ADIM: GENİŞ 2 SÜTUNLU YAPI
# ==========================================
col_sol, col_sag = st.columns([1.2, 2]) # Sağ taraf (Tablo) bilerek daha geniş bırakıldı

with col_sol:
    st.markdown("### 📝 Adım 1: Hayvan Bilgileri")
    with st.container(border=True):
        hayvan_tipi = st.selectbox("Hayvanın Tipi", ["Besi Sığırı", "Buzağı", "Damızlık Boğa"])
        irk = st.selectbox("Irkı", ["Siyah Alaca (Holstein)", "Simental (Flekvi)", "Montofon (Esmer)", "Yerli Kara", "Angus", "Şarole (Charolais)", "Limuzin", "Hereford", "Belçika Mavisi", "Melez (Kırma)"])
        col_yas, col_kond = st.columns(2)
        yas = col_yas.number_input("Yaşı (ay)", value=16, min_value=1)
        kondisyon = col_kond.slider("Kondisyon Skoru", 1.0, 5.0, 5.0, 0.5)
        canli_agirlik = st.number_input("Mevcut Canlı Ağırlık (kg)", value=300, step=10)
        adg = st.number_input("Hedeflenen Günlük Ağırlık Artışı (kg/gün)", value=1.600, step=0.1)

    with st.expander("🌤️ Çevre ve Barınak Koşulları (Opsiyonel)", expanded=False):
        camur = st.selectbox("Zemindeki Çamur Miktarı", ["Yok", "Bileğe Kadar", "Dize Kadar"])
        deri_durumu = st.selectbox("Deri ve Kıl Durumu", ["Kuru", "Islak / Çamurlu"])

with col_sag:
    st.markdown("### 🌾 Adım 2: Yem Seçimi ve Limitler")
    
    # Yem veritabanını oku
    try:
        df_yem_ham = pd.read_csv("yem_veritabani.csv")
        if 'min_kg' not in df_yem_ham.columns: df_yem_ham['min_kg'] = 0.0
        if 'maks_kg' not in df_yem_ham.columns: df_yem_ham['maks_kg'] = 15.0
    except FileNotFoundError:
        st.error("yem_veritabani.csv dosyası bulunamadı!")
        st.stop()
        
    # YENİ ÖZELLİK: Arama ve Seçme (Dropdown)
    st.markdown("Kullanıcının elindeki yemleri aşağıdaki listeden arayarak seçin. Seçtiğiniz yemler tabloya düşecektir.")
    tum_yemler = df_yem_ham['yem_adi'].tolist()
    varsayilanlar = ["Misir Silaji", "Yonca Kuru Otu", "Arpa Ezmesi", "Bugday Samani"] # Tablo ilk açıldığında boş kalmasın diye
    secilen_isimler = st.multiselect("🔍 Rasyona Eklenecek Yemleri Seçiniz:", options=tum_yemler, default=[y for y in varsayilanlar if y in tum_yemler])
    
    if not secilen_isimler:
        st.warning("Lütfen listeden en az bir yem seçiniz!")
        st.stop()
        
    # Sadece seçilen yemleri filtrele
    df_secilen = df_yem_ham[df_yem_ham['yem_adi'].isin(secilen_isimler)].copy().reset_index(drop=True)
    
    # YENİ ÖZELLİK: Tabloda sadece gerekli sütunları göster (Karmaşayı önler)
    st.markdown("Aşağıdaki tablodan seçtiğiniz yemlerin güncel fiyatını ve hayvan başına verilebilecek **Min/Maks limitlerini (kg)** ayarlayabilirsiniz.")
    duzenlenen_gorunum = st.data_editor(
        df_secilen,
        column_config={
            "yem_grubu": None, "kuru_madde_yuzde": None, "ham_protein_yuzde": None, 
            "me_mcal_kg": None, "kalsiyum_yuzde": None, "fosfor_yuzde": None, 
            "ndf_yuzde": None, "endf_yuzde": None,
            "yem_adi": st.column_config.TextColumn("Seçilen Yem Adı", disabled=True),
            "fiyat_tl": st.column_config.NumberColumn("Fiyat (TL/kg)"),
            "min_kg": st.column_config.NumberColumn("Min İzin (kg)"),
            "maks_kg": st.column_config.NumberColumn("Maks Sınır (kg)")
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed" # Satır ekleme işini artık yukarıdaki multiselect yapıyor
    )
    # Düzenlenmiş fiyat ve limitleri ana hesaplama df'ine geri aktar
    df_secilen['fiyat_tl'] = duzenlenen_gorunum['fiyat_tl']
    df_secilen['min_kg'] = duzenlenen_gorunum['min_kg']
    df_secilen['maks_kg'] = duzenlenen_gorunum['maks_kg']

st.markdown("---")

# ==========================================
# HESAPLAMA MOTORU
# ==========================================
ihtiyac_km = round((canli_agirlik * 0.015) + (adg * 2.3) + 0.02, 1)
ihtiyac_hp = round((canli_agirlik * 1.5) + (adg * 240), 0)
ihtiyac_me = round((canli_agirlik * 0.04) + (adg * 6.1), 2)
if camur == "Dize Kadar": ihtiyac_me *= 1.10 
elif camur == "Bileğe Kadar": ihtiyac_me *= 1.05
if deri_durumu == "Islak / Çamurlu": ihtiyac_me *= 1.05
ihtiyac_ca = round((canli_agirlik * 0.08) + (adg * 10.6), 1)
ihtiyac_p = round((canli_agirlik * 0.04) + (adg * 6.25), 1)
ihtiyac_ndf_min = round(ihtiyac_km * 0.28, 1)

# ==========================================
# 3. ADIM: ÇÖZÜCÜ VE SONUÇ EKRANI (TAM GENİŞLİK)
# ==========================================
st.markdown("### ⚙️ Adım 3: Optimizasyon")
btn_coz = st.button("🚀 MATEMATİKSEL RASYONU ÇÖZ", type="primary", use_container_width=True)

if btn_coz:
    prob = pulp.LpProblem("En_Ucuz_Rasyon", pulp.LpMinimize)
    yem_vars = []
    for index, row in df_secilen.iterrows():
        var = pulp.LpVariable(f"yem_{index}", lowBound=row['min_kg'], upBound=row['maks_kg'])
        yem_vars.append(var)
        
    prob += pulp.lpSum([yem_vars[i] * df_secilen.loc[i, 'fiyat_tl'] for i in range(len(yem_vars))])
    prob += pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'kuru_madde_yuzde']/100) for i in range(len(yem_vars))]) >= ihtiyac_km * 0.98
    prob += pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'kuru_madde_yuzde']/100) for i in range(len(yem_vars))]) <= ihtiyac_km * 1.05
    prob += pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'ham_protein_yuzde']*10) for i in range(len(yem_vars))]) >= ihtiyac_hp
    prob += pulp.lpSum([yem_vars[i] * df_secilen.loc[i, 'me_mcal_kg'] for i in range(len(yem_vars))]) >= ihtiyac_me
    total_ca = pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'kalsiyum_yuzde']*10) for i in range(len(yem_vars))])
    total_p = pulp.lpSum([yem_vars[i] * (df_secilen.loc[i, 'fosfor_yuzde']*10) for i in range(len(yem_vars))])
    prob += total_ca >= ihtiyac_ca
    prob += total_p >= ihtiyac_p
    
    prob.solve()
    
    if pulp.LpStatus[prob.status] == "Optimal":
        st.toast("✅ Başarılı! En uygun maliyetli rasyon hesaplandı.", icon="🎉")
        
        rasyon_km=rasyon_hp=rasyon_me=rasyon_ca=rasyon_p=rasyon_ndf=maliyet=0.0
        for i, var in enumerate(yem_vars):
            kg = var.varValue
            df_secilen.at[i, 'Önerilen Miktar (kg)'] = round(kg, 2)
            km_katkisi = kg * (df_secilen.loc[i, 'kuru_madde_yuzde'] / 100)
            rasyon_km += km_katkisi
            rasyon_hp += kg * (df_secilen.loc[i, 'ham_protein_yuzde'] * 10)
            rasyon_me += kg * df_secilen.loc[i, 'me_mcal_kg']
            rasyon_ca += kg * (df_secilen.loc[i, 'kalsiyum_yuzde'] * 10)
            rasyon_p += kg * (df_secilen.loc[i, 'fosfor_yuzde'] * 10)
            rasyon_ndf += km_katkisi * (df_secilen.loc[i, 'ndf_yuzde'] / 100)
            maliyet += kg * df_secilen.loc[i, 'fiyat_tl']
            
        # Alt kısımda sonuçları geniş geniş gösterelim
        st.divider()
        col_sonuc_tablo, col_sonuc_rapor = st.columns([1.5, 1])
        
        with col_sonuc_tablo:
            st.markdown("#### 📊 Besin Maddeleri Denge Panosu")
            def durum_hesapla(rasyon, ihtiyac):
                if rasyon == 0: return "-"
                if rasyon < ihtiyac * 0.98: return "EKSİK"
                if rasyon > ihtiyac * 1.05: return "FAZLA"
                return "TAMAM"
                
            denge_verileri = {
                "Parametre": ["Kuru Madde (kg)", "Ham Protein (g)", "ME (Mcal)", "Kalsiyum (g)", "Fosfor (g)", "NDF (kg)"],
                "İhtiyaç": [ihtiyac_km, ihtiyac_hp, ihtiyac_me, ihtiyac_ca, ihtiyac_p, ihtiyac_ndf_min],
                "Rasyon": [round(rasyon_km,1), round(rasyon_hp,0), round(rasyon_me,1), round(rasyon_ca,1), round(rasyon_p,1), round(rasyon_ndf,1)],
                "Sonuç": [durum_hesapla(rasyon_km, ihtiyac_km), durum_hesapla(rasyon_hp, ihtiyac_hp), durum_hesapla(rasyon_me, ihtiyac_me), durum_hesapla(rasyon_ca, ihtiyac_ca), durum_hesapla(rasyon_p, ihtiyac_p), durum_hesapla(rasyon_ndf, ihtiyac_ndf_min)]
            }
            def stil_uygula(val):
                if val == "EKSİK": return "background-color: #F87171; color: white; font-weight: bold;"
                elif val == "FAZLA": return "background-color: #60A5FA; color: white; font-weight: bold;"
                elif val == "TAMAM": return "background-color: #34D399; color: black; font-weight: bold;"
                return ""
            st.dataframe(pd.DataFrame(denge_verileri).style.map(stil_uygula, subset=["Sonuç"]), use_container_width=True)
            
            st.success(f"**💰 Günlük Hayvan Başı Maliyet:** {round(maliyet, 2)} TL")
            st.dataframe(df_secilen[df_secilen['Önerilen Miktar (kg)'] > 0][['yem_adi', 'Önerilen Miktar (kg)']], use_container_width=True, hide_index=True)

        with col_sonuc_rapor:
            st.markdown("#### 🩺 Veteriner Risk Analizi")
            saptanan_riskler = risk_analizi(rasyon_km, rasyon_ndf, rasyon_ca, rasyon_p, rasyon_me, ihtiyac_me, rasyon_hp, ihtiyac_hp)
            for r in saptanan_riskler:
                if "GÜVENLİ" in r: st.success(r)
                else: st.error(r)
                
            st.info(f"🔬 **Klinik Oranlar:**\n\nCa/P Oranı: `{round(rasyon_ca/rasyon_p, 2) if rasyon_p > 0 else 0}`\n\nKuru Maddede NDF: `% {round((rasyon_ndf/rasyon_km)*100, 1) if rasyon_km > 0 else 0}`")
            
            pdf_bytes = create_pdf(hayvan_tipi, irk, canli_agirlik, adg, maliyet, df_secilen, rasyon_ca, rasyon_p, rasyon_ndf, rasyon_km, saptanan_riskler)
            st.download_button("📥 RESMİ KLİNİK RAPORU İNDİR (PDF)", data=pdf_bytes, file_name="Veteriner_Rasyon_Raporu.pdf", mime="application/pdf", type="primary", use_container_width=True)
    else:
        st.error("⚠️ Seçilen yem sınırları ile (Max kısıtları çok düşük olabilir) hayvanın ihtiyacını karşılayacak matematiksel bir rasyon kurulamadı. Lütfen yem limitlerini artırın.")