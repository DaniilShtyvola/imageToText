import { FC, useState, useEffect } from "react";
import { PageWrapper, PageContainer } from "../Page.styled.ts";
import "./Admin.css";

import { Spinner, Alert, Button, Form, Pagination } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";

import { jwtDecode } from "jwt-decode";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faFaceFrown,
  faUser,
  faUserTie,
  faCheck,
  faXmark,
  faMagnifyingGlass,
  faInfo,
} from "@fortawesome/free-solid-svg-icons";

import UserInfoModal from "../../components/UserInfoModal/UserInfoModal.tsx";
import GoogleChart from "../../components/GoogleChart/GoogleChart.tsx";

const API_URL = "http://127.0.0.1:8000";

interface User {
  name: string;
  password: string;
  role: string;
  subscription_status: string;
}

interface UserAnalytics {
  username: string;
  registered_at: string;
  last_login: string;
  session_duration: number | null;
  activity_last_30_days: number;
}

const Admin: FC = () => {
  const [loading, setLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [analytics, setAnalytics] = useState<UserAnalytics[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [currentPage, setCurrentPage] = useState(1);
  const [showUserModal, setShowUserModal] = useState(false);
  const [selectedUsername, setSelectedUsername] = useState<string | null>(null);
  const usersPerPage = 6;

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      const decoded: any = jwtDecode(token);
      setIsLoggedIn(decoded.role === "admin");
    }
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
        const data = await response.json();
        setUsers(data);
      } catch (error) {
        setErrorMessage("Failed to load users.");
      } finally {
        setLoading(false);
      }
    };

    const fetchAnalytics = async () => {
      try {
        const response = await fetch(`${API_URL}/analytics`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        });
        const data = await response.json();
        setAnalytics(data);
      } catch (error) {
        setErrorMessage("Failed to load analytics.");
      }
    };

    fetchUsers();
    fetchAnalytics();
  }, []);

  const handleSubscriptionUpdate = async (username: string, currentStatus: string) => {
    const newStatus = currentStatus === "active" ? "inactive" : "active";
    try {
      await fetch(`${API_URL}/update_subscription/${username}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ subscription_status: newStatus }),
      });
      setUsers((prev) =>
        prev.map((user) =>
          user.name === username ? { ...user, subscription_status: newStatus } : user
        )
      );
    } catch {
      setErrorMessage("Failed to update subscription status.");
    }
  };

  const filteredUsers = users.filter((user) =>
    user.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const indexOfLastUser = currentPage * usersPerPage;
  const indexOfFirstUser = indexOfLastUser - usersPerPage;
  const currentUsers = filteredUsers.slice(indexOfFirstUser, indexOfLastUser);

  const pageNumbers = Array.from(
    { length: Math.ceil(filteredUsers.length / usersPerPage) },
    (_, i) => i + 1
  );

  return (
    <PageWrapper>
      <PageContainer>
        {isLoggedIn ? (
          <div style={{ width: "100%", display: "flex", gap: "18px" }}>
            <div style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <Form.Control
                  className="FormPlaceholder"
                  type="text"
                  placeholder="Enter username"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{ minWidth: "200px", backgroundColor: "#212529", color: "white" }}
                />
              </div>
              {loading ? (
                <Spinner animation="border" />
              ) : errorMessage ? (
                <Alert variant="danger">{errorMessage}</Alert>
              ) : (
                <>
                  {currentUsers.map((user) => (
                    <div
                      key={user.name}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        border: "1px solid #212529",
                        borderRadius: "8px",
                        padding: "8px",
                        marginBottom: "12px",
                        color: "white",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center" }}>
                        <FontAwesomeIcon
                          icon={user.role === "user" ? faUser : faUserTie}
                          style={{ fontSize: "185%", marginRight: "12px", color: "#ccc" }}
                        />
                        <div>
                          <p style={{ margin: 0 }}>{user.name}</p>
                          <p style={{ margin: 0, fontSize: "70%", color: "#aaa" }}>{user.role}</p>
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <Button
                          variant={user.subscription_status === "active" ? "success" : "danger"}
                          onClick={() => handleSubscriptionUpdate(user.name, user.subscription_status)}
                        >
                          <FontAwesomeIcon icon={user.subscription_status === "active" ? faCheck : faXmark} />
                        </Button>
                        <Button variant="dark" onClick={() => {
                          setSelectedUsername(user.name);
                          setShowUserModal(true);
                        }}>
                          <FontAwesomeIcon icon={faInfo} />
                        </Button>
                      </div>
                    </div>
                  ))}

                  {pageNumbers.length > 1 && (
                    <Pagination className="justify-content-center">
                      <Pagination.Prev onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))} />
                      {pageNumbers.map((number) => (
                        <Pagination.Item
                          key={number}
                          active={number === currentPage}
                          onClick={() => setCurrentPage(number)}
                        >
                          {number}
                        </Pagination.Item>
                      ))}
                      <Pagination.Next
                        onClick={() =>
                          setCurrentPage((prev) =>
                            prev < pageNumbers.length ? prev + 1 : prev
                          )
                        }
                      />
                    </Pagination>
                  )}
                </>
              )}
            </div>
            <div style={{ width: "100%" }}>
              <GoogleChart data={analytics} />
            </div>
          </div>
        ) : (
          <p style={{ color: "#aaa", textAlign: "center" }}>
            <FontAwesomeIcon icon={faFaceFrown} /> You must be logged in as admin to use this.
          </p>
        )}

        {selectedUsername && (
          <UserInfoModal
            username={selectedUsername}
            showModal={showUserModal}
            handleClose={() => {
              setShowUserModal(false);
              setSelectedUsername(null);
            }}
          />
        )}
      </PageContainer>
    </PageWrapper>
  );
};

export default Admin;