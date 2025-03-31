import styled from "styled-components";

export const PageHeaderWrapper = styled.div`
   width: 100%;
   display: flex;
   justify-content: center;
   background-color: rgb(23, 25, 27);
   height: 8vh;
   padding-top: 2vh;
`;

export const HeaderContainer = styled.div`
   display: flex;
   width: 1120px;
   justify-content: space-between;
   align-items: center;

   svg {
      margin-left: 18px;
      font-size: 90%;
   }
`;
