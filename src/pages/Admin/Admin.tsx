import { FC, useState, useEffect } from "react";
import { PageWrapper, PageContainer } from "../Page.styled.ts";
import "./Admin.css";

import { Spinner, Alert, Button, Form, Pagination } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFaceFrown, faUser, faUserTie, faCheck, faXmark, faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons";

const API_URL = import.meta.env.VITE_API_URL;

interface User {
   name: string;
   password: string;
   role: string;
   subscription_status: string;
}

const Admin: FC = () => {
   const [loading, setLoading] = useState(false);
   const [isLoggedIn, setIsLoggedIn] = useState(false);

   const [errorMessage, setErrorMessage] = useState<string | null>(null);
   const [users, setUsers] = useState<User[]>([]);

   const [searchTerm, setSearchTerm] = useState<string>("");

   const [currentPage, setCurrentPage] = useState(1);
   const [usersPerPage] = useState(5);

   useEffect(() => {
      const fetchCurrentUser = async () => {
         const token = localStorage.getItem("token");
         if (!token) {
            setIsLoggedIn(false);
            return;
         }

         const response = await fetch(`${API_URL}/users/me`, {
            headers: {
               Authorization: `Bearer ${token}`,
            },
         });

         if (response.ok) {
            const data = await response.json();

            if (data.role === "admin") {
               setIsLoggedIn(true);
            } else {
               setIsLoggedIn(false);
            }
         } else {
            setIsLoggedIn(false);
         }
      };

      fetchCurrentUser();

      const handleLogOutUpdate = () => setIsLoggedIn(false);
      window.addEventListener("loggedOut", handleLogOutUpdate);
      return () => window.removeEventListener("loggedOut", handleLogOutUpdate);
   }, []);

   useEffect(() => {
      const fetchUsers = async () => {
         setLoading(true);
         try {
            const response = await fetch(`${API_URL}/users`, {
               headers: {
                  Authorization: `Bearer ${localStorage.getItem("token")}`,
               },
            });
            if (!response.ok) {
               throw new Error("Error while receiving data.");
            }
            const data = await response.json();
            setUsers(data);
         } catch (error) {
            setErrorMessage("Failed to load users.");
         } finally {
            setLoading(false);
         }
      };
      fetchUsers();
   }, []);

   const handleSubscriptionUpdate = async (username: string, currentStatus: string) => {
      const newStatus = currentStatus === "active" ? "inactive" : "active";
      try {
         const response = await fetch(`${API_URL}/update_subscription/${username}`, {
            method: "PUT",
            headers: {
               "Content-Type": "application/json",
               Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
            body: JSON.stringify({
               subscription_status: newStatus,
            }),
         });

         if (!response.ok) {
            throw new Error("Error updating subscription.");
         }

         setUsers((prevUsers) =>
            prevUsers.map((user) => (user.name === username ? { ...user, subscription_status: newStatus } : user)),
         );
      } catch (error) {
         setErrorMessage("Failed to update subscription status.");
      }
   };

   const filteredUsers = users.filter((user) => user.name.toLowerCase().includes(searchTerm.toLowerCase()));

   const indexOfLastUser = currentPage * usersPerPage;
   const indexOfFirstUser = indexOfLastUser - usersPerPage;
   const currentUsers = filteredUsers.slice(indexOfFirstUser, indexOfLastUser);

   const paginate = (pageNumber: number) => setCurrentPage(pageNumber);

   const pageNumbers = [];
   for (let i = 1; i <= Math.ceil(filteredUsers.length / usersPerPage); i++) {
      pageNumbers.push(i);
   }

   return (
      <PageWrapper>
         <PageContainer
            style={{
               width: "600px",
            }}
         >
            {isLoggedIn ? (
               <div style={{ width: "100%" }}>
                  <div
                     style={{
                        display: "flex",
                        justifyContent: "space-between",
                     }}
                  >
                     <div
                        style={{
                           display: "flex",
                           alignItems: "center",
                           marginBottom: "20px",
                        }}
                     >
                        <FontAwesomeIcon
                           style={{
                              fontSize: "140%",
                              color: "rgb(33, 37, 41)",
                              marginRight: "12px",
                           }}
                           icon={faMagnifyingGlass}
                        />
                        <Form.Control
                           className='FormPlaceholder'
                           type='text'
                           id='inputUserName'
                           placeholder='Enter username'
                           value={searchTerm}
                           onChange={(e) => setSearchTerm(e.target.value)}
                           style={{
                              width: "auto",
                              minWidth: "200px",
                              backgroundColor: "rgb(33, 37, 41)",
                              border: "1px solid rgb(33, 37, 41)",
                              color: "white",
                              display: "inline-block",
                           }}
                        />
                     </div>
                  </div>
                  <div style={{ display: "flex", width: "100%", gap: "20px" }}>
                     <div style={{ width: "100%" }}>
                        {loading ? (
                           <Spinner animation='border' />
                        ) : errorMessage ? (
                           <Alert variant='danger'>{errorMessage}</Alert>
                        ) : (
                           <>
                              {currentUsers.map((user) => (
                                 <div
                                    style={{
                                       display: "flex",
                                       justifyContent: "space-between",
                                       border: "1px solid rgb(33, 37, 41)",
                                       borderRadius: "8px",
                                       alignItems: "center",
                                       padding: "8px",
                                       marginBottom: "12px",
                                       color: "white",
                                    }}
                                 >
                                    <div
                                       style={{
                                          display: "flex",
                                          alignItems: "center",
                                       }}
                                    >
                                       <FontAwesomeIcon
                                          style={{
                                             fontSize: "185%",
                                             color: "rgba(255, 255, 255, 0.55)",
                                             marginRight: "12px",
                                          }}
                                          icon={user.role == "user" ? faUser : faUserTie}
                                       />
                                       <div>
                                          <p style={{ margin: 0 }}>{user.name}</p>
                                          <p
                                             style={{
                                                margin: 0,
                                                fontSize: "70%",
                                                color: "rgba(255, 255, 255, 0.55)",
                                             }}
                                          >
                                             {user.role}
                                          </p>
                                       </div>
                                    </div>
                                    <div
                                       style={{
                                          display: "flex",
                                       }}
                                    >
                                       <p
                                          style={{
                                             margin: 0,
                                             fontSize: "80%",
                                             color: "rgba(255, 255, 255, 0.55)",
                                             width: "80px",
                                             textAlign: "right",
                                             marginRight: "8px",
                                          }}
                                       >
                                          Subscription status:{" "}
                                       </p>
                                       <Button
                                          variant={user.subscription_status == "active" ? "success" : "danger"}
                                          style={{
                                             width: "40px",
                                          }}
                                          onClick={() => handleSubscriptionUpdate(user.name, user.subscription_status)}
                                       >
                                          <FontAwesomeIcon
                                             style={{
                                                fontSize: "115%",
                                             }}
                                             icon={user.subscription_status == "active" ? faCheck : faXmark}
                                          />
                                       </Button>
                                    </div>
                                 </div>
                              ))}
                              {pageNumbers.length > 1 && (
                                 <Pagination>
                                    <Pagination.Prev
                                       onClick={() => currentPage > 1 && setCurrentPage(currentPage - 1)}
                                    />
                                    {pageNumbers.map((number) => (
                                       <Pagination.Item
                                          key={number}
                                          active={number === currentPage}
                                          onClick={() => paginate(number)}
                                       >
                                          {number}
                                       </Pagination.Item>
                                    ))}
                                    <Pagination.Next
                                       onClick={() =>
                                          currentPage < pageNumbers.length && setCurrentPage(currentPage + 1)
                                       }
                                    />
                                 </Pagination>
                              )}
                           </>
                        )}
                     </div>
                  </div>
               </div>
            ) : (
               <p style={{ color: "rgba(255, 255, 255, 0.55)", textAlign: "center" }}>
                  <FontAwesomeIcon icon={faFaceFrown} /> You must be logged in as admin to use this.
               </p>
            )}
         </PageContainer>
      </PageWrapper>
   );
};

export default Admin;
