import React, { useRef, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import SyntaxHighlighter from "react-syntax-highlighter";
import Markdown from "react-markdown";
import { VscArrowDown, VscArrowUp } from "react-icons/vsc";
import { useTranslation } from "react-i18next";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";
import { Textarea } from "@nextui-org/react";
import { RootState } from "#/store";
import { Cell, appendJupyterInput } from "#/state/jupyterSlice";
import { useScrollToBottom } from "#/hooks/useScrollToBottom";
import { I18nKey } from "#/i18n/declaration";
import { createJupyterCode } from "#/services/chatService";
import { useWsClient } from "#/context/ws-client-provider";


interface IJupyterCell {
  cell: Cell;
}

function JupyterCell({ cell }: IJupyterCell): JSX.Element {
  const code = cell.content;

  if (cell.type === "input") {
    return (
      <div className="rounded-lg bg-gray-800 dark:bg-gray-900 p-2 text-xs">
        <div className="mb-1 text-gray-400">EXECUTE</div>
        <pre
          className="scrollbar-custom scrollbar-thumb-gray-500 hover:scrollbar-thumb-gray-400 dark:scrollbar-thumb-white/10 dark:hover:scrollbar-thumb-white/20 overflow-auto px-5"
          style={{ padding: 0, marginBottom: 0, fontSize: "0.75rem" }}
        >
          <SyntaxHighlighter
            language="python"
            style={atomOneDark}
            wrapLongLines
          >
            {code}
          </SyntaxHighlighter>
        </pre>
      </div>
    );
  }

  // aggregate all the NON-image lines into a single plaintext.
  const lines: { type: "plaintext" | "image"; content: string }[] = [];
  let current = "";
  for (const line of code.split("\n")) {
    if (line.startsWith("![image](data:image/png;base64,")) {
      lines.push({ type: "plaintext", content: current });
      lines.push({ type: "image", content: line });
      current = "";
    } else {
      current += `${line}\n`;
    }
  }
  lines.push({ type: "plaintext", content: current });

  return (
    <div className="rounded-lg bg-gray-800 dark:bg-gray-900 p-2 text-xs">
      <div className="mb-1 text-gray-400">STDOUT/STDERR</div>
      <pre
        className="scrollbar-custom scrollbar-thumb-gray-500 hover:scrollbar-thumb-gray-400 dark:scrollbar-thumb-white/10 dark:hover:scrollbar-thumb-white/20 overflow-auto px-5 max-h-[60vh] bg-gray-800"
        style={{ padding: 0, marginBottom: 0, fontSize: "0.75rem" }}
      >
        {/* display the lines as plaintext or image */}
        {lines.map((line, index) => {
          if (line.type === "image") {
            return (
              <div key={index}>
                <Markdown urlTransform={(value: string) => value}>
                  {line.content}
                </Markdown>
              </div>
            );
          }
          return (
            <div key={index}>
              <SyntaxHighlighter language="plaintext" style={atomOneDark}>
                {line.content}
              </SyntaxHighlighter>
            </div>
          );
        })}
      </pre>
    </div>
  );
}

interface JupyterEditorProps {
  maxWidth: number;
}

function JupyterEditor({ maxWidth }: JupyterEditorProps) {
  const { t } = useTranslation();
  const dispatch = useDispatch();

  const { send } = useWsClient();
  const { cells } = useSelector((state: RootState) => state.jupyter);
  const jupyterRef = React.useRef<HTMLDivElement>(null);

  const { hitBottom, scrollDomToBottom, onChatBodyScroll } =
    useScrollToBottom(jupyterRef);

  const [inputValue, setInputValue] = useState("");

  const handleInputSubmit = () => {
    if (inputValue.trim()) {
      dispatch(appendJupyterInput(inputValue));
      send(createJupyterCode(inputValue));
      setInputValue("");
    }
  };
  const onKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault(); // prevent a new line
      handleInputSubmit();
    }
  };

  let jupyterEditor = (
    <div className="flex-1" style={{ maxWidth, height: "85%" }}>
      <div
        className="overflow-y-auto h-full max-h-[85%] scrollbar-custom scrollbar-thumb-gray-500 hover:scrollbar-thumb-gray-400 dark:scrollbar-thumb-white/10 dark:hover:scrollbar-thumb-white/20"
        ref={jupyterRef}
        onScroll={(e) => onChatBodyScroll(e.currentTarget)}
      >
        {cells.map((cell, index) => (
          <JupyterCell key={index} cell={cell} />
        ))}
      </div>
      {!hitBottom && (
        <div className="sticky bottom-10 flex items-center justify-center">
          <button
            type="button"
            className="relative border-1 text-sm rounded px-3 py-1 border-neutral-600 bg-neutral-700 cursor-pointer select-none"
          >
            <span className="flex items-center" onClick={scrollDomToBottom}>
              <VscArrowDown className="inline mr-2 w-3 h-3" />
              <span className="inline-block" onClick={scrollDomToBottom}>
                {t(I18nKey.CHAT_INTERFACE$TO_BOTTOM)}
              </span>
            </span>
          </button>
        </div>
      )}
    </div>
  );
  jupyterEditor = (
    <div className="JupyterEditor" style={{ height: "100%", position: "relative" }}>
      {jupyterEditor}
      <div
        className="sticky bottom-0 flex p-1 "
        onKeyDown={onKeyPress}
        style={{ bottom: 0, position: "sticky", width: "100%" }}
      >
        <Textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={onKeyPress}
          placeholder="Enter Python code here..."
          className="p-1"
          classNames={{
            inputWrapper: "bg-neutral-700 border border-neutral-600 rounded-lg",
            input: "pr-16 text-neutral-400",
          }}
          maxRows={10}
          minRows={1}
          variant="bordered"
        />
        <button
          type="button"
          onClick={handleInputSubmit}
          className="p-2 bg-blue-600 text-white rounded-r"
          aria-label="Run"
        >
          <VscArrowUp size={25} />
        </button>
      </div>
    </div>
  );
  return jupyterEditor;
}

export default JupyterEditor;
