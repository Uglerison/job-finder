import {
  cloneElement,
  useId,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactElement,
  type ReactNode,
} from 'react';

import './primitives.css';

function classes(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ');
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  loading?: boolean;
  loadingLabel?: string;
  size?: 'small' | 'default' | 'large';
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
};

export function Button({
  children,
  className,
  disabled,
  loading = false,
  loadingLabel = 'Carregando…',
  size = 'default',
  type = 'button',
  variant = 'primary',
  ...props
}: ButtonProps) {
  return (
    <button
      aria-busy={loading || undefined}
      className={classes(
        'ui-button',
        `ui-button--${variant}`,
        `ui-button--${size}`,
        className,
      )}
      disabled={disabled || loading}
      type={type}
      {...props}
    >
      {loading && <span aria-hidden="true" className="ui-spinner" />}
      <span>{loading ? loadingLabel : children}</span>
    </button>
  );
}

type CardProps = HTMLAttributes<HTMLElement> & {
  density?: 'compact' | 'default';
};

export function Card({
  children,
  className,
  density = 'default',
  ...props
}: CardProps) {
  return (
    <section
      className={classes('ui-card', `ui-card--${density}`, className)}
      {...props}
    >
      {children}
    </section>
  );
}

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: 'neutral' | 'success' | 'warning' | 'error';
};

export function Badge({
  children,
  className,
  tone = 'neutral',
  ...props
}: BadgeProps) {
  return (
    <span
      className={classes('ui-badge', `ui-badge--${tone}`, className)}
      {...props}
    >
      {children}
    </span>
  );
}

type AccessibleControlProps = {
  'aria-describedby'?: string;
  'aria-invalid'?: boolean | 'false' | 'true';
};

type FieldProps = {
  children: ReactElement<AccessibleControlProps>;
  className?: string;
  error?: string | null;
  hint?: string;
  htmlFor: string;
  label: string;
};

export function Field({
  children,
  className,
  error,
  hint,
  htmlFor,
  label,
}: FieldProps) {
  const messageId = useId();
  const hintId = hint ? `${messageId}-hint` : undefined;
  const errorId = error ? `${messageId}-error` : undefined;
  const describedBy = [children.props['aria-describedby'], hintId, errorId]
    .filter(Boolean)
    .join(' ');
  const control = cloneElement(children, {
    'aria-describedby': describedBy || undefined,
    'aria-invalid': error ? true : children.props['aria-invalid'],
  });

  return (
    <div className={classes('ui-field', error && 'ui-field--error', className)}>
      <label htmlFor={htmlFor}>{label}</label>
      {control}
      {hint && (
        <span className="ui-field__hint" id={hintId}>
          {hint}
        </span>
      )}
      {error && (
        <span className="ui-field__error" id={errorId} role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

type PageHeaderProps = {
  actions?: ReactNode;
  className?: string;
  description?: ReactNode;
  eyebrow?: string;
  title: string;
};

export function PageHeader({
  actions,
  className,
  description,
  eyebrow,
  title,
}: PageHeaderProps) {
  return (
    <header className={classes('ui-page-header', className)}>
      <div className="ui-page-header__copy">
        {eyebrow && <span className="ui-meta-label">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="ui-page-header__actions">{actions}</div>}
    </header>
  );
}

type NoticeProps = HTMLAttributes<HTMLDivElement> & {
  title?: string;
  tone?: 'info' | 'success' | 'warning' | 'error';
};

export function Notice({
  children,
  className,
  title,
  tone = 'info',
  ...props
}: NoticeProps) {
  return (
    <div
      className={classes('ui-notice', `ui-notice--${tone}`, className)}
      role={tone === 'error' ? 'alert' : 'status'}
      {...props}
    >
      {title && <strong>{title}</strong>}
      <div>{children}</div>
    </div>
  );
}

type EmptyStateProps = {
  action?: ReactNode;
  className?: string;
  description: ReactNode;
  title: string;
};

export function EmptyState({
  action,
  className,
  description,
  title,
}: EmptyStateProps) {
  return (
    <section className={classes('ui-empty-state', className)}>
      <span aria-hidden="true" className="ui-empty-state__mark">
        ∅
      </span>
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action && <div className="ui-empty-state__action">{action}</div>}
    </section>
  );
}

type LoadingStateProps = {
  className?: string;
  label?: string;
};

export function LoadingState({
  className,
  label = 'Carregando',
}: LoadingStateProps) {
  return (
    <div
      aria-label={label}
      className={classes('ui-loading-state', className)}
      role="status"
    >
      <span aria-hidden="true" className="ui-spinner" />
      <span>{label}</span>
    </div>
  );
}
