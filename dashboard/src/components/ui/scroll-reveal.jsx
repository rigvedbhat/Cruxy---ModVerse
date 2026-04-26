import React, { useState, useRef, useEffect } from 'react';

export const ScrollReveal = ({ children, className = "", delay = 0, once = true }) => {
    const [isVisible, setIsVisible] = useState(false);
    const domRef = useRef();

    useEffect(() => {
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        setIsVisible(true);
                    }, delay);
                    if (once && domRef.current) observer.unobserve(domRef.current);
                }
            });
        }, { threshold: 0.1 });
        
        const currentRef = domRef.current;
        if (currentRef) observer.observe(currentRef);
        return () => {
            if (currentRef) observer.unobserve(currentRef);
        };
    }, [delay, once]);

    return (
        <div 
            ref={domRef} 
            className={`transition-all duration-1000 ease-out transform ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'} relative z-20 ${className}`}
        >
            {children}
        </div>
    );
};
