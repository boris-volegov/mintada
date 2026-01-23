import { useState, useEffect } from 'react';
import './ScrollToTop.css';

export const ScrollToTop = () => {
    const [isVisible, setIsVisible] = useState(false);

    const toggleVisibility = () => {
        const scrollContainer = document.querySelector('.content-wrapper') || window;
        const scrollTop = scrollContainer instanceof Window ? scrollContainer.scrollY : scrollContainer.scrollTop;

        if (scrollTop > 300) {
            setIsVisible(true);
        } else {
            setIsVisible(false);
        }
    };

    const scrollToTop = () => {
        const scrollContainer = document.querySelector('.content-wrapper') || window;
        scrollContainer.scrollTo({
            top: 0,
            behavior: 'smooth',
        });
    };

    useEffect(() => {
        const scrollContainer = document.querySelector('.content-wrapper') || window;
        scrollContainer.addEventListener('scroll', toggleVisibility);
        return () => {
            scrollContainer.removeEventListener('scroll', toggleVisibility);
        };
    }, []);

    if (!isVisible) {
        return null;
    }

    return (
        <button className="scroll-to-top" onClick={scrollToTop} aria-label="Scroll to top">
            <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
            >
                <path d="M12 19V5" />
                <path d="M5 12l7-7 7 7" />
            </svg>
        </button>
    );
};
