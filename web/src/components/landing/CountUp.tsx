"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Counts from zero to `value` the first time it scrolls into view, then stays there.
 * With reduced motion, or before it is seen, it simply shows the final value.
 */
export function CountUp({ value, format }: { value: number; format: (value: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState<number | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frame = 0;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();
        const start = performance.now();
        const tick = (now: number) => {
          const progress = Math.min((now - start) / 900, 1);
          const eased = 1 - (1 - progress) ** 3;
          setShown(progress < 1 ? value * eased : null);
          if (progress < 1) frame = requestAnimationFrame(tick);
        };
        frame = requestAnimationFrame(tick);
      },
      { threshold: 0.4 },
    );
    observer.observe(node);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [value]);

  return (
    <span ref={ref} aria-label={format(value)}>
      <span aria-hidden="true">{format(shown ?? value)}</span>
    </span>
  );
}
