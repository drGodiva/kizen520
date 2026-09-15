import streamlit as st
import base64
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from openai import OpenAI
from weasyprint import HTML
import streamlit.components.v1 as components

# Cấu hình trang Streamlit
st.set_page_config(page_title="Hệ thống Kizen 520 - MBA", layout="wide")

st.title("🪓 MASTERING BIOLOGY ACADEMY - KIZEN 520 AUTOMATION")
st.markdown("Hệ thống trích xuất AI, tạo báo cáo PDF và gửi Email tự động.")

# ==========================================
# PHẦN 1: CẤU HÌNH API & EMAIL
# ==========================================
with st.sidebar:
    st.header("⚙️ Cấu hình hệ thống")
    openai_api_key = st.text_input("Nhập OpenAI API Key", type="password")
    
    st.markdown("---")
    st.subheader("Cấu hình Email gửi đi")
    sender_email = st.text_input("Email gửi", value="phungtam5965@gmail.com")
    sender_password = st.text_input("Mật khẩu ứng dụng (App Password)", type="password")
    
    st.markdown("---")
    st.info("💡 Đảm bảo bạn đã cài đặt wkhtmltopdf trên Windows để xuất file PDF.")

# ==========================================
# PHẦN 2: HÀM TRÍCH XUẤT ẢNH BẰNG OPENAI
# ==========================================
def extract_data_from_image(image_bytes, api_key):
    client = OpenAI(api_key=api_key)
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # Prompt bọc lót kỹ thuật cho AI
    prompt = """
    Bạn là một chuyên gia phân tích chỉ số cơ thể y tế. Hãy đọc ảnh báo cáo Kizen 520 và trả về MỘT CHUỖI JSON CHUẨN (không có markdown, không có text dư thừa) chứa các key sau:
    "name", "time", "age", "height", "score", "weight", "water", "protein", "mineral", "fat", "bmi", "fatrate", "vfat", "bmr", "muscle", "bioage", "stdweight", "ctrlweight", "ctrlfat".
    Nếu không thấy giá trị, điền "0".
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
    )
    
    result_text = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(result_text)

# ==========================================
# PHẦN 3: GIAO DIỆN XỬ LÝ CHÍNH
# ==========================================
uploaded_file = st.file_uploader("📥 Tải ảnh quét Kizen 520 lên đây (từ Telegram hoặc máy tính)", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Ảnh báo cáo gốc", width=400)
    
    if st.button("🚀 Bắt đầu trích xuất bằng AI"):
        if not openai_api_key:
            st.error("⚠️ Vui lòng nhập OpenAI API Key ở thanh bên trái!")
        else:
            with st.spinner("🤖 BỘ NÃO AI ĐANG XỬ LÝ DỮ LIỆU..."):
                try:
                    # Trích xuất dữ liệu
                    extracted_data = extract_data_from_image(uploaded_file.getvalue(), openai_api_key)
                    st.success("✅ Trích xuất thành công!")
                    
                    # Đọc file HTML gốc
                    with open("index.html", "r", encoding="utf-8") as f:
                        html_content = f.read()
                    
                    # Tiêm dữ liệu vừa quét được vào file HTML bằng Javascript
                    injection_script = f"""
                    <script>
                        setTimeout(() => {{
                            const data = {json.dumps(extracted_data)};
                            const mapping = {{
                                'val-name': 'name', 'p2-name': 'name',
                                'val-age': 'age', 'p2-age': 'age',
                                'val-height': 'height', 'p2-height': 'height',
                                'val-score': 'score', 'p2-score': 'score',
                                'val-weight': 'weight', 'p2-weight': 'weight', 'lbl-weight': 'weight',
                                'val-water': 'water', 'p2-water': 'water', 'p2-water-tbl': 'water',
                                'val-protein': 'protein', 'p2-pro': 'protein',
                                'val-mineral': 'mineral', 'p2-min': 'mineral',
                                'val-fat': 'fat', 'p2-fat': 'fat', 'lbl-fat': 'fat',
                                'val-bmi': 'bmi', 'p2-bmi': 'bmi', 'lbl-bmi': 'bmi',
                                'val-fatrate': 'fatrate', 'p2-fatrate': 'fatrate', 'lbl-fatrate': 'fatrate',
                                'val-vfat': 'vfat', 'p2-vfat': 'vfat',
                                'val-bmr': 'bmr', 'p2-bmr': 'bmr',
                                'lbl-muscle': 'muscle', 'p2-muscle': 'muscle', 'p2-muscle-block': 'muscle',
                                'val-bioage': 'bioage', 'p2-bioage': 'bioage',
                                'val-stdweight': 'stdweight', 'p2-stdweight': 'stdweight',
                                'val-ctrlweight': 'ctrlweight', 'p2-ctrlweight': 'ctrlweight',
                                'val-ctrlfat': 'ctrlfat', 'p2-ctrlfat': 'ctrlfat'
                            }};
                            for (const [id, key] of Object.entries(mapping)) {{
                                const el = document.getElementById(id);
                                if (el && data[key]) el.textContent = data[key];
                            }}
                        }}, 500);
                    </script>
                    """
                    
                    # Ráp script vào cuối file HTML
                    final_html = html_content.replace("</body>", injection_script + "</body>")
                    
                    # Lưu tạm file HTML để tạo PDF
                    with open("temp_report.html", "w", encoding="utf-8") as f:
                        f.write(final_html)
                        
                    # Hiển thị trực tiếp giao diện tuyệt đẹp trên Streamlit
                    st.markdown("### 📄 BẢN XEM TRƯỚC BÁO CÁO")
                    components.html(final_html, height=800, scrolling=True)
                    
                    # Chuyển đổi thành PDF
                    with st.spinner("🖨️ Đang đóng gói file PDF bản in nền trắng..."):
                        pdf_options = {
                            'page-size': 'A4',
                            'margin-top': '0mm', 'margin-right': '0mm',
                            'margin-bottom': '0mm', 'margin-left': '0mm',
                            'encoding': "UTF-8",
                            'print-media-type': '' # Kích hoạt chế độ tiết kiệm mực
                        }
                        # CHÚ Ý: Cần trỏ đường dẫn tới wkhtmltopdf trên Windows nếu chạy nội bộ
                        path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
                        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf) if os.path.exists(path_wkhtmltopdf) else None
                        
                        pdf_bytes = pdfkit.from_string(final_html, False, options=pdf_options, configuration=config)
                        
                        st.download_button(
                            label="⬇️ TẢI PDF BÁO CÁO",
                            data=pdf_bytes,
                            file_name=f"Bao_Cao_Kizen_{extracted_data.get('name', 'KhachHang')}.pdf",
                            mime="application/pdf",
                        )
                        
                    # Khối gửi Email
                    st.markdown("---")
                    st.subheader("✉️ Gửi tự động cho Khách hàng")
                    customer_email = st.text_input("Nhập Email của khách hàng:")
                    if st.button("🚀 GỬI BÁO CÁO QUA EMAIL"):
                        if not sender_password:
                            st.error("⚠️ Thầy chưa nhập Mật khẩu ứng dụng Email ở cột trái!")
                        elif not customer_email:
                            st.error("⚠️ Vui lòng nhập email khách hàng!")
                        else:
                            try:
                                msg = MIMEMultipart()
                                msg['From'] = sender_email
                                msg['To'] = customer_email
                                msg['Subject'] = "Mastering Biology Academy - Báo cáo chỉ số cơ thể Kizen 520"
                                
                                body = f"Chào anh/chị {extracted_data.get('name', '')},\n\nMastering Biology Academy xin gửi đính kèm bản báo cáo phân tích chỉ số cơ thể chuyên sâu Kizen 520.\n\nTrân trọng,\nĐội ngũ chuyên gia."
                                msg.attach(MIMEText(body, 'plain'))
                                
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(pdf_bytes)
                                encoders.encode_base64(part)
                                part.add_header('Content-Disposition', f'attachment; filename="BaoCao_Kizen520.pdf"')
                                msg.attach(part)
                                
                                server = smtplib.SMTP('smtp.gmail.com', 587)
                                server.starttls()
                                server.login(sender_email, sender_password)
                                server.send_message(msg)
                                server.quit()
                                st.success(f"✅ Đã gửi email thành công tới {customer_email}!")
                            except Exception as e:
                                st.error(f"❌ Lỗi gửi email: {e}")
                                
                except Exception as e:
                    st.error(f"❌ Lỗi trong quá trình xử lý: {e}")