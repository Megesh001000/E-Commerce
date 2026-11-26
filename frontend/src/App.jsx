import { useState } from 'react'

import { Route,Routes } from 'react-router-dom'
import './App.css'
import MainNavbar from './components/Navbar'
import Home  from './pages/Home'
import Shop from './pages/Shop'
import ProductDetail from './pages/ProductDetail'



function App() {
  return(
    <>
    <MainNavbar/>
    <Routes>
      <Route path="/" element={<Home />}/>
      <Route path="/shop" element={<Shop />}/>
      <Route path='/shop/product/:slug' element={<ProductDetail/>}/>
      
    </Routes>
    
    </>
  )
}

export default App