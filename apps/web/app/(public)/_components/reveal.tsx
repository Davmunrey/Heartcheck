"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * Scroll-reveal wrapper (Apple-style fade-up). Adds the `.in` class when the
 * element enters the viewport; CSS in globals.css does the easing. Respects
 * prefers-reduced-motion (the CSS no-ops there). `once` keeps it revealed.
 */
export function Reveal({
  children,
  className = "",
  variant = "reveal",
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  variant?: "reveal" | "reveal reveal-scale" | "stagger";
  as?: "div" | "section" | "ul" | "header";
}) {
  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setShown(true);
            io.disconnect();
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -10% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const Comp = Tag as "div";
  return (
    <Comp ref={ref as never} className={`${variant} ${shown ? "in" : ""} ${className}`}>
      {children}
    </Comp>
  );
}
