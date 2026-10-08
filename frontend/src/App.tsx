import { useEffect } from 'react'
import { Route, Routes, useLocation, useNavigationType } from 'react-router-dom'
import NavBar from './components/NavBar.tsx'
import Footer from './components/Footer.tsx'
import Home from './pages/Home.tsx'
import Products from './pages/Products.tsx'
import About from './pages/About.tsx'
import Login from './pages/Login.tsx'
import Signup from './pages/Signup.tsx'
import NotFound from './pages/NotFound.tsx'
import ProductDetail from './pages/ProductDetail.tsx'
import ChatWidget from './components/ChatWidget.tsx'
import ChatResults from './components/ChatResults.tsx'

const TITLES: Record<string, string> = {
  '/': 'Campus Customs | Yale Bulldog Blue',
  '/products': 'Products | Campus Customs',
  '/about': 'About Us | Campus Customs',
  '/login': 'Log in | Campus Customs',
  '/signup': 'Create account | Campus Customs',
}

function RouteEffects() {
  const { pathname } = useLocation()
  const navigationType = useNavigationType()
  useEffect(() => {
    // New pages start at the top; Back/Forward keeps the browser's restored scroll position.
    if (navigationType !== 'POP') window.scrollTo(0, 0)
    // Product pages set their own title once the product loads.
    if (!pathname.startsWith('/products/')) document.title = TITLES[pathname] ?? 'Page not found | Campus Customs'
  }, [pathname, navigationType])
  return null
}

export default function App() {
  return (
    <div className="app">
      <RouteEffects />
      <NavBar />
      <main className="main">
        <ChatResults />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
      <ChatWidget />
    </div>
  )
}
