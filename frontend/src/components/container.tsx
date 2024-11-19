import { NavLink } from "@remix-run/react";
import clsx from "clsx";
import React from "react";
import { IoIosArrowUp, IoIosArrowDown } from "react-icons/io";
import IconButton from "./IconButton";

function BetaBadge() {
  return (
    <span className="text-[11px] leading-5 text-root-primary bg-neutral-400 px-1 rounded-xl">
      Beta
    </span>
  );
}

interface ContainerProps {
  label?: string;
  labels?: {
    label: string;
    to: string;
    icon?: React.ReactNode;
    isBeta?: boolean;
  }[];
  children: React.ReactNode;
  className?: React.HTMLAttributes<HTMLDivElement>["className"];
}

export function Container({
  label,
  labels,
  children,
  className,
}: ContainerProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(false);

  const handleCollapse = () => {
    const workspace = document.querySelector(".workspace")?.parentElement as HTMLDivElement;
    const terminal = document.querySelector(".Terminal")?.parentElement as HTMLDivElement;
    if (workspace && terminal) {
      workspace.style.height = "100%";
      if (!isCollapsed) {
        terminal.style.height = "22.9px";
      } else {
        terminal.style.height = "50%";
      }
      setIsCollapsed(!isCollapsed);
    }
  };
  return (
    <div
      className={clsx(
        "bg-neutral-800 border border-neutral-600 rounded-xl flex flex-col",
        className,
      )}
    >
      {labels && (
        <div className="flex text-xs h-[36px] workspace">
          {labels.map(({ label: l, to, icon, isBeta }) => (
            <NavLink
              end
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  "px-2 border-b border-r border-neutral-600 bg-root-primary flex-1",
                  "first-of-type:rounded-tl-xl last-of-type:rounded-tr-xl last-of-type:border-r-0",
                  "flex items-center gap-2",
                  isActive && "bg-root-secondary",
                )
              }
            >
              {icon}
              {l}
              {isBeta && <BetaBadge />}
            </NavLink>
          ))}
        </div>
      )}
      {!labels && label && (
        <div className={"px-2 h-[36px] border-b border-neutral-600 text-xs flex items-center " + label}  >
          {label}
          {label === "Terminal" && (
            <IconButton
              onClick={handleCollapse}
              icon={isCollapsed ? <IoIosArrowUp /> : <IoIosArrowDown />}
              ariaLabel={isCollapsed ? "Open Terminal" : "Close Terminal"}
              style={{ marginLeft: "auto" }}
            />
          )}
        </div>
      )}
      <div className="overflow-auto h-full rounded-b-xl">{children}</div>
    </div>
  );
}
