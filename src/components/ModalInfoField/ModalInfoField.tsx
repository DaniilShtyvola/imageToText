import React from "react";

import { FontAwesomeIcon, FontAwesomeIconProps } from "@fortawesome/react-fontawesome";

type ModalInfoFieldProps = {
  caption: string;
  text: string;
  icon: FontAwesomeIconProps["icon"];
};

const ModalInfoField: React.FC<ModalInfoFieldProps> = ({ caption, text, icon }) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
      }}
    >
      <FontAwesomeIcon
        style={{
          fontSize: "140%",
          color: "rgb(76, 80, 85)",
          marginRight: "8px",
        }}
        icon={icon}
      />
      <div>
        <span
          style={{
            color: "rgb(100, 105, 111)",
            fontSize: "70%",
          }}
        >
          {caption}
        </span>
        <p
          style={{
            margin: 0,
            top: "-6px",
            left: "1px",
            position: "relative",
          }}
        >
          {text}
        </p>
      </div>
    </div>
  );
};

export default ModalInfoField;
