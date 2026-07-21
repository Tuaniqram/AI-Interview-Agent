import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
}

const paddings = { sm: 'p-3', md: 'p-4', lg: 'p-6' };

export function Card({ children, className = '', hover = false, padding = 'md', onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={`bg-elevated shadow-sm rounded-xl ${paddings[padding]} ${
        hover ? 'shadow-md transition-shadow' : ''
      } ${onClick ? 'cursor-pointer' : ''} focus-visible:outline-none ${className}`}
    >
      {children}
    </div>
  );
}
