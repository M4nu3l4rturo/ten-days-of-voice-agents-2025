import React, { forwardRef } from 'react';

// --- DATOS DE EJEMPLO DE ÓRDENES (PROPORCIONADOS POR EL USUARIO) ---
// Estos datos están listos para ser utilizados por un componente de Historial de Pedidos.
const SAMPLE_ORDERS = [
  {
    "id": "order-3f7c9e01",
    "items": [
      {
        "product_id": "sneaker-ultraboost-23",
        "name": "Ultraboost 23 Running Shoes",
        "unit_price": 17000,
        "quantity": 1,
        "line_total": 17000,
        "attrs": {
          "size_us": "10.5",
          "color": "Core Black"
        }
      }
    ],
    "total": 17000,
    "currency": "INR",
    "created_at": "2025-11-29T18:05:11.450122Z"
  },
  {
    "id": "order-8b1d5a2f",
    "items": [
      {
        "product_id": "tee-techfit-01",
        "name": "Techfit Training Tee",
        "unit_price": 2500,
        "quantity": 2,
        "line_total": 5000,
        "attrs": {
          "size": "L",
          "color": "White"
        }
      },
      {
        "product_id": "ball-pro-001",
        "name": "Pro Match Football",
        "unit_price": 4500,
        "quantity": 1,
        "line_total": 4500,
        "attrs": {
          "size": "5"
        }
      }
    ],
    "total": 9500,
    "currency": "INR",
    "created_at": "2025-11-29T18:15:30.987654Z"
  },
  {
    "id": "order-5c4a6b3d",
    "items": [
      {
        "product_id": "sneaker-samba-og",
        "name": "Samba OG Classics",
        "unit_price": 8500,
        "quantity": 1,
        "line_total": 8500,
        "attrs": {
          "size_us": "8",
          "color": "White/Green"
        }
      }
    ],
    "total": 8500,
    "currency": "INR",
    "created_at": "2025-11-29T18:22:45.765432Z"
  }
];
// --- FIN DE LOS DATOS DE EJEMPLO ---

// --- UTILIDADES Y COMPONENTES NECESARIOS ---

// Utilidad cn: combina condicionalmente clases de Tailwind
const cn = (...classes) => classes.filter(Boolean).join(' ');

// Tipo de propiedades para el botón (mantenido del original)
interface MockButtonProps extends React.ComponentProps<'button'> {
  variant?: 'default' | 'primary';
  size?: 'default' | 'sm' | 'lg';
  disabled?: boolean;
}

/**
 * Componente Button Mock: implementa un botón básico con estilo de alto contraste Adidas.
 */
const Button = forwardRef<HTMLButtonElement, MockButtonProps>(
  ({ children, onClick, className, variant = 'primary', size = 'default', disabled = false, ...props }, ref) => {
    const baseClasses = 'inline-flex items-center justify-center whitespace-nowrap rounded-sm text-sm font-bold tracking-wide transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 uppercase';

    const sizeClasses = {
      default: 'h-11 px-6 py-2',
      sm: 'h-9 px-4',
      lg: 'h-14 px-10 text-lg',
    }[size];

    // Estilos de alto contraste (Blanco sobre Negro o Negro sobre Blanco)
    const variantClasses = {
      // Primary: Botón de acción principal (Negro sobre Blanco, estilo premium)
      primary: 'bg-white text-black shadow-lg hover:bg-gray-200 focus-visible:ring-white',
      // Default: Botón secundario (Transparente con borde blanco)
      default: 'bg-transparent text-white border border-white hover:bg-white/10 focus-visible:ring-white',
    }[variant];

    return (
      <button
        ref={ref}
        onClick={onClick}
        disabled={disabled}
        className={cn(baseClasses, sizeClasses, variantClasses, className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);


/**
 * Icono inspirado en el logo de las Tres Rayas de Adidas (simulado con geometría).
 */
function ThreeStripesIcon() {
  // SVG que simula el look de rendimiento/movimiento de Adidas
  return (
    <svg 
      width="90" 
      height="90" 
      viewBox="0 0 100 100" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className="mb-8 text-white filter drop-shadow-[0_0_10px_rgba(255,255,255,0.4)]"
    >
      {/* Tres rectángulos inclinados */}
      <rect x="10" y="30" width="80" height="10" fill="white" transform="rotate(-15 10 30)" />
      <rect x="10" y="50" width="80" height="10" fill="white" transform="rotate(-15 10 50)" />
      <rect x="10" y="70" width="80" height="10" fill="white" transform="rotate(-15 10 70)" />
    </svg>
  );
}

// Tipo de propiedades para la vista de bienvenida
interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  disabled?: boolean;
  error?: string | null;
}

/**
 * Vista de bienvenida con estilo de pantalla de inicio de juego.
 * Exportada con nombre (export const) para que coincida con el import { WelcomeView } en view-controller.
 */
export const WelcomeView = React.forwardRef<HTMLDivElement, WelcomeViewProps>(
  ({ startButtonText, onStartCall, disabled = false, error = null }, ref) => {
    return (
      // Contenedor principal con fondo negro profundo y fuente limpia (como Inter/sans-serif)
      <div 
        ref={ref} 
        className="min-h-screen w-full flex items-center justify-center p-4 bg-gray-950 text-white"
      >
        
        {/* Tarjeta de bienvenida minimalista y de alto contraste */}
        <section className="
          bg-gray-900 p-8 md:p-16 
          rounded-sm shadow-2xl shadow-black/80
          flex flex-col items-center justify-center text-center max-w-md w-full
          border-t-4 border-white/80 // Linea superior como detalle de marca
        ">
          
          <ThreeStripesIcon />

          <h1 className="text-5xl sm:text-6xl font-black uppercase text-white mb-2 tracking-tighter">
            Sneaker Hub
          </h1>
          
          <h2 className="text-xl font-light text-gray-300 mb-6 tracking-wider">
            AI Voice Specialist
          </h2>
          
          <p className="text-gray-400 max-w-prose leading-relaxed text-base mb-8 border-b border-gray-700 pb-6">
            Welcome to the future of shopping. Use your voice to browse our latest collection, check sizes, and place an order instantly.
          </p>

          {/* Mostrar error si existe */}
          {error && (
              <p className="text-sm text-red-400 mb-4 p-3 bg-red-900/40 rounded-sm border border-red-700 w-full"> 
                  {error}
              </p>
          )}

          {/* Botón de acción principal */}
          <Button 
            variant="primary" 
            size="lg" 
            onClick={onStartCall} 
            disabled={disabled}
            className={cn(
              "mt-4 w-full max-w-xs transition-transform duration-100 ease-in-out font-extrabold",
              disabled ? 'opacity-70' : 'hover:scale-[1.02] active:scale-95'
            )}
          >
            {startButtonText}
          </Button>

          {/* Indicador de estado del sistema */}
          <div className="mt-8 pt-4 w-full border-t border-gray-800">
              <p className="text-xs text-gray-500 font-medium flex items-center justify-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  <span className="text-gray-400 uppercase tracking-widest">System Operational</span>
              </p>
          </div>
        </section>
      </div>
    );
  }
);
