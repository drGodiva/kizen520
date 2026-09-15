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
import os
import streamlit.components.v1 as components
import fitz  # PyMuPDF để bóc tách PDF thành ảnh
import re    # Thư viện gọt chữ thừa của AI

# ==========================================
# CẤU HÌNH TRANG & CSS THƯƠNG HIỆU MBA
# ==========================================
st.set_page_config(page_title="Hệ thống Kizen 520 - MBA", layout="wide", page_icon="🪓")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #012B1D; color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #004D40; border-right: 2px solid #D4AF37; }
    h1, h2, h3, h4, h5, h6, .st-emotion-cache-10trblm { color: #D4AF37 !important; }
    .stButton>button {
        background-color: #D4AF37; color: #012B1D; font-weight: 900;
        border: none; border-radius: 6px; transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #F5E6BE; color: #000000; }
</style>
""", unsafe_allow_html=True)

st.title("🪓 MASTERING BIOLOGY ACADEMY - KIZEN 520")
st.markdown("**Hệ thống trích xuất AI, tạo báo cáo PDF và gửi Email tự động.**")

# ==========================================
# LẤY BẢO MẬT TỪ KÉT SẮT (SECRETS)
# ==========================================
try:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    sender_password = st.secrets["EMAIL_PASSWORD"]
except KeyError:
    st.error("⚠️ Hệ thống chưa tìm thấy Khóa Bảo Mật (Secrets). Thầy vui lòng vào Settings -> Secrets trên Streamlit Cloud để cấu hình.")
    st.stop()

sender_email = "phungtam5965@gmail.com"

# ==========================================
# HÀM XỬ LÝ NHIỀU ẢNH VÀ TRÍCH XUẤT OPENAI BẢO MẬT KÉP
# ==========================================
def extract_data_from_images(image_bytes_list, api_key):
    client = OpenAI(api_key=api_key)
    
    # Câu lệnh thép dành cho AI (Prompt)
    prompt = """
    Bạn là chuyên gia phân tích chỉ số cơ thể y tế. BẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON CHUẨN (JSON OBJECT).
    Đọc thật kỹ toàn bộ ảnh (đặc biệt quét thật kỹ khu vực trên cùng của trang báo cáo) để lấy chính xác:
    - "name": Tên khách hàng (Thường nằm to nhất ở góc trên).
    - "height": Chiều cao (Số đo cm).
    - "weight": Cân nặng (Số đo kg, thường là con số to nhất ở Trang 1 và Trang 2).
    - "age": Tuổi.
    - Các key khác: "time", "score", "water", "protein", "mineral", "fat", "bmi", "fatrate", "vfat", "bmr", "muscle", "bioage", "stdweight", "ctrlweight", "ctrlfat".
    
    Quy tắc thép:
    1. Chỉ trả về JSON, tuyệt đối không giải thích hay bình luận thêm.
    2. Chỉ lấy phần con số (ví dụ: 65.5), TUYỆT ĐỐI KHÔNG kèm chữ "kg", "%", "cm" hay "Tuổi" vào dữ liệu.
    3. TUYỆT ĐỐI KHÔNG được điền "0" cho Tên, Chiều cao, Cân nặng, Tuổi. Hãy tìm kỹ bằng mọi giá. Nếu không có số thập phân thì giữ nguyên số nguyên.
    """
    
    # Nạp nội dung prompt
    content_list = [{"type": "text", "text": prompt}]
    
    # Nạp từng tấm ảnh (hoặc từng trang PDF đã cắt thành ảnh) vào não AI
    for img_bytes in image_bytes_list:
        b64_image = base64.b64encode(img_bytes).decode('utf-8')
        content_list.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}})
    
    # Gọi AI với thuộc tính ÉP BUỘC JSON
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" }, 
        messages=[{"role": "user", "content": content_list}]
    )
    
    result_text = response.choices[0].message.content.strip()
    
    # Lớp bảo vệ số 2: Gọt sạch râu ria bằng Regex để tránh lỗi char 0
    match = re.search(r'\{.*\}', result_text, re.DOTALL)
    if match:
        result_text = match.group(0)
        
    try:
        return json.loads(result_text)
    except Exception as e:
        st.error(f"⚠️ Bộ não AI đã trích xuất lỗi cú pháp: {e}")
        st.code(result_text, language='json')
        return {}

# ==========================================
# GIAO DIỆN XỬ LÝ CHÍNH
# ==========================================
with st.sidebar:
    if os.path.exists("assets/logo_mba.png"):
        st.image("assets/logo_mba.png", use_container_width=True)
        
    st.header("⚙️ Trạng thái hệ thống")
    st.success("✅ Đã khóa bảo mật API Key")
    st.success("✅ Đã kết nối Email phungtam5965")
    st.markdown("---")
    st.markdown("🌐 **Môi trường Cloud Ready**")

# NÚT UPLOAD HỖ TRỢ CHỌN NHIỀU FILE VÀ ĐUÔI PDF
uploaded_files = st.file_uploader(
    "📥 Tải ảnh hoặc PDF Kizen 520 lên đây (Có thể chọn nhiều file cùng lúc)", 
    type=['png', 'jpg', 'jpeg', 'pdf'], 
    accept_multiple_files=True
)

if uploaded_files:
    col1, col2 = st.columns([1, 2])
    
    # Xử lý bóc tách file tải lên
    processed_images = []
    with col1:
        st.markdown("**📁 Các trang dữ liệu sẽ nạp vào AI:**")
        for file in uploaded_files:
            file_bytes = file.read()
            if file.name.lower().endswith('.pdf'):
                # Bóc tách từng trang PDF thành ảnh
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("jpeg")
                    processed_images.append(img_data)
                    st.image(img_data, caption=f"📄 {file.name} - Trang {page_num + 1}", use_container_width=True)
            else:
                # Nếu là ảnh thường thì nạp thẳng
                processed_images.append(file_bytes)
                st.image(file_bytes, caption=f"🖼️ {file.name}", use_container_width=True)
    
    with col2:
        if st.button("🚀 BẮT ĐẦU TRÍCH XUẤT BẰNG BỘ NÃO AI"):
            if not processed_images:
                st.warning("⚠️ Chưa có ảnh hoặc dữ liệu hợp lệ để quét.")
            else:
                with st.spinner("🤖 ĐANG PHÂN TÍCH CHỈ SỐ TỪ CÁC TÀI LIỆU..."):
                    try:
                        # Gọi hàm trích xuất
                        extracted_data = extract_data_from_images(processed_images, openai_api_key)
                        
                        if extracted_data: 
                            st.success(f"✅ Trích xuất thành công dữ liệu của khách hàng: **{extracted_data.get('name', 'Chưa rõ tên')}**!")
                            
                            # Đọc file HTML gốc
                            with open("index.html", "r", encoding="utf-8") as f:
                                html_content = f.read()
                            
                            # Tiêm dữ liệu vào HTML
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
                                        'lbl-bmi': 'bmi', 'p2-bmi': 'bmi',
                                        'lbl-fatrate': 'fatrate', 'p2-fatrate': 'fatrate',
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
                            
                            final_html = html_content.replace("</body>", injection_script + "</body>")
                            
                            # Hiển thị bản xem trước
                            st.markdown("### 📄 BẢN XEM TRƯỚC BÁO CÁO (Nền Đen)")
                            components.html(final_html, height=800, scrolling=True)
                            
                            # Chuyển đổi thành PDF bằng WeasyPrint
                            with st.spinner("🖨️ Đang đóng gói file PDF bản in nền trắng..."):
                                pdf_bytes = HTML(string=final_html, base_url=os.path.dirname(os.path.abspath(__file__))).write_pdf()
                                
                                st.download_button(
                                    label="⬇️ TẢI PDF BÁO CÁO",
                                    data=pdf_bytes,
                                    file_name=f"Bao_Cao_Kizen_{extracted_data.get('name', 'KhachHang')}.pdf",
                                    mime="application/pdf",
                                )
                                
                            # Lưu file PDF tạm để gửi email
                            with open("temp_report.pdf", "wb") as f:
                                f.write(pdf_bytes)
                            st.session_state['pdf_ready'] = True
                            st.session_state['client_name'] = extracted_data.get('name', 'Khách hàng')
                                        
                    except Exception as e:
                        st.error(f"❌ Lỗi trong quá trình xử lý tổng thể: {e}")

# ==========================================
# KHỐI GỬI EMAIL (NẰM DƯỚI CÙNG TRANG)
# ==========================================
if st.session_state.get('pdf_ready'):
    st.markdown("---")
    st.header("✉️ GỬI TỰ ĐỘNG CHO KHÁCH HÀNG")
    st.info("Báo cáo đã sẵn sàng. Thầy vui lòng nhập Email khách hàng để gửi đi.")
    
    col_em1, col_em2 = st.columns([2, 1])
    with col_em1:
        customer_email = st.text_input("Nhập Email của khách hàng:")
    with col_em2:
        st.write("")
        st.write("")
        if st.button("🚀 GỬI BÁO CÁO QUA EMAIL", use_container_width=True):
            if not customer_email:
                st.error("⚠️ Vui lòng nhập email khách hàng!")
            else:
                try:
                    with st.spinner("Đang kết nối với máy chủ Email..."):
                        msg = MIMEMultipart()
                        msg['From'] = sender_email
                        msg['To'] = customer_email
                        msg['Subject'] = f"Mastering Biology Academy - Báo cáo Kizen 520 của {st.session_state.get('client_name')}"
                        
                        body = f"Chào anh/chị {st.session_state.get('client_name')},\n\nMastering Biology Academy xin gửi đính kèm bản báo cáo phân tích chỉ số cơ thể chuyên sâu Kizen 520.\n\nTrân trọng,\nĐội ngũ chuyên gia MBA - Người Mài Rìu."
                        msg.attach(MIMEText(body, 'plain'))
                        
                        # Đọc lại file PDF tạm
                        with open("temp_report.pdf", "rb") as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename="BaoCao_Kizen520.pdf"')
                            msg.attach(part)
                        
                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(sender_email, sender_password)
                        server.send_message(msg)
                        server.quit()
                        
                        st.success(f"✅ Đã gửi Email kèm file PDF thành công tới {customer_email}!")
                except Exception as e:
                    st.error(f"❌ Lỗi gửi email: Vui lòng kiểm tra lại App Password hoặc kết nối mạng. (Chi tiết: {e})")