import { Link } from 'react-router-dom';
import { OpenAPI } from "../../api";
import background1 from "../../assets/images/background_1.png";
import browseCatalog from "../../assets/images/browse_catalog.png";
import manageCoinCollection from "../../assets/images/manage_coin_collection.png";

import './LandingPage.css';

export function LandingPage() {
    return (
        <div className="landing-page-container" style={{
            backgroundImage: `url(${background1})`
        }}>

            {/* Headline Section */}
            <div className="landing-headline-section">
                <h1 className="landing-title">
                    Explore coins. Organize your collection.
                </h1>
                <p className="landing-subtitle">
                    Browse a world coin catalog and keep your personal collection tidy — with fast search, lists, and item management.
                </p>
            </div>

            <div className="landing-buttons-container">
                {/* 1. Catalog Button */}
                <Link to="/catalog/issuers" className="landing-card-link">
                    <div className="landing-card">
                        {/* Gradient Stripe */}
                        <div className="card-stripe-gradient-yellow" />

                        <div className="card-image-container-catalog">
                            <img
                                src={browseCatalog}
                                alt="Catalog"
                                className="card-image"
                            />
                        </div>

                        {/* Middle Separator Gradient */}
                        <div className="card-stripe-middle-yellow" />

                        <div className="card-text-container">
                            <h2 className="card-title-yellow">
                                Catalog of World Coins
                            </h2>
                        </div>
                    </div>
                </Link>

                {/* 2. Collection Button */}
                <Link to="/collection" className="landing-card-link">
                    <div className="landing-card">
                        {/* Gradient Stripe */}
                        <div className="card-stripe-gradient-green" />

                        <div className="card-image-container-collection">
                            <img
                                src={manageCoinCollection}
                                alt="Collection"
                                className="card-image"
                            />
                        </div>

                        {/* Middle Separator Gradient */}
                        <div className="card-stripe-middle-green" />

                        <div className="card-text-container">
                            <h2 className="card-title-green">
                                Manage Your Collection
                            </h2>
                        </div>
                    </div>
                </Link>
            </div>
        </div>
    );
}

export default LandingPage;
