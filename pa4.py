import streamlit as st
import openai
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os

# ตั้งค่า OpenAI API Key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("กรุณาตั้งค่า OpenAI API Key ใน Environment Variables")
else:
    openai.api_key = openai_api_key

# ส่วนหัวข้อแอป
st.title("ตัววิเคราะห์เนื้อหาภาษาญี่ปุ่น")
st.write(
    "ใส่ข้อความภาษาญี่ปุ่นหรือ URL ของเนื้อหาเพื่อแปลและวิเคราะห์คำศัพท์ "
    "คำศัพท์จะแบ่งตามระดับความยาก N3, N2, และ N1"
)

# รับข้อความหรือ URL จากผู้ใช้
user_input = st.text_area("กรอกข้อความภาษาญี่ปุ่น หรือใส่ลิงก์เพื่อวิเคราะห์:")

# ฟังก์ชันสำหรับดึงเนื้อหาจากลิงก์
def fetch_content_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # ดึงเนื้อหาจากแท็กที่เหมาะสม
        for tag in ["article", "div", "main", "body"]:
            content = soup.find(tag)
            if content:
                return content.get_text(strip=True)
        st.error("ไม่พบเนื้อหาหลักในลิงก์นี้")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
    return None

# ฟังก์ชันแปลข้อความ
def translate_text(text):
    try:
        prompt = f"แปลข้อความภาษาญี่ปุ่นนี้เป็นภาษาไทย:\n{text}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"การแปลข้อความล้มเหลว: {e}")
        return None

# ฟังก์ชันดึงคำศัพท์ตามระดับความยาก
def extract_vocabulary(text):
    try:
        prompt = (
            f"จากข้อความด้านล่างนี้ ให้ดึงคำศัพท์ตามระดับความยาก N3, N2, และ N1 "
            f"และสร้างตารางแยกตามระดับความยาก โดยแต่ละคำให้ระบุ:\n"
            f"1. คำศัพท์\n2. คำอ่าน (Hiragana และ Romaji)\n3. คำแปล\n4. ตัวอย่างประโยค (พร้อมแปลเป็นภาษาไทย)\n\n"
            f"ข้อความ:\n{text}"
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"การดึงคำศัพท์ล้มเหลว: {e}")
        return None

# เมื่อกดปุ่มวิเคราะห์
if st.button("วิเคราะห์"):
    if user_input:
        # ตรวจสอบว่าเป็น URL หรือข้อความ
        parsed = urlparse(user_input)
        if parsed.scheme and parsed.netloc:
            st.write("**ตรวจพบ Input เป็นลิงก์**")
            japanese_text = fetch_content_from_url(user_input)
        else:
            st.write("**ตรวจพบ Input เป็นข้อความธรรมดา**")
            japanese_text = user_input

        if japanese_text:
            # แสดงข้อความต้นฉบับ
            st.write("### ข้อความต้นฉบับ")
            st.write(japanese_text)

            # แปลข้อความ
            st.write("### การแปลข้อความ")
            translation = translate_text(japanese_text)
            if translation:
                st.write(translation)

            # วิเคราะห์คำศัพท์
            st.write("### คำศัพท์ที่แยกตามระดับความยาก")
            vocab_content = extract_vocabulary(japanese_text)
            if vocab_content:
                tables = {"N3": [], "N2": [], "N1": []}
                for line in vocab_content.split("\n"):
                    if line.startswith("N3:"):
                        tables["N3"].append(line[3:].split("\t"))
                    elif line.startswith("N2:"):
                        tables["N2"].append(line[3:].split("\t"))
                    elif line.startswith("N1:"):
                        tables["N1"].append(line[3:].split("\t"))

                for level, data in tables.items():
                    if data:
                        st.write(f"#### คำศัพท์ระดับ {level}")
                        df = pd.DataFrame(data, columns=["คำศัพท์", "คำอ่าน (Hiragana และ Romaji)", "คำแปล", "ตัวอย่างประโยค"])
                        st.dataframe(df)
                        # เพิ่มปุ่มดาวน์โหลด
                        csv = df.to_csv(index=False)
                        st.download_button(
                            f"ดาวน์โหลดคำศัพท์ระดับ {level}", csv, f"vocabulary_{level}.csv", mime="text/csv"
                        )
                    else:
                        st.write(f"ไม่มีคำศัพท์ในระดับ {level}")
    else:
        st.warning("กรุณากรอกข้อความหรือใส่ลิงก์ก่อนเริ่มทำงาน")
