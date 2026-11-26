import { useParams } from "react-router-dom";
import { useState,useEffect } from "react";

import "./ProductDetail.css"

const API_URL = 'http://127.0.0.1:8000/api/products/';

function ProductDetail(){
    const {slug}=useParams();
    const [product,setProduct]=useState(null);
    const [loading,setLoading]=useState(true);
    const [error,setError]=useState('');
    const[quantity,setQuantity]=useState(1);
    const [selectedImage,setSelectedImage]=useState(null);


    useEffect(()=>{
        async function fetchProduct() {
            try{
                setLoading(true);
                setError('');

                const response=await fetch(`${API_URL}?search=${slug}`);

                if(!response.ok){
                    throw new Error('Unable to fetch product');
                }

                const data=await response.json();
                
                const products=data.results ?? data;

                const foundProduct=products.find(
                    item=>item.slug ===slug
                );
                if (!foundProduct) {
                    throw new Error('Product not found');
                }
                setProduct(foundProduct);
                const initialImage=foundProduct.images?.find(image=>image.is_primary) || foundProduct.images?.[0] || null;
                setSelectedImage(initialImage)
            }catch(err){
                setError(err.message);
            }finally{
                setLoading(false);
            }     
        }
        fetchProduct();
    },[slug]);

    if (loading) return <p>Loading product...</p>;
    if (error) return <p>{error}</p>;

    const primaryImage=product.images?.find(
        image=>image.is_primary
    );

    const productImages=product.images?.filter(image=>image.image||image.image_url) || [];

    const getImageUrl=(image)=>{
        if (image.image){
            return `http://127.0.0.1:8000${image.image}`;
        }
        return image.image_url||'';
    }
    const imageUrl=primaryImage?.image?`http://127.0.0.1:8000${primaryImage.image}`: primaryImage?.image_url || '';

  return (
    <main className="product-detail-page">
        <div className="container">
            <div className="product-detail-layout">
                <div className="product0gallery">
                    <div className="product-detail-image">
                        {/* main image */}
                        {selectedImage ? (
                            <img src={getImageUrl(selectedImage)} alt={product.name} />
                        ):(
                            <div className="product-image-placeholder">
                                Image coming soon
                            </div>
                        )
                        }
                    </div>
                    {/* Image thumbnails */}
                    {productImages.length>1&&(
                        <div className="product-thumbnails">
                            {productImages.map(image=>
                                <button 
                                    key={image.id}
                                    className={`product-thumbnail ${selectedImage?.id===image?.id?'active':''}`} 
                                    onClick={()=>setSelectedImage(image)}
                                >
                                    <img
                                        src={getImageUrl(image)}
                                        alt={product.name}
                                    />

                                </button>
                            )}
                            
                        </div>
                    )}
                </div>
                {/* Right: Product Information */}
                <div className="product-detail-info">
                    <span className="product-category">{product.category?.name}</span>

                    <h1>{product.name}</h1>

                    <h2>
                        ₹{Number(product.price).toLocaleString('en-IN')}
                    </h2>

                    <p className="product-description">{product.description || 'No description available.'}</p>

                    <p>
                        Brand: {product.brand?.name || 'Unbranded'}
                    </p>

                    <p>
                        {product.stock >0
                        ?`In stock: ${product.stock}`
                        :'Out of stock'}
                    </p>
                    <div className="product-quantity">
                        <label >Quantity</label>
                        <div className="quantity-controls">
                            <button
                                onClick={()=>setQuantity(prev=>Math.max(1,prev-1))}
                                disabled={quantity<=1}
                            >
                                -
                            </button>

                            <span>{quantity}</span>
                            <button
                                onClick={()=>setQuantity(prev=>Math.min(product.stock,prev+1))}
                                disabled={quantity>=product.stock}
                            >
                                +
                            </button>
                        </div>
                    </div>
                    <button className="add-to-cart-btn" disabled={product.stock<=0}>
                            {product.stock >0 ? "Add to Cart":"Out of Stock"}
                    </button>
                </div>  
            </div>      
        </div>
    </main>
  )
}

export default ProductDetail
