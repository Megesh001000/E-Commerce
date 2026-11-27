import { useParams } from "react-router-dom";
import { useState,useEffect } from "react";

import "./ProductDetail.css"
import productDetails from "../data/ProductDetails"
import reviewsData from "../data/reviewsData";

const API_URL = 'http://127.0.0.1:8000/api/products/';

function RatingStars({rating,color}){
    return(
        <div className="rating-stars">
            {[1,2,3,4,5].map(star=>{
                const fill=Math.min(
                    Math.max(rating-(star-1),0),
                    1
                );
                return(
                    <span className="rating-star" key={star}>
                        ★
                        <span 
                            className="rating-star-fill" 
                            style={{width:`${fill * 100}%`,color:color}}
                             
                        >
                             ★
                        </span>
                    </span>
                )
                
            })}
           
        </div>
    )
}
function ProductDetail(){
    const {slug}=useParams();
    const [product,setProduct]=useState(null);
    const [loading,setLoading]=useState(true);
    const [error,setError]=useState('');
    const[quantity,setQuantity]=useState(1);
    const [selectedImage,setSelectedImage]=useState(null);
    const [openSection,setOpenSection]=useState('highlights')

    const [reviewReaction,setReviewReaction]=useState({})
    const [replyOpen,setReplyOpen]=useState({})
    const [replyTexts,setReplyTexts]=useState({})
    const [postedReplies,setPostedReplies]=useState({})

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
    const extraDetails=productDetails[product.slug] ||{
        highlights:[],
        specifications:[]
    };

    const reviewData=reviewsData[product.slug]||{
        averageRating:0,
        totalReviews:0,
        ratingBreakdown:[],
        comments:[]
    };
    const getRatingColor=(rating)=>{
        if (rating >=4) return  "#16A34A"; // green
        if(rating>=3) return  "#E9A23B"; // orange
        return "#DC2626"; // red

    }

    const handleReviewReaction =(reviewId,reaction)=>{
        setReviewReaction(prev=>({
            [reviewId]:prev[reviewId]===reaction?null:reaction
        }))
    }
    

    const productImages=product.images?.filter(image=>image.image||image.image_url) || [];

    const getImageUrl=(image)=>{
        if (image.image){
            return `http://127.0.0.1:8000${image.image}`;
        }
        return image.image_url||'';
    }

  return (
    <main className="product-detail-page">
        <div className="container">
            <div className="product-detail-layout">
                <div className="product-gallery">
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
            <section className="product-extra-details">
                <div className="detail-accordion">
                    <button 
                        className="detail-accordion-header"
                        onClick={()=>setOpenSection(openSection==='highlights' ? null:"highlights")} 
                    >
                        <h2>Product Highlights</h2>
                        <span>{openSection==="highlights"?"-":"+"}</span>

                    </button>
                    {openSection ==="highlights" && (
                        <div className="detail-accordion-content">
                            <ul>
                                {extraDetails.highlights.map((item,index)=>(
                                    <li key={index}>{item}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
                {/* specifications */}
                <div className="detail-accordion">
                    <button
                        className="detail-accordion-header"
                        onClick={()=>setOpenSection(openSection==="specifications"?null:"specifications")}
                    >
                        <h2>Specifications</h2>
                        <span>{openSection==="specifications"?"-":"+"}</span>

                    </button>
                    {openSection==="specifications" &&(
                        <div className="detail-accordion-content">
                            {extraDetails.specifications.map((item,index)=>(
                                <div className="specification-row" key={index}>
                                    <span>{item.label}</span>
                                    <strong>{item.value}</strong>
                                </div>
                            ))}
                        </div>

                    )}
                </div>
            </section>    
            <section className="product-reviews">
                <h2>Customer Reviews</h2>
                
                <div className="rating-summary">
                    {/* left - avg rating*/}

                    <div className="rating-overview">
                        <h3>{reviewData.averageRating.toFixed(1)}</h3>
                        <RatingStars
                            rating={reviewData.averageRating}
                            color={getRatingColor(reviewData.averageRating)}
                        />
                        <p>{reviewData.totalReviews} customer reviews</p>
                    </div>
                    {/* Right: Rating distribution */}
                    <div className="rating-breakdown">
                        {reviewData.ratingBreakdown.map(item=>(
                            <div className="rating-bar-row" key={item.stars}>
                                <span>{item.stars} ★</span>

                                <div className="rating-bar">
                                    <div 
                                        className="rating-bar-fill"
                                        style={{
                                            width: reviewData.totalReviews >0
                                            ? `${(item.count/reviewData.totalReviews)*100}%`
                                            : "0%",
                                            backgroundColor:getRatingColor(item.stars)
                                        }}
                                        
                                    />  
                                </div>
                                <span>{item.count}</span>
                            </div>
                        ))}
                    </div> 
                </div>

                <div className="review-list">
                    <h3>REcent Reviews</h3>
                </div>
            </section>
        </div>
       
    </main>
  )
}

export default ProductDetail
