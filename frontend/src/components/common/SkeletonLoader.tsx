import React from 'react';

interface Props {
  lines?: number;
  className?: string;
}

export const SkeletonLoader: React.FC<Props> = ({ lines = 4, className = '' }) => {
  return (
    <div className={`animate-pulse space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 bg-[#18202c] rounded"
          style={{ width: `${Math.max(40, 100 - i * 15)}%` }}
        />
      ))}
    </div>
  );
};
