import './Home.css';
import { Link } from 'react-router-dom';
function Home() {
    return (
        <main className="home-page">
            <section className='hero-section'>
                <div className='container'>
                    <div className='row align-items-center'>
                        <div className='col-lg-6 hero-content'>
                            <span className='hero-label'>
                                DISCOVER SOMETHING NEW
                            </span>
                            <h1>
                                Everything you love.
                                <span> All in one place.</span>
                            </h1>
                            <p>
                                Explore the latest trends, everyday essentials
                                and products you'll love. Find everything
                                you need, all in one destination.
                            </p>

                            <div className='hero-buttons'>
                                <a href="/shop" className='hero-shop-btn'>
                                    Explore Collection
                                    <span>→</span>
                                </a>
                            </div>

                            <div className='hero-note'>
                                Discover more. Shop better. Live better.
                            </div>    
                        </div>
                        <div className='col-lg-6 hero-visual'>
                                <div className='hero-image-placeholder'>
                                    <div className='hero-image-text'>
                                        <span>YOUR NEXT</span>
                                        <strong>FAVOURITE</strong>
                                        <span>IS WAITING</span>
                                    </div>
                                </div>
                        </div>
                    </div>

                </div>
            </section>
            <section className='categories-section'>
                <div className="container">
                    <div className="categories-heading">
                        <span className="section-label">
                            EXPLORE OUR COLLECTION
                        </span>

                        <h2>Shop by Category</h2>

                        <p>Explore collections curated for your everyday needs.</p>
                    </div>
                    <div className='row'>
                        {[
                            'Fashion',
                            'Electronics',
                            'Beauty',
                            'Home & Living',
                            'Accessories',
                            'Sports'
                        ].map((category,index)=>(
                            <div className='col-lg-4 col-md-6' key={category}>
                                
                                <Link 
                                    to={`/shop?category=${encodeURIComponent(category)}`}
                                    className={`category-card category-${index+1}`}
                                >
                                    <div className="category-card-content">
                                        <h3>{category}</h3>
                                        <span>Explore Collection →</span>
                                    </div>
                                </Link>
                            </div>
                        ))}

                    </div>
                </div>
            </section>
        </main>
    );
}

export default Home;
