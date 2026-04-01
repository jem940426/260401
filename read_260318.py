import os
import json
import unicodedata
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# 1. .env 파일에서 API 키를 가져옴
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("경고: .env 파일에서 GEMINI_API_KEY를 찾을 수 없습니다.")
else:
    genai.configure(api_key=api_key)

def get_display_width(text):
    """한글은 폭을 2로, 영문/숫자는 1로 계산합니다."""
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in str(text))

def pad_text(text, width):
    """지정한 폭에 맞춰 텍스트 뒤에 공백을 추가합니다."""
    text = str(text)
    return text + ' ' * max(0, width - get_display_width(text))

def print_table(data_dict):
    """딕셔너리 데이터를 표 형태로 출력합니다."""
    col1_w = max([get_display_width(k) for k in data_dict.keys()] + [get_display_width("항목")])
    col2_w = max([get_display_width(v) for v in data_dict.values()] + [get_display_width("내용")])
    
    print(f"┌─{'─'*col1_w}─┬─{'─'*col2_w}─┐")
    print(f"│ {pad_text('항목', col1_w)} │ {pad_text('내용', col2_w)} │")
    print(f"├─{'─'*col1_w}─┼─{'─'*col2_w}─┤")
    for k, v in data_dict.items():
        print(f"│ {pad_text(k, col1_w)} │ {pad_text(v, col2_w)} │")
    print(f"└─{'─'*col1_w}─┴─{'─'*col2_w}─┘")

def process_receipt():
    folder_path = "260318"
    
    # 260318 폴더 확인
    if not os.path.exists(folder_path):
        print(f"오류: '{folder_path}' 폴더가 존재하지 않습니다.")
        return

    # 폴더 내 이미지 파일 검색
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
    
    if not image_files:
        print(f"오류: '{folder_path}' 폴더 안에 이미지 파일이 없습니다.")
        return

    # 2. 첫 번째 사진을 열기
    first_image_path = os.path.join(folder_path, image_files[0])
    
    try:
        img = Image.open(first_image_path)
    except Exception as e:
        print(f"이미지를 여는 중 오류 발생: {e}")
        return

    # 3. Gemini AI 모델 설정 및 메시지 전송
    model = genai.GenerativeModel(
        'gemini-2.5-flash', 
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = """
이 영수증에서 날짜, 상호명, 총금액, 부가세를 찾아줘.
없는 항목은 '없음'이라고 써줘.
반드시 아래의 JSON 형식으로만 응답해줘:
{
  "날짜": "문자열",
  "상호명": "문자열",
  "총금액": "문자열",
  "부가세": "문자열"
}
"""
    
    print(f"\n[{first_image_path}] 분석을 요청하는 중...\n")
    try:
        response = model.generate_content([prompt, img])
        
        # 4. JSON 문자열을 파싱하여 표 모양으로 화면에 출력
        data = json.loads(response.text)
        
        # 금액 항목에서 숫자 외의 모든 문자(원, ₩, 콤마 등) 제거
        for key in ["총금액", "부가세"]:
            if key in data and data[key] != "없음":
                data[key] = "".join(filter(str.isdigit, data[key]))
                
        print_table(data)
        
    except json.JSONDecodeError:
        print("결과를 JSON으로 변환하는 중 오류가 발생했습니다.")
        print("원본 모델 응답:")
        print(response.text)
    except Exception as e:
        print(f"AI 요청 중 오류 발생: {e}")

if __name__ == "__main__":
    process_receipt()
