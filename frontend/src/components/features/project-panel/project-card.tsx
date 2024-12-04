import React from "react";
import { formatTimeDelta } from "#/utils/format-time-delta";
import { DeleteButton } from "./delete-button";
import { ProjectRepoLink } from "./project-repo-link";
import { ProjectState, ProjectStateIndicator } from "./project-state-indicator";

interface ProjectCardProps {
  onClick: () => void;
  onDelete: () => void;
  onChangeTitle: (title: string) => void;
  name: string;
  repo: string | null;
  lastUpdated: string; // ISO 8601
  state?: ProjectState;
}

export function ProjectCard({
  onClick,
  onDelete,
  onChangeTitle,
  name,
  repo,
  lastUpdated,
  state = "cold",
}: ProjectCardProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleBlur = () => {
    if (inputRef.current?.value) {
      const trimmed = inputRef.current.value.trim();
      onChangeTitle(trimmed);
      inputRef.current!.value = trimmed;
    } else {
      // reset the value if it's empty
      inputRef.current!.value = name;
    }
  };

  const handleInputClick = (event: React.MouseEvent<HTMLInputElement>) => {
    event.stopPropagation();
  };

  const handleDelete = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    onDelete();
  };

  return (
    <div
      data-testid="project-card"
      onClick={onClick}
      className="h-[100px] w-full px-[18px] py-4 border-b border-neutral-600"
    >
      <div className="flex items-center justify-between">
        <input
          ref={inputRef}
          data-testid="project-card-title"
          onClick={handleInputClick}
          onBlur={handleBlur}
          type="text"
          defaultValue={name}
          className="text-sm leading-6 font-semibold bg-transparent"
        />

        <div className="flex items-center gap-2">
          <ProjectStateIndicator state={state} />
          <DeleteButton onClick={handleDelete} />
        </div>
      </div>
      {repo && (
        <ProjectRepoLink repo={repo} onClick={(e) => e.stopPropagation()} />
      )}
      <p className="text-xs text-neutral-400">
        <time>{formatTimeDelta(new Date(lastUpdated))} ago</time>
      </p>
    </div>
  );
}