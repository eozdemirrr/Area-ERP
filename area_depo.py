import streamlit as st
import json
import os
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import tempfile
import re # Boşluk temizliği için eklendi

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Area Kurumsal Yönetim", layout="wide", page_icon="🏢")

# --- KULLANICI YETKİLENDİRME ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["kullanici"] = ""
    st.session_state["rol"] = ""
    st.session_state["isim"] = ""

# --- BULUT VERİTABANI İŞLEMLERİ ---
FIREBASE_URL = "https://areaerp-default-rtdb.europe-west1.firebasedatabase.app/area_db.json"

def veritabanini_yukle():
    try:
        # Önbelleğe takılmamak için zaman damgası eklendi
        cevap = requests.get(f"{FIREBASE_URL}?nocache={datetime.now().timestamp()}")
        if cevap.status_code == 200:
            data = cevap.json()
            if data is None: data = {}
            tamir_edildi = False
            if "urunler" not in data: data["urunler"] = {}; tamir_edildi = True
            if "stok" not in data: data["stok"] = {}; tamir_edildi = True
            if "hareketler" not in data: data["hareketler"] = []; tamir_edildi = True
            if "id_sayaci" not in data: data["id_sayaci"] = 1; tamir_edildi = True
            if "kullanicilar" not in data:
                data["kullanicilar"] = {
                    "depo": {"sifre": "1234", "rol": "Depo", "isim": "Depo Sorumlusu"},
                    "muhasebe": {"sifre": "1234", "rol": "Finans", "isim": "Finans Departmanı"},
                    "servis": {"sifre": "1234", "rol": "Servis", "isim": "Servis Personeli"},
                    "admin": {"sifre": "admin123", "rol": "Yönetici", "isim": "Sistem Yöneticisi"}
                }
                tamir_edildi = True
            
            # Kategori veritabanı eklendi (Multi Dış/İç dahil)
            if "kategoriler" not in data:
                data["kategoriler"] = ["VRF Dış", "VRF İç", "Multi Dış", "Multi İç", "Duvar Tipi Split", "Ticari Tip Split", "Yedek Parça", "Aksesuar", "Diğer"]
                tamir_edildi = True

            if tamir_edildi: veritabanini_kaydet(data)
            return data
    except:
        st.error("⚠️ Bulut veritabanına bağlanılamadı!")
    return None

def veritabanini_kaydet(db):
    if db is None: return False
    try:
        cevap = requests.put(FIREBASE_URL, json=db)
        return cevap.status_code == 200
    except:
        return False

def isim_temizle(metin):
    # Çift boşlukları ve yasaklı karakterleri temizleyen kod
    yasakli = [".", "$", "#", "[", "]", "/"]
    metin = str(metin).strip()
    metin = re.sub(r'\s+', ' ', metin)
    for char in yasakli:
        metin = metin.replace(char, "-")
    return metin

def son_3_ayda_mi(tarih_str):
    if not tarih_str or tarih_str == "-": return False
    try:
        t = datetime.strptime(tarih_str, "%d.%m.%Y %H:%M:%S")
        return (datetime.now() - t).days <= 90
    except: return False

db = veritabanini_yukle()
if db is None:
    st.error("❌ Veritabanı bağlantısı koptu! Lütfen sayfayı yenileyin.")
    st.stop()

KATEGORILER = db.get("kategoriler", ["VRF Dış", "VRF İç", "Multi Dış", "Multi İç", "Duvar Tipi Split", "Ticari Tip Split", "Yedek Parça", "Aksesuar", "Diğer"])

# =====================================================================
# GİRİŞ SİSTEMİ
# =====================================================================
if not st.session_state["logged_in"]:
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        col_l1, col_l2, col_l3 = st.columns([1, 1, 1])
        with col_l2: st.image(logo_path, use_container_width=True)
    st.markdown("<h2 style='text-align: center; color: #2c3e50;'>AREA İKLİMLENDİRME ERP GİRİŞİ</h2>", unsafe_allow_html=True)
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            k_adi = st.text_input("👤 Kullanıcı Adı:").strip().lower()
            sifre = st.text_input("🔑 Şifre:", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                kullanicilar_db = db.get("kullanicilar", {})
                if k_adi in kullanicilar_db and kullanicilar_db[k_adi]["sifre"] == sifre:
                    st.session_state["logged_in"] = True
                    st.session_state["kullanici"] = k_adi
                    st.session_state["rol"] = kullanicilar_db[k_adi]["rol"]
                    st.session_state["isim"] = kullanicilar_db[k_adi]["isim"]
                    st.rerun()
                else: st.error("❌ Hatalı Kullanıcı Adı veya Şifre!")
    st.stop()

# =====================================================================
# ANA SİSTEM
# =====================================================================
logo_path = "logo.png"
if os.path.exists(logo_path):
    col_t1, col_t2, col_t3 = st.columns([1, 1, 1])
    with col_t2: st.image(logo_path, use_container_width=True)

st.markdown("<h2 style='text-align: center; color: #2c3e50;'>AREA İKLİMLENDİRME KURUMSAL YÖNETİM PORTALI</h2>", unsafe_allow_html=True)
st.markdown("---")

st.sidebar.success(f"👋 Hoş Geldin, {st.session_state['isim']}")
st.sidebar.markdown("---")
sayfalar = []
if st.session_state["rol"] == "Depo": sayfalar = ["📦 Depo Yönetim Ekranı", "📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Finans": sayfalar = ["🧾 Finans & Muhasebe", "📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Servis": sayfalar = ["📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Yönetici": sayfalar = ["📦 Depo Yönetim Ekranı", "💼 Yönetici", "🧾 Finans & Muhasebe", "📊 Genel Stok Envanteri", "📈 Yönetim Paneli"]

secilen_sayfa = st.sidebar.radio("📁 Menü", sayfalar)
if st.sidebar.button("🚪 Güvenli Çıkış Yap", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 1. DEPO YÖNETİM ---
if secilen_sayfa == "📦 Depo Yönetim Ekranı":
    st.header("📦 Depo Çıkış Paneli")
    if not db["stok"]: st.warning("⚠️ Sistemde stok bulunmamaktadır.")
    else:
        with st.form("depo_cikis_formu", clear_on_submit=True):
            urun = st.selectbox("Çıkan Ürün (Cihaz):", sorted(list(db["stok"].keys())))
            firma = st.text_input("Gideceği Firma / Şantiye:").upper().strip()
            c3, c4 = st.columns(2)
            mevcut = db["stok"].get(urun, 0)
            
            # ALİCAN İÇİN DEĞİŞİKLİK: max_value kaldırıldı
            adet = c3.number_input(f"Miktar (Mevcut: {mevcut})", min_value=1, step=1)
            notlar = c4.text_input("Ek Notlar / İrsaliye No:")
            
            if st.form_submit_button("🚚 DEPODAN ÇIKIŞ YAP"):
                if firma == "": st.error("Lütfen Firma Adını Yazın!")
                elif adet > mevcut: st.error(f"❌ Stok yetersiz! Mevcutta sadece {mevcut} adet var.")
                else:
                    taze_db = veritabanini_yukle()
                    if taze_db:
                        taze_db["stok"][urun] -= adet
                        taze_db["hareketler"].insert(0, {"id": taze_db["id_sayaci"], "tarih_cikis": datetime.now().strftime("%d.%m.%Y %H:%M:%S"), "tarih_onay": "-", "tarih_fatura": "-", "urun": urun, "adet": adet, "firma": firma, "notlar": notlar, "durum": "Fiyat Bekliyor", "fiyat": 0, "islem_yapan": st.session_state["kullanici"]})
                        taze_db["id_sayaci"] += 1
                        if veritabanini_kaydet(taze_db): st.success("✅ Çıkış Başarılı! Yönetici onayına iletildi."); st.rerun()

    st.markdown("---")
    st.subheader("🕒 Son 3 Ayın Çıkış Kayıtları")
    cikislar = [h for h in db["hareketler"] if son_3_ayda_mi(h.get("tarih_cikis", "-"))]
    if cikislar:
        df_cikis = pd.DataFrame(cikislar)[["id", "tarih_cikis", "firma", "urun", "adet", "durum"]]
        df_cikis.columns = ["İşlem No", "Çıkış Tarihi", "Firma", "Ürün", "Adet", "Durum"]
        st.dataframe(df_cikis, use_container_width=True, hide_index=True)

# --- 2. YÖNETİCİ ---
elif secilen_sayfa == "💼 Yönetici":
    st.header("💼 Yönetici Onay Paneli")
    bekleyenler = [h for h in db["hareketler"] if h["durum"] == "Fiyat Bekliyor"]
    if not bekleyenler: st.success("Tebrikler, onay bekleyen işlem yok.")
    else:
        for islem in bekleyenler:
            with st.expander(f"🔴 {islem['firma']} | {islem['tarih_cikis']}", expanded=True):
                # YÖNETİCİ DÜZENLEME FORMU
                with st.form(f"fiyat_form_{islem['id']}"):
                    c_f, c_u, c_a = st.columns([2, 3, 1])
                    
                    yeni_firma = c_f.text_input("Firma / Şantiye:", value=islem['firma'])
                    
                    urun_listesi = sorted(list(db["stok"].keys()))
                    if islem['urun'] not in urun_listesi:
                        urun_listesi.insert(0, islem['urun'])
                    try: u_idx = urun_listesi.index(islem['urun'])
                    except: u_idx = 0
                    
                    yeni_urun = c_u.selectbox("Ürün:", urun_listesi, index=u_idx)
                    yeni_adet = c_a.number_input("Adet:", min_value=1, value=int(islem['adet']), step=1)
                    
                    y_fiyat = st.number_input("Toplam Satış Bedeli (₺):", min_value=0.0, step=500.0)
                    
                    c_b1, c_b2 = st.columns(2)
                    btn_guncelle = c_b1.form_submit_button("🔄 Bilgileri Güncelle", use_container_width=True)
                    btn_onayla = c_b2.form_submit_button("💰 Bedeli Onayla", use_container_width=True)
                    
                    if btn_guncelle or btn_onayla:
                        eski_urun = islem["urun"]
                        eski_adet = islem["adet"]
                        
                        taze_db = veritabanini_yukle()
                        if taze_db:
                            idx = next((i for i, h in enumerate(taze_db["hareketler"]) if h["id"] == islem["id"]), None)
                            if idx is not None:
                                taze_db["stok"][eski_urun] = taze_db["stok"].get(eski_urun, 0) + eski_adet
                                taze_db["stok"][yeni_urun] = taze_db["stok"].get(yeni_urun, 0) - yeni_adet
                                
                                taze_db["hareketler"][idx]["firma"] = yeni_firma.upper()
                                taze_db["hareketler"][idx]["urun"] = yeni_urun
                                taze_db["hareketler"][idx]["adet"] = yeni_adet
                                
                                if btn_onayla:
                                    taze_db["hareketler"][idx]["fiyat"] = y_fiyat
                                    taze_db["hareketler"][idx]["durum"] = "Fatura Bekliyor"
                                    taze_db["hareketler"][idx]["tarih_onay"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                                    
                                if veritabanini_kaydet(taze_db): st.rerun()

    st.markdown("---")
    st.subheader("🕒 Son 3 Ayda Onaylanan İşlemler")
    onaylananlar = [h for h in db["hareketler"] if h["durum"] in ["Fatura Bekliyor", "Tamamlandı"] and son_3_ayda_mi(h.get("tarih_onay", "-"))]
    if onaylananlar:
        df_onay = pd.DataFrame(onaylananlar)[["id", "tarih_onay", "firma", "urun", "fiyat", "durum"]]
        df_onay.columns = ["İşlem No", "Onay Tarihi", "Firma", "Ürün", "Tutar (₺)", "Durum"]
        st.dataframe(df_onay, use_container_width=True, hide_index=True)

# --- 3. FİNANS ---
elif secilen_sayfa == "🧾 Finans & Muhasebe":
    st.header("🧾 Fatura Kesim Paneli")
    bekleyenler = [h for h in db["hareketler"] if h["durum"] == "Fatura Bekliyor"]
    if not bekleyenler: st.success("Harika! Kesilmeyi bekleyen fatura yok.")
    else:
        for islem in bekleyenler:
            st.markdown(f"### 🔵 {islem['firma']}")
            st.write(f"**Ürün:** {islem['urun']} | **Bedel:** {islem['fiyat']:,.2f} ₺")
            if st.button(f"✅ Faturası Kesildi (ID: {islem['id']})", use_container_width=True):
                islem["durum"], islem["tarih_fatura"] = "Tamamlandı", datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                if veritabanini_kaydet(db): st.rerun()

    st.markdown("---")
    st.subheader("🕒 Son 3 Ayda Kesilen Faturalar")
    kesilenler = [h for h in db["hareketler"] if h["durum"] == "Tamamlandı" and son_3_ayda_mi(h.get("tarih_fatura", "-"))]
    if kesilenler:
        df_fatura = pd.DataFrame(kesilenler)[["id", "tarih_fatura", "firma", "urun", "fiyat"]]
        df_fatura.columns = ["İşlem No", "Fatura Tarihi", "Firma", "Ürün", "Tutar (₺)"]
        st.dataframe(df_fatura, use_container_width=True, hide_index=True)

# --- 4. STOK ENVANTERİ ---
elif secilen_sayfa == "📊 Genel Stok Envanteri":
    if st.session_state["rol"] in ["Yönetici", "Depo"]:
        st.subheader("➕ Yeni Cihaz / Ürün Girişi")
        
        # ALİCAN İÇİN YENİ ÖZELLİK: Mevcut ürünü otomatik doldurma
        mevcut_urunler_listesi = sorted(list(db["urunler"].keys()))
        secilen_mevcut = st.selectbox("💡 Mevcut bir ürüne stok ekleyecekseniz buradan seçin (Otomatik Doldurur):", ["Yeni Kart Oluştur"] + mevcut_urunler_listesi)
        
        varsayilan_marka = ""
        varsayilan_seri = ""
        varsayilan_model = ""
        
        if secilen_mevcut != "Yeni Kart Oluştur":
            d = db["urunler"][secilen_mevcut]
            varsayilan_marka = d.get("Marka", "")
            varsayilan_seri = d.get("Seri", "")
            varsayilan_model = d.get("Model Kodu", "")

        with st.form("yeni_mal_formu", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            marka = isim_temizle(c1.text_input("Marka:", value=varsayilan_marka).upper())
            seri = isim_temizle(c2.text_input("Seri:", value=varsayilan_seri).upper())
            model = isim_temizle(c3.text_input("Model Kodu:", value=varsayilan_model).upper())
            cesit = c4.selectbox("Kategori:", KATEGORILER)
            adet = st.number_input("Adet:", min_value=1)
            
            if st.form_submit_button("📥 Envantere Ekle"):
                if model == "": st.error("Lütfen Model Kodu girin!")
                else:
                    taze_db = veritabanini_yukle()
                    if taze_db:
                        urun_ad = f"{marka} {seri} - {model} ({cesit})".replace("  ", " ").strip()
                        taze_db["urunler"][urun_ad] = {"Marka": marka, "Seri": seri, "Model Kodu": model, "Kategori": cesit}
                        taze_db["stok"][urun_ad] = taze_db["stok"].get(urun_ad, 0) + adet
                        if veritabanini_kaydet(taze_db): st.success("✅ Envantere Eklendi!"); st.rerun()

    st.subheader("📦 Mevcut Depo Stokları")
    if st.session_state["rol"] == "Servis": st.info("ℹ️ Servis Yetkisi: Stok bilgilerini sadece görüntüleyebilirsiniz.")
    
    stok_k = {k: [] for k in KATEGORILER}
    stok_k["Diğer"] = []
    if db.get("stok"):
        for u_ad, a in db["stok"].items():
            if a > 0:
                detay = db["urunler"].get(u_ad, {})
                kat = detay.get("Kategori", "Diğer")
                stok_k.setdefault(kat, []).append({"Kategori": kat, "Marka": detay.get("Marka", "-"), "Seri": detay.get("Seri", "-"), "Model": detay.get("Model Kodu", u_ad), "Adet": a})
        
        html_t = ""
        st_var = False
        
        gosterilecek_katlar = list(dict.fromkeys(KATEGORILER + ["Diğer"]))
        
        for k in gosterilecek_katlar:
            urunler = stok_k.get(k, [])
            if urunler:
                st_var = True
                st.markdown(f"#### 🔹 {k} Stoğu")
                st.dataframe(pd.DataFrame(urunler), use_container_width=True, hide_index=True)
                html_t += f"<h3>{k}</h3><table border='1' style='width:100%; border-collapse:collapse;'><tr><th>Kategori</th><th>Marka</th><th>Seri</th><th>Model</th><th>Adet</th></tr>"
                for u in urunler: html_t += f"<tr><td>{u['Kategori']}</td><td>{u['Marka']}</td><td>{u['Seri']}</td><td>{u['Model']}</td><td><b>{u['Adet']}</b></td></tr>"
                html_t += "</table>"
        
        if st_var:
            trh = datetime.now().strftime("%d.%m.%Y")
            h_s = f"<html><body style='font-family:Arial;'><h1>AREA ENVANTER ({trh})</h1>{html_t}<script>window.onload=function(){{window.print();}}</script></body></html>"
            st.download_button("📥 Stok Raporunu İndir/Yazdır", data=h_s, file_name=f"Stok_{trh}.html", mime="text/html", use_container_width=True)

# --- 5. YÖNETİM PANELİ ---
elif secilen_sayfa == "📈 Yönetim Paneli":
    st.header("📈 Area Yönetim Paneli")
    # SENİN SEKME YAPIN TAMAMEN GERİ GELDİ VE T4 EKLENDİ
    t1, t2, t3, t4 = st.tabs(["📊 Satış Raporları", "🗑️ Veri Yönetimi", "👥 Kullanıcı Yönetimi", "🏷️ Kategori Yönetimi"])
    
    # SENİN YAZDIĞIN T1 KISMI (HİÇ DOKUNULMADI)
    with t1:
        tamam = [h for h in db["hareketler"] if h["durum"] == "Tamamlandı"]
        if tamam:
            df = pd.DataFrame(tamam)
            st.metric("💰 Toplam Ciro", f"{df['fiyat'].sum():,.2f} ₺")
            st.dataframe(df[["id", "tarih_cikis", "firma", "urun", "adet", "fiyat"]], use_container_width=True, hide_index=True)
            
    # SENİN YAZDIĞIN T2 KISMI
    with t2:
        if db["stok"]:
            sil = st.selectbox("Katalogdan Silinecek Ürün:", ["Seçiniz..."] + sorted(list(db["stok"].keys())))
            if sil != "Seçiniz..." and st.button("🚨 SİL", type="primary"):
                taze_db = veritabanini_yukle()
                if taze_db:
                    if sil in taze_db["stok"]: del taze_db["stok"][sil]
                    if sil in taze_db["urunler"]: del taze_db["urunler"][sil]
                    if veritabanini_kaydet(taze_db): st.success("Silindi!"); st.rerun()
                    
    # SENİN YAZDIĞIN T3 KISMI (SİLİNEN KISIM GERİ GETİRİLDİ, HİÇ DOKUNULMADI)
    with t3:
        kullanicilar = db.get("kullanicilar", {})
        st.dataframe(pd.DataFrame([{"Ad": k, "İsim": v["isim"], "Rol": v["rol"]} for k, v in kullanicilar.items()]), hide_index=True)
        with st.form("y_k_f"):
            c1, c2 = st.columns(2)
            n_k = c1.text_input("Kullanıcı Adı:").lower().strip()
            n_s = c2.text_input("Şifre:")
            n_i = st.text_input("Personel İsmi:")
            n_r = st.selectbox("Rol:", ["Depo", "Finans", "Servis", "Yönetici"])
            if st.form_submit_button("Ekle"):
                if n_k and n_s:
                    db["kullanicilar"][n_k] = {"sifre": n_s, "rol": n_r, "isim": n_i}
                    if veritabanini_kaydet(db): st.success("Eklendi!"); st.rerun()
        st.markdown("---")
        sec_k = st.selectbox("Düzenlenecek Personel:", list(kullanicilar.keys()))
        if sec_k:
            with st.form("guncelle_f"):
                p = kullanicilar[sec_k]
                y_i = st.text_input("Görünür İsim:", value=p["isim"])
                rllr = ["Depo", "Finans", "Servis", "Yönetici"]
                try: idx = rllr.index(p.get("rol", "Depo"))
                except: idx = 0
                y_r = st.selectbox("Rol:", rllr, index=idx)
                y_s = st.text_input("Şifre:", value=p["sifre"])
                if st.form_submit_button("Kaydet"):
                    db["kullanicilar"][sec_k] = {"isim": y_i, "rol": y_r, "sifre": y_s}
                    if veritabanini_kaydet(db): st.success("Güncellendi!"); st.rerun()

    # YENİ EKLENEN T4 KISMI
    with t4:
        st.subheader("🏷️ Kategori Yönetimi")
        mevcut_kategoriler = db.get("kategoriler", KATEGORILER)
        
        st.markdown("**Sistemde Kayıtlı Kategoriler:**")
        st.info(", ".join(mevcut_kategoriler))
        
        st.markdown("---")
        with st.form("kategori_ekle_form"):
            yeni_kat = st.text_input("Yeni Kategori Ekle (Örn: VRF Aksesuar):").strip()
            if st.form_submit_button("➕ Sisteme Ekle"):
                if yeni_kat and yeni_kat not in mevcut_kategoriler:
                    taze_db = veritabanini_yukle()
                    if taze_db:
                        taze_db["kategoriler"] = taze_db.get("kategoriler", mevcut_kategoriler) + [yeni_kat]
                        if veritabanini_kaydet(taze_db): st.success(f"'{yeni_kat}' başarıyla eklendi!"); st.rerun()
                elif yeni_kat in mevcut_kategoriler:
                    st.error("Bu kategori zaten mevcut!")
                    
        st.markdown("---")
        silinecek_kat = st.selectbox("Silinecek Kategori Seçin:", ["Seçiniz..."] + mevcut_kategoriler)
        if silinecek_kat != "Seçiniz..." and st.button("🚨 Seçili Kategoriyi Sil", type="primary"):
            if silinecek_kat == "Diğer":
                st.error("⚠️ 'Diğer' kategorisi sistemin düzgün çalışması için silinemez!")
            else:
                taze_db = veritabanini_yukle()
                if taze_db:
                    kats = taze_db.get("kategoriler", mevcut_kategoriler)
                    if silinecek_kat in kats:
                        kats.remove(silinecek_kat)
                        taze_db["kategoriler"] = kats
                        if veritabanini_kaydet(taze_db): st.success(f"'{silinecek_kat}' sistemden silindi!"); st.rerun()
