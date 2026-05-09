export function SkeletonBlock({ className = "" }) {
  return <div className={`animate-pulse rounded-2xl bg-slate-200/70 ${className}`} />;
}

export function PageSkeleton({ rows = 3 }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <SkeletonBlock key={index} className="h-28" />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-4">
          {Array.from({ length: rows }).map((_, index) => (
            <SkeletonBlock key={index} className="h-32" />
          ))}
        </div>
        <SkeletonBlock className="h-80" />
      </div>
    </div>
  );
}
