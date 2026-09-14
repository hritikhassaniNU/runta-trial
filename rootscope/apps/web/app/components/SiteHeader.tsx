"use client";

import { useEffect, useState } from "react";

export function SiteHeader() {
  const [apiUp, setApiUp] = useState<boolean | null>(null);

  useEffect(() => {
    void fetch("/health", { cache: "no-store" })
      .then((response) => setApiUp(response.ok))
      .catch(() => setApiUp(false));
  }, []);

  return (
    <header className="topbar">
      <a className="brand" href="/">
        <strong>RootScope</strong>
        <span className="brand-sub">incident intelligence</span>
      </a>
      <div className="topbar-meta">
        <span
          className={
            apiUp === false ? "status-dot bad" : apiUp ? "status-dot ok" : "status-dot"
          }
        >
          {apiUp === false ? "API down" : apiUp ? "API up" : "API…"}
        </span>
        <span className="topbar-product">agent workspace</span>
      </div>
    </header>
  );
}
