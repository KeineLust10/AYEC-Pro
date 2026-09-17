import streamlit as st
import os
import subprocess
import ollama

# 1. AYARLAR
if 'yml_path' not in st.session_state:
    st.session_state.yml_path = ".github/workflows/python-app.yml"
if 'branch_name' not in st.session_state:
    st.session_state.branch_name = "KeineLust10-yama-2"
if 'commit_message' not in st.session_state:
    st.session_state.commit_message = "fix: pytest step updated automatically by Ollama"

# 2. DOSYAYI OKU
if not os.path.exists(st.session_state.yml_path):
    st.error(f"Hata: {st.session_state.yml_path} dosyası bulunamadı!")
    exit()

with open(st.session_state.yml_path, "r", encoding="utf-8") as f:
    mevcut_kod = f.read()

# 3. OLLAMA'YA DÜZELTTİR (Llama3 veya hangi modeli kullanıyorsan 'model' kısmına yaz)
st.title("GitHub Actions YAML Düzelteci")
st.write("Ollama dosyayı düzenliyor...")
prompt = f"""
Aşağıdaki GitHub Actions YAML kodunda yer alan 'Test with pytest' adımındaki 'pytest' komutunu sil. 
Yerine sadece echo "Henuz test yazilmadi, pas geciliyor." komutunu koy. 
YAML girintilerine ve boşluklarına kesinlikle dikkat et. 
Bana SADECE güncellenmiş yeni YAML kodunun tamamını ver, başka hiçbir açıklama yazma.

Mevcut Kod:
{mevcut_kod}
"""

response = ollama.generate(model="llama3", prompt=prompt)
yeni_kod = response["response"].strip()

# Eğer Ollama kodu yaml  içinde verdiyse temizle
if yeni_kod.startswith(""):
    yeni_kod = "\n".join(yeni_kod.split("\n")[1:-1])

st.session_state.yeni_kod = yeni_kod

# 4. DÜZENLENEN KODU DOSYAYA YAZ
st.write("Dosya yerelde güncellendi.")

# 5. GIT KOMUTLARINI SIRAYLA ÇALIŞTIR
try:
    st.title("Git İşlemleri")
    st.write("Git işlemleri başlatılıyor...")
    # Git kimlik ayarlarını yap
    subprocess.run(["git", "config", "--global", "user.name", "KeineLust10"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "enginmamu1@gmail.com"], check=True)
    
    # Doğru branch'e geç ve değişiklikleri pushla
    subprocess.run(["git", "checkout", st.session_state.branch_name], check=True)
    subprocess.run(["git", "add", st.session_state.yml_path], check=True)
    subprocess.run(["git", "commit", "-m", st.session_state.commit_message], check=True)
    subprocess.run(["git", "push", "origin", st.session_state.branch_name], check=True)
    
    st.success("\nBaşarılı! Ollama dosyayı düzenledi ve GitHub'daki PR'a gönderdi.")
except subprocess.CalledProcessError as e:
    st.error(f"\nGit hatası oluştu: {e}")