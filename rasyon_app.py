import streamlit as st
import pandas as pd
import pulp
from fpdf import FPDF

# --- 1. AYARLAR ---
st.set_page_config(page_title="Veteriner Rasyon Modülü", layout="wide")

# --- 2. OTOMATİK DEV YEM VERİTABANI ---
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

with open("yem_veritabani.csv", "w", encoding="utf-8") as f:
    f.write(EKSIKSIZ_YEM_LISTESI)

df_yem_ham = pd.read_csv("yem_veritabani.csv")
df_yem_ham['min_kg'] = 0.0
df_yem_ham['maks_kg'] = 15.0

# --- 3. YARDIMCI FONKSİYONLAR ---
def tr2eng(text):
    chars = {'ı':'i', 'ş':'s', 'ğ':'g', 'ç':'c', 'ö':'o', 'ü':'u', 'İ':'I', 'Ş':'S', 'Ğ':'G', 'Ç':'C', 'Ö':'O', 'Ü':'U'}
    for k, v in chars.items(): text = str(text).replace(k, v)
    return text

def risk_analizi(r_km, r_ndf, r_ca, r_p, r_me, i_me, r_hp, i_hp):
    riskler = []
    ndf_orani = (r_ndf / r_km) * 100 if r_km > 0 else 0
    ca_p_orani = r_ca / r_p if r_p > 0 else 0

    if ndf_orani < 28:
        riskler.append("ASİDOZ RİSKİ: Rasyondaki kaba yem (NDF) yetersiz. Rumen pH'ı düşebilir.")
    if 0 < ca_p_orani < 1.2:
        riskler.append("ÜROLİTİYAZİS RİSKİ: Ca/P oranı çok düşük. İdrar taşı oluşabilir.")
    elif ca_p_orani > 3.0:
        riskler.append("MİNERAL BLOKAJI RİSKİ: Aşırı Kalsiyum emilimi bozuyor.")
    if r_hp > (i_hp * 1.15):
        riskler.append("HEPATİK STRES: Fazla protein verildi. Karaciğer yorulabilir.")
    if r_me > (i_me * 1.15):
        riskler.append("KARACİĞER YAĞLANMASI: Aşırı enerji yüklemesi mevcut.")
    if not riskler:
        riskler.append("RASYON GÜVENLİ: Klinik parametreler fizyolojik sınırlar içerisindedir.")
    return riskler

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

# --- 4. GÖRSEL VE BAŞLIK ---
col_logo, col_metin = st.columns([1, 5])
with col_logo:
    # ÇÖZÜM: HTML kullanarak görseli kullanıcı tarayıcısına yükletiyoruz, Python'u yormuyoruz.
    st.markdown('<img src="https://upload.wikimedia.org/wikipedia/commons/0/0c/Cow_female_black_white.jpg" style="width:100%; border-radius:10px;">', unsafe_allow_html=True)
with col_metin:
    st.title("🐄 Veteriner Klinik Rasyon Modülü")
    st.info("Bu sistem, hayvan sağlığını ve metabolik sınırları (NDF, Ca/P) koruyarak en düşük maliyetli rasyonu otomatik hesaplar.")

st.divider()

# --- 5. ARAYÜZ ---
col_sol, col_sag = st.columns(2)

with col_sol:
    st.subheader("📝 Adım 1: Hayvan Bilgileri")
    hayvan_tipi = st.selectbox("Hayvanın Tipi", ["Besi Sığırı", "Buzağı", "Damızlık Boğa"])
    irk = st.selectbox("Irkı", [
        "Siyah Alaca (Holstein)", "Simental (Flekvi)", "Montofon (Esmer)", 
        "Yerli Kara", "Angus", "Şarole (Charolais)", "Limuzin", "Hereford", 
        "Belçika Mavisi", "Doğu Anadolu Kırmızısı (DAK)", "Boz Irk", 
        "Güney Anadolu Kırmızısı (GAK)", "Melez (Kırma)"
    ])
    yas = st.number_input("Yaşı (ay)", value=16, min_value=1)
    kondisyon = st.slider("Kondisyon Skoru", 1.0, 5.0, 5.0, 0.5)
    canli_agirlik = st.number_input("Mevcut Canlı Ağırlık (kg)", value=300, step=10)
    adg = st.number_input("Hedeflenen Günlük Ağırlık Artışı (kg/gün)", value=1.600, step=0.1)

    st.subheader("🌤️ Adım 2: Çevre ve Barınak Koşulları")
    sicaklik = st.number_input("Mevcut Sıcaklık (°C)", value=18.0)
    gecmis_sicaklik = st.number_input("Geçen Ayın Ort. Sıcaklığı (°C)", value=15.0)
    camur = st.selectbox("Zemindeki Çamur Miktarı", ["Yok", "Bileğe Kadar", "Dize Kadar"])
    deri_durumu = st.selectbox("Deri ve Kıl Durumu", ["Kuru", "Islak / Çamurlu"])
    mera = st.checkbox("Merada Otluyor mu?", value=False)

with col_sag:
    st.subheader("🌾 Adım 3: Yem Seçimi ve Limitler")
    st.markdown("**1. Rasyona Eklenecek Yemleri Seçin:**")
    tum_yemler = df_yem_ham['yem_adi'].tolist()
    varsayilanlar = ["Misir Silaji", "Yonca Kuru Otu", "Arpa Ezmesi", "Bugday Samani", "Soya Kuspesi (%44)", "Mermer Tozu (Ca Kaynagi)"]
    
    secilen_isimler = st.multiselect(
        "Listeden arayın veya seçin:", 
        options=tum_yemler, 
        default=[y for y in varsayilanlar if y in tum_yemler]
    )
    
    if not secilen_isimler:
        st.warning("Lütfen listeden en az bir yem seçiniz!")
        st.stop()
        
    df_secilen = df_yem_ham[df_yem_ham['yem_adi'].isin(secilen_isimler)].copy().reset_index(drop=True)
    
    st.markdown("**2. Fiyat ve Limit Ayarlamaları:**")
    duzenlenen_gorunum = st.data_editor(
        df_secilen,
        column_config={
            "yem_grubu": None, "kuru_madde_yuzde": None, "ham_protein_yuzde": None, 
            "me_mcal_kg": None, "kalsiyum_yuzde": None, "fosfor_yuzde": None, 
            "ndf_yuzde": None, "endf_yuzde": None,
            "yem_adi": st.column_config.TextColumn("Seçilen Yem", disabled=True),
            "fiyat_tl": st.column_config.NumberColumn("Fiyat (TL/kg)"),
            "min_kg": st.column_config.NumberColumn("Min (kg)"),
            "maks_kg": st.column_config.NumberColumn("Maks Sınır (kg)")
        },
        hide_index=True,
        use_container_width=True
    )
    df_secilen['fiyat_tl'] = duzenlenen_gorunum['fiyat_tl']
    df_secilen['min_kg'] = duzenlenen_gorunum['min_kg']
    df_secilen['maks_kg'] = duzenlenen_gorunum['maks_kg']

st.divider()

# --- 6. HESAPLAMALAR ---
ihtiyac_km = round((canli_agirlik * 0.015) + (adg * 2.3) + 0.02, 1)
ihtiyac_hp = round((canli_agirlik * 1.5) + (adg * 240), 0)
ihtiyac_me = round((canli_agirlik * 0.04) + (adg * 6.1), 2)
if camur == "Dize Kadar": ihtiyac_me *= 1.10 
elif camur == "Bileğe Kadar": ihtiyac_me *= 1.05
if deri_durumu == "Islak / Çamurlu": ihtiyac_me *= 1.05
if sicaklik < 5.0: ihtiyac_me *= 1.05
if mera: ihtiyac_me *= 1.10
ihtiyac_ca = round((canli_agirlik * 0.08) + (adg * 10.6), 1)
ihtiyac_p = round((canli_agirlik * 0.04) + (adg * 6.25), 1)
ihtiyac_ndf_min = round(ihtiyac_km * 0.28, 1)

# --- 7. ÇÖZÜCÜ VE SONUÇLAR ---
btn_coz = st.button("🚀 OPTİMAL RASYONU HESAPLA VE ÇÖZ", type="primary", use_container_width=True)

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
            
        col_sonuc_tablo, col_sonuc_rapor = st.columns(2)
        
        with col_sonuc_tablo:
            st.subheader("📊 Besin Karşılama Tablosu")
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
            st.dataframe(pd.DataFrame(denge_verileri), use_container_width=True)
            
            st.success(f"**💰 Toplam Günlük Maliyet (Hayvan Başı): {round(maliyet, 2)} TL**")
            st.dataframe(df_secilen[df_secilen['Önerilen Miktar (kg)'] > 0][['yem_adi', 'Önerilen Miktar (kg)']], use_container_width=True, hide_index=True)

        with col_sonuc_rapor:
            st.subheader("🩺 Klinik Risk Değerlendirmesi")
            saptanan_riskler = risk_analizi(rasyon_km, rasyon_ndf, rasyon_ca, rasyon_p, rasyon_me, ihtiyac_me, rasyon_hp, ihtiyac_hp)
            for r in saptanan_riskler:
                if "GÜVENLİ" in r: st.success(r)
                else: st.error(r)
                
            st.info(f"🔬 **Klinik Oranlar:**\n\nCa/P Oranı: `{round(rasyon_ca/rasyon_p, 2) if rasyon_p > 0 else 0}`\n\nKuru Maddede NDF Oranı: `% {round((rasyon_ndf/rasyon_km)*100, 1) if rasyon_km > 0 else 0}`")
            
            pdf_bytes = create_pdf(hayvan_tipi, irk, canli_agirlik, adg, maliyet, df_secilen, rasyon_ca, rasyon_p, rasyon_ndf, rasyon_km, saptanan_riskler)
            st.download_button("📥 RESMİ KLİNİK RAPORU İNDİR (PDF)", data=pdf_bytes, file_name="CUVet_Rasyon_Raporu.pdf", mime="application/pdf", type="primary", use_container_width=True)
    else:
        st.error("⚠️ Seçilen yem limitleri ile matematiksel model kurulamadı. Lütfen 'Maks Sınır' değerlerini artırın veya listeye daha fazla yem ekleyin.")