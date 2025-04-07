import { FC, useState, useEffect, useRef } from "react";
import { PageWrapper, PageContainer } from "../Page.styled.ts";

import { Spinner, Button, Image, Alert, Modal } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFaceFrown, faShareFromSquare, faComment, faQuestion } from "@fortawesome/free-solid-svg-icons";

const Main: FC = () => {
   const fileInputRef = useRef<HTMLInputElement | null>(null);
   const [loading, setLoading] = useState(false);
   const [isLoggedIn, setIsLoggedIn] = useState(false);

   const [image, setImage] = useState<string | null>(null);
   const [ocrResult, setOcrResult] = useState<string | null>(null);
   const [uploadCount, setUploadCount] = useState(0);

   const [errorMessage, setErrorMessage] = useState<string | null>(null);
   const [showModal, setShowModal] = useState(false);

   const username = localStorage.getItem("username");

   useEffect(() => {
      const token = localStorage.getItem("token");
      if (token) {
         setIsLoggedIn(true);
      }

      const handleLogOutUpdate = () => setIsLoggedIn(false);
      window.addEventListener("loggedOut", handleLogOutUpdate);
      return () => window.removeEventListener("loggedOut", handleLogOutUpdate);
   }, []);

   const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      if (!loading && event.target.files && event.target.files[0]) {
         const file = event.target.files[0];
         const reader = new FileReader();
         reader.onloadend = () => setImage(reader.result as string);
         reader.readAsDataURL(file);

         setOcrResult("");
      }
   };

   const handleImageClick = () => fileInputRef.current?.click();

   const checkSubscription = async (): Promise<boolean> => {
      if (!username) {
         console.error("No username found!");
         return false;
      }

      const API_URL = import.meta.env.VITE_API_URL;

      const url = `${API_URL}/subscription_status/${username}`;
      console.log(`Check subscription: ${url}`);

      try {
         const response = await fetch(url, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
         });

         console.log("HTTP status:", response.status);
         const text = await response.text();
         console.log("Answer server:", text);

         if (!response.ok) throw new Error(`Error HTTP ${response.status}`);

         const data = JSON.parse(text);
         return data.subscription_status === "active";
      } catch (error) {
         console.error("Subscription verification error:", error);
         return false;
      }
   };

   const handleSendImage = async () => {
      if (!image) return;
      if (!username) {
         setErrorMessage("Error: Username not found");
         return;
      }

      setLoading(true);
      setErrorMessage(null);

      const isSubscribed = await checkSubscription();

      if (!isSubscribed) {
         if (uploadCount >= 2) {
            setShowModal(true);
            setLoading(false);
            return;
         }
         setUploadCount(uploadCount + 1);
      }

      try {
         const AI_API_URL = import.meta.env.VITE_AI_API_URL;
         const base64Image = image.split(",")[1];

         const fullUrl = `${AI_API_URL}/ocr/base64/detailed`;
         console.log("Send image to:", fullUrl);

         const response = await fetch(fullUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ base64_image: base64Image }),
         });

         const text = await response.text();
         console.log("Answer AI API:", text);

         if (!response.ok) throw new Error(`Error AI API: ${response.status}`);

         const data = JSON.parse(text);
         setOcrResult(data.full_text);
      } catch (error) {
         console.error("Error sending image:", error);
         setOcrResult("");
      } finally {
         setLoading(false);
      }
   };

   const handleBuySubscription = () => {
      window.open("https://bank.gov.ua/ua/about/support-the-armed-forces", "_blank");
   };

   return (
      <PageWrapper>
         <PageContainer>
            {isLoggedIn ? (
               <div>
                  {errorMessage && (
                     <Alert variant='danger' onClose={() => setErrorMessage(null)} dismissible>
                        {errorMessage}
                     </Alert>
                  )}
                  <div
                     style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "1rem",
                     }}
                  >
                     <p style={{ color: "rgba(255, 255, 255, 0.55)", margin: 0 }}>Selected image:</p>
                     <Button variant='success' disabled={image == null || loading} onClick={handleSendImage}>
                        <FontAwesomeIcon icon={faShareFromSquare} style={{ marginRight: "6px" }} />
                        Send image
                     </Button>
                  </div>
                  <input
                     type='file'
                     accept='image/*'
                     ref={fileInputRef}
                     onChange={handleImageChange}
                     style={{ display: "none" }}
                  />
                  <div onClick={handleImageClick}>
                     {image ? (
                        <Image
                           src={image}
                           style={{
                              cursor: "pointer",
                              width: "400px",
                              objectFit: "cover",
                              marginTop: 0,
                           }}
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
                              cursor: "pointer",
                              fontSize: "120%",
                           }}
                        >
                           <p>
                              <FontAwesomeIcon icon={faFaceFrown} /> No image selected
                           </p>
                        </div>
                     )}
                  </div>
                  {loading && (
                     <div
                        style={{
                           display: "flex",
                           justifyContent: "center",
                           marginTop: "1rem",
                        }}
                     >
                        <Spinner animation='border' style={{ color: "white" }} />
                     </div>
                  )}
                  {ocrResult && !loading && (
                     <div
                        style={{
                           color: "white",
                           border: "1px solid rgb(33, 37, 41)",
                           width: "400px",
                           padding: "1rem",
                           marginTop: "1rem",
                           display: "flex",
                        }}
                     >
                        <FontAwesomeIcon
                           icon={ocrResult === "Текст не обнаружен на изображении" ? faQuestion : faComment}
                           style={{
                              marginRight: "6px",
                              color: "rgba(255, 255, 255, 0.55)",
                              fontSize: "150%",
                           }}
                        />
                        <p style={{ marginBottom: 0 }}>{ocrResult}</p>
                     </div>
                  )}
               </div>
            ) : (
               <p style={{ color: "rgba(255, 255, 255, 0.55)", textAlign: "center" }}>
                  <FontAwesomeIcon icon={faFaceFrown} /> You must be logged in to use this.
               </p>
            )}

            <Modal show={showModal} onHide={() => setShowModal(false)}>
               <Modal.Header closeButton>
                  <Modal.Title>Subscription</Modal.Title>
               </Modal.Header>
               <Modal.Body>
                  You have reached your limit of 2 downloads. To continue, please purchase a subscription{" "}
               </Modal.Body>
               <Modal.Footer>
                  <Button variant='secondary' onClick={() => setShowModal(false)}>
                     Close
                  </Button>
                  <Button variant='primary' onClick={handleBuySubscription}>
                     Buy subscription
                  </Button>
               </Modal.Footer>
            </Modal>
         </PageContainer>
      </PageWrapper>
   );
};

export default Main;
