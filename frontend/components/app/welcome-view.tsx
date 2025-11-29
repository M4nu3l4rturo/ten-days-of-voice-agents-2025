import React from 'react';

// --- UTILIDADES MOCK (Para resolver el error de importación de ruta) ---
// Utilidad cn: combina condicionalmente clases de Tailwind
const cn = (...classes: (string | undefined | null | boolean)[]) => classes.filter(Boolean).join(' ');

interface MockButtonProps extends React.ComponentProps<'button'> {
  variant?: 'default' | 'primary';
  size?: 'default' | 'sm' | 'lg';
}

/**
 * Componente Button Mock: implementa un botón básico con estilos de Tailwind
 * para asegurar la funcionalidad sin dependencias externas.
 */
const Button = ({ children, onClick, className, variant = 'default', size = 'default', ...props }: MockButtonProps) => {
  const baseClasses = 'inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';

  const sizeClasses = {
    default: 'h-10 px-4 py-2',
    sm: 'h-9 rounded-md px-3',
    lg: 'h-11 px-8 rounded-xl',
  }[size];

  const variantClasses = {
    default: 'bg-gray-100 text-gray-900 shadow-sm hover:bg-gray-200',
    primary: 'bg-blue-600 text-white shadow-lg hover:bg-blue-700',
  }[variant];

  return (
    <button
      onClick={onClick}
      className={cn(baseClasses, sizeClasses, variantClasses, className)}
      {...props}
    >
      {children}
    </button>
  );
};
// ----------------------------------------------------------------


/**
 * Icono de Gamepad/Joystick para la vista de bienvenida con estilo gaming.
 */
function GameIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="80"
      height="80"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-yellow-400 mb-6 drop-shadow-lg"
    >
      {/* Icono Gamepad */}
      <path d="M6 10h2l3-3l1 1l3-3h2"></path>
      <path d="M12 21a9 9 0 0 0 9-9v-3l-3-1l-3 3h-6l-3-3l-3 1v3a9 9 0 0 0 9 9z"></path>
      <path d="M12 15h0"></path>
      <path d="M9 15h0"></path>
      <path d="M15 15h0"></path>
    </svg>
  );
}

// Tipo de propiedades para la vista de bienvenida
interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

/**
 * Vista de bienvenida con estilo de pantalla de inicio de juego.
 * Se utiliza React.forwardRef para pasar el ref correctamente.
 */
const WelcomeView = React.forwardRef<HTMLDivElement, WelcomeViewProps>(
  ({ startButtonText, onStartCall }, ref) => {
    return (
      // Contenedor principal para centrar la sección de bienvenida y aplicar el fondo del juego
      <div ref={ref} className="min-h-screen w-full flex items-center justify-center p-4 bg-zinc-950 text-white font-mono">
        
        {/* Tarjeta de bienvenida con estilo de arcade/juego */}
        <section className="
          bg-zinc-800/80 backdrop-blur-sm p-8 md:p-12 
          rounded-2xl shadow-[0_0_40px_rgba(255,255,0,0.3),0_0_15px_rgba(255,255,255,0.1)]
          flex flex-col items-center justify-center text-center max-w-lg w-full
          border-2 border-yellow-400/50
        ">
          
          <GameIcon /> {/* Icono de Gamepad */}

          <h1 className="text-4xl sm:text-5xl font-extrabold text-yellow-400 mb-2 drop-shadow-md tracking-wider">
            AI VOICE CHALLENGE
          </h1>
          
          <p className="text-gray-300 max-w-prose pt-1 leading-6 text-lg mb-8">
            Prepárate para interactuar con tu agente de voz AI en esta simulación.
          </p>

          {/* Utilizamos el componente 'Button' mock (autocontenido) */}
          <Button 
            variant="primary" 
            size="lg" 
            onClick={onStartCall} 
            className="mt-4 w-full max-w-xs text-xl font-bold uppercase
                       bg-green-500 hover:bg-green-600 text-white
                       shadow-[0_4px_0_0_#16a34a] hover:shadow-[0_2px_0_0_#16a34a] 
                       active:translate-y-[2px] transition-all duration-100 ease-out"
          >
            {startButtonText}
          </Button>
        </section>
        
        {/* Pie de página simple para estado */}
        <div className="fixed bottom-4 left-0 w-full flex justify-center">
          <p className="text-gray-500 text-sm font-mono tracking-wider">
            {/* Usamos un pequeño indicador de estado */}
            <span className="inline-block w-3 h-3 bg-green-500 rounded-full animate-pulse mr-2"></span>
            SISTEMA OPERACIONAL
          </p>
        </div>
      </div>
    );
  }
);

// Se cambia de export default a exportación con nombre para coincidir con la importación en view-controller.tsx
export { WelcomeView };
