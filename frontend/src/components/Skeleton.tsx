import React from "react";
import "./Skeleton.css";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  className?: string;
  style?: React.CSSProperties;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width,
  height,
  borderRadius,
  className = "",
  style,
}) => {
  const customStyles: React.CSSProperties = {
    width: width ?? "100%",
    height: height ?? "1rem",
    borderRadius: borderRadius ?? "6px",
    ...style,
  };

  return <div className={`skeleton-shimmer ${className}`} style={customStyles} />;
};

export const SkeletonCard: React.FC<{ rows?: number }> = ({ rows = 3 }) => {
  return (
    <div className="skeleton-card-container">
      <div className="skeleton-card-header">
        <Skeleton width="44px" height="44px" borderRadius="12px" />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "6px" }}>
          <Skeleton width="60%" height="16px" />
          <Skeleton width="40%" height="12px" />
        </div>
      </div>
      <div className="skeleton-card-body">
        {Array.from({ length: rows }).map((_, idx) => (
          <Skeleton
            key={idx}
            width={idx === rows - 1 ? "75%" : "100%"}
            height="14px"
            style={{ marginBottom: "8px" }}
          />
        ))}
      </div>
    </div>
  );
};

export const SkeletonTable: React.FC<{ rows?: number; columns?: number }> = ({
  rows = 5,
  columns = 4,
}) => {
  return (
    <div className="skeleton-table-container">
      <div className="skeleton-table-header">
        {Array.from({ length: columns }).map((_, idx) => (
          <Skeleton key={idx} width="70%" height="14px" />
        ))}
      </div>
      <div className="skeleton-table-body">
        {Array.from({ length: rows }).map((_, rIdx) => (
          <div key={rIdx} className="skeleton-table-row">
            {Array.from({ length: columns }).map((_, cIdx) => (
              <Skeleton
                key={cIdx}
                width={cIdx === 0 ? "85%" : "60%"}
                height="14px"
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};
