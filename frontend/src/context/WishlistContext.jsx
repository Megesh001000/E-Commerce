import { createContext,useContext,useState } from "react";
const WishlistContext=createContext();
export function WishlistProvider({children}){
    const [wishlist,setWishlist]=useState([]);

    const toggleWishlist=(product)=>{
        setWishlist(prev=>{
            const alreadyAdded=prev.some(item=>item.id===product.id);

            if(alreadyAdded){
                return prev.filter(item=>item.id !== product.id);
            }

            return [...prev,product];
        });
    };

    const isWishlisted =(productId)=>{
        return wishlist.some(item=>item.id===productId)
    }

    return(
        <WishlistContext.Provider 
            value={{
                wishlist,
                toggleWishlist,
                isWishlisted
            }}
        >
             {children}
        
        </WishlistContext.Provider>
    );
}

export function useWishlist(){
    return useContext(WishlistContext);
}