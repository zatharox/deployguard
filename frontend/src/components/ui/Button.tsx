import { ReactNode } from 'react';

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void | Promise<void>;
  variant?: 'primary' | 'ghost';
  icon?: string;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
}

export default function Button({
  children,
  onClick,
  variant = 'primary',
  icon,
  disabled = false,
  type = 'button',
}: ButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`ui-button ui-button-${variant}`}
      aria-disabled={disabled}
    >
      {icon && (
        <span className="ui-button-icon" aria-hidden="true">
          {icon}
        </span>
      )}

      <span>{children}</span>
    </button>
  );
}