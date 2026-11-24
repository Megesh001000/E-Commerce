import { useState } from 'react'

import { Route,Routes } from 'react-router-dom'
import './App.css'
import MainNavbar from './components/Navbar'
import Home  from './pages/Home'


function App() {
  return(
    <>
    <MainNavbar/>
    <Routes>
      <Route path="/" element={<Home/>}/>
      <Route path="/shop" element={}/>

      
    </Routes>
    <Home/>
    </>
  )
}

export default App