import { FC, useState, useEffect, useRef } from 'react';
import {
   PageWrapper,
   PageContainer
} from '../Page.styled.ts';

import { Spinner, Button, Image, Alert } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faFaceFrown, faShareFromSquare, faComment } from '@fortawesome/free-solid-svg-icons';

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

   const checkSubscription = async (token: string): Promise<boolean> => {
      try {
         const response = await fetch(`${API_URL}/users/subscription_status`, {
            method: 'GET',
            headers: {
               'Authorization': `Bearer ${token}`,
               'Content-Type': 'application/json',
            },
         });

         // Проверка на успешный ответ
         if (!response.ok) {
            console.error(`HTTP error! Status: ${response.status}`);
            // Логируем текст ошибки для дальнейшего анализа
            const errorText = await response.text();
            console.error('Error response body:', errorText);
            throw new Error(`HTTP error! Status: ${response.status}`);
         }

         // Пробуем распарсить ответ как JSON
         const data = await response.json();

         // Проверяем полученные данные
         console.log('Subscription status:', data);

         return data.subscription_status === 'active'; // или другой статус, если в ответе строка "active"
      } catch (error) {
         console.error('Error checking subscription:', error);
         return false; // Вернем false, если произошла ошибка
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
      if (!isSubscribed) {
         setLoading(false);
         setErrorMessage("Your subscription is inactive. Please renew it to use this feature.");
         return;
      }

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
