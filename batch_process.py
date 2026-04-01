import os
import json
import time
import shutil
from dotenv import load_dotenv
from google import genai
from PIL import Image
import openpyxl
from openpyxl import Workbook

def main():
    # 1. .env 파일에서 GEMINI_API_KEY를 읽어옴
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("경고: .env 파일에서 GEMINI_API_KEY를 찾을 수 없습니다.")
        return

    # 새로운 google-genai SDK 클라이언트 설정
    client = genai.Client(api_key=api_key)

    # 2. 260318 폴더 안의 파일 찾기
    folder_path = "260318"
    error_folder = os.path.join(folder_path, "error")
    outputs_folder = "outputs"

    if not os.path.exists(folder_path):
        print(f"오류: '{folder_path}' 폴더가 존재하지 않습니다.")
        return

    # 필요한 폴더 생성
    os.makedirs(error_folder, exist_ok=True)
    os.makedirs(outputs_folder, exist_ok=True)

    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
    
    if not image_files:
        print(f"오류: '{folder_path}' 폴더 안에 이미지 파일이 없습니다.")
        return

    # 3. Gemini Vision API 설정 (Gemini 3.1 Flash Lite Preview)
    model_name = 'gemini-3.1-flash-lite-preview'
    
    prompt = """
이 영수증에서 날짜, 상호명, 총금액, 부가세를 찾아줘.
없는 항목은 '없음'이라고 써줘.
반드시 아래의 JSON 형식으로만 응답해줘:
{
  "날짜": "문자열 (또는 없음)",
  "상호명": "문자열 (또는 없음)",
  "총금액": "숫자 (또는 없음)",
  "부가세": "숫자 (또는 없음)"
}
"""

    print(f"'{folder_path}' 폴더에서 총 {len(image_files)}개의 파일을 찾았습니다.\n")

    success_count = 0
    failure_count = 0
    results = []
    failure_details = []

    # 4. 각 파일 처리
    for file_name in image_files:
        file_path = os.path.join(folder_path, file_name)
        
        # "파일명 처리 중..." 출력
        print(f"{file_name} 처리 중...", end=" ", flush=True)
        
        try:
            img = Image.open(file_path)
            
            # API 호출
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, img],
                config={'response_mime_type': 'application/json'}
            )
            
            # JSON 파싱
            data = json.loads(response.text)
            
            # 실패 판단 기준 적용
            check_fields = ["날짜", "상호명", "총금액"]
            missing_indicators = ["없음", "알 수 없음"]
            missing_count = 0
            
            for field in check_fields:
                val = str(data.get(field, "없음"))
                if any(indicator in val for indicator in missing_indicators):
                    missing_count += 1
            
            if missing_count >= 2:
                # 인식 실패로 간주
                print("실패 (인식 불가 영수증)")
                failure_count += 1
                failure_details.append({"파일명": file_name, "사유": "인식 불가 영수증 (결과 부족)"})
                shutil.move(file_path, os.path.join(error_folder, file_name))
            else:
                # 성공
                print("완료")
                success_count += 1
                data['파일명'] = file_name
                results.append(data)
            
        except Exception as e:
            err_msg = str(e).upper()
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                print(f"실패 (API 할당량 초과 - 작업을 중지합니다)")
                failure_details.append({"파일명": file_name, "사유": "API 할당량 초과 (429)"})
                # 중단 시 남은 파일들도 실패 목록에 추가 (선택 사항)
                remaining = image_files[image_files.index(file_name)+1:]
                for rem in remaining:
                    failure_details.append({"파일명": rem, "사유": "이전 파일에서 할당량 초과로 인한 중단"})
                break
            else:
                print(f"실패 (에러: {e})")
                failure_count += 1
                failure_details.append({"파일명": file_name, "사유": f"시스템 에러: {e}"})
                try:
                    shutil.move(file_path, os.path.join(error_folder, file_name))
                except Exception as move_err:
                    print(f"  -> 파일 이동 에러: {move_err}")
            
        # 요청 간 5초 지연
        time.sleep(5)

    # 5. 엑셀 저장 로직 (openpyxl)
    wb = Workbook()
    
    # [결과] 시트
    ws_result = wb.active
    ws_result.title = "결과"
    ws_result.append(["파일명", "날짜", "상호명", "총금액", "부가세"])
    
    for res in results:
        # 금액 데이터 숫자 변환 처리
        def to_int(val):
            if val is None or str(val) == "없음": return 0
            try:
                # 쉼표, '원', 공백 제거 후 숫자로 변환
                clean_val = str(val).replace(",", "").replace("원", "").strip()
                return int(float(clean_val)) if clean_val else 0
            except:
                return 0

        ws_result.append([
            res.get("파일명"),
            res.get("날짜"),
            res.get("상호명"),
            to_int(res.get("총금액")),
            to_int(res.get("부가세"))
        ])

    # [실패 목록] 시트
    ws_fail = wb.create_sheet("실패 목록")
    ws_fail.append(["실패한 파일명", "실패 이유"])
    for fail in failure_details:
        ws_fail.append([fail["파일명"], fail["사유"]])

    output_path = os.path.join(outputs_folder, "results.xlsx")
    wb.save(output_path)
    print(f"\noutputs/results.xlsx 저장 완료")

    # 최종 요약 출력
    print(f"[최종 결과물 요약]")
    print(f"성공 {success_count}건 / 실패 {failure_count}건")

if __name__ == "__main__":
    main()
