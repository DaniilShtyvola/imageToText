import React, { useEffect, useState } from "react";
import "../Modal.css";

import { Modal } from "react-bootstrap";

import { faCalendarPlus, faCalendarDay, faUser, faClock, faChartLine } from "@fortawesome/free-solid-svg-icons";

import ModalInfoField from "../ModalInfoField/ModalInfoField";

type UserAnalytics = {
  username: string;
  registered_at: string;
  last_login: string;
  session_duration: number;
  activity_last_30_days: number;
};

type UserAnalyticsModalProps = {
  username: string;
  showModal: boolean;
  handleClose: () => void;
};

const UserAnalyticsModal: React.FC<UserAnalyticsModalProps> = ({ username, showModal, handleClose }) => {
  const [analyticsData, setAnalyticsData] = useState<UserAnalytics | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const fetchUserAnalytics = async () => {
    setLoading(true);

    const API_URL = import.meta.env.VITE_API_URL;

    try {
      const response = await fetch(`${API_URL}/analytics/${username}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) {
        throw new Error("Error while receiving user analytics.");
      }

      const data = await response.json();
      setAnalyticsData(data);
    } catch (error) {
      setErrorMessage("Failed to load user analytics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (username) {
      fetchUserAnalytics();
    }
  }, [username]);

  const formatMinutes = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    return `${minutes} minute${minutes !== 1 ? "s" : ""}`;
  };

  if (loading) {
    return (
      <Modal show={showModal} onHide={handleClose}>
        <Modal.Header>
          <Modal.Title>Loading...</Modal.Title>
        </Modal.Header>
        <Modal.Body>Loading user analytics...</Modal.Body>
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
        {analyticsData ? (
          <div>
            <ModalInfoField caption={"Username:"} text={analyticsData.username} icon={faUser} />
            <ModalInfoField
              caption={"Registered at:"}
              text={new Date(analyticsData.registered_at).toLocaleString()}
              icon={faCalendarPlus}
            />
            <ModalInfoField
              caption={"Last Login:"}
              text={new Date(analyticsData.last_login).toLocaleString()}
              icon={faCalendarDay}
            />
            <ModalInfoField
              caption={"Session Duration:"}
              text={`${formatMinutes(analyticsData.session_duration)}`}
              icon={faClock}
            />
            <ModalInfoField
              caption={"Activity in Last 30 Days:"}
              text={`${analyticsData.activity_last_30_days}`}
              icon={faChartLine}
            />
          </div>
        ) : (
          <p>No analytics data available.</p>
        )}
      </Modal.Body>
    </Modal>
  );
};

export default UserAnalyticsModal;
