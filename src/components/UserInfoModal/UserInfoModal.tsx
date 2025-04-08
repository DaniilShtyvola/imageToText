import React, { useEffect, useState } from 'react';
import { Modal } from 'react-bootstrap';

import { FontAwesomeIcon, FontAwesomeIconProps } from "@fortawesome/react-fontawesome";
import { faCalendarPlus, faCalendarDay, faUser, faClock, faChartLine } from "@fortawesome/free-solid-svg-icons";

import './UserInfoModal.css';

type UserAnalytics = {
    username: string;
    registered_at: string;
    last_login: string;
    session_duration: number;
    activity_last_30_days: number;
};

type UserInfoModalProps = {
    username: string;
    showModal: boolean;
    handleClose: () => void;
};

const API_URL = import.meta.env.VITE_API_URL;

type UserInfoProps = {
    caption: string;
    text: string;
    icon: FontAwesomeIconProps['icon'];
};

const UserInfo: React.FC<UserInfoProps> = ({ caption, text, icon }) => {
    return (
        <div style={{
            display: "flex",
            alignItems: "center"
        }}>
            <FontAwesomeIcon
                style={{
                    fontSize: "140%",
                    color: "rgb(76, 80, 85)",
                    marginRight: "8px"
                }}
                icon={icon}
            />
            <div>
                <span style={{
                    color: "rgb(100, 105, 111)",
                    fontSize: "70%"
                }}>{caption}</span>
                <p style={{
                    margin: 0,
                    top: "-6px",
                    left: "1px",
                    position: "relative"
                }}>{text}</p>
            </div>
        </div>
    );
}

const UserInfoModal: React.FC<UserInfoModalProps> = ({ username, showModal, handleClose }) => {
    const [analyticsData, setAnalyticsData] = useState<UserAnalytics | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>('');

    const fetchUserAnalytics = async () => {
        setLoading(true);

        try {
            const response = await fetch(`${API_URL}/analytics/${username}`, {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('token')}`,
                },
            });

            if (!response.ok) {
                throw new Error('Error while receiving user analytics.');
            }

            const data = await response.json();
            setAnalyticsData(data);
        } catch (error) {
            setErrorMessage('Failed to load user analytics.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (username) {
            fetchUserAnalytics();
        }
    }, [username]);

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
            <Modal.Header>
                <Modal.Title>Analytics for {analyticsData?.username}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                {analyticsData ? (
                    <div>
                        <UserInfo caption={"Username:"} text={analyticsData.username} icon={faUser}/>
                        <UserInfo caption={"Registered at:"} text={new Date(analyticsData.registered_at).toLocaleString()} icon={faCalendarPlus}/>
                        <UserInfo caption={"Last Login:"} text={new Date(analyticsData.last_login).toLocaleString()} icon={faCalendarDay}/>
                        <UserInfo caption={"Session Duration:"} text={`${analyticsData.session_duration}`} icon={faClock}/>
                        <UserInfo caption={"Activity in Last 30 Days:"} text={`${analyticsData.activity_last_30_days}`} icon={faChartLine}/>
                    </div>
                ) : (
                    <p>No analytics data available.</p>
                )}
            </Modal.Body>
        </Modal>
    );
};

export default UserInfoModal;