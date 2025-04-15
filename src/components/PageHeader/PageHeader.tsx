import { FC, useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { PageHeaderWrapper, HeaderContainer } from "./PageHeader.styled.ts";

import { Container, Navbar, Nav, Dropdown } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";

import { useNavigate } from "react-router-dom";
import { jwtDecode } from "jwt-decode";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faRightToBracket,
  faRightFromBracket,
  faImage,
  faScrewdriverWrench,
  faMessage,
  faLanguage,
  faFont,
  faStarHalfStroke,
} from "@fortawesome/free-solid-svg-icons";

interface PageHeaderProps {}

const PageHeader: FC<PageHeaderProps> = () => {
  const [nickname, setNickname] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const navigate = useNavigate();

  const handleLoginUpdate = () => {
    const token = localStorage.getItem("token");

    if (!token) {
      setIsAdmin(false);
      setNickname(null);
      return;
    }

    try {
      const decoded: any = jwtDecode(token);

      const userRole = decoded.role;
      const userName = decoded.sub;

      if (userRole === "admin") {
        setIsAdmin(true);
      } else {
        setIsAdmin(false);
      }

      setNickname(userName);
    } catch (error) {
      console.error("Error decoding token:", error);
      setIsAdmin(false);
      setNickname(null);
    }
  };

  useEffect(() => {
    handleLoginUpdate();
    window.addEventListener("loggedIn", handleLoginUpdate);

    return () => {
      window.removeEventListener("loggedIn", handleLoginUpdate);
    };
  }, []);

  const handleLogOut = () => {
    localStorage.removeItem("token");
    window.dispatchEvent(new Event("loggedOut"));
    setNickname(null);
    setIsAdmin(false);
    navigate("/");
  };

  return (
    <PageHeaderWrapper>
      <HeaderContainer>
        <Navbar bg='dark' data-bs-theme='dark' style={{ width: "100%", borderRadius: "12px" }}>
          <Container>
            <Navbar.Brand style={{ userSelect: "none" }}>
              <span
                style={{
                  position: "relative",
                  top: "0px",
                  fontWeight: "700",
                  marginRight: "2px",
                }}
              >
                OCR
              </span>
              <FontAwesomeIcon
                style={{
                  fontSize: "110%",
                }}
                icon={faImage}
              />
              <FontAwesomeIcon
                icon={faMessage}
                style={{
                  fontSize: "80%",
                  position: "relative",
                  top: "-10px",
                  left: "-4px",
                  backgroundColor: "rgb(33, 37, 41)",
                  paddingLeft: "3px",
                  borderRadius: "6px",
                }}
              />
              <FontAwesomeIcon
                icon={faFont}
                style={{
                  fontSize: "60%",
                  position: "relative",
                  top: "-13px",
                  left: "-17px",
                  color: "rgb(33, 37, 41)",
                  borderRadius: "6px",
                }}
              />
            </Navbar.Brand>
            <Nav className='me-auto'>
              {!nickname && (
                <Nav.Link as={Link} to='/login' style={{ paddingRight: "22px" }}>
                  <FontAwesomeIcon icon={faRightToBracket} /> Log in
                </Nav.Link>
              )}
              {nickname && (
                <>
                  <Nav.Link as={Link} to='/image-to-text' style={{ paddingRight: "32px" }}>
                    <FontAwesomeIcon icon={faImage} /> Image to Text
                  </Nav.Link>
                  <Nav.Link as={Link} to='/translate-text' style={{ paddingRight: "32px" }}>
                    <FontAwesomeIcon icon={faLanguage} /> Translate Text
                  </Nav.Link>
                  <Nav.Link as={Link} to='/rate-the-review' style={{ paddingRight: "32px" }}>
                    <FontAwesomeIcon icon={faStarHalfStroke} style={{ position: "relative", top: "-1px" }} /> Rate the
                    Review
                  </Nav.Link>
                  {isAdmin && (
                    <Nav.Link as={Link} to='/admin' style={{ paddingRight: "22px" }}>
                      <FontAwesomeIcon icon={faScrewdriverWrench} /> Admin Panel
                    </Nav.Link>
                  )}
                </>
              )}
            </Nav>
            {nickname && (
              <Navbar.Collapse className='justify-content-end'>
                <Dropdown align='end' style={{ marginRight: "18px" }}>
                  <Dropdown.Toggle
                    as='div'
                    style={{
                      cursor: "pointer",
                      color: "white",
                      display: "inline-block",
                      width: "60px",
                      padding: "4px 14px",
                      position: "absolute",
                      left: "-28px",
                      top: "-2px",
                    }}
                  ></Dropdown.Toggle>
                  <span style={{ color: "white" }}>{nickname}</span>
                  <Dropdown.Menu
                    variant='dark'
                    style={{
                      padding: "4px",
                      marginTop: "-33px",
                      right: "-11.5px",
                    }}
                  >
                    <p
                      style={{
                        paddingRight: "6px",
                        textAlign: "end",
                        paddingTop: "4px",
                      }}
                    >
                      Logged in as: <span style={{ fontWeight: "700" }}>{nickname}</span>
                    </p>
                    <Dropdown.Item
                      style={{
                        borderRadius: "4px",
                        paddingRight: "6px",
                        textAlign: "end",
                      }}
                      onClick={() => handleLogOut()}
                    >
                      Sign out <FontAwesomeIcon style={{ marginLeft: "4px" }} icon={faRightFromBracket} />
                    </Dropdown.Item>
                  </Dropdown.Menu>
                </Dropdown>
              </Navbar.Collapse>
            )}
          </Container>
        </Navbar>
      </HeaderContainer>
    </PageHeaderWrapper>
  );
};

export default PageHeader;
