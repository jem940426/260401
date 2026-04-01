import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# 1. API 키 설정
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("경고: .env 파일에서 GEMINI_API_KEY를 찾을 수 없습니다.")
    exit(1)

genai.configure(api_key=api_key)

def process_and_rename_images():
    folder_path = "260318"
    
    if not os.path.exists(folder_path):
        print(f"오류: '{folder_path}' 폴더가 존재하지 않습니다.")
        return

    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
    
    if not image_files:
        print(f"오류: '{folder_path}' 폴더 안에 이미지 파일이 없습니다.")
        return

    print(f"총 {len(image_files)}개의 이미지 파일을 찾았습니다. 분석 및 이름 변경을 시작합니다...\n")

    model = genai.GenerativeModel(
        'gemini-2.5-flash', 
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = """
이 영수증에서 결제 날짜와 결제 시간을 찾아줘.
날짜는 YYYY-MM-DD 형식으로, 시간은 HH:MM:SS 형식으로 알려줘. (예: 2026-03-25, 14:30:00)
시간 정보가 전혀 없다면 '00:00:00'으로 적어줘.
반드시 아래의 JSON 형식으로만 응답해줘:
{
  "날짜": "YYYY-MM-DD",
  "시간": "HH:MM:SS"
}
"""

    # 추출된 데이터를 저장할 리스트: [{'original_path': path, 'date': date, 'time': time, 'ext': ext}, ...]
    receipt_data = []

    for file_name in image_files:
        file_path = os.path.join(folder_path, file_name)
        ext = os.path.splitext(file_name)[1]
        
        try:
            img = Image.open(file_path)
        except Exception as e:
            print(f"[{file_name}] 이미지 열기 실패: {e}")
            continue

        print(f"[{file_name}] 분석 중...")
        try:
            response = model.generate_content([prompt, img])
            data = json.loads(response.text)
            
            date_str = data.get("날짜", "")
            time_str = data.get("시간", "00:00:00")
            
            # YYYY-MM-DD 형태가 맞는지 간단히 확인
            if len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-':
                # YYMMDD 형식으로 변환 (예: 2026-03-25 -> 260325)
                formatted_date = date_str[2:4] + date_str[5:7] + date_str[8:10]
                receipt_data.append({
                    'original_path': file_path,
                    'original_name': file_name,
                    'date': formatted_date,
                    'time': time_str,
                    'ext': ext
                })
                print(f"  -> 추출 성공: {formatted_date} / {time_str}")
            else:
                print(f"  -> 날짜 형식 인식 실패: {date_str}")
        
        except Exception as e:
            print(f"  -> AI 분석 실패: {e}")
            
        # API Rate Limit 방지를 위해 약간 대기
        time.sleep(2)

    if not receipt_data:
        print("\n변경할 파일이 없습니다.")
        return

    # 날짜와 시간 순으로 정렬
    receipt_data.sort(key=lambda x: (x['date'], x['time']))

    print("\n[이름 변경 시작]")
    
    # 같은 날짜 내에서 순번 매기기용 딕셔너리
    date_counts = {}
    
    for item in receipt_data:
        date = item['date']
        
        if date not in date_counts:
            date_counts[date] = 1
        else:
            date_counts[date] += 1
            
        seq_num = date_counts[date]
        new_name = f"{date}_{seq_num}{item['ext']}"
        new_path = os.path.join(folder_path, new_name)
        
        # 파일 이름 변경 (같은 이름인 경우 건너뜀)
        if item['original_name'] == new_name:
            print(f"유지됨: {item['original_name']}")
            continue
            
        try:
            # 혹시 모를 이름 충돌 방지를 위해 임시 이름 사용도 고려할 수 있으나,
            # 여기서는 직접 변경 시도
            if os.path.exists(new_path) and item['original_path'] != new_path:
                 print(f"경고: {new_name} 파일이 이미 존재하여 덮어쓰거나 이름 규칙이 충돌합니다. 임시 이름 할당 중...")
                 # 단순 충돌 회피용 (실제 환경에서는 더 정교한 로직 필요)
                 temp_name = f"temp_{int(time.time())}_{new_name}"
                 os.rename(item['original_path'], os.path.join(folder_path, temp_name))
                 os.rename(os.path.join(folder_path, temp_name), new_path)
            else:
                 os.rename(item['original_path'], new_path)
                 
            print(f"변경 완료: {item['original_name']} -> {new_name}")
        except Exception as e:
            print(f"변경 실패 ({item['original_name']} -> {new_name}): {e}")

if __name__ == "__main__":
    process_and_rename_images()
