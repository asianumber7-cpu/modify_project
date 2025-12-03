import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search as SearchIcon, Mic, UploadCloud, X, Loader2, Volume2, AlertCircle } from 'lucide-react';
import client from '../api/client';
import ProductCard from '../components/product/ProductCard';

// Mock Data Types
interface ProductResponse {
    id: number;
    name: string;
    description: string;
    price: number;
    category: string;
    image_url: string;
    in_stock: boolean;
}

interface SearchResult {
    status: 'SUCCESS' | 'FAILURE';
    answer: string;
    products: ProductResponse[];
    search_path: 'INTERNAL' | 'EXTERNAL';
}

// 환경 변수 처리 (Vite)
const API_ENDPOINT = '/search/ai-search'; // client의 baseURL이 적용되므로 상대 경로 사용

const useSearchQuery = () => {
    const [searchParams] = useSearchParams();
    return searchParams.get('q') || '';
};

// TTS 유틸리티
const useTTS = () => {
    const speak = useCallback((text: string) => {
        if ('speechSynthesis' in window) {
            // 기존 발화 취소 (새로운 내용 우선)
            window.speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'ko-KR';
            utterance.rate = 1.0; // 속도 조절
            window.speechSynthesis.speak(utterance);
        } else {
            console.warn("TTS is not supported in this browser.");
        }
    }, []);
    return { speak };
};

export default function SearchPage() {
    const queryTextFromUrl = useSearchQuery();
    const [query, setQuery] = useState(queryTextFromUrl);
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [results, setResults] = useState<ProductResponse[]>([]);
    const [answer, setAnswer] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isError, setIsError] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    
    const { speak } = useTTS();

    // 파일 핸들링
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                alert('이미지 파일만 업로드할 수 있습니다.');
                return;
            }
            setImageFile(file);
        }
    };

    const handleImageDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            setImageFile(file);
        } else {
            alert('이미지 파일을 드래그해주세요.');
        }
    }, []);

    // 음성 인식 (Feature 8)
    const handleVoiceSearch = () => {
        if (!('webkitSpeechRecognition' in window)) {
            alert('브라우저가 음성 인식을 지원하지 않습니다. Chrome 사용을 권장합니다.');
            return;
        }

        const recognition = new (window as any).webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.lang = 'ko-KR';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => speak("듣고 있습니다. 검색어를 말씀해 주세요.");

        recognition.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            setQuery(transcript);
            // 음성 인식 성공 시 즉시 검색 트리거 (isVoice: true)
            handleSearch(transcript, imageFile, true); 
        };

        recognition.onerror = (event: any) => {
            console.error('Speech recognition error:', event.error);
            speak('죄송합니다. 음성을 잘 못 들었습니다.');
        };

        recognition.start();
    };

    // 통합 검색 실행
    // isVoice 파라미터 추가: 음성 검색 여부 판별
    const handleSearch = useCallback(async (currentQuery: string, currentImage: File | null, isVoice: boolean = false) => {
        if (!currentQuery && !currentImage) {
            if (isVoice) speak('검색어 또는 이미지가 확인되지 않았습니다.');
            return;
        }

        setIsLoading(true);
        setIsError(false);
        setResults([]);
        setAnswer(null);

        // API 호출용 FormData
        const formData = new FormData();
        formData.append('query', currentQuery);
        if (currentImage) {
            formData.append('image_file', currentImage);
        }

        try {
            // client 인스턴스 사용 (Base URL, Interceptor 적용)
            const response = await client.post<SearchResult>(API_ENDPOINT, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            const data = response.data;
            setAnswer(data.answer);
            setResults(data.products);
            
            // Feature 8 수정: 음성 검색(isVoice=true)일 때만 TTS 작동
            // + 모든 상품명이 아닌 AI 요약 답변(data.answer)만 읽음
            if (data.status === 'SUCCESS' && data.answer && isVoice) {
                speak(data.answer);
            }

        } catch (error: any) {
            console.error(error);
            const errorMessage = '검색 처리 중 오류가 발생했습니다.';
            setIsError(true);
            setResults([]);
            if (isVoice) speak(errorMessage);
        } finally {
            setIsLoading(false);
        }
    }, [speak]);

    // 폼 제출 (엔터 키 or 버튼 클릭) -> 음성 아님(false)
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        handleSearch(query, imageFile, false);
    };
    
    const previewUrl = imageFile ? URL.createObjectURL(imageFile) : null;

    // Deep Linking 처리 (URL 쿼리 파라미터) -> 음성 아님(false)
    useEffect(() => {
        if (queryTextFromUrl) {
            setQuery(queryTextFromUrl);
            handleSearch(queryTextFromUrl, null, false);
        }
    }, [queryTextFromUrl, handleSearch]);

    return (
        <div className="max-w-6xl mx-auto p-6 space-y-8">
            <h1 className="text-3xl font-bold text-gray-900">AI 통합 검색</h1>

            {/* 검색 입력 영역 */}
            <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
                <div className="flex items-center space-x-3 mb-4">
                    <SearchIcon className="w-5 h-5 text-gray-500" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="예: 청룡 영화제 아이유가 입은 코트 또는 빨간색 니트"
                        className="flex-1 text-lg border-none focus:ring-0 outline-none placeholder:text-gray-400"
                        aria-label="검색어 입력"
                    />
                    <button 
                        type="button" 
                        onClick={handleVoiceSearch}
                        className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                        aria-label="음성 검색 시작"
                    >
                        <Mic className="w-5 h-5 text-blue-500" />
                    </button>
                    <button 
                        type="submit" 
                        disabled={isLoading || (!query && !imageFile)}
                        className="px-4 py-2 bg-black text-white rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 transition-colors"
                    >
                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : '검색'}
                    </button>
                </div>

                {/* 이미지 업로드/미리보기 */}
                <div 
                    className={`mt-4 border-2 border-dashed rounded-lg p-4 transition-colors ${
                        imageFile ? 'border-green-400' : 'border-gray-300 hover:border-gray-400'
                    }`}
                    onDrop={handleImageDrop}
                    onDragOver={(e) => e.preventDefault()}
                >
                    {imageFile ? (
                        <div className="flex items-center space-x-4">
                            <img src={previewUrl || ''} alt="업로드 이미지 미리보기" className="w-16 h-16 object-cover rounded-md" />
                            <div className="flex-1">
                                <p className="text-sm font-medium text-gray-700">{imageFile.name}</p>
                                <p className="text-xs text-gray-500">클릭하여 교체하거나 X를 눌러 삭제</p>
                            </div>
                            <button onClick={() => setImageFile(null)} type="button" className="text-gray-500 hover:text-red-500" aria-label="이미지 삭제">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                    ) : (
                        <div className="text-center">
                            <input
                                type="file"
                                accept="image/*"
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                className="hidden"
                                id="image-upload-btn"
                            />
                            <label htmlFor="image-upload-btn" className="flex flex-col items-center cursor-pointer p-4">
                                <UploadCloud className="w-8 h-8 text-gray-400" />
                                <p className="text-sm text-gray-500 mt-2">이미지를 드래그하거나 클릭하여 업로드</p>
                            </label>
                        </div>
                    )}
                </div>
            </form>

            {/* 검색 결과 */}
            <div className="pt-6">
                <h2 className="text-xl font-semibold mb-4">검색 결과 ({results.length}개)</h2>
                
                {isLoading && (
                    <div className="flex flex-col items-center py-10">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                        <p className="mt-4 text-gray-600">
                            AI가 복잡한 검색을 분석 중입니다. 잠시만 기다려주세요...
                        </p>
                    </div>
                )}

                {!isLoading && isError && (
                    <div className="text-center py-10 text-red-500 bg-red-50 rounded-lg">
                        <AlertCircle className="w-6 h-6 mx-auto mb-2" />
                        <p>통합 검색 중 오류가 발생했습니다.</p>
                    </div>
                )}

                {/* AI 추천 답변 */}
                {!isLoading && !isError && answer && (
                    <div className="mb-10 p-6 bg-purple-50 rounded-2xl border border-purple-100 shadow-sm">
                        <h3 className="font-bold text-lg mb-2 text-purple-800 flex items-center gap-2">
                            <span className="text-xl">💡</span> AI 스타일리스트 추천
                            <button onClick={() => speak(answer)} className="p-1 rounded-full hover:bg-purple-100 transition-colors" aria-label="AI 답변 듣기">
                                <Volume2 className="w-4 h-4 text-purple-600" />
                            </button>
                        </h3>
                        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                            {answer}
                        </p>
                    </div>
                )}

                {/* 상품 리스트 */}
                {!isLoading && !isError && results.length > 0 ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                        {results.map((product) => (
                            <ProductCard key={product.id} product={product} /> 
                        ))}
                    </div>
                ) : (
                     !isLoading && !isError && (queryTextFromUrl || imageFile) && results.length === 0 && (
                        <div className="text-center py-10 text-gray-500">
                            검색 결과가 없습니다.
                        </div>
                    )
                )}

                {/* 하단 꼬리물기 검색 UI */}
                <div className="mt-12 fixed bottom-8 left-0 right-0 px-4 md:px-0 max-w-3xl mx-auto z-50 pointer-events-none">
                     <div className="bg-white/80 backdrop-blur-lg border border-gray-200 rounded-2xl shadow-2xl p-4 flex gap-3 ring-1 ring-black/5 pointer-events-auto">
                        <div className="w-10 h-10 bg-indigo-600 rounded-full flex items-center justify-center text-white shrink-0 shadow-md">
                            AI
                        </div>
                        <input 
                            type="text" 
                            placeholder="여기에 어울리는 하의를 추천해줄래?"
                            className="w-full bg-transparent outline-none text-gray-800 placeholder-gray-400"
                            aria-label="후속 검색 질문"
                            // 추후 기능 구현 예정 (엔터 시 handleSearch 호출 등)
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    setQuery(e.currentTarget.value);
                                    handleSearch(e.currentTarget.value, null, false);
                                    e.currentTarget.value = '';
                                }
                            }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}