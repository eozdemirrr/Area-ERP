import streamlit as st
import json
import os
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import tempfile

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Area Kurumsal Yönetim", layout="wide", page_icon="🏢")

# --- KULLANICI YETKİLENDİRME (LOGIN) SİSTEMİ ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["kullanici"] = ""
    st.session_state["rol"] = ""
    st.session_state["isim"] = ""

# --- BULUT VERİTABANI İŞLEMLERİ (FIREBASE) ---
FIREBASE_URL = "https://areaerp-default-rtdb.europe-west1.firebasedatabase.app/area_db.json"

def veritabanini_yukle():
    try:
        cevap = requests.get(FIREBASE_URL)
        if cevap.status_code == 200:
            data = cevap.json()
            if data is None: data = {}
            
            tamir_edildi = False
            if "urunler" not in data: data["urunler"] = {}; tamir_edildi = True
            if "stok" not in data: data["stok"] = {}; tamir_edildi = True
            if "hareketler" not in data: data["hareketler"] = []; tamir_edildi = True
            if "id_sayaci" not in data: data["id_sayaci"] = 1; tamir_edildi = True
            
            # --- VARSAYILAN KULLANICILAR ---
            if "kullanicilar" not in data:
                data["kullanicilar"] = {
                    "depo": {"sifre": "1234", "rol": "Depo", "isim": "Depo Sorumlusu"},
                    "muhasebe": {"sifre": "1234", "rol": "Finans", "isim": "Finans Departmanı"},
                    "servis": {"sifre": "1234", "rol": "Servis", "isim": "Servis Personeli"},
                    "admin": {"sifre": "admin123", "rol": "Yönetici", "isim": "Sistem Yöneticisi"}
                }
                tamir_edildi = True
            
            if tamir_edildi:
                veritabanini_kaydet(data)
            return data
    except:
        st.error("⚠️ Bulut veritabanına bağlanılamadı!")
        
    return {
        "stok": {}, "hareketler": [], "urunler": {}, "id_sayaci": 1,
        "kullanicilar": {
            "depo": {"sifre": "1234", "rol": "Depo", "isim": "Depo Sorumlusu"},
            "muhasebe": {"sifre": "1234", "rol": "Finans", "isim": "Finans Departmanı"},
            "servis": {"sifre": "1234", "rol": "Servis", "isim": "Servis Personeli"},
            "admin": {"sifre": "admin123", "rol": "Yönetici", "isim": "Sistem Yöneticisi"}
        }
    }

def veritabanini_kaydet(db):
    try:
        requests.put(FIREBASE_URL, json=db)
    except:
        st.error("❌ Değişiklikler buluta kaydedilemedi!")

db = veritabanini_yukle()

# --- YARDIMCI FONKSİYONLAR ---
def son_3_ayda_mi(tarih_str):
    if not tarih_str or tarih_str == "-": return False
    try:
        t = datetime.strptime(tarih_str, "%d.%m.%Y %H:%M:%S")
        return (datetime.now() - t).days <= 90
    except:
        return False

KATEGORILER = ["VRF Dış", "VRF İç", "Duvar Tipi Split", "Ticari Tip Split", "Yedek Parça", "Aksesuar", "Diğer"]

# =====================================================================
# LOBİ / GİRİŞ EKRANI
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
            giris_btn = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if giris_btn:
                kullanicilar_db = db.get("kullanicilar", {})
                if k_adi in kullanicilar_db and kullanicilar_db[k_adi]["sifre"] == sifre:
                    st.session_state["logged_in"] = True
                    st.session_state["kullanici"] = k_adi
                    st.session_state["rol"] = kullanicilar_db[k_adi]["rol"]
                    st.session_state["isim"] = kullanicilar_db[k_adi]["isim"]
                    st.rerun()
                else:
                    st.error("❌ Hatalı Kullanıcı Adı veya Şifre!")
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
st.sidebar.header("📁 Menü")

sayfalar = []
if st.session_state["rol"] == "Depo":
    sayfalar = ["📦 Depo Yönetim Ekranı", "📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Finans":
    sayfalar = ["🧾 Finans & Muhasebe", "📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Servis":
    sayfalar = ["📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Yönetici":
    sayfalar = ["📦 Depo Yönetim Ekranı", "💼 Yönetici", "🧾 Finans & Muhasebe", "📊 Genel Stok Envanteri", "📈 Yönetim Paneli"]

secilen_sayfa = st.sidebar.radio("Sayfa Seçin:", sayfalar)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Güvenli Çıkış Yap", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

# --- SAYFA İÇERİKLERİ ---

if secilen_sayfa == "📦 Depo Yönetim Ekranı":
    st.header("📦 Depo Çıkış Paneli")
    if not db["stok"]: st.warning("⚠️ Sistemde stok bulunmamaktadır.")
    else:
        with st.form("depo_cikis_formu", clear_on_submit=True):
            urun = st.selectbox("Çıkan Ürün (Cihaz):", sorted(list(db["stok"].keys())))
            firma = st.text_input("Gideceği Firma / Şantiye:")
            col3, col4 = st.columns(2)
            mevcut_stok = db["stok"].get(urun, 0)
            adet = col3.number_input(f"Miktar (Mevcut: {mevcut_stok})", min_value=1, max_value=mevcut_stok if mevcut_stok > 0 else 1, step=1)
            notlar = col4.text_input("Ek Notlar / İrsaliye No:")
            
            if st.form_submit_button("🚚 DEPODAN ÇIKIŞ YAP"):
                if firma.strip() == "": st.error("Lütfen Firma Adını Yazın!")
                else:
                    db["stok"][urun] -= adet
                    yeni_hareket = {
                        "id": db["id_sayaci"], "tarih_cikis": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                        "tarih_onay": "-", "tarih_fatura": "-", "urun": urun, "adet": adet,
                        "firma": firma.upper(), "notlar": notlar, "durum": "Fiyat Bekliyor", "fiyat": 0,
                        "islem_yapan": st.session_state["kullanici"] 
                    }
                    db["hareketler"].insert(0, yeni_hareket)
                    db["id_sayaci"] += 1
                    veritabanini_kaydet(db)
                    st.success(f"✅ Çıkış Başarılı! Yönetici onayına iletildi.")
                    st.rerun()

    st.markdown("---")
    st.subheader("🕒 Son 3 Ayın Çıkış Kayıtları")
    cikislar = [h for h in db["hareketler"] if son_3_ayda_mi(h.get("tarih_cikis", "-"))]
    if cikislar:
        df_cikis = pd.DataFrame(cikislar)[["id", "tarih_cikis", "firma", "urun", "adet", "durum"]]
        df_cikis.columns = ["İşlem No", "Çıkış Tarihi", "Firma", "Ürün", "Adet", "Durum"]
        st.dataframe(df_cikis, use_container_width=True, hide_index=True)

elif secilen_sayfa == "💼 Yönetici":
    st.header("💼 Yönetici Onay Paneli")
    bekleyenler = [h for h in db["hareketler"] if h["durum"] == "Fiyat Bekliyor"]
    if not bekleyenler: st.success("Onay bekleyen işlem yok.")
    else:
        for islem in bekleyenler:
            with st.expander(f"🔴 {islem['firma']} | {islem['tarih_cikis']}", expanded=True):
                st.write(f"**Ürün:** {islem['urun']} ({islem['adet']} Adet)")
                with st.form(f"fiyat_form_{islem['id']}"):
                    yeni_fiyat = st.number_input("Toplam Satış Bedeli (₺):", min_value=0.0, step=500.0)
                    if st.form_submit_button("💰 Onayla"):
                        islem["fiyat"] = yeni_fiyat
                        islem["tarih_onay"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S") 
                        islem["durum"] = "Fatura Bekliyor"
                        veritabanini_kaydet(db); st.rerun()

elif secilen_sayfa == "🧾 Finans & Muhasebe":
    st.header("🧾 Fatura Kesim Paneli")
    bekleyenler = [h for h in db["hareketler"] if h["durum"] == "Fatura Bekliyor"]
    if not bekleyenler: st.success("Bekleyen fatura yok.")
    else:
        for islem in bekleyenler:
            st.markdown(f"### 🔵 {islem['firma']}")
            st.write(f"**Ürün:** {islem['urun']} | **Bedel:** {islem['fiyat']:,.2f} ₺")
            if st.button(f"✅ Faturası Kesildi (ID: {islem['id']})", use_container_width=True):
                islem["durum"] = "Tamamlandı"
                islem["tarih_fatura"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S") 
                veritabanini_kaydet(db); st.rerun()

elif secilen_sayfa == "📊 Genel Stok Envanteri":
    if st.session_state["rol"] in ["Yönetici", "Depo"]:
        st.subheader("➕ Yeni Cihaz Girişi")
        with st.form("yeni_mal_formu", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            marka = c1.text_input("Marka:").upper()
            seri = c2.text_input("Seri:").upper()
            model = c3.text_input("Model Kodu:").upper()
            cesit = c4.selectbox("Kategori:", KATEGORILER)
            adet = st.number_input("Adet:", min_value=1)
            if st.form_submit_button("📥 Envantere Ekle"):
                urun_ad = f"{marka} {seri} - {model} ({cesit})"
                db["urunler"][urun_ad] = {"Marka": marka, "Seri": seri, "Model Kodu": model, "Kategori": cesit}
                db["stok"][urun_ad] = db["stok"].get(urun_ad, 0) + adet
                veritabanini_kaydet(db); st.rerun()
    
    if st.session_state["rol"] == "Servis":
        st.info("ℹ️ Servis Yetkisi: Stok bilgilerini sadece görüntüleyebilirsiniz.")

    stok_kategorize = {k: [] for k in KATEGORILER}
    stok_kategorize["Diğer"] = [] 
    
    if db.get("stok"):
        for urun_ad, adet in db["stok"].items():
            if adet > 0:
                detay = db["urunler"].get(urun_ad, {})
                kat = detay.get("Kategori", "Diğer")
                stok_kategorize.setdefault(kat, []).append({
                    "Kategori": kat,
                    "Marka": detay.get("Marka", "-"), 
                    "Seri": detay.get("Seri", "-"), 
                    "Model Kodu": detay.get("Model Kodu", urun_ad), 
                    "Adet": adet
                })
        
        html_tablo = ""
        stok_var = False
        for kat in KATEGORILER + ["Diğer"]:
            urunler = stok_kategorize.get(kat, [])
            if urunler:
                stok_var = True
                st.markdown(f"#### 🔹 {kat} Stoğu")
                st.dataframe(pd.DataFrame(urunler), use_container_width=True, hide_index=True)
                html_tablo += f"<h3>{kat}</h3><table border='1' style='width:100%; border-collapse: collapse;'><tr><th>Kategori</th><th>Marka</th><th>Seri</th><th>Model</th><th>Adet</th></tr>"
                for u in urunler: html_tablo += f"<tr><td>{u['Kategori']}</td><td>{u['Marka']}</td><td>{u['Seri']}</td><td>{u['Model Kodu']}</td><td><b>{u['Adet']}</b></td></tr>"
                html_tablo += "</table>"

        if stok_var:
            tarih = datetime.now().strftime("%d.%m.%Y")
            html_sablon = f"<html><body style='font-family: Arial;'><h1>AREA ENVANTER RAPORU ({tarih})</h1>{html_tablo}<script>window.onload = function() {{ window.print(); }}</script></body></html>"
            st.download_button("📥 Stok Raporunu İndir/Yazdır", data=html_sablon, file_name=f"Stok_{tarih}.html", mime="text/html", use_container_width=True)

elif secilen_sayfa == "📈 Yönetim Paneli":
    st.header("📈 Yönetim Paneli")
    t1, t2, t3 = st.tabs(["📊 Raporlar", "🗑️ Veri Yönetimi", "👥 Kullanıcılar"])
    
    with t1:
        tamam = [h for h in db["hareketler"] if h["durum"] == "Tamamlandı"]
        if tamam:
            df = pd.DataFrame(tamam)
            st.metric("💰 Toplam Ciro", f"{df['fiyat'].sum():,.2f} ₺")
            st.dataframe(df[["id", "tarih_cikis", "firma", "urun", "adet", "fiyat"]], use_container_width=True, hide_index=True)
        else: st.warning("İşlem yok.")

    with t2:
        if db["stok"]:
            sil = st.selectbox("Katalogdan Silinecek Ürün:", ["Seçiniz..."] + sorted(list(db["stok"].keys())))
            if sil != "Seçiniz..." and st.button("🚨 SİL", type="primary"):
                if sil in db["stok"]: del db["stok"][sil]
                if sil in db["urunler"]: del db["urunler"][sil]
                veritabanini_kaydet(db); st.rerun()

    with t3:
        kullanicilar = db.get("kullanicilar", {})
        st.dataframe(pd.DataFrame([{"Ad": k, "İsim": v["isim"], "Rol": v["rol"]} for k, v in kullanicilar.items()]), hide_index=True)
        with st.form("yeni_kullanici"):
            k1, k2 = st.columns(2)
            n_kadi = k1.text_input("Kullanıcı Adı:").lower().strip()
            n_sifre = k2.text_input("Şifre:")
            n_isim = st.text_input("İsim:")
            n_rol = st.selectbox("Rol:", ["Depo", "Finans", "Servis", "Yönetici"])
            if st.form_submit_button("Ekle"):
                if n_kadi and n_sifre:
                    db["kullanicilar"][n_kadi] = {"sifre": n_sifre, "rol": n_rol, "isim": n_isim}
                    veritabanini_kaydet(db); st.success("Eklendi!"); st.rerun()

        st.markdown("---")
        st.markdown("**⚙️ Güncelle**")
        sec_k = st.selectbox("Düzenlenecek Personel:", list(kullanicilar.keys()))
        if sec_k:
            with st.form("guncelle_form"):
                p = kullanicilar[sec_k]
                y_isim = st.text_input("İsim:", value=p["isim"])
                roller = ["Depo", "Finans", "Servis", "Yönetici"]
                try: idx = roller.index(p.get("rol", "Depo"))
                except ValueError: idx = 0
                y_rol = st.selectbox("Rol:", roller, index=idx)
                y_sifre = st.text_input("Şifre:", value=p["sifre"])
                if st.form_submit_button("Kaydet"):
                    db["kullanicilar"][sec_k] = {"isim": y_isim, "rol": y_rol, "sifre": y_sifre}
                    veritabanini_kaydet(db); st.success("Güncellendi!"); st.rerun()
