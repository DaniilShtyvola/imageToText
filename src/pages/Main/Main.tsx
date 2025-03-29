import { FC, useState, useEffect, useRef } from 'react';
import {
   PageWrapper,
   PageContainer
} from '../Page.styled.ts';

import { Spinner, Button, Image, Alert } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faFaceFrown, faShareFromSquare, faComment, faQuestion } from '@fortawesome/free-solid-svg-icons';

const Main: FC = () => {
   const fileInputRef = useRef<HTMLInputElement | null>(null);

   const [loading, setLoading] = useState(false);
   const [isLoggedIn, setIsLoggedIn] = useState(false);

   const [image, setImage] = useState<string | null>(null);
   const [ocrResult, setOcrResult] = useState<string | null>(null);

   const [errorMessage, setErrorMessage] = useState<string | null>(null);

   const API_URL = import.meta.env.VITE_API_URL;

   useEffect(() => {
      const token = localStorage.getItem("token");
      if (token) {
         setIsLoggedIn(true);
      }

      const handleLogOutUpdate = () => {
         setIsLoggedIn(false);
      };
      window.addEventListener("loggedOut", handleLogOutUpdate);

      return () => {
         window.removeEventListener("loggedOut", handleLogOutUpdate);
      };
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

   const checkSubscription = async (username: string): Promise<boolean> => {
      try {
         const response = await fetch(`${ API_URL }/subscription_status/${ username }`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
         });

         if (!response.ok) {
            throw new Error(`HTTP error! status: ${ response.status }`);
         }

         const data = await response.json();
         return data.subscription_status === "active";
      } catch (error) {
         console.error("Error checking subscription:", error);
         return false;
      }
   };

   const handleSendImage = async () => {
      if (!image) return;
      const token = localStorage.getItem("token");

      if (!token) {
         setErrorMessage("You must be logged in.");
         return;
      }

      setLoading(true);
      setErrorMessage(null);

      const isSubscribed = await checkSubscription(token);
      // if (!isSubscribed) {
      //    setLoading(false);
      //    setErrorMessage("Your subscription is inactive. Please renew it to use this feature.");
      //    return;
      // }
      return;

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
                  {errorMessage && (
                     <Alert variant="danger" onClose={() => setErrorMessage(null)} style={{ width: "400px" }} dismissible>
                        {errorMessage}
                     </Alert>
                  )}
                  <div style={{
                     display: "flex",
                     justifyContent: "space-between",
                     alignItems: "center",
                     marginBottom: "1rem"
                  }}>
                     <p style={{
                        color: "rgba(255, 255, 255, 0.55)",
                        margin: 0
                     }}>Selected image:</p>
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
                     <div style={{ display: "flex", justifyContent: "center", marginTop: "1rem" }}>
                        <Spinner animation="border" style={{ color: "white" }} />
                     </div>
                  ) : (
                     <>
                        {ocrResult ? (
                           <div>
                              {ocrResult != "Текст не обнаружен на изображении" && <p style={{ color: "rgba(255, 255, 255, 0.55)", margin: "1rem 0 0 1rem" }}>Found text:</p>}
                              <div style={{
                                 display: "flex",
                                 color: "white",
                                 width: "400px",
                                 border: "1px solid rgb(33, 37, 41)",
                                 padding: "1rem",
                                 marginTop: "1rem"
                              }}>
                                 <FontAwesomeIcon
                                    icon={ocrResult == "Текст не обнаружен на изображении" ? faQuestion : faComment}
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
                  <p style={{
                     color: "rgba(255, 255, 255, 0.55)",
                     margin: 0,
                     textAlign: "center"
                  }}>
                     <FontAwesomeIcon icon={faFaceFrown} /> You must be logged in to use this.
                  </p>
               </div>
            )}
         </PageContainer>
      </PageWrapper>
   );
};

export default Main;
