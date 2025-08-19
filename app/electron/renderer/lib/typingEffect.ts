import { useEffect, useRef } from 'react';

interface UseTypingEffectOptions {
  text: string;
  onUpdate: (text: string) => void;
  onComplete?: () => void;
  skip?: boolean;
  baseDelay?: number;
  punctuationDelay?: number;
}

export function useTypingEffect({
  text,
  onUpdate,
  onComplete,
  skip = false,
  baseDelay = 25,
  punctuationDelay = 200,
}: UseTypingEffectOptions) {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const indexRef = useRef(0);

  useEffect(() => {
    if (skip) {
      onUpdate(text);
      onComplete?.();
      return;
    }

    // Intl.Segmenter 사용 (크롬 지원)
    let segments: string[] = [];
    
    console.log('타이핑 효과 시작:', text);
    console.log('텍스트 길이:', text.length);
    
    if (typeof Intl !== 'undefined' && 'Segmenter' in Intl) {
      // @ts-ignore - Intl.Segmenter는 아직 TypeScript 타입이 없을 수 있음
      const segmenter = new Intl.Segmenter('ko', { granularity: 'grapheme' });
      segments = Array.from(segmenter.segment(text), seg => seg.segment);
      console.log('Intl.Segmenter 사용, segments:', segments);
    } else {
      // 폴백: grapheme-splitter 사용
      try {
        const GraphemeSplitter = require('grapheme-splitter');
        const splitter = new GraphemeSplitter();
        segments = splitter.splitGraphemes(text);
        console.log('GraphemeSplitter 사용, segments:', segments);
      } catch {
        // 최종 폴백: 기본 split
        segments = text.split('');
        console.log('기본 split 사용, segments:', segments);
      }
    }

    indexRef.current = 0;

    const typeNext = () => {
      if (indexRef.current < segments.length) {
        const currentSegment = segments[indexRef.current];
        const displayText = segments.slice(0, indexRef.current + 1).join('');
        
        console.log(`타이핑 단계 ${indexRef.current}: '${currentSegment}' → '${displayText}'`);
        
        onUpdate(displayText);
        indexRef.current++;

        // 지연 시간 계산
        let delay = baseDelay;
        
        // 구두점 뒤 추가 지연
        if (/[.,!?…]/.test(currentSegment)) {
          delay += punctuationDelay;
        }
        
        // 줄바꿈 뒤 추가 지연
        if (currentSegment === '\n') {
          delay += punctuationDelay / 2;
        }

        console.log(`다음 타이핑 예약: ${delay}ms 후 단계 ${indexRef.current}`);
        timeoutRef.current = setTimeout(typeNext, delay);
      } else {
        // 완료
        onComplete?.();
      }
    };

    typeNext();

    return () => {
      console.log('타이핑 효과 cleanup 호출됨, 현재 index:', indexRef.current);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        console.log('타이핑 timeout 정리됨');
      }
    };
  }, [text, skip, baseDelay, punctuationDelay, onUpdate, onComplete]);
}
