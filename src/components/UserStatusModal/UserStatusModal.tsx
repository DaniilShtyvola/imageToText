import React, { useEffect, useState } from "react";
import { Modal, Button, Form } from "react-bootstrap";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faUser,
  faCommentDots,
  faClock,
  faHammer,
  faLock,
  faUnlock,
  faComment,
} from "@fortawesome/free-solid-svg-icons";

import ModalInfoField from "../ModalInfoField/ModalInfoField";
import "../Modal.css";

type User = {
  username: string;
  is_blocked: boolean;
  block_reason: string;
  blocked_by: string;
  blocked_at: string;
};

type UserStatusModalProps = {
  username: string;
  showModal: boolean;
  handleClose: () => void;
};

const UserStatusModal: React.FC<UserStatusModalProps> = ({ username, showModal, handleClose }) => {
  const [user, setBlockedUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const [reason, setReason] = useState<string>("");

  const fetchBlockedUser = async () => {
    setLoading(true);

    const API_URL = import.meta.env.VITE_API_URL;

    try {
      const response = await fetch(`${API_URL}/blocked_user/${username}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) {
        throw new Error("Error while receiving user User.");
      }

      const data = await response.json();
      setBlockedUser(data);
    } catch (error) {
      setErrorMessage("Failed to load user User.");
    } finally {
      setLoading(false);
    }
  };

  const handleBlockUser = async (username: string, is_blocked: boolean) => {
    const API_URL = import.meta.env.VITE_API_URL;

    try {
      const response = await fetch(`${API_URL}/block_user/${username}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          is_blocked: !is_blocked,
          block_reason: reason != "" ? reason : null,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to update user block status.");
      }

      const event = new CustomEvent("blockedUserEvent");
      window.dispatchEvent(event);

      handleClose();
    } catch (error) {
      setErrorMessage("Failed to update user block status.");
    }
  };

  useEffect(() => {
    if (username) {
      fetchBlockedUser();
    }
  }, [username]);

  if (loading) {
    return (
      <Modal show={showModal} onHide={handleClose}>
        <Modal.Header>
          <Modal.Title>Loading...</Modal.Title>
        </Modal.Header>
        <Modal.Body>Loading user User...</Modal.Body>
      </Modal>
    );
  }

  if (errorMessage) {
    return (
      <Modal show={showModal} onHide={handleClose}>
        <Modal.Header>
          <Modal.Title>Error</Modal.Title>
        </Modal.Header>
        <Modal.Body>{errorMessage}</Modal.Body>
      </Modal>
    );
  }

  return (
    <Modal show={showModal} onHide={handleClose}>
      <Modal.Body>
        {user ? (
          <div>
            <p style={{ margin: 0, fontSize: "120%" }}>
              This user is currently
              <span
                style={{
                  color: user.is_blocked ? "rgb(220, 53, 69)" : "rgb(25, 135, 84)",
                  fontWeight: "700",
                }}
              >
                {" "}
                {user.is_blocked ? "blocked!" : "not blocked!"}
              </span>
            </p>
            <ModalInfoField caption={"Username:"} text={user.username} icon={faUser} />
            {user.is_blocked ? (
              <>
                <ModalInfoField caption={"Block reason:"} text={user.block_reason} icon={faComment} />
                <ModalInfoField caption={"Blocked by:"} text={user.blocked_by} icon={faHammer} />
                <ModalInfoField
                  caption={"Blocked at:"}
                  text={new Date(user.blocked_at).toLocaleString()}
                  icon={faClock}
                />
              </>
            ) : (
              <></>
            )}
          </div>
        ) : (
          <p>No User data available.</p>
        )}
      </Modal.Body>
      {user ? (
        <Modal.Footer>
          {!user.is_blocked ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                flex: 1,
              }}
            >
              <FontAwesomeIcon
                style={{
                  fontSize: "140%",
                  color: "rgb(33, 37, 41)",
                  marginRight: "12px",
                }}
                icon={faCommentDots}
              />
              <Form.Control
                className='FormPlaceholder'
                type='text'
                id='inputReason'
                placeholder='Enter reason'
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                style={{
                  width: "100%",
                  backgroundColor: "rgb(33, 37, 41)",
                  border: "1px solid rgb(33, 37, 41)",
                  color: "white",
                  paddingLeft: "10px",
                }}
              />
            </div>
          ) : (
            <></>
          )}
          <Button
            style={{
              width: "40px",
              marginLeft: "8px",
              height: "40.79px",
            }}
            variant='dark'
            onClick={() => handleBlockUser(user.username, user.is_blocked)}
          >
            <FontAwesomeIcon
              style={{
                fontSize: "115%",
                color: user.is_blocked ? "rgb(220, 53, 69)" : "rgb(25, 135, 84)",
              }}
              icon={user.is_blocked ? faLock : faUnlock}
            />
          </Button>
        </Modal.Footer>
      ) : (
        <></>
      )}
    </Modal>
  );
};

export default UserStatusModal;
