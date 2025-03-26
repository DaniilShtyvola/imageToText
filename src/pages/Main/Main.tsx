import { FC, useState, useEffect } from 'react';
import {
   PageWrapper,
   PageContainer
} from '../Page.styled.ts';

import { Spinner, Pagination, Button, Form, InputGroup, Alert } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCheck } from '@fortawesome/free-solid-svg-icons'

interface MarketProps { }

const Market: FC<MarketProps> = () => {
   const [loading, setLoading] = useState(false);

   const [message, setMessage] = useState<{ text: string, variant: string } | null>(null);
   const [isFadingOut, setIsFadingOut] = useState(false);

   useEffect(() => {
      if (message) {
         const fadeOutTimer = setTimeout(() => {
            setIsFadingOut(true);
         }, 3000);

         const removeMessageTimer = setTimeout(() => {
            setMessage(null);
            setIsFadingOut(false);
         }, 4000);

         return () => {
            clearTimeout(fadeOutTimer);
            clearTimeout(removeMessageTimer);
         };
      }
   }, [message]);

   return (
      <PageWrapper>
         <PageContainer>
            {loading ? (
               <div className="d-flex justify-content-center align-items-center" style={{ height: "400px" }}>
                  <Spinner animation="border" style={{ color: "white" }} />
               </div>
            ) : (
               <div>

               </div>
            )}
         </PageContainer>
      </PageWrapper>
   );
};

export default Market;
