import { useState, useEffect } from 'react';
import './ScrollToTop.css';

function getScrollContainer(): HTMLElement | Window {
    return document.querySelector<HTMLElement>('.content-wrapper') ?? window;
}

export const ScrollToTop = () => {
    const [isVisible, setIsVisible] = useState(false);

    const toggleVisibility = (scrollContainer: HTMLElement | Window) => {
        const scrollTop = scrollContainer instanceof Window ? scrollContainer.scrollY : scrollContainer.scrollTop;

        setIsVisible(scrollTop > 300);
    };

    const scrollToTop = () => {
        const scrollContainer = getScrollContainer();
        scrollContainer.scrollTo({
            top: 0,
            behavior: 'smooth',
        });
    };

    useEffect(() => {
        const scrollContainer = getScrollContainer();
        const onScroll = () => toggleVisibility(scrollContainer);
        scrollContainer.addEventListener('scroll', onScroll);
        toggleVisibility(scrollContainer);

        return () => {
            scrollContainer.removeEventListener('scroll', onScroll);
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
