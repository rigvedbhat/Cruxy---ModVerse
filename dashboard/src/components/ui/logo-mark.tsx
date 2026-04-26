import React from "react";

type LogoMarkProps = {
  className?: string;
};

function LogoMark({ className = "" }: LogoMarkProps) {
  return (
    <span className={`inline-flex items-center text-2xl font-bold ${className}`}>
      <span className="text-white">Sero</span>
      <span className="text-[#5865F2]">mod</span>
    </span>
  );
}

export default LogoMark;
