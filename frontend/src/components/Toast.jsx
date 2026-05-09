export default function Toast({ toast, onClose }) {
  if (!toast) {
    return null;
  }

  const toneClass =
    toast.type === "error"
      ? "border-red-200 bg-red-50 text-red-800"
      : "border-emerald-200 bg-emerald-50 text-emerald-800";

  return (
    <div className="fixed bottom-5 right-5 z-50 w-[min(22rem,calc(100vw-2rem))]">
      <div className={`rounded-2xl border px-4 py-3 shadow-lg ${toneClass}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">{toast.title}</p>
            {toast.message ? (
              <p className="mt-1 text-sm leading-5 opacity-80">{toast.message}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg px-2 text-lg leading-6 opacity-70 transition hover:bg-white/50 hover:opacity-100"
            aria-label="Закрыть уведомление"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  );
}
