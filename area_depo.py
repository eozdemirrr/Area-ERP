import streamlit as st
import json
import os
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
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

# 🔥 GİZLİ ANAHTAR (Bunu kendi Firebase anahtarınla doldur!)
FIREBASE_GIZLI_ANAHTARI = "rMPqxkiWV0kBCUig343NLrgxMbElWeEmMJkmNJ2j"
FIREBASE_URL = "https://areaerp-default-rtdb.europe-west1.firebasedatabase.app/area_db.json"

def veritabanini_yukle():
    try:
        hedef_url = f"{FIREBASE_URL}?auth={FIREBASE_GIZLI_ANAHTARI}"
        cevap = requests.get(hedef_url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
        if cevap.status_code == 200:
            data = cevap.json()
            if data is None: data = {}
            # ... (diğer kontrol blokları aynı kalıyor)
            return data
    except:
        st.error("⚠️ Veritabanı bağlantı hatası!")
    return None

def veritabanini_kaydet(db):
    if db is None: return False
    try:
        hedef_url = f"{FIREBASE_URL}?auth={FIREBASE_GIZLI_ANAHTARI}"
        cevap = requests.put(hedef_url, json=db)
        return cevap.status_code == 200
    except: return False

def isim_temizle(metin):
    yasakli = [".", "$", "#", "[", "]", "/"]
    metin = str(metin).strip()
    metin = re.sub(r'\s+', ' ', metin)
    for char in yasakli: metin = metin.replace(char, "-")
    return metin

def son_3_ayda_mi(tarih_str):
    if not tarih_str or tarih_str == "-": return False
    try:
        t = datetime.strptime(tarih_str, "%d.%m.%Y %H:%M:%S")
        return (simdi() - t).days <= 90
    except: return False

db = veritabanini_yukle()
KATEGORILER = db.get("kategoriler", ["VRF Dış", "VRF İç", "Multi Dış", "Multi İç", "Duvar Tipi Split", "Ticari Tip Split", "Yedek Parça", "Aksesuar", "Diğer"])

# =====================================================================
# ANA SİSTEM MENÜ YÖNETİMİ
# =====================================================================
# ... (Giriş ve Menü yapısı aynı kalıyor, Sipariş Ekranı'nı güncelliyoruz)

# --- 0. YENİ: AKILLI SİPARİŞ EKRANI ---
if secilen_sayfa == "📝 Sipariş Ekranı":
    st.header("📝 Yeni Satış & Sipariş Oluşturma Paneli")
    
    if "sepet" not in st.session_state: st.session_state["sepet"] = []

    # --- AKILLI FİLTRELEME ---
    st.subheader("🔍 1. Ürün Filtreleme ve Seçim")
    
    col_f1, col_f2 = st.columns(2)
    secilen_kat = col_f1.selectbox("Kategori Seç:", KATEGORILER)
    
    # Kategoriye göre marka listesini çıkar
    filtrelenmis_urunler = {k: v for k, v in db["urunler"].items() if v.get("Kategori") == secilen_kat}
    markalar = sorted(list(set([v.get("Marka", "Bilinmiyor") for v in filtrelenmis_urunler.values()])))
    secilen_marka = col_f2.selectbox("Marka Seç:", markalar)
    
    # Marka ve Kategoriye göre model listesi
    modeller = {k: v for k, v in filtrelenmis_urunler.items() if v.get("Marka") == secilen_marka}
    urun_secim = st.selectbox("Model Seç:", list(modeller.keys()))
    
    mevcut_adet = db["stok"].get(urun_secim, 0)
    adet = st.number_input(f"Adet (Mevcut: {mevcut_adet})", min_value=1, step=1, max_value=mevcut_adet)
    
    if st.button("➕ Sepete Ekle"):
        st.session_state["sepet"].append({"urun": urun_secim, "adet": adet})
        st.rerun()

    # --- SEPET VE SİPARİŞ ---
    if st.session_state["sepet"]:
        st.markdown("---")
        st.subheader("📋 Sepet")
        df_sepet = pd.DataFrame(st.session_state["sepet"])
        st.table(df_sepet)
        
        with st.form("siparis_formu"):
            firma = st.text_input("Firma / Şantiye:")
            sevk = st.text_area("📍 Sevk Adresi:")
            notlar = st.text_input("Notlar:")
            if st.form_submit_button("🚀 Siparişi Depoya Gönder"):
                taze_db = veritabanini_yukle()
                # (Sipariş oluşturma mantığı buraya devam ediyor...)
                st.success("Sipariş iletildi!")
                st.session_state["sepet"] = []
                st.rerun()
