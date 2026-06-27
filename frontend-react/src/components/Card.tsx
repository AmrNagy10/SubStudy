// Card Component

interface CardProps {
    children: React.ReactNode;
    className?: string;
}

const Card: React.FC<CardProps> = ({ children, className = '' }) => {
    return (
        <div className={`bg-dark-800 border border-dark-700 rounded-2xl shadow-xl ${className}`}>
            {children}
        </div>
    );
};

window.Components.Card = Card;
