import React, { FC, useState, useEffect } from "react";
import { PageWrapper, PageContainer } from "../Page.styled.ts";
import "./Auth.css";

import { Form, Button, Alert } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";

import { FontAwesomeIcon, FontAwesomeIconProps } from "@fortawesome/react-fontawesome";
import { faFaceSadTear, faFaceLaugh, faLaugh } from "@fortawesome/free-solid-svg-icons";

import axios from "axios";

const AuthPage: FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");

  const [message, setMessage] = useState<{
    text: string;
    variant: string;
    icon?: FontAwesomeIconProps["icon"];
  } | null>(null);
  const [isFadingOut, setIsFadingOut] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const API_URL = import.meta.env.VITE_API_URL;

    try {
      if (isLogin) {
        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);

        const response = await axios.post(`${API_URL}/token`, formData, {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        });

        localStorage.setItem("token", response.data.access_token);
        localStorage.setItem("username", username);

        setMessage({
          text: "Login successful!",
          variant: "success",
          icon: faFaceLaugh,
        });
        window.dispatchEvent(new Event("loggedIn"));
      } else {
        await axios.post(`${API_URL}/register`, { name: username, password });

        setMessage({
          text: "Successfully registered!",
          variant: "success",
          icon: faFaceLaugh,
        });
        setIsLogin(true);
      }

      setPassword("");
      setUsername("");
    } catch (error: any) {
      let errorText = isLogin ? "Login failed." : "Registration failed.";

      if (
        isLogin &&
        error.response &&
        error.response.status === 403 &&
        typeof error.response.data.detail === "string" &&
        error.response.data.detail.startsWith("User is blocked")
      ) {
        errorText = "You are blocked!";
      }

      setMessage({
        text: errorText,
        variant: "danger",
        icon: faFaceSadTear,
      });
    }
  };

  useEffect(() => {
    if (message) {
      const fadeOutTimer = setTimeout(() => setIsFadingOut(true), 3000);
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
        <Form onSubmit={handleSubmit} style={{ width: "300px" }}>
          <Form.Group controlId='formUsername' className='mb-3'>
            <Form.Control
              className='FormPlaceholder'
              style={{
                backgroundColor: "rgb(33, 37, 41)",
                color: "white",
                border: "none",
              }}
              type='text'
              placeholder='Enter username'
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </Form.Group>
          <Form.Group controlId='formPassword' className='mb-3'>
            <Form.Control
              className='FormPlaceholder'
              style={{
                backgroundColor: "rgb(33, 37, 41)",
                color: "white",
                border: "none",
              }}
              type='password'
              placeholder='Enter password'
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Form.Group>
          <Button className='w-100' variant='dark' type='submit'>
            {isLogin ? "Log in" : "Create an account"}
          </Button>
          {message && (
            <Alert
              style={{
                opacity: isFadingOut ? 0 : 1,
                height: isFadingOut ? 0 : "43px",
                padding: isFadingOut ? 0 : "8px",
                marginTop: "16px",
                textAlign: "center",
                marginBottom: 0,
                overflow: "hidden",
                transition: "opacity 1s ease-in-out, height 1s ease-in-out, padding 1s ease-in-out",
                backgroundColor: message.variant == "success" ? "rgb(40, 167, 69)" : "rgb(220, 53, 69)",
                color: "white",
                border: "rgb(33, 37, 41) 1px solid",
              }}
            >
              {message.icon && <FontAwesomeIcon icon={message.icon} style={{ marginRight: "6px" }} />}
              {message.text}
            </Alert>
          )}
          <p style={{ color: "grey", textAlign: "center", marginTop: "12px" }}>
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <span
              style={{
                color: "rgb(87, 165, 204)",
                textDecoration: "none",
                cursor: "pointer",
              }}
              onClick={() => setIsLogin(!isLogin)}
            >
              {isLogin ? "Create one!" : "Log in!"}
            </span>
          </p>
        </Form>
      </PageContainer>
    </PageWrapper>
  );
};

export default AuthPage;
