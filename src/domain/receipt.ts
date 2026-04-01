/**
 * 영수증 데이터 도메인 모델
 */
export type Category = '식비' | '교통비' | '사무용품' | '숙박비' | '기타';

export interface Receipt {
  readonly filename: string;
  readonly date: string;
  readonly vendor: string;
  readonly totalAmount: number | '실패' | '에러' | '없음';
  readonly vat: number | '실패' | '에러' | '없음';
  readonly category: Category | '실패' | '에러' | '없음';
}
