import streamlit as st
import json
import os
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import tempfile
import re

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Area Kurumsal Yönetim", layout="wide", page_icon="🏢")

# --- KULLANICI YETKİLENDİRME ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["kullanici"] = ""
    st.session_state["rol"] = ""
    st.session_state["isim"] = ""

# --- TÜRKİYE SAATİ AYARI (UTC +3) ---
def simdi():
    return datetime.utcnow() + timedelta(hours=3)

# 🔥🔥 KRİTİK GÜVENLİK AYARI (VIP KART) 🔥🔥
FIREBASE_GIZLI_ANAHTARI = "rMPqxkiWV0kBCUig343NLrgxMbElWeEmMJkmNJ2j"

# --- BULUT VERİTABANI İŞLEMLERİ ---
FIREBASE_URL = "https://areaerp-default-rtdb.europe-west1.firebasedatabase.app/area_db.json"

def veritabanini_yukle():
    try:
        hedef_url = f"{FIREBASE_URL}?auth={FIREBASE_GIZLI_ANAHTARI}"
        cevap = requests.get(hedef_url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
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
                    "satis": {"sifre": "1234", "rol": "Satış", "isim": "Satış Temsilcisi"},
                    "depo": {"sifre": "1234", "rol": "Depo", "isim": "Depo Sorumlusu"},
                    "muhasebe": {"sifre": "1234", "rol": "Finans", "isim": "Finans Departmanı"},
                    "servis": {"sifre": "1234", "rol": "Servis", "isim": "Servis Personeli"},
                    "admin": {"sifre": "admin123", "rol": "Yönetici", "isim": "Sistem Yöneticisi"}
                }
                tamir_edildi = True
            
            if "kategoriler" not in data:
                data["kategoriler"] = ["VRF Dış", "VRF İç", "Multi Dış", "Multi İç", "Duvar Tipi Split", "Ticari Tip Split", "Yedek Parça", "Aksesuar", "Diğer"]
                tamir_edildi = True

            if tamir_edildi: veritabanini_kaydet(data)
            return data
        else:
            st.error(f"⚠️ Güvenlik Bağlantı Hatası: Lütfen Gizli Anahtarın doğru olduğunu kontrol edin. (Hata: {cevap.status_code})")
    except Exception as e:
        st.error(f"⚠️ Bulut veritabanına bağlanılamadı! Detay: {e}")
    return None

def veritabanini_kaydet(db):
    if db is None: return False
    try:
        hedef_url = f"{FIREBASE_URL}?auth={FIREBASE_GIZLI_ANAHTARI}"
        cevap = requests.put(hedef_url, json=db)
        return cevap.status_code == 200
    except:
        return False

def isim_temizle(metin):
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
        return (simdi() - t).days <= 90
    except: return False

db = veritabanini_yukle()
if db is None:
    st.error("❌ Veritabanı bağlantısı koptu! Lütfen sayfayı yenileyin veya internet bağlantınızı kontrol edin.")
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
# ANA SİSTEM MENÜ YÖNETİMİ
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

if st.session_state["rol"] == "Satış": sayfalar = ["📝 Sipariş Ekranı", "📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Depo": sayfalar = ["📦 Depo Yönetim Ekranı", "📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Finans": sayfalar = ["🧾 Finans & Muhasebe", "📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Servis": sayfalar = ["📊 Genel Stok Envanteri"]
elif st.session_state["rol"] == "Yönetici": sayfalar = ["📝 Sipariş Ekranı", "📦 Depo Yönetim Ekranı", "💼 Yönetici", "🧾 Finans & Muhasebe", "📊 Genel Stok Envanteri", "📈 Yönetim Paneli"]

secilen_sayfa = st.sidebar.radio("📁 Menü", sayfalar)
if st.sidebar.button("🚪 Güvenli Çıkış Yap", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

# --- 0. SİPARİŞ EKRANI (AKILLI FİLTRELEME VE SEVK ADRESİ) ---
if secilen_sayfa == "📝 Sipariş Ekranı":
    st.header("📝 Yeni Satış & Sipariş Oluşturma Paneli")
    st.info("💡 Buradan açtığınız siparişler direkt olarak Depo personelinin önüne düşecektir.")
    
    if "sepet" not in st.session_state:
        st.session_state["sepet"] = []

    if not db["stok"]: st.warning("⚠️ Sistemde eklenecek stok bulunmamaktadır.")
    else:
        st.subheader("🔍 1. Müşteri Sepetine Ürün Ekle (Akıllı Filtre)")
        
        # --- AKILLI FİLTRELEME BAŞLANGICI ---
        col_kat, col_marka = st.columns(2)
        secilen_kat = col_kat.selectbox("Kategori Seçiniz:", KATEGORILER)
        
        # Sadece seçilen kategoriye ait ürünleri bul
        kat_urunleri = [u_ad for u_ad, detay in db["urunler"].items() if detay.get("Kategori") == secilen_kat]
        
        if not kat_urunleri:
            st.warning("Bu kategoride sisteme kayıtlı ürün bulunmuyor.")
        else:
            # Seçilen kategoriye ait markaları çıkar
            markalar = sorted(list(set([db["urunler"][u].get("Marka", "Diğer") for u in kat_urunleri])))
            secilen_marka = col_marka.selectbox("Marka Seçiniz:", markalar)
            
            # Kategori ve Markaya göre son model listesi
            son_modeller = [u for u in kat_urunleri if db["urunler"][u].get("Marka", "Diğer") == secilen_marka]
            
            if not son_modeller:
                st.warning("Bu markada ürün bulunmuyor.")
            else:
                col_mod, col_ad = st.columns([3, 1])
                urun_secim = col_mod.selectbox("Satılan Model (Cihaz):", sorted(son_modeller))
                mevcut = db["stok"].get(urun_secim, 0)
                
                # Adet seçimi
                adet = col_ad.number_input(f"Miktar (Depoda: {mevcut})", min_value=1, step=1, max_value=mevcut if mevcut > 0 else 1)
                
                if st.button("➕ Seçili Modeli Sepete Ekle", type="primary"):
                    if adet > mevcut: 
                        st.error(f"❌ Dikkat: Stok yetersiz! {urun_secim} için depoda {mevcut} adet görünüyor.")
                    else:
                        st.session_state["sepet"].append({"urun": urun_secim, "adet": adet})
                        st.success(f"✅ {adet} adet '{urun_secim}' sepete eklendi!")
                        st.rerun()
        # --- AKILLI FİLTRELEME SONU ---

        if st.session_state["sepet"]:
            st.markdown("---")
            st.subheader("📋 2. Siparişi Tamamla ve Depoya İlet")
            
            df_sepet = pd.DataFrame(st.session_state["sepet"])
            df_sepet.index += 1
            df_sepet.columns = ["Ürün", "Adet"]
            st.table(df_sepet)
            
            if st.button("🗑️ Sepeti Temizle"):
                st.session_state["sepet"] = []
                st.rerun()
                
            with st.form("siparis_tamamla_formu", clear_on_submit=True):
                firma = st.text_input("Siparişi Veren Firma / Şantiye:").upper().strip()
                sevk_adresi = st.text_area("📍 Sevk Adresi / Teslimat Noktası (Opsiyonel):", placeholder="Açık adres, ilçe, vb. girebilirsiniz...").strip()
                notlar = st.text_input("Depo İçin Ek Notlar / Teslimat Bilgisi:")
                
                if st.form_submit_button("🚀 SİPARİŞİ ONAYLA VE DEPOYA GÖNDER"):
                    if firma == "": 
                        st.error("Lütfen Firma Adını Yazın!")
                    else:
                        taze_db = veritabanini_yukle()
                        if taze_db:
                            zaman = simdi().strftime("%d.%m.%Y %H:%M:%S")
                            for item in st.session_state["sepet"]:
                                u = item["urun"]
                                a = item["adet"]
                                
                                taze_db["hareketler"].insert(0, {
                                    "id": taze_db["id_sayaci"], 
                                    "tarih_siparis": zaman, 
                                    "tarih_cikis": "-", 
                                    "tarih_onay": "-", 
                                    "tarih_fatura": "-", 
                                    "urun": u, 
                                    "adet": a, 
                                    "firma": firma, 
                                    "sevk_adresi": sevk_adresi, 
                                    "notlar": notlar, 
                                    "durum": "Depo Bekliyor", 
                                    "fiyat": 0, 
                                    "islem_yapan": st.session_state["kullanici"]
                                })
                                taze_db["id_sayaci"] += 1
                            
                            if veritabanini_kaydet(taze_db): 
                                st.session_state["sepet"] = []
                                st.success("✅ Sipariş Başarıyla Depo Ekranına İletildi!")
                                st.rerun()

# --- 1. DEPO YÖNETİM ---
elif secilen_sayfa == "📦 Depo Yönetim Ekranı":
    st.header("📦 Depo Çıkış & Hazırlık Paneli")
    st.info("Aşağıdaki listede Satış/Yönetici tarafından açılmış ve depodan çıkış yapması beklenen siparişler yer almaktadır.")
    
    bekleyen_siparisler = [h for h in db["hareketler"] if h.get("durum") == "Depo Bekliyor"]
    
    if not bekleyen_siparisler:
        st.success("🎉 Harika! Şu an depodan çıkışı bekleyen hiçbir sipariş yok.")
    else:
        gruplar = {}
        for islem in bekleyen_siparisler:
            firma = islem["firma"]
            if firma not in gruplar:
                gruplar[firma] = []
            gruplar[firma].append(islem)
            
        for firma, islemler in gruplar.items():
            st.markdown(f"### 🔵 Müşteri: {firma}")
            if islemler[0].get("sevk_adresi"):
                st.info(f"📍 **Sevk Adresi:** {islemler[0].get('sevk_adresi')}")
            if islemler[0].get("notlar"):
                st.caption(f"📝 **Ek Not:** {islemler[0].get('notlar')}")
                
            df_tablo = pd.DataFrame(islemler)[["id", "tarih_siparis", "urun", "adet"]]
            df_tablo.columns = ["İşlem No", "Sipariş Tarihi", "Hazırlanacak Ürün", "Adet"]
            st.table(df_tablo.set_index("İşlem No"))
            
            grup_idleri = [i["id"] for i in islemler]
            if st.button(f"🚀 {firma} SİPARİŞİNİ DEPODAN ÇIKART", key=f"btn_cikis_{firma}", use_container_width=True, type="primary"):
                taze_db = veritabanini_yukle()
                if taze_db:
                    zaman = simdi().strftime("%d.%m.%Y %H:%M:%S")
                    basarili = True
                    for h in taze_db["hareketler"]:
                        if h["id"] in grup_idleri:
                            u = h["urun"]
                            a = h["adet"]
                            
                            mevcut_stok = taze_db["stok"].get(u, 0)
                            if mevcut_stok >= a:
                                taze_db["stok"][u] = mevcut_stok - a
                                h["durum"] = "Fiyat Bekliyor"
                                h["tarih_cikis"] = zaman
                            else:
                                st.error(f"❌ Kritik Hata: {u} için depoda yeterli stok yok! (Mevcut: {mevcut_stok}, İstenen: {a})")
                                basarili = False
                                break
                    
                    if basarili and veritabanini_kaydet(taze_db): 
                        st.rerun()
            st.markdown("---")

    st.markdown("---")
    st.subheader("🕒 Son 3 Ayın Çıkış Kayıtları (Tamamlananlar)")
    cikislar = [h for h in db["hareketler"] if son_3_ayda_mi(h.get("tarih_cikis", "-")) and h.get("durum") != "Depo Bekliyor"]
    if cikislar:
        df_cikis = pd.DataFrame(cikislar)[["id", "tarih_cikis", "firma", "urun", "adet", "durum"]]
        df_cikis.columns = ["İşlem No", "Çıkış Tarihi", "Firma", "Ürün", "Adet", "Durum"]
        st.dataframe(df_cikis, use_container_width=True, hide_index=True)

# --- 2. YÖNETİCİ ---
elif secilen_sayfa == "💼 Yönetici":
    st.header("💼 Yönetici Onay Paneli")
    bekleyenler = [h for h in db["hareketler"] if h["durum"] == "Fiyat Bekliyor"]
    if not bekleyenler: st.success("Tebrikler, fiyat onayı bekleyen çıkış işlemi yok.")
    else:
        for islem in bekleyenler:
            with st.expander(f"🔴 {islem['firma']} | Çıkış: {islem['tarih_cikis']}", expanded=True):
                if islem.get('sevk_adresi'):
                    st.caption(f"📍 **Sevk Adresi:** {islem['sevk_adresi']}")
                
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
                                    taze_db["hareketler"][idx]["tarih_onay"] = simdi().strftime("%d.%m.%Y %H:%M:%S")
                                    
                                if veritabanini_kaydet(taze_db): st.rerun()

    st.markdown("---")
    st.subheader("🕒 Son 3 Ayda Onaylanan İşlemler")
    onaylananlar = [h for h in db["hareketler"] if h["durum"] in ["Fatura Bekliyor", "Tamamlandı"] and son_3_ayda_mi(h.get("tarih_onay", "-"))]
    if onaylananlar:
        df_onay = pd.DataFrame(onaylananlar)[["id", "tarih_onay", "firma", "urun", "adet", "fiyat", "durum"]]
        df_onay.columns = ["İşlem No", "Onay Tarihi", "Firma", "Ürün", "Adet", "Tutar (₺)", "Durum"]
        st.dataframe(df_onay, use_container_width=True, hide_index=True)

# --- 3. FİNANS ---
elif secilen_sayfa == "🧾 Finans & Muhasebe":
    st.header("🧾 Fatura Kesim Paneli")
    bekleyenler = [h for h in db["hareketler"] if h["durum"] == "Fatura Bekliyor"]
    if not bekleyenler: st.success("Harika! Kesilmeyi bekleyen fatura yok.")
    else:
        gruplar = {}
        for islem in bekleyenler:
            firma = islem["firma"]
            if firma not in gruplar:
                gruplar[firma] = []
            gruplar[firma].append(islem)
            
        for firma, islemler in gruplar.items():
            st.markdown(f"### 🔵 {firma}")
            df_tablo = pd.DataFrame(islemler)[["id", "tarih_cikis", "urun", "adet", "fiyat"]]
            df_tablo["fiyat"] = df_tablo["fiyat"].apply(lambda x: f"{x:,.2f} ₺")
            df_tablo.columns = ["İşlem No", "Çıkış Tarihi", "Ürün", "Adet", "Bedel"]
            
            st.table(df_tablo.set_index("İşlem No"))
            
            toplam_tutar = sum([i["fiyat"] for i in islemler])
            c1, c2 = st.columns([3, 1])
            c1.info(f"**💰 Toplam Fatura Bedeli:** {toplam_tutar:,.2f} ₺")
            
            grup_idleri = [i["id"] for i in islemler]
            if c2.button(f"✅ Faturasını Kes", key=f"btn_fat_{firma}", use_container_width=True):
                taze_db = veritabanini_yukle()
                if taze_db:
                    zaman = simdi().strftime("%d.%m.%Y %H:%M:%S")
                    for h in taze_db["hareketler"]:
                        if h["id"] in grup_idleri:
                            h["durum"] = "Tamamlandı"
                            h["tarih_fatura"] = zaman
                    if veritabanini_kaydet(taze_db): st.rerun()
            st.markdown("---")

    st.markdown("---")
    st.subheader("🕒 Son 3 Ayda Kesilen Faturalar")
    kesilenler = [h for h in db["hareketler"] if h["durum"] == "Tamamlandı" and son_3_ayda_mi(h.get("tarih_fatura", "-"))]
    if kesilenler:
        df_fatura = pd.DataFrame(kesilenler)[["id", "tarih_fatura", "firma", "urun", "adet", "fiyat"]]
        df_fatura.columns = ["İşlem No", "Fatura Tarihi", "Firma", "Ürün", "Adet", "Tutar (₺)"]
        st.dataframe(df_fatura, use_container_width=True, hide_index=True)

# --- 4. STOK ENVANTERİ ---
elif secilen_sayfa == "📊 Genel Stok Envanteri":
    if st.session_state["rol"] in ["Yönetici", "Depo", "Satış"]:
        st.subheader("➕ Yeni Cihaz / Ürün Girişi")
        
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
            trh = simdi().strftime("%d.%m.%Y")
            h_s = f"<html><body style='font-family:Arial;'><h1>AREA ENVANTER ({trh})</h1>{html_t}<script>window.onload=function(){{window.print();}}</script></body></html>"
            st.download_button("📥 Stok Raporunu İndir/Yazdır", data=h_s, file_name=f"Stok_{trh}.html", mime="text/html", use_container_width=True)

# --- 5. YÖNETİM PANELİ ---
elif secilen_sayfa == "📈 Yönetim Paneli":
    st.header("📈 Area Yönetim Paneli")
    t1, t2, t3, t4 = st.tabs(["📊 Satış Raporları", "🗑️ Veri Yönetimi", "👥 Kullanıcı Yönetimi", "🏷️ Kategori Yönetimi"])
    
    with t1:
        tamam = [h for h in db["hareketler"] if h["durum"] == "Tamamlandı"]
        if tamam:
            df = pd.DataFrame(tamam)
            st.metric("💰 Toplam Ciro", f"{df['fiyat'].sum():,.2f} ₺")
            st.dataframe(df[["id", "tarih_cikis", "firma", "urun", "adet", "fiyat"]], use_container_width=True, hide_index=True)
            
    with t2:
        st.subheader("📦 Katalogdan Ürün Sil")
        if db["stok"]:
            sil = st.selectbox("Katalogdan Silinecek Ürün:", ["Seçiniz..."] + sorted(list(db["stok"].keys())))
            if sil != "Seçiniz..." and st.button("🚨 ÜRÜNÜ SİL", type="primary"):
                taze_db = veritabanini_yukle()
                if taze_db:
                    if sil in taze_db["stok"]: del taze_db["stok"][sil]
                    if sil in taze_db["urunler"]: del taze_db["urunler"][sil]
                    if veritabanini_kaydet(taze_db): st.success("Silindi!"); st.rerun()

        st.markdown("---")
        st.subheader("🔙 Hatalı İşlem / Sipariş İptali")
        st.info("💡 İptal edilen işlem depodan çıkmış durumdaysa cihazlar otomatik olarak stoğa geri eklenir.")
        
        islem_secenekleri = ["Seçiniz..."]
        for h in db.get("hareketler", []):
            islem_secenekleri.append(f"ID: {h['id']} | {h['firma']} | {h['urun']} ({h['adet']} Adet) - {h['durum']}")
            
        silinecek_islem_str = st.selectbox("İptal Edilecek İşlemi Seçin:", islem_secenekleri)
        
        if silinecek_islem_str != "Seçiniz..." and st.button("🚨 İŞLEMİ İPTAL ET", type="primary"):
            secilen_id = int(silinecek_islem_str.split("|")[0].replace("ID:", "").strip())
            
            taze_db = veritabanini_yukle()
            if taze_db:
                idx_to_delete = None
                for i, h in enumerate(taze_db["hareketler"]):
                    if h["id"] == secilen_id:
                        idx_to_delete = i
                        break
                        
                if idx_to_delete is not None:
                    iptal_edilen = taze_db["hareketler"].pop(idx_to_delete)
                    i_urun = iptal_edilen["urun"]
                    i_adet = iptal_edilen["adet"]
                    i_durum = iptal_edilen.get("durum", "")
                    
                    if i_durum != "Depo Bekliyor":
                        taze_db["stok"][i_urun] = taze_db["stok"].get(i_urun, 0) + i_adet
                        mesaj = f"✅ İşlem (ID: {secilen_id}) silindi! {i_adet} adet '{i_urun}' depoya geri eklendi."
                    else:
                        mesaj = f"✅ Henüz depodan çıkmayan Sipariş (ID: {secilen_id}) başarıyla iptal edildi."
                    
                    if veritabanini_kaydet(taze_db): 
                        st.success(mesaj)
                        st.rerun()
                    
    with t3:
        kullanicilar = db.get("kullanicilar", {})
        st.dataframe(pd.DataFrame([{"Ad": k, "İsim": v["isim"], "Rol": v["rol"]} for k, v in kullanicilar.items()]), hide_index=True)
        with st.form("y_k_f"):
            c1, c2 = st.columns(2)
            n_k = c1.text_input("Kullanıcı Adı:").lower().strip()
            n_s = c2.text_input("Şifre:")
            n_i = st.text_input("Personel İsmi:")
            n_r = st.selectbox("Rol:", ["Satış", "Depo", "Finans", "Servis", "Yönetici"])
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
                rllr = ["Satış", "Depo", "Finans", "Servis", "Yönetici"]
                try: idx = rllr.index(p.get("rol", "Depo"))
                except: idx = 0
                y_r = st.selectbox("Rol:", rllr, index=idx)
                y_s = st.text_input("Şifre:", value=p["sifre"])
                if st.form_submit_button("Kaydet"):
                    db["kullanicilar"][sec_k] = {"isim": y_i, "rol": y_r, "sifre": y_s}
                    if veritabanini_kaydet(db): st.success("Güncellendi!"); st.rerun()

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
