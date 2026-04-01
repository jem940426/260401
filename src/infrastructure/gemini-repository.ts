import { GoogleGenerativeAI } from '@google/generative-ai';
import { z } from 'zod';
import { Receipt, Category } from '../domain/receipt';

/**
 * Gemini 응답 형태 정의 (Zod 스키마)
 */
const ReceiptResponseSchema = z.object({
  날짜: z.string(),
  상호명: z.string(),
  총금액: z.union([z.number(), z.literal('없음')]),
  부가세: z.union([z.number(), z.literal('없음')]),
  카테고리: z.enum(['식비', '교통비', '사무용품', '숙박비', '기타'])
});

export class GeminiReceiptRepository {
  private readonly genAI: GoogleGenerativeAI;
  private readonly modelName = 'gemini-1.5-flash-lite-preview-0924'; // 최신 모델 권장

  constructor(apiKey: string) {
    this.genAI = new GoogleGenerativeAI(apiKey);
  }

  /**
   * 영수증 이미지를 분석하여 데이터와 카테고리를 추출
   */
  public async analyzeReceipt(
    imageUint8Array: Uint8Array,
    mimeType: string,
    filename: string
  ): Promise<Receipt> {
    const model = this.genAI.getGenerativeModel({ model: this.modelName });

    const prompt = `
이 영수증에서 날짜, 상호명, 총금액, 부가세를 찾아줘.
또한 상호명과 구매 항목을 보고 아래 카테고리 중 하나로 자동 분류해줘:
[식비 / 교통비 / 사무용품 / 숙박비 / 기타]

없는 항목은 '없음'이라고 써줘.
반드시 아래의 JSON 형식으로만 응답해줘:
{
  "날짜": "문자열 (또는 없음)",
  "상호명": "문자열 (또는 없음)",
  "총금액": "숫자 (또는 없음)",
  "부가세": "숫자 (또는 없음)",
  "카테고리": "상단 제안된 카테고리 중 하나"
}
`;

    try {
      const result = await model.generateContent([
        prompt,
        {
          inlineData: {
            data: btoa(
              Array.from(imageUint8Array)
                .map((b) => String.fromCharCode(b))
                .join('')
            ),
            mimeType,
          },
        },
      ]);

      const responseText = result.response.text();
      // JSON 문자열만 추출 (```json 및 기타 텍스트 제거)
      const jsonStart = responseText.indexOf('{');
      const jsonEnd = responseText.lastIndexOf('}') + 1;
      const cleanJson = responseText.substring(jsonStart, jsonEnd);
      
      const rawData = JSON.parse(cleanJson);
      const data = ReceiptResponseSchema.parse(rawData);

      return {
        filename,
        date: data.날짜,
        vendor: data.상호명,
        totalAmount: data.총금액,
        vat: data.부가세,
        category: data.카테고리 as Category,
      };
    } catch (error) {
      console.error('Gemini Analysis Failed:', error);
      return {
        filename,
        date: '에러',
        vendor: '에러',
        totalAmount: '에러',
        vat: '에러',
        category: '에러' as any, // 런타임 에러 대응
      };
    }
  }
}
