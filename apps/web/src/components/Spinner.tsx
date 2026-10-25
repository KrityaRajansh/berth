export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-10 text-sm text-slate-600">
      <span
        aria-hidden
        className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent"
      />
      {label}
    </div>
  );
}
