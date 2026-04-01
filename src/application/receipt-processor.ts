import { Receipt } from '../domain/receipt';
import { GeminiReceiptRepository } from '../infrastructure/gemini-repository';

export interface ProcessReceiptRequest {
  readonly imageBuffer: Buffer;
  readonly mimeType: string;
  readonly filename: string;
}

export class ReceiptProcessorUseCase {
  constructor(private readonly geminiRepository: GeminiReceiptRepository) {}

  /**
   * 단일 영수증 처리
   */
  public async execute(request: ProcessReceiptRequest): Promise<Receipt> {
    return await this.geminiRepository.analyzeReceipt(
      request.imageBuffer,
      request.mimeType,
      request.filename
    );
  }

  /**
   * 다중 영수증 처리
   */
  public async executeBatch(requests: ProcessReceiptRequest[]): Promise<Receipt[]> {
    const results: Receipt[] = [];
    
    // 할당량 제한을 고려한 순차 처리 (필요시 지연 추가 가능)
    for (const request of requests) {
      const receipt = await this.execute(request);
      results.push(receipt);
      
      // API 호출 간 짧은 지연 (속도 조절이 필요한 경우)
      if (requests.length > 1) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    }
    
    return results;
  }
}
