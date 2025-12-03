// frontend/src/pages/ProductDetail.tsx

import React, { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query'; // [FIX] 올바른 Import
import client from '../api/client'; 
import { Loader2, Zap, Heart, MessageSquare, ShoppingCart, Send, Maximize2 } from 'lucide-react';
import ProductCard from '../components/product/ProductCard'; 
import Modal from '../components/ui/Modal'; 
import { useProductDetail } from '../hooks/useProducts'; // [FIX] 기존 훅 재사용

// Data Types
interface ProductResponse {
  id: number;
  name: string;
  description: string;
  price: number;
  stock_quantity: number;
  category: string;
  image_url: string;
  in_stock: boolean;
  created_at: string;
  updated_at: string;
}

interface CoordinationResponse {
    answer: string;
    products: ProductResponse[];
}

interface LLMQueryResponse {
    answer: string;
}

// [FIX] React Query의 useMutation을 올바르게 사용
// client.useMutation이 아니라 useMutation 훅 내부에서 client.post를 호출합니다.
const useLLMQuery = (productId: number) => {
    return useMutation<LLMQueryResponse, Error, string>({
        mutationFn: async (question: string) => {
            // client는 Axios Instance입니다.
            const res = await client.post(`/products/${productId}/llm-query`, { question });
            return res.data;
        },
    });
};

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  
  // hooks/useProducts.ts에 정의된 훅 사용
  const { data: product, isLoading: isProductLoading, isError: isProductError } = useProductDetail(id);
  
  // AI 코디 관련 상태
  const [coordinationResult, setCoordinationResult] = useState<CoordinationResponse | null>(null);
  const [isCoordinationLoading, setIsCoordinationLoading] = useState(false);

  // LLM 질문 상태
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [qaHistory, setQaHistory] = useState<Array<{ type: 'user' | 'ai', text: string }>>([]);
  
  // Hook 호출 (조건부 렌더링 이전에 선언 - Hooks 규칙 준수)
  const llmQueryMutation = useLLMQuery(product?.id || 0);

  // 모달 상태
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalContent, setModalContent] = useState<React.ReactNode>(null);

  // 장바구니 및 위시리스트 상태 관리
  const [isWished, setIsWished] = useState(false);

  // --------------------------------------------------
  // AI 기능 핸들러
  // --------------------------------------------------

  // AI 코디 추천 기능
  const handleAICoordination = useCallback(async () => {
    if (!product) return;
    setIsCoordinationLoading(true);
    setCoordinationResult(null);

    try {
        // [FIX] 백엔드 URL 구조에 맞게 수정 (/api/v1은 client baseURL에 포함됨)
        const res = await client.get<CoordinationResponse>(`/products/ai-coordination/${product.id}`); 
        const apiResponse = res.data;

        setCoordinationResult(apiResponse);
        
        setModalTitle("✨ AI 스타일리스트 추천 코디");
        setModalContent(
            <div className="space-y-6">
                <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
                    <p className="text-gray-800 font-medium whitespace-pre-wrap leading-relaxed">
                        {apiResponse.answer}
                    </p>
                </div>
                <div>
                    <h4 className="text-sm font-bold text-gray-500 mb-3">추천 아이템</h4>
                    {apiResponse.products.length > 0 ? (
                        <div className="grid grid-cols-2 gap-4">
                            {apiResponse.products.map(p => (
                                <ProductCard key={p.id} product={p} />
                            ))}
                        </div>
                    ) : (
                        <p className="text-center text-gray-400 py-4">추천 상품을 찾지 못했습니다.</p>
                    )}
                </div>
            </div>
        );
        setIsModalOpen(true);

    } catch (e) {
        alert('AI 코디 분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        console.error("AI Coordination Error:", e);
    } finally {
        setIsCoordinationLoading(false);
    }
  }, [product]);

  // --------------------------------------------------
  // UI 기능 핸들러 (Mock API 연결)
  // --------------------------------------------------
  const handleAddToCart = () => {
    // 🚨 [FIX 7] 장바구니 기능 Mock: 실제 API 연결 전까지 동작하도록 처리
    alert(`🛒 ${product?.name} (ID: ${product?.id}) 장바구니에 담기 성공!`);
  };
  
  const handleToggleWishlist = () => {
    // 🚨 [FIX 8] 하트 기능 Mock: 상태 변경 및 알림 처리
    setIsWished(prev => !prev);
    alert(`💖 위시리스트 ${isWished ? '제거' : '추가'} 완료`);
  };

  // LLM 질문 제출 핸들러
  const handleLLMSubmit = () => {
    const trimmedQuestion = currentQuestion.trim();
    if (!trimmedQuestion || llmQueryMutation.isPending) return;

    setQaHistory(prev => [...prev, { type: 'user', text: trimmedQuestion }]);
    setCurrentQuestion('');

    llmQueryMutation.mutate(trimmedQuestion, {
        onSuccess: (data) => {
            setQaHistory(prev => [...prev, { type: 'ai', text: data.answer }]);
        },
        onError: (error) => {
            setQaHistory(prev => [...prev, { type: 'ai', text: "죄송합니다. AI 서비스 연결에 실패했습니다." }]);
            console.error(error);
        }
    });
  };
  
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleLLMSubmit();
    }
  };

  // --------------------------------------------------
  // 렌더링
  // --------------------------------------------------
  if (isProductLoading) {
    return <div className="text-center py-40"><Loader2 className="w-10 h-10 animate-spin mx-auto text-gray-300" /></div>;
  }
  if (isProductError || !product) {
    return <div className="text-center py-40 text-gray-500">상품 정보를 불러올 수 없습니다.</div>;
  }

  const defaultAIBriefing = product.description 
    ? product.description 
    : "AI가 상품 상세 정보를 분석하고 있습니다...";

  const getMockPriceRange = (price: number) => {
      const min = Math.floor(price * 0.9 / 1000) * 1000;
      const max = Math.ceil(price * 1.1 / 1000) * 1000;
      return `${min.toLocaleString()}원 ~ ${max.toLocaleString()}원`;
  };

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 animate-fade-in">
      {/* 상품 정보 영역 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 mb-16">
        
        {/* 이미지/갤러리 */}
        <div className="relative bg-gray-100 rounded-2xl overflow-hidden aspect-[3/4] shadow-sm">
            <img 
                src={product.image_url || "/placeholder.png"} 
                alt={product.name} 
                className="w-full h-full object-cover hover:scale-105 transition-transform duration-500"
                onError={(e) => (e.currentTarget.src = "/placeholder.png")}
            />
            <button className="absolute top-4 right-4 p-2 bg-white/70 backdrop-blur-md rounded-full text-gray-700 hover:bg-white transition-all shadow-sm">
                <Maximize2 className="w-5 h-5" />
            </button>
        </div>

        {/* 상품 상세 */}
        <div className="flex flex-col justify-center space-y-8">
          <div>
            <p className="text-sm font-bold text-indigo-600 mb-2 tracking-wide uppercase">{product.category}</p>
            <h1 className="text-4xl font-bold text-gray-900 leading-tight mb-4">{product.name}</h1>
            <p className="text-3xl font-medium text-gray-900">{product.price.toLocaleString()}원</p>
          </div>

          <div className="prose prose-sm text-gray-600 border-t border-gray-100 pt-6">
             <p>{product.description}</p>
          </div>
          
          <div className="space-y-4 pt-4">
             <div className="flex items-center space-x-2 text-sm text-gray-500">
                <div className={`w-2 h-2 rounded-full ${product.in_stock ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span>{product.in_stock ? `재고 보유 (${product.stock_quantity}개)` : '일시 품절'}</span>
             </div>

              <div className="flex space-x-3">
                <button 
                    // 🚨 [FIX 9] onClick 핸들러 추가: 장바구니 Mock 함수 연결
                    onClick={handleAddToCart}
                    className="flex-1 py-4 bg-gray-900 text-white font-bold rounded-xl flex items-center justify-center space-x-2 hover:bg-black transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-1"
                >
                  <span>장바구니 담기</span>
                </button>
                <button 
                    // 🚨 [FIX 10] onClick 핸들러 추가 및 상태 기반 스타일 적용
                    onClick={handleToggleWishlist}
                    className={`p-4 bg-white border border-gray-200 rounded-xl transition-colors ${isWished ? 'text-red-500 hover:bg-red-50 border-red-200' : 'text-gray-700 hover:bg-gray-50'}`}
                >
                 <Heart className="w-5 h-5 fill-current" />
                </button>
              </div>
          </div>
          
          {/* AI 추천 버튼들 */}
          <div className="pt-8 border-t border-gray-100">
             <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                <Zap className="w-4 h-4 text-yellow-500 mr-1" /> AI 쇼핑 어시스턴트
             </h3>
             <div className="flex flex-wrap gap-2">
                <button 
                    onClick={handleAICoordination} 
                    disabled={isCoordinationLoading}
                    className="flex items-center space-x-2 px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-sm font-medium rounded-full shadow-md hover:shadow-lg hover:from-purple-700 hover:to-indigo-700 transition-all disabled:opacity-70"
                >
                    {isCoordinationLoading ? <Loader2 className='w-4 h-4 animate-spin' /> : <Zap className="w-4 h-4" />}
                    <span>이 옷과 어울리는 코디 추천</span>
                </button>
                <button className="btn-ai-subtle">
                    비슷한 가격대 ({getMockPriceRange(product.price)})
                </button>
                <button className="btn-ai-subtle">
                    유사한 스타일
                </button>
             </div>
          </div>
        </div>
      </div>

      {/* LLM 상품 설명 및 Q&A 영역 */}
      <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
        <div className="p-6 md:p-8 bg-gradient-to-br from-indigo-50 to-white border-b border-indigo-50">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                <div className="p-2 bg-indigo-100 rounded-lg">
                    <MessageSquare className="w-6 h-6 text-indigo-600" />
                </div>
                AI 스타일리스트에게 물어보세요
            </h2>
        </div>
        
        <div className="p-6 md:p-8 grid md:grid-cols-3 gap-8">
            <div className="md:col-span-1 space-y-4">
                <div className="p-5 bg-gray-50 rounded-xl border border-gray-100">
                    <strong className="block text-indigo-600 mb-2 text-sm font-bold uppercase tracking-wider">AI Insight</strong> 
                    <p className="text-gray-700 text-sm leading-relaxed">{defaultAIBriefing}</p>
                </div>
                <div className="p-5 bg-blue-50 rounded-xl border border-blue-100">
                     <p className="text-blue-800 text-xs font-medium">
                        💡 팁: "이 옷 세탁은 어떻게 해?", "여름에 입기 더울까?" 처럼 자연스럽게 물어보세요.
                     </p>
                </div>
            </div>

            {/* Q&A 채팅창 */}
            <div className="md:col-span-2 flex flex-col h-[500px] border border-gray-200 rounded-xl bg-white shadow-inner">
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {qaHistory.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-3">
                            <MessageSquare className="w-12 h-12 opacity-20" />
                            <p>궁금한 점을 입력하시면 AI가 즉시 답변해드립니다.</p>
                        </div>
                    ) : (
                        qaHistory.map((item, index) => (
                            <div key={index} className={`flex ${item.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[80%] p-3.5 rounded-2xl text-sm leading-relaxed shadow-sm ${
                                    item.type === 'user' 
                                    ? 'bg-gray-900 text-white rounded-br-none' 
                                    : 'bg-indigo-50 text-gray-800 rounded-tl-none border border-indigo-100'
                                }`}>
                                    {item.text}
                                </div>
                            </div>
                        ))
                    )}
                    {llmQueryMutation.isPending && (
                        <div className="flex justify-start">
                            <div className="bg-white border border-gray-100 p-3 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                                <span className="text-xs text-gray-500 font-medium">AI가 답변 작성 중...</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="p-4 border-t border-gray-100 bg-gray-50/50">
                    <div className="flex gap-2">
                        <input 
                            type="text"
                            value={currentQuestion}
                            onChange={(e) => setCurrentQuestion(e.target.value)}
                            onKeyPress={handleKeyPress}
                            disabled={llmQueryMutation.isPending}
                            placeholder="상품에 대해 궁금한 점을 입력하세요..."
                            className="flex-1 px-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all shadow-sm text-sm"
                        />
                        <button
                            onClick={handleLLMSubmit}
                            disabled={llmQueryMutation.isPending || !currentQuestion.trim()}
                            className="px-5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-sm"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
      </div>
      
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={modalTitle} maxWidth="max-w-3xl">
        {modalContent}
      </Modal>

      <style>{`
          .btn-ai-subtle {
              @apply px-4 py-2 bg-white border border-gray-200 text-gray-600 text-xs font-medium rounded-full hover:bg-gray-50 hover:border-gray-300 transition-colors;
          }
          @keyframes fade-in {
              from { opacity: 0; transform: translateY(10px); }
              to { opacity: 1; transform: translateY(0); }
          }
          .animate-fade-in {
              animation: fade-in 0.5s ease-out forwards;
          }
      `}</style>
    </div>
  );
}