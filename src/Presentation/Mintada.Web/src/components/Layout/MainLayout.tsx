import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { OpenAPI } from '../../api';
import './MainLayout.css';

interface MainLayoutProps {
    children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {

    return (
        <div className="app-container">
            {/* 1. Yellow Brand Stripe (Split into Solid Logo part & Gradient rest) */}
            <header className="brand-stripe-container">
                <div className="brand-part-solid">
                    <Link to="/" className="brand-link">
                        <img
                            src={`${OpenAPI.BASE}/images/branding/mintada_logo.png`}
                            alt="Mintada"
                            className="brand-logo"
                        />
                    </Link>
                </div>

                <div className="brand-part-gradient">
                    <div className="language-selector">
                        <span>EN</span>
                        <span className="arrow-down"></span>
                    </div>
                    <div className="auth-buttons">
                        <button className="btn-auth-ghost">Sign in</button>
                        <button className="btn-auth-solid">Register</button>
                    </div>
                </div>
            </header>

            {/* 2. Secondary Navigation Bar Removed as per request */}

            <main className="main-content-area">
                <div className="content-wrapper">
                    {children}
                </div>
            </main>
        </div>
    );
}
