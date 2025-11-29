import React, { forwardRef } from 'react';

// =============================================================================
// UTILIDADES
// =============================================================================

/**
 * Utilidad cn: combina condicionalmente clases de Tailwind.
 */
const cn = (...classes: (string | boolean | undefined)[]) => classes.filter(Boolean).join(' ');

// =============================================================================
// COMPONENTE BUTTON
// =============================================================================

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary';
  size?: 'default' | 'sm' | 'lg';
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, className, variant = 'default', size = 'default', disabled = false, ...props }, ref) => {
    const baseClasses = 'inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';

    const sizeClasses = {
      default: 'h-10 px-4 py-2',
      sm: 'h-9 rounded-md px-3',
      lg: 'h-12 px-6 rounded-xl text-lg',
    }[size];

    const variantClasses = {
      default: 'bg-gray-700 text-gray-200 shadow-sm hover:bg-gray-600 focus-visible:ring-gray-400',
      primary: 'bg-gradient-to-r from-orange-600 to-orange-500 text-white shadow-lg hover:from-orange-500 hover:to-orange-400 focus-visible:ring-orange-400',
    }[variant];

    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(baseClasses, sizeClasses, variantClasses, className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

// =============================================================================
// ICONO QUICKBASKET
// =============================================================================

function QuickBasketIcon() {
  return (
    <svg
      width="80"
      height="80"
      viewBox="0 0 80 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="mb-6 drop-shadow-xl"
    >
      <defs>
        <linearGradient id="basketGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FF6B35" />
          <stop offset="100%" stopColor="#FF9B66" />
        </linearGradient>
      </defs>
      {/* Cuerpo del carrito */}
      <path
        d="M20 25H60L55 50H25L20 25Z"
        fill="url(#basketGradient)"
        stroke="#FF6B35"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      {/* Base del carrito */}
      <path
        d="M25 50L21 65H59L55 50"
        stroke="#FF6B35"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Ruedas */}
      <circle cx="30" cy="70" r="4" fill="#FF6B35" />
      <circle cx="50" cy="70" r="4" fill="#FF6B35" />
      {/* Asa del carrito */}
      <path
        d="M30 25C30 18 35 15 40 15C45 15 50 18 50 25"
        stroke="#4A90E2"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  );
}

// =============================================================================
// COMPONENTE WELCOME VIEW
// =============================================================================

interface WelcomeViewProps {
  startButtonText?: string;
  onStartCall: () => void;
  disabled?: boolean;
  error?: string;
}

export const WelcomeView: React.FC<WelcomeViewProps> = ({
  startButtonText = '🎤 Hablar con Marielena',
  onStartCall,
  disabled = false,
  error,
}) => {
  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <section
        className="
          bg-gray-800/90 backdrop-blur-sm
          p-8 md:p-12 
          rounded-3xl 
          shadow-2xl shadow-orange-500/20
          flex flex-col items-center justify-center text-center 
          max-w-lg w-full
          border border-gray-700/50
          transition-all duration-300 hover:shadow-orange-500/30
        "
      >
        {/* Icono */}
        <QuickBasketIcon />

        {/* Título Principal */}
        <h1 className="text-4xl sm:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-orange-600 mb-2">
          Forum Supermayoristas
        </h1>

        {/* Subtítulo */}
        <h2 className="text-xl sm:text-2xl font-semibold text-gray-300 mb-2">
          Tu Asistente de Compras IA
        </h2>

        {/* Badge de Marielena */}
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-orange-500/10 border border-orange-500/30 rounded-full mb-6">
          <span className="text-2xl">🇻🇪</span>
          <span className="text-sm font-medium text-orange-300">Impulsado por Marielena</span>
        </div>

        {/* Descripción */}
        <p className="text-gray-400 max-w-prose leading-relaxed text-base mb-8 px-4">
          Marielena, tu compañera de compras experta, te ayudará a armar tu lista usando solo tu voz. 
          Dile lo que necesitas y ella lo agregará a tu carrito en tiempo real.
        </p>

        {/* Características destacadas */}
        <div className="grid grid-cols-2 gap-3 w-full mb-8 text-sm">
          <div className="flex items-center gap-2 text-gray-400">
            <span className="text-orange-400">🥘</span>
            <span>Recetas Criollas</span>
          </div>
          <div className="flex items-center gap-2 text-gray-400">
            <span className="text-orange-400">🚀</span>
            <span>Delivery Rápido</span>
          </div>
          <div className="flex items-center gap-2 text-gray-400">
            <span className="text-orange-400">🎤</span>
            <span>Pide por Voz</span>
          </div>
          <div className="flex items-center gap-2 text-gray-400">
            <span className="text-orange-400">💲</span>
            <span>Precios de Mayor</span>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="w-full mb-4 p-4 bg-red-900/40 border border-red-700/50 rounded-xl">
            <p className="text-sm text-red-300 flex items-center gap-2">
              <span className="text-lg">⚠️</span>
              {error}
            </p>
          </div>
        )}

        {/* Botón Principal */}
        <Button
          variant="primary"
          size="lg"
          onClick={onStartCall}
          disabled={disabled}
          className={cn(
            'w-full max-w-xs transition-transform duration-200 ease-out font-semibold',
            disabled ? 'opacity-70 cursor-not-allowed' : 'hover:scale-[1.03] active:scale-[0.98]'
          )}
        >
          {disabled ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin">⏳</span>
              Conectando...
            </span>
          ) : (
            startButtonText
          )}
        </Button>

        {/* Footer Info */}
        <div className="mt-8 pt-6 w-full border-t border-gray-700/50">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <span className="text-sm text-gray-400 font-medium">Agente listo para conectar</span>
          </div>
          <p className="text-xs text-gray-500">
            Powered by{' '}
            <span className="text-orange-400 font-semibold">LiveKit</span>
            {' '}&{' '}
            <span className="text-orange-400 font-semibold">Murf AI</span>
          </p>
        </div>
      </section>
    </div>
  );
};

export default WelcomeView;
