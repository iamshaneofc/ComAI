import clsx from "clsx";

export function Card({
  title,
  description,
  children,
  className,
}: {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={clsx(
        "rounded-xl border border-slate-200/80 bg-white p-5 shadow-card dark:border-slate-800 dark:bg-slate-900",
        className
      )}
    >
      {(title || description) && (
        <header className="mb-4">
          {title && <h2 className="text-base font-semibold text-ink dark:text-slate-100">{title}</h2>}
          {description && <p className="mt-1 text-sm text-ink-muted">{description}</p>}
        </header>
      )}
      {children}
    </section>
  );
}
