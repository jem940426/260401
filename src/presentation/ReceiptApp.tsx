import React, { useState, useRef } from 'react';
import { Upload, FileDown, Trash2, CheckCircle, AlertTriangle, Loader2, Info } from 'lucide-react';
import { GeminiReceiptRepository } from '../infrastructure/gemini-repository';
import { ReceiptProcessorUseCase, ProcessReceiptRequest } from '../application/receipt-processor';
import { ExcelService } from '../infrastructure/excel-service';
import { Receipt } from '../domain/receipt';

// API 초기화 (환경 변수: VITE_GEMINI_API_KEY)
const apiKey = import.meta.env.VITE_GEMINI_API_KEY || '';
const repository = new GeminiReceiptRepository(apiKey);
const processor = new ReceiptProcessorUseCase(repository);

const ReceiptApp: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [results, setResults] = useState<Receipt[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * 파일 선택 시 핸들러
   */
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  /**
   * 분석 시작 로직
   */
  const handleStartAnalysis = async () => {
    if (files.length === 0 || isProcessing) return;
    
    setIsProcessing(true);
    setResults([]);
    setProgress(0);

    const requests: ProcessReceiptRequest[] = [];
    
    // 파일들을 Buffer로 변환 (브라우저에서는 ArrayBuffer)
    for (const file of files) {
      const arrayBuffer = await file.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer); // Node Polyfill 필요할 수 있음 (또는 브라우저 API 직접 사용)
      requests.push({
        imageBuffer: buffer,
        mimeType: file.type,
        filename: file.name
      });
    }

    try {
      const processed: Receipt[] = [];
      for (let i = 0; i < requests.length; i++) {
        const result = await processor.execute(requests[i]);
        processed.push(result);
        setResults((prev) => [...prev, result]);
        setProgress(Math.round(((i + 1) / requests.length) * 100));
        
        // 할당량 고려 지연
        if (requests.length > 1 && i < requests.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }
    } catch (error) {
      console.error('Analysis Batch Failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  /**
   * 결과 초기화
   */
  const handleReset = () => {
    setFiles([]);
    setResults([]);
    setProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const successCount = results.filter(r => r.date !== '실패' && r.date !== '에러').length;
  const failCount = results.length - successCount;

  return (
    <div className="glass-card">
      <header>
        <h1>🧾 영수증 자동 처리기</h1>
        <div className="sidebar-info">
          <h3><Info className="inline" size={18} /> 사용방법</h3>
          <p>1. 하단 박스에서 영수증 이미지(JPG, PNG, WebP)를 선택하세요.<br/>
             2. <strong>분석 시작</strong>을 누르면 Gemini AI가 내역과 카테고리를 자동 분류합니다.<br/>
             3. 완료 후 <strong>엑셀 다운로드</strong> 버튼을 눌러 저장하세요.</p>
        </div>
      </header>

      <section>
        <div className="file-uploader" onClick={() => fileInputRef.current?.click()}>
          <Upload size={48} color="#6366f1" style={{ marginBottom: '1rem' }} />
          <p>{files.length > 0 ? `📂 ${files.length}개의 파일 선택됨` : '이미지를 드래그하거나 클릭하여 업로드하세요'}</p>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            multiple 
            accept="image/*" 
            hidden 
          />
        </div>

        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
          <button 
            className="btn-primary" 
            onClick={handleStartAnalysis}
            disabled={files.length === 0 || isProcessing}
          >
            {isProcessing ? <><Loader2 className="animate-spin inline" size={18} /> 분석 중...</> : '🚀 분석 시작'}
          </button>
          
          <button className="btn-secondary" onClick={handleReset}>
            <Trash2 className="inline" size={18} /> 초기화
          </button>
        </div>

        {isProcessing && (
          <div style={{ marginTop: '1rem' }}>
            <div style={{ height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${progress}%`, height: '100%', background: '#6366f1', transition: 'width 0.3s' }} />
            </div>
            <p style={{ fontSize: '0.875rem', color: '#64748b', marginTop: '0.5rem' }}>진행률: {progress}%</p>
          </div>
        )}
      </section>

      {results.length > 0 && (
        <section style={{ marginTop: '2.5rem' }}>
          <hr style={{ border: 'none', borderTop: '1px solid #e2e8f0', marginBottom: '2rem' }} />
          <h2>📊 분석 결과 목록</h2>
          
          <div className="summary-card">
            <span className="status-success"><CheckCircle size={20} className="inline" /> 성공 {successCount}건</span>
            <span className="status-fail"><AlertTriangle size={20} className="inline" /> 실패 {failCount}건</span>
          </div>

          <table className="results-table">
            <thead>
              <tr>
                <th>파일명</th>
                <th>날짜</th>
                <th>상호명</th>
                <th>총금액</th>
                <th>부가세</th>
                <th>카테고리</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i}>
                  <td>{r.filename}</td>
                  <td className={r.date === '실패' || r.date === '에러' ? 'status-fail' : ''}>{r.date}</td>
                  <td>{r.vendor}</td>
                  <td>{typeof r.totalAmount === 'number' ? r.totalAmount.toLocaleString() : r.totalAmount}</td>
                  <td>{typeof r.vat === 'number' ? r.vat.toLocaleString() : r.vat}</td>
                  <td>{r.category}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: '2rem' }}>
            <button className="btn-primary" onClick={() => ExcelService.downloadReceipts(results)}>
              <FileDown className="inline" size={18} /> 엑셀 파일 다운로드 (receipt_analysis.xlsx)
            </button>
          </div>
        </section>
      )}
    </div>
  );
};

export default ReceiptApp;
