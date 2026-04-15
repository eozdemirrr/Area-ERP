import streamlit as st
import json
import os
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import tempfile
import webbrowser

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
            if "kullanicilar" not in data:
                data["kullanicilar"] = {
                    "depo": {"sifre": "1234", "rol": "Depo", "isim": "Depo Sorumlusu"},
                    "muhasebe": {"sifre": "1234", "rol": "Finans", "isim": "Finans Departmanı"},
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
            k_adi = st.text_input("👤 Kullanıcı Adı (Örn: admin, depo, muhasebe):").strip().lower()
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
# GİRİŞ YAPILDIKTAN SONRA ÇALIŞACAK ANA SİSTEM
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

# =====================================================================
# 1. DEPO YÖNETİM EKRANI
# =====================================================================
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
                    st.success(f"✅ Çıkış Başarılı! ({adet} Adet -> {firma}) Yönetici onayına iletildi.")
                    st.rerun()

    st.markdown("---")
    st.subheader("🕒 Son 3 Ayın Çıkış Kayıtları")
    cikislar = [h for h in db["hareketler"] if son_3_ayda_mi(h.get("tarih_cikis", "-"))]
    if cikislar:
        df_cikis = pd.DataFrame(cikislar)[["id", "tarih_cikis", "firma", "urun", "adet", "durum"]]
        df_cikis.columns = ["İşlem No", "Çıkış Tarihi", "Firma", "Ürün", "Adet", "Durum"]
        st.dataframe(df_cikis, use_container_width=True, hide_index=True)

# =====================================================================
# 2. YÖNETİCİ
# =====================================================================
elif secilen_sayfa == "💼 Yönetici":
    st.header("💼 Yönetici Onay Paneli")
    bekleyenler = [h for h in db["hareketler"] if h["durum"] == "Fiyat Bekliyor"]
    if not bekleyenler: st.success("Tebrikler, şu an onayınızı bekleyen bir işlem yok.")
    else:
        for islem in bekleyenler:
            yapan = islem.get("islem_yapan", "Bilinmiyor")
            with st.expander(f"🔴 {islem['firma']} | Çıkış: {islem['tarih_cikis']} (Çıkan: {yapan})", expanded=True):
                st.write(f"**Ürün Detayı:** {islem['urun']} ({islem['adet']} Adet)")
                col_f1, col_f2 = st.columns([2, 1])
                with col_f1:
                    with st.form(f"fiyat_form_{islem['id']}"):
                        yeni_fiyat = st.number_input("Toplam Satış Bedeli (₺):", min_value=0.0, step=500.0)
                        if st.form_submit_button("💰 Bedeli Onayla ve Finansa Aktar"):
                            islem["fiyat"] = yeni_fiyat
                            islem["tarih_onay"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S") 
                            islem["durum"] = "Fatura Bekliyor"
                            veritabanini_kaydet(db); st.rerun()
                with col_f2:
                    st.write(""); st.write("")
                    if st.button(f"❌ İPTAL ET / STOĞA İADE", key=f"del_{islem['id']}", use_container_width=True):
                        db["stok"][islem["urun"]] += islem["adet"]
                        db["hareketler"] = [h for h in db["hareketler"] if h["id"] != islem["id"]]
                        veritabanini_kaydet(db); st.warning("İptal edildi ve stoğa döndü."); st.rerun()

    st.markdown("---")
    st.subheader("🕒 Son 3 Ayda Onaylanan İşlemler")
    onaylananlar = [h for h in db["hareketler"] if h["durum"] in ["Fatura Bekliyor", "Tamamlandı"] and son_3_ayda_mi(h.get("tarih_onay", "-"))]
    if onaylananlar:
        df_onay = pd.DataFrame(onaylananlar)[["id", "tarih_onay", "firma", "urun", "fiyat", "durum"]]
        df_onay.columns = ["İşlem No", "Onay Tarihi", "Firma", "Ürün", "Belirlenen Tutar (₺)", "Güncel Durum"]
        st.dataframe(df_onay, use_container_width=True, hide_index=True)

# =====================================================================
# 3. FİNANS VE MUHASEBE
# =====================================================================
elif secilen_sayfa == "🧾 Finans & Muhasebe":
    st.header("🧾 Finans ve Fatura Kesim Paneli")
    
    # Bekleyen Faturalar Kısmı
    bekleyenler = [h for h in db["hareketler"] if h["durum"] == "Fatura Bekliyor"]
    if not bekleyenler: st.success("Harika! Kesilmeyi bekleyen fatura bulunmuyor.")
    else:
        for islem in bekleyenler:
            st.markdown(f"### 🔵 {islem['firma']}")
            st.write(f"**Ürün:** {islem['urun']} | **Bedel:** {islem['fiyat']:,.2f} ₺")
            st.write(f"**Yönetici Onay Saati:** {islem.get('tarih_onay', '-')}")
            if st.button(f"✅ Faturası Kesildi (ID: {islem['id']})", use_container_width=True):
                islem["durum"] = "Tamamlandı"
                islem["tarih_fatura"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S") 
                veritabanini_kaydet(db); st.rerun()
            st.markdown("---")

    # Son 3 Ayda Kesilen Faturalar Kısmı (YENİ EKLENDİ)
    st.markdown("---")
    st.subheader("🕒 Son 3 Ayda Kesilen Faturalar")
    kesilenler = [h for h in db["hareketler"] if h["durum"] == "Tamamlandı" and son_3_ayda_mi(h.get("tarih_fatura", "-"))]
    if kesilenler:
        df_fatura = pd.DataFrame(kesilenler)[["id", "tarih_fatura", "firma", "urun", "fiyat"]]
        df_fatura.columns = ["İşlem No", "Fatura Tarihi", "Firma", "Ürün", "Tahsil Edilen Tutar (₺)"]
        st.dataframe(df_fatura, use_container_width=True, hide_index=True)
    else:
        st.info("Son 3 ayda faturası kesilen işlem bulunmuyor.")

# =====================================================================
# 4. GENEL STOK ENVANTERİ
# =====================================================================
elif secilen_sayfa == "📊 Genel Stok Envanteri":
    if st.session_state["rol"] in ["Yönetici", "Depo"]:
        st.subheader("➕ Yeni Cihaz / Ürün Girişi")
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
        st.markdown("---")
        
    st.subheader("📦 Mevcut Depo Stokları (Kategori Bazlı)")
    st.info("ℹ️ Servis Yetkisi: Stok bilgilerini sadece görüntüleyebilirsiniz.") if st.session_state["rol"] == "Servis" else None
    
    stok_kategorize = {k: [] for k in KATEGORILER}
    stok_kategorize["Diğer/Tanımsız"] = [] 
    
    if db.get("stok"):
        for urun_ad, adet in db["stok"].items():
            if adet > 0:
                detay = db["urunler"].get(urun_ad, {})
                kat = detay.get("Kategori", "Diğer/Tanımsız")
                if kat == "Duvar Split": kat = "Duvar Tipi Split"
                if kat == "Ticari Split": kat = "Ticari Tip Split"
                if kat not in stok_kategorize: stok_kategorize[kat] = []
                stok_kategorize[kat].append({"Marka": detay.get("Marka", "-"), "Seri": detay.get("Seri", "-"), "Model Kodu": detay.get("Model Kodu", urun_ad), "Adet": adet})
        
        html_stok_tablolari = "" 
        stok_var_mi = False
        for kat in KATEGORILER + ["Diğer/Tanımsız"]:
            urunler = stok_kategorize.get(kat, [])
            if urunler:
                stok_var_mi = True
                st.markdown(f"#### 🔹 {kat} Stoğu")
                st.dataframe(pd.DataFrame(urunler), use_container_width=True, hide_index=True)
                html_stok_tablolari += f"<h3 style='color:#2980b9;'>🔹 {kat} Stoğu</h3><table><tr><th>Marka</th><th>Seri</th><th>Model Kodu</th><th>Adet</th></tr>"
                for u in urunler: html_stok_tablolari += f"<tr><td>{u['Marka']}</td><td>{u['Seri']}</td><td>{u['Model Kodu']}</td><td><b>{u['Adet']}</b></td></tr>"
                html_stok_tablolari += "</table>"
        
        if stok_var_mi:
            if st.button("🖨️ Stok Listesini Yazdır (HTML)"):
                html = f"<html><head><meta charset='utf-8'><style>body {{ font-family: Arial; padding: 20px; }} table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }} th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }} th {{ background: #34495e; color: white; }} .btn {{ background: #27ae60; color: white; padding: 12px; border: none; cursor: pointer; }} @media print {{ .btn {{ display: none; }} }}</style></head><body><button class='btn' onclick='window.print()'>Yazdır</button><h1>AREA ENVANTER RAPORU</h1>{html_stok_tablolari}</body></html>"
                p = os.path.join(tempfile.gettempdir(), "Area_Stok_Raporu.html")
                with open(p, "w", encoding="utf-8") as f: f.write(html)
                webbrowser.open("file://" + p)
        else: st.info("Depo tamamen boş.")

# =====================================================================
# 5. YÖNETİM PANELİ (KOKPİT + KULLANICI YÖNETİMİ)
# =====================================================================
elif secilen_sayfa == "📈 Yönetim Paneli":
    st.header("📈 Area Yönetim Paneli")
    
    tab1, tab2, tab3 = st.tabs(["📊 Satış & Ciro Raporları", "🗑️ Veri / Hata Yönetimi", "👥 Kullanıcı Yönetimi"])
    
    # ---------------- TAB 1: RAPORLAR ----------------
    with tab1:
        tamamlanan_isler = [h for h in db["hareketler"] if h["durum"] == "Tamamlandı"]
        if tamamlanan_isler:
            df_tamam = pd.DataFrame(tamamlanan_isler)
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Toplam Gerçekleşen Ciro", f"{df_tamam['fiyat'].sum():,.2f} ₺")
            c2.metric("📦 Toplam Satılan Cihaz", f"{df_tamam['adet'].sum()} Adet")
            c3.metric("🤝 Toplam Başarılı İşlem", f"{len(df_tamam)} Kez")
            
            st.markdown("---")
            c4, c5 = st.columns(2)
            with c4:
                st.markdown("**🏆 İlk 3 Firma**")
                st.dataframe(df_tamam.groupby("firma")["fiyat"].sum().nlargest(3).reset_index().rename(columns={"firma":"Firma","fiyat":"Ciro"}), use_container_width=True, hide_index=True)
            with c5:
                st.markdown("**🏆 İlk 3 Ürün**")
                st.dataframe(df_tamam.groupby("urun")["adet"].sum().nlargest(3).reset_index().rename(columns={"urun":"Ürün","adet":"Adet"}), use_container_width=True, hide_index=True)
                
            st.markdown("---")
            st.subheader("🔎 Detaylı Rapor")
            f_firma, f_urun = st.columns(2)
            secilen_firma = f_firma.selectbox("Firma Filtresi:", ["Tümü"] + sorted(list(df_tamam["firma"].unique())))
            secilen_urun = f_urun.selectbox("Ürün Filtresi:", ["Tümü"] + sorted(list(df_tamam["urun"].unique())))
            
            df_rapor = df_tamam.copy()
            if secilen_firma != "Tümü": df_rapor = df_rapor[df_rapor["firma"] == secilen_firma]
            if secilen_urun != "Tümü": df_rapor = df_rapor[df_rapor["urun"] == secilen_urun]
            
            st.dataframe(df_rapor[["id", "tarih_cikis", "firma", "urun", "adet", "fiyat"]], use_container_width=True, hide_index=True)
            
            if st.button("🖨️ Raporu Yazdır (HTML)"):
                html = """<html><head><meta charset='utf-8'><style>body { font-family: Arial; padding: 20px;} table { width: 100%; border-collapse: collapse; } th, td { border: 1px solid #ccc; padding: 8px; text-align: left;} th { background: #34495e; color: white; } .btn { background: #2980b9; color: white; padding: 12px; border: none; cursor: pointer; } @media print { .btn { display: none; } }</style></head><body><button class='btn' onclick='window.print()'>Yazdır</button><h1>SATIŞ RAPORU</h1><table><tr><th>No</th><th>Tarih</th><th>Firma</th><th>Ürün</th><th>Adet</th><th>Ciro (₺)</th></tr>"""
                for idx, row in df_rapor.iterrows(): html += f"<tr><td>{row['id']}</td><td>{row['tarih_cikis']}</td><td>{row['firma']}</td><td>{row['urun']}</td><td>{row['adet']}</td><td>{row['fiyat']:,.2f}</td></tr>"
                html += "</table></body></html>"
                p = os.path.join(tempfile.gettempdir(), "Satis.html")
                with open(p, "w", encoding="utf-8") as f: f.write(html)
                webbrowser.open("file://" + p)
        else:
            st.warning("⚠️ Henüz faturalandırılmış işlem yok.")

    # ---------------- TAB 2: SİLME YÖNETİMİ ----------------
    with tab2:
        st.subheader("🗑️ Test / Hatalı Kayıt (İşlem) Silme")
        if db["hareketler"]:
            sil_secim = st.selectbox("İptal Edilecek İşlemi Seçin:", ["Seçiniz..."] + [f"{h['id']} - {h['firma']} ({h['durum']})" for h in db["hareketler"]])
            if sil_secim != "Seçiniz..." and st.button("🚨 Seçili İşlemi Kalıcı Olarak Sil", type="primary"):
                sec_id = int(sil_secim.split(" - ")[0])
                idx = next((i for i, d in enumerate(db["hareketler"]) if d["id"] == sec_id), None)
                if idx is not None:
                    db["stok"][db["hareketler"][idx]["urun"]] += db["hareketler"][idx]["adet"] 
                    db["hareketler"].pop(idx) 
                    veritabanini_kaydet(db); st.success("İşlem silindi ve ürünler stoğa döndü!"); st.rerun()
        else: st.info("Sistemde silinecek hareket/işlem kaydı yok.")
        
        st.markdown("---")
        
        st.subheader("🧹 Ürün Katalogdan Tamamen Silme")
        st.info("Deneme amacıyla eklediğiniz veya artık kullanmadığınız ürünleri sistemden kalıcı olarak temizleyebilirsiniz.")
        if db["stok"]:
            silinecek_urun = st.selectbox("Katalogdan Silinecek Ürünü Seçin:", ["Seçiniz..."] + sorted(list(db["stok"].keys())))
            
            if silinecek_urun != "Seçiniz...":
                if st.button("🚨 Seçili Ürünü Katalogdan ve Stoktan Sil", type="primary"):
                    if silinecek_urun in db["stok"]:
                        del db["stok"][silinecek_urun]
                    if silinecek_urun in db["urunler"]:
                        del db["urunler"][silinecek_urun]
                    veritabanini_kaydet(db)
                    st.success(f"✅ {silinecek_urun} sistemden tamamen silindi!")
                    st.rerun()
        else:
            st.write("Sistemde silinecek hiçbir ürün yok.")

    # ---------------- TAB 3: KULLANICI YÖNETİMİ ----------------
    with tab3:
        st.subheader("👥 Kullanıcı (Personel) Yönetimi")
        kullanicilar = db.get("kullanicilar", {})
        df_kullanici = pd.DataFrame([{"Kullanıcı Adı": k, "Görünür İsim": v["isim"], "Yetki / Rol": v["rol"]} for k, v in kullanicilar.items()])
        st.dataframe(df_kullanici, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("**➕ Yeni Kullanıcı Ekle**")
        with st.form("yeni_kullanici_form"):
            c_kadi, c_sifre = st.columns(2)
            yeni_kadi = c_kadi.text_input("Kullanıcı Adı (Boşluksuz, küçük harf):").strip().lower()
            yeni_sifre = c_sifre.text_input("Şifre:")
            c_isim, c_rol = st.columns(2)
            yeni_isim = c_isim.text_input("Personel İsmi:")
            yeni_rol = c_rol.selectbox("Yetki Seviyesi:", ["Depo", "Finans", "Servis", "Yönetici"])
            
            if st.form_submit_button("Sisteme Ekle"):
                if yeni_kadi == "" or yeni_sifre == "": st.error("Kullanıcı adı ve şifre boş bırakılamaz!")
                elif " " in yeni_kadi: st.error("Kullanıcı adında boşluk olamaz!")
                elif yeni_kadi in kullanicilar: st.error("Bu kullanıcı adı zaten sistemde var!")
                else:
                    db["kullanicilar"][yeni_kadi] = {"sifre": yeni_sifre, "rol": yeni_rol, "isim": yeni_isim}
                    veritabanini_kaydet(db); st.success(f"{yeni_isim} sisteme eklendi!"); st.rerun()
                    
        st.markdown("---")
        
       st.markdown("**⚙️ Personel Bilgilerini Güncelle**")
        secilen_kullanici = st.selectbox("Düzenlenecek Personeli Seç:", list(kullanicilar.keys()))
        if secilen_kullanici:
            with st.form("guncelle_pers_form"):
                p_verisi = kullanicilar[secilen_kullanici]
                yeni_isim = st.text_input("Görünür İsim:", value=p_verisi["isim"])
                
                # --- BURASI KRİTİK: Hata önleyici yapı ---
                roller = ["Depo", "Finans", "Servis", "Yönetici"]
                mevcut_rol = p_verisi.get("rol", "Depo") # Rol yoksa Depo say
                
                # Eğer veritabanındaki rol listede yoksa hata verme, varsayılan olarak ilkini seç
                try:
                    rol_index = roller.index(mevcut_rol)
                except ValueError:
                    rol_index = 0 
                
                yeni_rol = st.selectbox("Sistem Yetkisi:", roller, index=rol_index)
                # ---------------------------------------
                
                yeni_sifre = st.text_input("Giriş Şifresi:", value=p_verisi["sifre"])
                
                if st.form_submit_button("🔄 Bilgileri Kaydet"):
                    if yeni_sifre == "" or yeni_isim == "":
                        st.error("İsim ve Şifre alanları boş bırakılamaz!")
                    else:
                        db["kullanicilar"][secilen_kullanici]["isim"] = yeni_isim
                        db["kullanicilar"][secilen_kullanici]["rol"] = yeni_rol
                        db["kullanicilar"][secilen_kullanici]["sifre"] = yeni_sifre
                        veritabanini_kaydet(db)
                        st.success(f"✅ {secilen_kullanici} kullanıcısının bilgileri başarıyla güncellendi!")
                        st.rerun()
