// Button Component

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost';
    fullWidth?: boolean;
}

const Button: React.FC<ButtonProps> = ({ 
    children, 
    variant = 'primary', 
    fullWidth = false, 
    className = '', 
    disabled,
    ...props 
}) => {
    const baseClasses = "inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-dark-900";
    
    const variants = {
        primary: "bg-primary text-white hover:bg-[#6b4ce6] focus:ring-primary shadow-[0_0_15px_rgba(124,92,255,0.4)] hover:shadow-[0_0_25px_rgba(124,92,255,0.6)] disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed",
        secondary: "bg-dark-800 text-gray-200 border border-dark-700 hover:border-gray-500 focus:ring-gray-500",
        ghost: "text-gray-400 hover:text-white hover:bg-dark-800"
    };

    const widthClass = fullWidth ? "w-full" : "";
    const paddingClass = "px-6 py-3";

    return (
        <button 
            className={`${baseClasses} ${variants[variant]} ${widthClass} ${paddingClass} ${className}`}
            disabled={disabled}
            {...props}
        >
            {children}
        </button>
    );
};

window.Components.Button = Button;
