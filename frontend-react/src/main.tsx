const { React, ReactDOM } = window;

const init = () => {
    // Wait until Babel standalone has compiled App.tsx
    if (!window.Components.App) {
        setTimeout(init, 50);
        return;
    }

    const { App } = window.Components;
    const rootElement = document.getElementById('root');
    
    if (rootElement) {
        const root = ReactDOM.createRoot(rootElement);
        root.render(
            <React.StrictMode>
                <App />
            </React.StrictMode>
        );
    }
};

init();
