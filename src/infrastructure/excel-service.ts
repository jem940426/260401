import * as XLSX from 'xlsx';
import { Receipt } from '../domain/receipt';

export class ExcelService {
  /**
   * 영수증 목록을 엑셀 파일로 변환하여 다운로드
   */
  public static downloadReceipts(receipts: Receipt[]): void {
    const data = receipts.map((r) => ({
      '파일명': r.filename,
      '날짜': r.date,
      '상호명': r.vendor,
      '총금액': r.totalAmount,
      '부가세': r.vat,
      '카테고리': r.category,
    }));

    const worksheet = XLSX.utils.json_to_sheet(data);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, '영수증분석결과');

    // 실패 목록 시트 추가 (필요 시)
    const failures = receipts.filter((r) => r.date === '실패' || r.date === '에러');
    if (failures.length > 0) {
      const failData = failures.map((f) => ({
        '파일명': f.filename,
        '상태': f.date === '에러' ? '분석 에러' : '정보 부족(실패)',
      }));
      const failSheet = XLSX.utils.json_to_sheet(failData);
      XLSX.utils.book_append_sheet(workbook, failSheet, '실패목록');
    }

    // 파일 내보내기
    XLSX.writeFile(workbook, 'receipt_analysis.xlsx');
  }
}
