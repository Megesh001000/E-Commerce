import { useSearchParams } from 'react-router-dom';
import { useEffect,useState } from 'react';
import './Shop.css'
const API_URL = 'http://127.0.0.1:8000/api/products/';
const categoryGroups = {
    Electronics: [
        'Electronics',
        'Laptops',
        'Mobiles',
        'Smart Phones',
        'TVs',
        'Audio',
        'Ear Buds'
    ]
};

function Shop() {
    const [searchParams]=useSearchParams();
    const selectedCategory = searchParams.get('category');

    const [products,setProducts]=useState([]);
    const [loading,setLoading]=useState(true);
    const [error,setError]=useState('');




    useEffect (()=>{
        async function fetchProducts() {
            try{
                setLoading(true);
                setError('');

                const response=await fetch(API_URL);

                if (!response.ok){
                    throw new Error('Unable to fetch products');
                }

                const data=await response.json();
                setProducts(data.results ?? data);
            }catch (err){
                setError(err.message);
            }finally {
                setLoading(false);
            }
        }
        fetchProducts();
        },[])
    
        const filterProducts=selectedCategory ? products.filter(
            product =>{
                const productCategory=product.category?.name?.toLowerCase();
                const childCatgories=categoryGroups[selectedCategory];
                if(childCatgories){
                    return childCatgories.some(
                        category=>category.toLowerCase()===productCategory
                    );
                }
                return -productCategory==selectedCategory.toLowerCase;;
            }):products;


    return(
        <main className="shop-page">
            <section className='shop-header'>
                <div className="container">
                    <span className='section-label'>
                        DISCOVER OUR COLLECTION
                    </span>

                    <h1>{selectedCategory || 'Explore All Products'} </h1>
                    <p>
                        Find your favourites and discover something new.
                    </p>
                </div>
            </section>
            <section className='shop-products-section'>
                <div className="container">
                    <div className="shop-toolbar">
                        <h2>Our Products</h2>

                        <span>
                            {selectedCategory ? `Category:${selectedCategory}`:'All Categories'}
                        </span>
                    </div>
                    {!loading && !error && filterProducts.length===0 &&(
                        <div className="shop-empty">
                            <h3>No products found</h3>
                            <p>Try exploring another category.</p>
                        </div>
                    )}
                    {loading && <p>Loading products...</p>}

                    {error && <p>{error}</p>}

                    {!loading && !error && filterProducts.length >0 &&(
                        <div className="shop-product-grid">
                            {filterProducts.map(product =>{
                                const primaryImage =product.images?.find(image=>image.is_primary);
                                const imageUrl=primaryImage?.image ? `http://127.0.0.1:8000${primaryImage.image}` :primaryImage?.image_url || '';

                                return(
                                    <article className="shop-product-card" key={product.id}>
                                        <div className="shop-product-image">
                                            {imageUrl ?(
                                                <img
                                                    src={imageUrl}
                                                    alt={product.name}
                                                    onError={(e)=>{
                                                        e.currentTarget.style.display= 'none';
                                                        e.currentTarget.parentElement.innerHTML='<div class="product-image-placeholder">Image coming soon</div>';

                                                    }}
                                                />
                                                ):(
                                                    <div className="product-image-placeholder">
                                                        Image coming soon
                                                    </div>
                                                )
                                            };
                                        </div>

                                        <div className="shop-product-info">
                                            <span>{product.category?.name}</span>
                                            <h3>{product.name}</h3>
                                            <p>₹{Number(product.price).toLocaleString('en-IN')}</p>
                                        </div>
                                    </article>
                                );
                            })}
                        </div>
                    )}
                </div>

            </section>
        </main>
    );
}


export default Shop;