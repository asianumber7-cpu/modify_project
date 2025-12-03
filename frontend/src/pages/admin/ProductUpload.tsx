import React, { useState, useRef, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Upload, FileText, AlertCircle, CheckCircle, Image as ImageIcon, 
  FileSpreadsheet, X, Loader2, Trash2 
} from 'lucide-react';
import client from '@/api/client';
import { Button } from '@/components/ui/button';

// --- Types ---
type UploadMode = 'image' | 'csv';

interface FileQueueItem {
  id: string;
  file: File;
  status: 'idle' | 'processing' | 'success' | 'error';
  progress: number;
  resultMsg?: string;
  errorMsg?: string;
}

// --- Config ---
const UPLOAD_CONFIG = {
  image: {
    title: 'AI 이미지 자동 등록 (Bulk)',
    desc: '여러 장의 이미지를 드래그하세요. AI가 병렬로 분석하여 상품을 자동 등록합니다.',
    endpoint: '/products/upload/image-auto', 
    accept: '.png, .jpg, .jpeg, .webp',
    label: '이미지 파일 선택 (다중 가능)',
    icon: <ImageIcon className="w-5 h-5" />,
    multiple: true
  },
  csv: {
    title: 'CSV 대량 등록',
    desc: 'CSV 파일을 사용하여 상품을 일괄 등록합니다.',
    endpoint: '/products/upload/csv',
    accept: '.csv',
    label: 'CSV 파일 선택',
    icon: <FileSpreadsheet className="w-5 h-5" />,
    multiple: false
  }
};

export default function ProductUpload() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<UploadMode>('image');
  const [fileQueue, setFileQueue] = useState<FileQueueItem[]>([]);
  const [isGlobalProcessing, setIsGlobalProcessing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  
  const queryClient = useQueryClient();

  // --- Helper: Logs ---
  const addLog = useCallback((log: string) => {
    setLogs((prev) => {
      const newLogs = prev.length >= 100 ? prev.slice(1) : prev;
      return [...newLogs, `[${new Date().toLocaleTimeString()}] ${log}`];
    });
  }, []);

  // --- Helper: Update Item State ---
  const updateItemStatus = (id: string, updates: Partial<FileQueueItem>) => {
    setFileQueue(prev => prev.map(item => item.id === id ? { ...item, ...updates } : item));
  };

  // --- Mutation (Single File Upload) ---
  const uploadMutation = useMutation({
    mutationFn: async (item: FileQueueItem) => {
      const formData = new FormData();
      formData.append('file', item.file);

      const config = UPLOAD_CONFIG[mode];
      
      const response = await client.post(config.endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            updateItemStatus(item.id, { progress: percent });
          }
        }
      });
      return response.data;
    }
  });

  // --- Handlers ---
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files).map(file => ({
        id: Math.random().toString(36).substring(7),
        file,
        status: 'idle' as const,
        progress: 0
      }));

      if (mode === 'csv') {
        // CSV는 1개만 허용
        setFileQueue(newFiles.slice(0, 1));
      } else {
        // 이미지는 추가
        setFileQueue(prev => [...prev, ...newFiles]);
      }
      
      addLog(`📂 Added ${newFiles.length} file(s) to queue.`);
      // Reset input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const removeFile = (id: string) => {
    setFileQueue(prev => prev.filter(f => f.id !== id));
  };

  const handleStartUpload = async () => {
    if (fileQueue.length === 0) return;
    setIsGlobalProcessing(true);
    addLog("🚀 Starting Batch Upload...");

    // CSV는 단건 처리
    if (mode === 'csv') {
      const item = fileQueue[0];
      if (!item) return;
      
      updateItemStatus(item.id, { status: 'processing', progress: 0 });
      try {
        const data = await uploadMutation.mutateAsync(item);
        updateItemStatus(item.id, { status: 'success', resultMsg: `성공: ${data.success}, 실패: ${data.failed}` });
        addLog(`✅ CSV Upload Complete. Success: ${data.success}`);
        queryClient.invalidateQueries({ queryKey: ['products'] });
      } catch (err: any) {
        updateItemStatus(item.id, { status: 'error', errorMsg: err.message });
        addLog(`❌ CSV Error: ${err.message}`);
      }
      setIsGlobalProcessing(false);
      return;
    }

    // Image Bulk Processing (Concurrency Control: 3 parallel requests)
    const PENDING_QUEUE = fileQueue.filter(f => f.status === 'idle' || f.status === 'error');
    const CONCURRENCY = 3;
    
    // Process items in chunks or simplified queue
    // 단순화를 위해 for...of 로 순차 처리하되, Promise.all로 묶을 수 있음.
    // 여기서는 안정성을 위해 3개씩 끊어서 처리
    
    for (let i = 0; i < PENDING_QUEUE.length; i += CONCURRENCY) {
      const batch = PENDING_QUEUE.slice(i, i + CONCURRENCY);
      
      await Promise.all(batch.map(async (item) => {
        updateItemStatus(item.id, { status: 'processing', progress: 0 });
        try {
          const data = await uploadMutation.mutateAsync(item);
          updateItemStatus(item.id, { 
            status: 'success', 
            progress: 100, 
            resultMsg: data.name // 상품명 표시
          });
          addLog(`✅ Uploaded: ${item.file.name} -> ${data.name}`);
        } catch (err: any) {
          const errMsg = err.response?.data?.detail || "Upload failed";
          updateItemStatus(item.id, { status: 'error', errorMsg: errMsg });
          addLog(`❌ Failed: ${item.file.name} - ${errMsg}`);
        }
      }));
    }

    queryClient.invalidateQueries({ queryKey: ['products'] });
    setIsGlobalProcessing(false);
    addLog("✨ All tasks finished.");
  };

  const currentConfig = UPLOAD_CONFIG[mode];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">상품 업로드 관리</h1>
      <p className="text-gray-500 mb-6">AI 자동 등록 또는 CSV 대량 등록을 선택하세요.</p>

      {/* 1. Mode Tabs */}
      <div className="flex space-x-4 mb-6">
        {(Object.keys(UPLOAD_CONFIG) as UploadMode[]).map((tabKey) => (
          <button
            key={tabKey}
            onClick={() => { setMode(tabKey); setFileQueue([]); setLogs([]); }}
            className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-bold transition-all ${
              mode === tabKey 
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-200 dark:shadow-none' 
                : 'bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            {UPLOAD_CONFIG[tabKey].icon}
            <span>{UPLOAD_CONFIG[tabKey].title}</span>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 2. Upload Area & Queue (Left/Center) */}
        <div className="lg:col-span-2 space-y-6">
            
          {/* Drop Zone */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-3xl shadow-sm border border-gray-100 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
              {currentConfig.icon} {currentConfig.title}
            </h3>
            
            <div 
              className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center transition-colors min-h-[200px]
                ${isGlobalProcessing ? 'bg-gray-50 dark:bg-gray-900 border-gray-300 cursor-not-allowed' : 'border-gray-300 dark:border-gray-600 hover:border-purple-500 cursor-pointer'}
              `}
              onClick={() => !isGlobalProcessing && fileInputRef.current?.click()}
            >
              <input 
                type="file" 
                multiple={currentConfig.multiple}
                accept={currentConfig.accept} 
                ref={fileInputRef} 
                className="hidden" 
                onChange={handleFileSelect}
                disabled={isGlobalProcessing}
              />
              <Upload className="w-12 h-12 text-gray-400 mb-4" />
              <p className="text-gray-600 dark:text-gray-300 font-medium mb-1">
                {isGlobalProcessing ? '처리 중입니다...' : '파일을 클릭하거나 여기로 드래그하세요'}
              </p>
              <p className="text-xs text-gray-400">{currentConfig.accept} 지원</p>
            </div>
          </div>

          {/* File Queue List */}
          {fileQueue.length > 0 && (
            <div className="bg-white dark:bg-gray-800 p-6 rounded-3xl shadow-sm border border-gray-100 dark:border-gray-700">
              <div className="flex justify-between items-center mb-4">
                <h4 className="font-bold text-gray-800 dark:text-white">
                  대기열 ({fileQueue.length}개)
                </h4>
                <div className="flex gap-2">
                    <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => setFileQueue([])} 
                        disabled={isGlobalProcessing}
                        className="text-red-500 hover:text-red-600 hover:bg-red-50"
                    >
                        전체 삭제
                    </Button>
                    <Button 
                        onClick={handleStartUpload} 
                        disabled={isGlobalProcessing || fileQueue.every(f => f.status === 'success')}
                        className="bg-purple-600 hover:bg-purple-700 text-white"
                    >
                        {isGlobalProcessing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                        {isGlobalProcessing ? '처리 중...' : '일괄 등록 시작'}
                    </Button>
                </div>
              </div>

              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                {fileQueue.map((item) => (
                  <div key={item.id} className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-100 dark:border-gray-700">
                    {/* Icon Status */}
                    <div className="flex-shrink-0">
                        {item.status === 'idle' && <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500"><FileText size={16}/></div>}
                        {item.status === 'processing' && <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />}
                        {item.status === 'success' && <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center text-green-600"><CheckCircle size={16}/></div>}
                        {item.status === 'error' && <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-red-600"><AlertCircle size={16}/></div>}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{item.file.name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {item.status === 'processing' && (
                            <div className="w-full bg-gray-200 rounded-full h-1.5 dark:bg-gray-700 max-w-[150px]">
                                <div className="bg-purple-600 h-1.5 rounded-full transition-all" style={{ width: `${item.progress}%` }}></div>
                            </div>
                        )}
                        <p className={`text-xs ${
                            item.status === 'error' ? 'text-red-500' : 
                            item.status === 'success' ? 'text-green-500' : 'text-gray-500'
                        }`}>
                            {item.status === 'idle' ? '대기 중' : 
                             item.status === 'processing' ? 'AI 분석 중...' :
                             item.status === 'success' ? (item.resultMsg || '완료') : 
                             (item.errorMsg || '실패')}
                        </p>
                      </div>
                    </div>

                    {/* Action */}
                    {item.status === 'idle' || item.status === 'error' ? (
                        <button 
                            onClick={() => removeFile(item.id)} 
                            disabled={isGlobalProcessing}
                            className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-gray-400 hover:text-red-500 transition-colors"
                        >
                            <Trash2 size={16} />
                        </button>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 3. Log Area (Right) */}
        <div className="lg:col-span-1">
          <div className="bg-black text-green-400 p-6 rounded-3xl font-mono text-xs h-full min-h-[400px] overflow-hidden flex flex-col shadow-xl border border-gray-800">
            <div className="flex items-center gap-2 border-b border-gray-800 pb-3 mb-3 text-gray-400">
              <FileText size={14} />
              <span className="font-bold tracking-wider">SYSTEM_LOGS</span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-1 custom-scrollbar">
               {logs.length === 0 ? (
                    <span className="text-gray-700 animate-pulse">Waiting for action...</span>
                ) : (
                    logs.map((log, i) => <div key={i} className="break-all hover:bg-gray-900/50 p-1 rounded border-l-2 border-transparent hover:border-green-500 transition-all">{log}</div>)
                )}
                <div ref={useCallback((node: HTMLDivElement | null) => { if (node) node.scrollIntoView({ behavior: 'smooth' }); }, [logs])} />
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}