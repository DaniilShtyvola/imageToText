import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Header from './components/PageHeader/PageHeader.tsx';
import Auth from './pages/Auth/Auth.tsx';
import Main from './pages/Main/Main.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
         <Header />
         <main>
            <Routes>
               <Route path="/" element={<Main />} />
               <Route path="/login" element={<Auth />} />
            </Routes>
         </main>
      </BrowserRouter>
  </StrictMode>,
)
