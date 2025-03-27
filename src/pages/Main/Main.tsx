import { FC, useState, useEffect, useRef } from 'react';
import {
   PageWrapper,
   PageContainer
} from '../Page.styled.ts';

import { Spinner, Button, Image } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faFaceFrown, faShareFromSquare, faComment } from '@fortawesome/free-solid-svg-icons';

const Main: FC = () => {
   const fileInputRef = useRef<HTMLInputElement | null>(null);

   const [loading, setLoading] = useState(false);

   const [isLoggedIn, setIsLoggedIn] = useState(false);

   const [image, setImage] = useState<string | null>(null);
   const [ocrResult, setOcrResult] = useState<string | null>(null);

   useEffect(() => {
      const token = localStorage.getItem("token");
      if (token) {
         setIsLoggedIn(true);
      }
   }, []);

   const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      if (event.target.files && event.target.files[0]) {
         const file = event.target.files[0];
         const reader = new FileReader();
         reader.onloadend = () => {
            setImage(reader.result as string);
         };
         reader.readAsDataURL(file);
      }
   };

   const handleImageClick = () => {
      if (fileInputRef.current) {
         fileInputRef.current.click();
      }
   };

   const handleSendImage = async () => {
      if (!image) return;

      setLoading(true);
      try {
         const AI_API_URL = import.meta.env.VITE_AI_API_URL;

         const base64Image = image.split(',')[1];
         const response = await fetch(`${AI_API_URL}/ocr/base64`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base64_image: base64Image })
         });
         const data = await response.json();
         setOcrResult(data.text);
      } catch (error) {
         console.error('Error sending image:', error);
      } finally {
         setLoading(false);
      }
   };

   return (
      <PageWrapper>
         <PageContainer>
            {isLoggedIn ? (
               <div>
                  <div style={{
                     display: "flex",
                     justifyContent: "space-between",
                     alignItems: "center",
                     marginBottom: "1rem"
                  }}>
                     <p
                        style={{
                           color: "rgba(255, 255, 255, 0.55)",
                           margin: 0
                        }}
                     >Selected image:</p>
                     <Button
                        variant="success"
                        style={{ padding: "6px 16px" }}
                        disabled={image == null || loading}
                        onClick={handleSendImage}
                     >
                        <FontAwesomeIcon icon={faShareFromSquare} style={{ marginRight: "6px" }} />Send image
                     </Button>
                  </div>
                  <input
                     type="file"
                     accept="image/*"
                     ref={fileInputRef}
                     onChange={handleImageChange}
                     style={{ display: 'none' }}
                  />
                  <div>
                     {image ? (
                        <Image
                           src={image}
                           alt="Select image"
                           fluid
                           style={{
                              cursor: 'pointer',
                              width: '400px',
                              objectFit: 'cover',
                              marginTop: 0
                           }}
                           onClick={handleImageClick}
                        />
                     ) : (
                        <div
                           style={{
                              width: "400px",
                              height: "400px",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              color: "rgba(255, 255, 255, 0.55)",
                              border: "1px solid rgb(33, 37, 41)",
                              cursor: 'pointer',
                              fontSize: "120%"
                           }}
                           onClick={handleImageClick}
                        >
                           <p><FontAwesomeIcon icon={faFaceFrown} /> No image selected</p>
                        </div>
                     )}
                  </div>
                  {loading ? (
                     <div className="d-flex justify-content-center align-items-center" style={{ height: "400px" }}>
                        <Spinner animation="border" style={{ color: "white" }} />
                     </div>
                  ) : (
                     <>
                        {ocrResult ? (
                           <div>
                              <p style={{ color: "rgba(255, 255, 255, 0.55)", margin: "1rem" }}>Found text:</p>
                              <div style={{
                                 display: "flex",
                                 color: "white",
                                 width: "400px",
                                 border: "1px solid rgb(33, 37, 41)",
                                 padding: "1rem"
                              }}>
                                 <FontAwesomeIcon
                                    icon={faComment}
                                    style={{
                                       marginRight: "6px",
                                       color: "rgba(255, 255, 255, 0.55)",
                                       fontSize: "150%"
                                    }}
                                 />
                                 <p style={{
                                    marginBottom: 0
                                 }}>{ocrResult}</p>
                              </div>
                           </div>
                        ) : (
                           <div>
                              <p style={{ color: "rgba(255, 255, 255, 0.55)", margin: "1rem 0" }}>Waiting for image...</p>
                           </div>
                        )}
                     </>
                  )}
               </div>
            ) : (
               <div>
                  <p
                     style={{
                        color: "rgba(255, 255, 255, 0.55)",
                        margin: 0,
                        textAlign: "center"
                     }}
                  ><FontAwesomeIcon icon={faFaceFrown} /> You must be logged in to use this.</p>
               </div>
            )}
         </PageContainer>
      </PageWrapper>
   );
};

export default Main;