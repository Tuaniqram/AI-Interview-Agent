import { ReactNode, Children, useRef, useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface CarouselProps {
  children: ReactNode;
  className?: string;
  autoPlay?: boolean;
  interval?: number;
}

export function Carousel({ children, className = '', autoPlay = false, interval = 5000 }: CarouselProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const dragState = useRef({ isDragging: false, startX: 0, scrollLeft: 0 });
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const items = useRef(Children.toArray(children));
  items.current = Children.toArray(children);

  const updateScrollState = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 0);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth);
    const slides = Array.from(el.children) as HTMLElement[];
    let nearest = 0;
    let minDist = Infinity;
    slides.forEach((slide, i) => {
      const d = Math.abs(el.scrollLeft - slide.offsetLeft);
      if (d < minDist) { minDist = d; nearest = i; }
    });
    setCurrentPage(nearest);
    setTotalPages(slides.length);
  }, []);

  const scrollToPage = useCallback((page: number) => {
    const el = scrollRef.current;
    if (!el) return;
    (el.children[page] as HTMLElement)?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const el = scrollRef.current;
    if (!el) return;
    dragState.current.isDragging = true;
    dragState.current.startX = e.pageX - el.getBoundingClientRect().left;
    dragState.current.scrollLeft = el.scrollLeft;
    el.style.cursor = 'grabbing';
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragState.current.isDragging) return;
    e.preventDefault();
    const el = scrollRef.current;
    if (!el) return;
    const x = e.pageX - el.getBoundingClientRect().left;
    const walk = (x - dragState.current.startX) * 1.5;
    el.scrollLeft = dragState.current.scrollLeft - walk;
  }, []);

  const handleMouseUp = useCallback(() => {
    if (!dragState.current.isDragging) return;
    dragState.current.isDragging = false;
    const el = scrollRef.current;
    if (el) el.style.cursor = '';
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => updateScrollState();
    el.addEventListener('scroll', onScroll, { passive: true });
    updateScrollState();
    return () => el.removeEventListener('scroll', onScroll);
  }, [updateScrollState]);

  useEffect(() => {
    if (!autoPlay || items.current.length < 2) return;
    const id = setInterval(() => {
      const el = scrollRef.current;
      if (!el) return;
      const slides = Array.from(el.children) as HTMLElement[];
      if (!slides.length) return;
      const next = (currentPage + 1) % slides.length;
      slides[next].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
    }, interval);
    return () => clearInterval(id);
  }, [autoPlay, interval, currentPage]);

  if (items.current.length === 0) return null;

  return (
    <div className={`relative group ${className}`}>
      <div
        ref={scrollRef}
        className="overflow-x-auto scrollbar-none flex snap-x snap-mandatory cursor-grab"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {items.current.map((item, i) => (
          <div key={i} className="snap-start shrink-0">
            {item}
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <>
          <button
            type="button"
            onClick={() => {
              const el = scrollRef.current;
              if (!el) return;
              const prev = el.children[Math.max(0, currentPage - 1)] as HTMLElement;
              prev?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
            }}
            disabled={!canScrollLeft}
            className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 text-white items-center justify-center transition-opacity opacity-0 group-hover:opacity-100 disabled:opacity-0 hidden md:flex"
            aria-label="Previous slide"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <button
            type="button"
            onClick={() => {
              const el = scrollRef.current;
              if (!el) return;
              const next = el.children[Math.min(totalPages - 1, currentPage + 1)] as HTMLElement;
              next?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
            }}
            disabled={!canScrollRight}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 text-white items-center justify-center transition-opacity opacity-0 group-hover:opacity-100 disabled:opacity-0 hidden md:flex"
            aria-label="Next slide"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-1.5 mt-3">
          {Array.from({ length: totalPages }).map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => scrollToPage(i)}
              className={`w-2 h-2 rounded-full transition-all ${
                i === currentPage ? 'bg-[var(--action-primary)] w-4' : 'bg-[var(--border-color)]'
              }`}
              aria-label={`Go to slide ${i + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
