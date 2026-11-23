import Container from "react-bootstrap/Container";
import Nav from "react-bootstrap/Nav";
import Navbar from "react-bootstrap/Navbar";
import {Search,ShoppingBag,UserRound} from "lucide-react";
import { useState } from "react";
import "./Navbar.css";
function MainNavbar(){
    const [expanded,setExpanded]=useState(false);
    return(
        <Navbar expand="lg" className="nova-navbar" expanded={expanded} onToggle={setExpanded}>
            <Container>
                <Navbar.Brand href="/" className="nova-brand">nōva<span>.</span></Navbar.Brand>
                <Navbar.Toggle aria-controls="nova-navigation" aria-label="Toggle navigation" className={`custom-toggler ${expanded ? 'active' : ' '}`}>
                    <span></span>
                    <span></span>
                    <span></span>
                </Navbar.Toggle>
                    <Navbar.Collapse className="nova-navigation">
                        <Nav className="mx-auto nova-links">
                            <Nav.Link href="/" onClick={()=>setExpanded(false)}>Home </Nav.Link>
                            <Nav.Link href="/shop"  onClick={()=>setExpanded(false)}>Shop</Nav.Link>
                            <Nav.Link href="/categories" onClick={()=>setExpanded(false)}>Categories</Nav.Link>
                            <Nav.Link href="/about"  onClick={()=>setExpanded(false)}>About</Nav.Link>
                        </Nav>

                        <div className="nova-actions">
                            <button aria-label="Search"><Search /></button>
                            <button aria-label="Account"><UserRound /></button>
                            <button aria-label="Shopping bag"><ShoppingBag /></button>
                        </div>
                    </Navbar.Collapse>
            
            </Container>
        </Navbar>
    );
}

export default MainNavbar   