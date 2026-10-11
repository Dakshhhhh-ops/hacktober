import { useEffect, useState } from "react";

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    // The Clipboard API is missing on some pages (for example file://); use a hidden field.
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.append(field);
    field.select();
    const ok = document.execCommand("copy");
    field.remove();
    return ok;
  }
}

export default function CopyButton({ text, label = "Copy", className = "" }) {
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!message) return undefined;
    const timer = setTimeout(() => setMessage(""), 1600);
    return () => clearTimeout(timer);
  }, [message]);

  async function handleClick() {
    setMessage((await copyText(text)) ? "Copied" : "Copy failed");
  }

  return (
    <button className={"chip " + className} type="button" onClick={handleClick}>
      <span aria-live="polite">{message || label}</span>
    </button>
  );
}
