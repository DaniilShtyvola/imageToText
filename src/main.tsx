import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Header from "./components/PageHeader/PageHeader.tsx";
import Auth from "./pages/Auth/Auth.tsx";
import ImageToText from "./pages/ImageToText/ImageToText.tsx";
import TranslateText from "./pages/TranslateText/TranslateText.tsx";
import Admin from "./pages/Admin/Admin.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Header />
      <main>
        <Routes>
          <Route path='/' element={<></>} />
          <Route path='/login' element={<Auth />} />
          <Route path='/admin' element={<Admin />} />
          <Route path='/image-to-text' element={<ImageToText />} />
          <Route path='/translate-text' element={<TranslateText />} />
        </Routes>
      </main>
    </BrowserRouter>
  </StrictMode>,
);
